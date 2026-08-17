# -*- coding: utf-8 -*-
import time

import config
import database as db
from utils import is_group_chat, safe_delete, safe_name, areply, acall
from handlers.moderation import _get_target_from_reply
from handlers.ui import title

TOGGLE_FIELDS = {
    "anti_link": "🔗 قفل لینک",
    "anti_forward": "↪️ حذف فوروارد",
    "anti_gif": "🎞 حذف گیف",
    "anti_photo": "🖼 حذف عکس",
    "anti_sticker": "😀 حذف استیکر",
    "anti_video": "🎬 حذف ویدیو",
    "anti_voice": "🎙 حذف صدا/موزیک",
    "anti_mention": "🆔 حذف آیدی/منشن",
    "anti_spam": "🚫 ضد اسپم متنی",
    "welcome_enabled": "👋 خوش‌آمدگویی",
    "auto_accept_join_requests": "✅ پذیرش خودکار درخواست عضویت",
}


async def handle_activation(bot, message) -> bool:
    text = (message.text or "").strip()
    if text not in config.ACTIVATION_KEYWORDS:
        return False
    if not is_group_chat(message):
        return True

    group = db.get_group(message.chat_id)
    if group["activated"]:
        await areply(message, "✅ ربات از قبل در این گروه فعاله.\nبرای تنظیمات: تنظیمات")
        return True

    db.update_group(message.chat_id, activated=1)
    db.set_group_owner(message.chat_id, message.sender_id)
    db.set_group_activated_at(message.chat_id)
    name = await safe_name(bot, message.sender_id, group_id=message.chat_id)
    db.add_group_admin(message.chat_id, message.sender_id, name)
    await areply(
        message,
        f"{title('فعال‌سازی موفق', '💎')}\n"
        "ربات با موفقیت در این گروه فعال شد و شما به‌عنوان «مالک گروه» ثبت شدید! 👑\n\n"
        "🔸 تنظیمات: تنظیمات\n"
        "🔸 راهنمای کامل: راهنما",
    )
    return True


async def settings_command(bot, message):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات به تنظیمات دسترسی دارن.")
        return
    group = db.get_group(message.chat_id)
    if not group["activated"]:
        await areply(message, "ربات هنوز در این گروه فعال نشده. یک ادمین باید بفرسته: فعالسازی")
        return
    await _send_settings_text(message, group)


async def _send_settings_text(message, group):
    lines = [title("تنظیمات گروه", "⚙️"), ""]
    for field, label in TOGGLE_FIELDS.items():
        state = "🟢 روشن" if group.get(field) else "🔴 خاموش"
        lines.append(f"{label} ← {state}")
    lines.append("")
    lines.append("برای روشن/خاموش کردن بنویس:")
    lines.append("تنظیم <نام> روشن   یا   تنظیم <نام> خاموش")
    lines.append("")
    lines.append("نام‌ها: لینک، فوروارد، گیف، عکس، استیکر، ویدیو، صدا، منشن، اسپم، خوشامد، عضویت")
    lines.append("مثال: تنظیم لینک روشن")
    await areply(message, "\n".join(lines))


_FIELD_ALIASES = {
    "لینک": "anti_link", "فوروارد": "anti_forward", "گیف": "anti_gif",
    "عکس": "anti_photo", "منشن": "anti_mention", "اسپم": "anti_spam",
    "خوشامد": "welcome_enabled",
    "استیکر": "anti_sticker", "ویدیو": "anti_video", "صدا": "anti_voice",
    "عضویت": "auto_accept_join_requests",
}


async def handle_settings_toggle_text(bot, message) -> bool:
    text = (message.text or "").strip()
    if not text.startswith("تنظیم "):
        return False
    if not db.is_group_admin(message.chat_id, message.sender_id):
        return False
    parts = text.split()
    if len(parts) != 3 or parts[1] not in _FIELD_ALIASES or parts[2] not in ("روشن", "خاموش"):
        return False
    field = _FIELD_ALIASES[parts[1]]
    db.update_group(message.chat_id, **{field: 1 if parts[2] == "روشن" else 0})
    group = db.get_group(message.chat_id)
    await areply(message, f"✅ «{parts[1]}» {parts[2]} شد.\n")
    await _send_settings_text(message, group)
    return True


