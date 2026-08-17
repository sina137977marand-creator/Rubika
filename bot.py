# -*- coding: utf-8 -*-
"""
ربات مدیریت گروه روبیکا (با توکن رسمی، کتابخانه rubka)
اجرا: python bot.py

نکته: نسخه‌ی نصب‌شده‌ی rubka به‌صورت کامل async هست (rubka.asynco) - یعنی
هر متدی از bot یا message باید با await صدا زده بشه. کل پروژه بر همین اساس نوشته شده.
"""
import logging

from rubka import Robot, Message

import config
import database as db
from utils import is_group_chat, is_private_chat, looks_like_math_expression, areply, acall

from handlers import moderation, games, calculator, profile, economy
from handlers import group_admin_actions as gaa
from handlers import admin_panel, start

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Robot(token=config.BOT_TOKEN)

if config.BOT_TOKEN in ("", "PASTE_YOUR_BOT_TOKEN_HERE"):
    logger.error(
        "❌ توکن ربات تنظیم نشده! توی config.py مقدار BOT_TOKEN رو با توکن واقعی "
        "جایگزین کنید یا متغیر محیطی BOT_TOKEN رو ست کنید."
    )


def _split_command(text: str, keyword: str):
    """اگه متن با کلیدواژه شروع بشه، بقیه‌ی متن بعد از کلیدواژه رو برمی‌گردونه."""
    if text == keyword:
        return ""
    if text.startswith(keyword + " "):
        return text[len(keyword):].strip()
    return None


@bot.on_message()
async def router(bot: Robot, message: Message):
    try:
        await _route(bot, message)
    except Exception:
        logger.exception("خطا در پردازش پیام")


# ---------------- درخواست عضویت در گروه (best-effort) ----------------
# نکته: مستندات عمومی rubka مشخص نمی‌کنه که آیا رویدادی برای «درخواست عضویت»
# وجود داره یا نه. این بخش فقط اگه چنین قابلیتی در نسخه‌ی نصب‌شده‌ی شما موجود
# باشه فعال میشه؛ در غیر این‌صورت بی‌خطر نادیده گرفته میشه.
if hasattr(bot, "on_join_request"):
    @bot.on_join_request()
    async def _join_request_handler(bot: Robot, req):
        try:
            chat_id = getattr(req, "chat_id", None)
            user_id = getattr(req, "user_id", None) or getattr(req, "sender_id", None)
            if not chat_id or not user_id:
                return
            group = db.get_group(chat_id)
            if not group.get("auto_accept_join_requests"):
                return
            for method_name in ("approve_chat_join_request", "accept_join_request", "approve_join_request"):
                method = getattr(bot, method_name, None)
                if method:
                    await acall(method, chat_id, user_id)
                    break
        except Exception:
            logger.exception("خطا در پردازش درخواست عضویت")
else:
    logger.warning(
        "این نسخه‌ی rubka رویداد on_join_request رو نداره؛ پذیرش خودکار درخواست "
        "عضویت غیرفعال می‌مونه (تنظیمش تو پنل هست ولی عملاً کاری نمی‌کنه)."
    )


