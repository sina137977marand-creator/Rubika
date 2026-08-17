# -*- coding: utf-8 -*-
import logging

import config
import database as db
from utils import (
    is_group_chat, contains_link, contains_mention,
    safe_delete, guess_message_kind, safe_name, acall, areply,
)

logger = logging.getLogger(__name__)


async def _warn_and_maybe_ban(bot, message, reason: str):
    group_id = message.chat_id
    user_id = message.sender_id
    await safe_delete(bot, group_id, message.message_id)
    count = db.add_warn(group_id, user_id)
    name = await safe_name(bot, user_id, group_id=group_id)
    if count >= config.MAX_WARN_COUNT:
        db.ban_user(group_id, user_id)
        db.reset_warn(group_id, user_id)
        await acall(
            bot.send_message, group_id,
            f"⛔️ {name} به دلیل رسیدن به سقف اخطار، پیام‌هاش دیگه در این گروه نمایش داده نمیشه.\n"
            f"(توجه: چون API رسمی روبیکا اجازه‌ی کیک واقعی نمیده، این یک «بن نرم»ه؛ "
            f"برای حذف واقعی از گروه یک ادمین باید دستی این کارو بکنه.)",
        )
    else:
        await acall(bot.send_message, group_id, f"⚠️ {name} {reason}\nاخطار: {count}/{config.MAX_WARN_COUNT}")


def _looks_like_spam(text: str) -> bool:
    stripped = (text or "").strip()
    if len(stripped) < 6:
        return False
    max_run, run = 1, 1
    for i in range(1, len(stripped)):
        if stripped[i] == stripped[i - 1]:
            run += 1
            max_run = max(max_run, run)
        else:
            run = 1
    return max_run >= 12


async def moderate_message(bot, message) -> bool:
    """
    اجرای فیلترهای گروه روی یک پیام.
    خروجی True یعنی پیام حذف/مدیریت شد و نباید هندلرهای بعدی (دستورات و...) روش اجرا بشن.
    """
    chat_id = message.chat_id
    user_id = message.sender_id
    if not is_group_chat(message):
        return False

    group = db.get_group(chat_id)
    if not group["activated"]:
        return False

    if db.is_banned(chat_id, user_id):
        await safe_delete(bot, chat_id, message.message_id)
        return True

    if db.is_muted(chat_id, user_id):
        await safe_delete(bot, chat_id, message.message_id)
        return True

    admin = db.is_group_admin(chat_id, user_id)
    db.log_message(chat_id, message.message_id)

    if admin:
        return False

    text = message.text or ""
    kind = guess_message_kind(message)

    if group["anti_forward"] and kind == "forward":
        await _warn_and_maybe_ban(bot, message, "فوروارد کردن پیام مجاز نیست.")
        return True

    if group["anti_gif"] and kind == "gif":
        await _warn_and_maybe_ban(bot, message, "ارسال گیف مجاز نیست.")
        return True

    if group["anti_photo"] and kind == "photo":
        await _warn_and_maybe_ban(bot, message, "ارسال عکس مجاز نیست.")
        return True

    if group.get("anti_sticker") and kind == "sticker":
        await _warn_and_maybe_ban(bot, message, "ارسال استیکر مجاز نیست.")
        return True

    if group.get("anti_video") and kind == "video":
        await _warn_and_maybe_ban(bot, message, "ارسال ویدیو مجاز نیست.")
        return True

    if group.get("anti_voice") and kind == "voice":
        await _warn_and_maybe_ban(bot, message, "ارسال پیام صوتی/موزیک مجاز نیست.")
        return True

    if group["anti_link"] and contains_link(text, message):
        await _warn_and_maybe_ban(bot, message, "ارسال لینک مجاز نیست.")
        return True

    if group["anti_mention"] and contains_mention(text, message):
        await _warn_and_maybe_ban(bot, message, "منشن کردن آیدی مجاز نیست.")
        return True

    if group["anti_spam"] and _looks_like_spam(text):
        await _warn_and_maybe_ban(bot, message, "این پیام به‌عنوان اسپم شناسایی شد.")
        return True

    return False


async def warn_command(bot, message):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن و «وارن» رو بفرست.")
        return
    count = db.add_warn(message.chat_id, target)
    name = await safe_name(bot, target, group_id=message.chat_id)
    if count >= config.MAX_WARN_COUNT:
        db.ban_user(message.chat_id, target)
        db.reset_warn(message.chat_id, target)
        await areply(message, f"⛔️ {name} به سقف اخطار رسید و بن (نرم) شد.")
    else:
        await areply(message, f"⚠️ {name} اخطار گرفت. ({count}/{config.MAX_WARN_COUNT})")


async def unwarn_command(bot, message):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن.")
        return
    db.reset_warn(message.chat_id, target)
    await areply(message, "✅ اخطارها پاک شد.")



async def _get_target_from_reply(bot, message):
    """
    آیدی فرستنده‌ی پیامی که رویش ریپلای شده رو برمی‌گردونه.
    تست واقعی نشون داد که message.reply_to_message_id مقدار درستی داره ولی
    bot.get_message برای گرفتن اون پیام جواب نمی‌ده (None برمی‌گردونه). پس
    خودمون هر پیام گروه رو (در bot.py، تابع index_message) ایندکس می‌کنیم و
    اینجا از همون ایندکس فرستنده رو پیدا می‌کنیم - این روش قابل‌اعتماده.
    """
    reply_id = getattr(message, "reply_to_message_id", None)
    if not reply_id:
        raw = getattr(message, "raw_data", {}) or {}
        reply_id = raw.get("reply_to_message_id") or raw.get("reply_message_id")

    if reply_id:
        sender = db.get_message_sender(message.chat_id, reply_id)
        if sender:
            return sender

    # fallback‌های best-effort (برای سازگاری با نسخه‌های احتمالی دیگر rubka)
    raw = getattr(message, "raw_data", {}) or {}
    for key in ("reply_to_message", "reply_message", "replied_message", "reply"):
        reply = raw.get(key)
        if isinstance(reply, dict):
            sender = (
                reply.get("sender_id") or reply.get("author_id")
                or reply.get("sender_guid") or reply.get("author_guid")
            )
            if sender:
                return sender

    if reply_id:
        for method_name in ("get_message", "get_messages", "get_message_by_id", "fetch_message"):
            method = getattr(bot, method_name, None)
            if not method:
                continue
            try:
                fetched = await acall(method, message.chat_id, reply_id)
                sender = _extract_sender(fetched)
                if sender:
                    return sender
            except Exception as e:
                logger.warning("تلاش برای گرفتن پیام ریپلای‌شده با %s شکست خورد: %s", method_name, e)

    logger.warning(
        "❗️ نتونستم فرستنده‌ی پیام ریپلای‌شده رو پیدا کنم (reply_id=%s). این یعنی اون پیام "
        "قبل از این‌که ربات ایندکسش کنه فرستاده شده (مثلاً قبل از فعال‌سازی یا آپدیت اخیر).",
        reply_id,
    )
    return None


def _extract_sender(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return (obj.get("sender_id") or obj.get("author_id")
                or obj.get("sender_guid") or obj.get("author_guid"))
    return getattr(obj, "sender_id", None)