async def setwelcome_command(bot, message, text: str):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    if not text.strip():
        await areply(message, "متن پیام خوش‌آمدگویی رو بعد از دستور بنویس.\nمتغیرها: {name} {group_title}")
        return
    db.update_group(message.chat_id, welcome_text=text.strip())
    await areply(message, "✅ متن خوش‌آمدگویی به‌روزرسانی شد.")


async def setrules_command(bot, message, text: str):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    if not text.strip():
        await areply(message, "متن قوانین رو بعد از دستور بنویس.")
        return
    db.update_group(message.chat_id, rules_text=text.strip())
    await areply(message, "✅ قوانین گروه به‌روزرسانی شد.")


async def rules_command(bot, message):
    group = db.get_group(message.chat_id)
    await areply(message, group.get("rules_text") or "قوانینی ثبت نشده.")


async def ban_command(bot, message):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن و «بن» رو بفرست.")
        return
    db.ban_user(message.chat_id, target)
    name = await safe_name(bot, target, group_id=message.chat_id)
    await areply(
        message,
        f"{title('بن نرم', '⛔️')}\n"
        f"{name} بن شد؛ از الان پیام‌هاش تو گروه خودکار حذف میشه.\n\n"
        "ℹ️ برای اخراج واقعی از گروه، یک ادمین باید دستی این کارو تو اپ روبیکا انجام بده.",
    )


async def unban_command(bot, message):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن.")
        return
    db.unban_user(message.chat_id, target)
    await areply(message, "✅ بن (نرم) کاربر برداشته شد.")


async def mute_command(bot, message, minutes_arg: str = ""):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن و «سکوت [دقیقه]» رو بفرست.")
        return
    minutes = 10
    if minutes_arg.strip().isdigit():
        minutes = int(minutes_arg.strip())
    until = int(time.time()) + minutes * 60
    db.mute_user(message.chat_id, target, until)
    name = await safe_name(bot, target, group_id=message.chat_id)
    await areply(message, f"🔇 {name} به مدت {minutes} دقیقه سکوت شد.")


async def unmute_command(bot, message):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن.")
        return
    db.unmute_user(message.chat_id, target)
    await areply(message, "🔊 سکوت کاربر برداشته شد.")


async def add_admin_command(bot, message):
    if not db.is_group_owner(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط مالک گروه می‌تونه ادمین ربات اضافه کنه.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن و «افزودن ادمین» رو بفرست.")
        return
    name = await safe_name(bot, target, group_id=message.chat_id)
    db.add_group_admin(message.chat_id, target, name)
    await areply(message, f"⭐️ {name} به ادمین‌های ربات در این گروه اضافه شد.")


async def remove_admin_command(bot, message):
    if not db.is_group_owner(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط مالک گروه.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن.")
        return
    db.remove_group_admin(message.chat_id, target)
    await areply(message, "✅ از ادمین‌های ربات حذف شد.")


async def clean_command(bot, message, count_arg: str = ""):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    chat_id = message.chat_id
    count = config.MAX_CLEAN_MESSAGES
    if count_arg.strip().isdigit():
        count = int(count_arg.strip())
    ids = db.get_recent_message_ids(chat_id, count)
    deleted = 0
    for mid in ids:
        if await safe_delete(bot, chat_id, mid):
            deleted += 1
    db.clear_recent_messages(chat_id)
    await acall(
        bot.send_message, chat_id,
        f"🧹 پاکسازی انجام شد. ({deleted}/{len(ids)} پیام حذف شد)\n"
        "توجه: اگه عدد کمتر از انتظار بود، یعنی API اجازه‌ی حذف بعضی پیام‌های قدیمی/دیگران رو نداده.",
    )