async def _route(bot: Robot, message: Message):
    text = (message.text or "").strip()
    chat_id = message.chat_id
    is_group = is_group_chat(message)

    logger.info(
        "📩 پیام جدید | chat_id=%s | is_group=%s | is_private=%s | فرستنده=%s | متن=%r",
        chat_id, is_group, is_private_chat(message), message.sender_id, text,
    )

    # ثبت فرستنده‌ی هر پیام گروه در ایندکس محلی - این تنها راه قابل‌اعتماد برای
    # پیدا کردن «فرستنده‌ی پیامی که رویش ریپلای شده» است (API رسمی جواب نمی‌ده).
    # باید همیشه اجرا بشه، حتی قبل از فیلترهای مدیریتی که ممکنه پیام رو حذف کنن.
    if is_group and message.message_id:
        db.index_message(chat_id, message.message_id, message.sender_id)

    # 1) اول فیلترهای مدیریتی گروه (ممکنه پیام رو حذف کنه)
    if is_group:
        if await moderation.moderate_message(bot, message):
            return

    # 2) فعال‌سازی (باید قبل از هر چیز دیگه چک بشه)
    if await gaa.handle_activation(bot, message):
        return

    if not text:
        return

    # 3) دستورات پی‌وی
    if is_private_chat(message):
        if await admin_panel.consume_awaiting_pv_text(bot, message):
            return
        if text in ("/start", "start", "شروع"):
            await start.start_command(bot, message)
            return
        if text in ("/help", "راهنما"):
            await start.help_command(bot, message)
            return
        if text in ("whoami", "/whoami"):
            await start.whoami_command(bot, message)
            return
        if text in ("checkjoin", "بررسی عضویت"):
            await start.checkjoin_command(bot, message)
            return
        if await admin_panel.handle_panel_shortcuts(bot, message):
            return
        if await admin_panel.dispatch_panel_text(bot, message, text):
            return
        await start.start_command(bot, message)
        return

    # 4) از اینجا به بعد فقط دستورات داخل گروه
    if not is_group:
        if text in ("/start", "start", "شروع", "/help", "راهنما"):
            logger.warning(
                "chat_id=%s نه Group تشخیص داده شد نه User/Bot - لطفاً این لاگ رو گزارش بدید.",
                chat_id,
            )
            await start.start_command(bot, message)
        return

    group = db.get_group(chat_id)
    if not group["activated"]:
        return  # گروه فعال نشده، فقط فعال‌سازی/فیلتر بالا کار می‌کنه

    # --- ثبت فعالیت کاربر + خوش‌آمدگویی به تازه‌واردها (best-effort، توضیح در README) ---
    is_new_member = db.touch_member(chat_id, message.sender_id)
    if is_new_member and group.get("welcome_enabled"):
        await _send_welcome(bot, message, group)

    if text in ("راهنما",):
        await start.help_command(bot, message)
        return

    if text in ("شناسایی", "شناسایی من"):
        from utils import safe_name
        name = await safe_name(bot, message.sender_id, group_id=message.chat_id)
        await areply(
            message,
            f"chat_id شما: {message.sender_id}\nاسمی که ربات می‌بینه: {name}",
        )
        return

    if text == "تنظیمات":
        await gaa.settings_command(bot, message)
        return

    if await gaa.handle_settings_toggle_text(bot, message):
        return

    if _split_command(text, "setwelcome") is not None:
        await gaa.setwelcome_command(bot, message, _split_command(text, "setwelcome"))
        return

    if _split_command(text, "setrules") is not None:
        await gaa.setrules_command(bot, message, _split_command(text, "setrules"))
        return

    if text == "rules" or text == "قوانین":
        await gaa.rules_command(bot, message)
        return

    if text == "بن":
        await gaa.ban_command(bot, message)
        return
    if text == "آنبن":
        await gaa.unban_command(bot, message)
        return
    if text == "سکوت" or _split_command(text, "سکوت") is not None:
        await gaa.mute_command(bot, message, _split_command(text, "سکوت") or "")
        return
    if text == "آنسکوت":
        await gaa.unmute_command(bot, message)
        return
    if text == "افزودن ادمین":
        await gaa.add_admin_command(bot, message)
        return
    if text == "حذف ادمین":
        await gaa.remove_admin_command(bot, message)
        return
    if text == "وارن":
        await moderation.warn_command(bot, message)
        return
    if text == "آنوارن":
        await moderation.unwarn_command(bot, message)
        return
    if text == "پاکسازی" or _split_command(text, "پاکسازی") is not None:
        await gaa.clean_command(bot, message, _split_command(text, "پاکسازی") or "")
        return

    # --- بازی‌ها ---
    if await games.handle_dice_text(bot, message):
        return
    if text == "کوییز":
        await games.quiz_command(bot, message)
        return
    if text == "امتیازات":
        await games.quiz_score_command(bot, message)
        return
    if text in ("حقیقت",):
        await games.truth_command(bot, message)
        return
    if text in ("جرات", "جرأت"):
        await games.dare_command(bot, message)
        return
    if text in ("جرات یا حقیقت", "جرأت یا حقیقت"):
        await games.truth_or_dare_command(bot, message)
        return
    if text in ("شیر یا خط", "شیر و خط", "شیرخط"):
        await games.coin_flip_command(bot, message)
        return

    # --- ماشین حساب (هم با دستور، هم به‌صورت خودکار) ---
    if _split_command(text, "حساب") is not None:
        await calculator.calc_command(bot, message, _split_command(text, "حساب"))
        return
    if looks_like_math_expression(text):
        await calculator.calc_command(bot, message, text)
        return

    # --- پروفایل / سرگرمی / آمار / تگ ---
    if text == "تاریخ":
        await profile.date_command(bot, message)
        return
    if text == "فال":
        await profile.fal_command(bot, message)
        return
    if _split_command(text, "فونت") is not None:
        await profile.font_command(bot, message, _split_command(text, "فونت"))
        return
    if text == "بیو" or _split_command(text, "بیو") is not None:
        await profile.bio_command(bot, message, _split_command(text, "بیو") or "")
        return
    if text == "حذف بیو":
        await profile.delete_bio_command(bot, message)
        return
    if text == "لقب" or _split_command(text, "لقب") is not None:
        await profile.title_command(bot, message, _split_command(text, "لقب") or "")
        return
    if text == "حذف لقب":
        await profile.delete_title_command(bot, message)
        return
    if text == "اصل" or _split_command(text, "اصل") is not None:
        await profile.origin_command(bot, message, _split_command(text, "اصل") or "")
        return
    if text == "حذف اصل":
        await profile.delete_origin_command(bot, message)
        return
    if text in ("آمار من", "آمار کاربر"):
        await profile.user_stats_command(bot, message)
        return
    if text == "آمار گروه":
        await profile.group_stats_command(bot, message)
        return
    if text == "تگ" or _split_command(text, "تگ") is not None:
        await profile.tag_command(bot, message, _split_command(text, "تگ") or "")
        return

    # --- اقتصاد / موجودی ---
    if text == "موجودی":
        await economy.balance_command(bot, message)
        return
    if _split_command(text, "افزایش موجودی") is not None:
        await economy.increase_balance_command(bot, message, _split_command(text, "افزایش موجودی"))
        return
    if _split_command(text, "کسر موجودی") is not None:
        await economy.decrease_balance_command(bot, message, _split_command(text, "کسر موجودی"))
        return

    # اگه کوییز فعالی باشه، شاید این پیام پاسخ به اون باشه
    if await games.try_answer_quiz(bot, message):
        return


async def _send_welcome(bot: Robot, message: Message, group: dict):
    from utils import safe_name
    from handlers.ui import title as ui_title
    name = await safe_name(bot, message.sender_id, group_id=message.chat_id)
    text_template = group.get("welcome_text") or config.DEFAULT_WELCOME_TEXT
    try:
        welcome_text = text_template.format(
            name=name, group_title=group.get("title") or "", mention=name,
        )
    except Exception:
        welcome_text = text_template
    await acall(
        bot.send_message, message.chat_id,
        f"{ui_title('به جمع ما خوش اومدی', '🎉')}\n{welcome_text}",
    )


def main():
    db.init_db()
    logger.info("ربات در حال اجراست...")
    bot.run()


if __name__ == "__main__":
    main()
