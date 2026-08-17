# -*- coding: utf-8 -*-
import database as db
import config
from utils import areply, acall
from handlers.ui import title, DIVIDER

# وضعیت "منتظر ورودی متنی" برای هر کاربر (برای گرفتن متن broadcast، guid کانال و ...)
AWAITING_STATE = {}

MENU_ITEMS = {
    "1": ("کانال‌های عضویت اجباری", "کانالها"),
    "2": ("افزودن کانال اجباری", "افزودن کانال"),
    "3": ("حذف کانال اجباری", "حذف کانال"),
    "4": ("ارسال همگانی به گروه‌ها", "همگانی گروه‌ها"),
    "5": ("ارسال همگانی به پی‌وی", "همگانی پی‌وی"),
    "6": ("ادمین‌های پنل", "ادمینها"),
    "7": ("افزودن ادمین پنل", "افزودن ادمین پنل"),
    "8": ("حذف ادمین پنل", "حذف ادمین پنل"),
    "9": ("آمار کامل ربات", "آمار"),
}


def _panel_menu_text():
    lines = [title("پنل مدیریت ربات", "🛠"), ""]
    for num, (label, cmd) in MENU_ITEMS.items():
        lines.append(f"{num}️⃣ {label} → بنویس «{cmd}»")
    lines.append(DIVIDER)
    lines.append("می‌تونی هم شماره‌ی گزینه (مثلاً «1») رو بفرستی، هم متن دستور رو مستقیم.")
    return "\n".join(lines)


_NUMBER_TO_CMD = {num: cmd for num, (label, cmd) in MENU_ITEMS.items()}


async def panel_command(bot, message):
    if not db.is_bot_admin(message.sender_id):
        await areply(message, "⛔️ شما دسترسی به پنل مدیریت ربات ندارید.")
        return
    await areply(message, _panel_menu_text())


async def handle_panel_shortcuts(bot, message) -> bool:
    """
    اجازه می‌ده کاربر به‌جای تایپ کامل دستور، فقط شماره‌ی منو رو بفرسته
    (فقط وقتی که ادمین پنل باشه و اخیراً panel رو باز کرده).
    """
    text = (message.text or "").strip()
    if text not in _NUMBER_TO_CMD:
        return False
    if not db.is_bot_admin(message.sender_id):
        return False
    real_cmd = _NUMBER_TO_CMD[text]
    return await dispatch_panel_text(bot, message, real_cmd)


async def dispatch_panel_text(bot, message, text: str) -> bool:
    """روتر دستورات متنی پنل. خروجی True یعنی این متن یه دستور پنل بود و پردازش شد."""
    sender = message.sender_id
    if text in ("panel", "پنل"):
        await panel_command(bot, message)
        return True

    if not db.is_bot_admin(sender):
        return False

    if text == "کانالها" or text == "کانال‌ها":
        await _channels_list(message)
        return True

    if text == "افزودن کانال":
        AWAITING_STATE[sender] = "addchannel"
        await areply(
            message,
            f"{title('افزودن کانال اجباری', '➕')}\n"
            "آیدی کانال و عنوان دلخواه رو بفرست، مثل:\n@mychannel عنوان کانال\n\nبرای لغو: cancel",
        )
        return True

    if text == "حذف کانال":
        AWAITING_STATE[sender] = "delchannel"
        await areply(message, "آیدی کانالی که می‌خوای حذف بشه رو بفرست.\n\nبرای لغو: cancel")
        return True

    if text == "همگانی گروه‌ها" or text == "همگانی گروها":
        AWAITING_STATE[sender] = "broadcast_groups"
        await areply(message, "📤 پیامی که می‌خوای به همه گروه‌های فعال بره رو بفرست.\n\nبرای لغو: cancel")
        return True

    if text == "همگانی پی‌وی" or text == "همگانی پیوی":
        AWAITING_STATE[sender] = "broadcast_pv"
        await areply(message, "📨 پیامی که می‌خوای به همه کاربرای پی‌وی بره رو بفرست.\n\nبرای لغو: cancel")
        return True

    if text == "ادمینها" or text == "ادمین‌ها":
        await _admins_list(message)
        return True

    if text == "افزودن ادمین پنل":
        if sender not in config.OWNER_IDS:
            await areply(message, "⛔️ فقط مالک اصلی ربات می‌تونه ادمین پنل اضافه کنه.")
            return True
        AWAITING_STATE[sender] = "addbotadmin"
        await areply(message, "chat_id کاربر مورد نظر رو بفرست.\n\nبرای لغو: cancel")
        return True

    if text == "حذف ادمین پنل":
        if sender not in config.OWNER_IDS:
            await areply(message, "⛔️ فقط مالک اصلی ربات.")
            return True
        AWAITING_STATE[sender] = "delbotadmin"
        await areply(message, "chat_id کاربری که می‌خوای حذف بشه رو بفرست.\n\nبرای لغو: cancel")
        return True

    if text == "آمار":
        await areply(message, stats_text())
        return True

    return False


async def _channels_list(message):
    channels = db.list_mandatory_channels()
    lines = [title("کانال‌های عضویت اجباری", "📢"), ""]
    if channels:
        for c in channels:
            lines.append(f"• {c['title'] or c['channel_guid']} — {c['channel_guid']}")
    else:
        lines.append("هیچ کانالی ثبت نشده.")
    lines.append("")
    lines.append("افزودن: «افزودن کانال»  |  حذف: «حذف کانال»")
    await areply(message, "\n".join(lines))


async def _admins_list(message):
    admins = db.list_bot_admins()
    lines = [title("ادمین‌های پنل", "👮"), ""]
    lines.extend(f"• {a}" for a in admins) if admins else lines.append("کسی ثبت نشده.")
    lines.append("")
    lines.append("افزودن: «افزودن ادمین پنل»  |  حذف: «حذف ادمین پنل»  (فقط مالک اصلی)")
    await areply(message, "\n".join(lines))


def stats_text():
    groups = db.list_activated_groups()
    all_groups = db.list_all_known_groups()
    pv_users = db.list_pv_users()
    return (
        f"{title('آمار کامل ربات', '📊')}\n"
        f"🔵 گروه‌های فعال‌شده: {len(groups)}\n"
        f"⚪️ کل گروه‌هایی که ربات عضوشونه: {len(all_groups)}\n"
        f"🟢 کاربران پی‌وی: {len(pv_users)}"
    )


async def consume_awaiting_pv_text(bot, message) -> bool:
    """
    اگه ادمین پنل منتظر ورودی متنی باشه (broadcast، افزودن کانال و ...)، این تابع
    پیام بعدی‌ش رو مصرف می‌کنه. خروجی True یعنی پیام مصرف شد.
    """
    sender = message.sender_id
    action = AWAITING_STATE.get(sender)
    if not action:
        return False
    if not db.is_bot_admin(sender):
        AWAITING_STATE.pop(sender, None)
        return False

    text = (message.text or "").strip()
    if text == "cancel":
        AWAITING_STATE.pop(sender, None)
        await areply(message, "لغو شد.")
        return True

    AWAITING_STATE.pop(sender, None)

    if action == "addchannel":
        parts = text.split(maxsplit=1)
        if not parts:
            await areply(message, "فرمت نامعتبر بود، دوباره تلاش کن: panel")
            return True
        guid = parts[0]
        ch_title = parts[1] if len(parts) > 1 else guid
        db.add_mandatory_channel(guid, ch_title)
        await areply(message, f"✅ کانال {ch_title} اضافه شد.")
        return True

    if action == "delchannel":
        db.remove_mandatory_channel(text)
        await areply(message, "✅ کانال حذف شد.")
        return True

    if action == "broadcast_groups":
        targets = [g["group_id"] for g in db.list_activated_groups()]
        sent, failed = 0, 0
        for chat_id in targets:
            try:
                await acall(bot.send_message, chat_id, text)
                sent += 1
            except Exception:
                failed += 1
        await areply(message, f"✅ ارسال همگانی به گروه‌ها تمام شد.\nموفق: {sent} | ناموفق: {failed}")
        return True

    if action == "broadcast_pv":
        targets = db.list_pv_users()
        sent, failed = 0, 0
        for chat_id in targets:
            try:
                await acall(bot.send_message, chat_id, text)
                sent += 1
            except Exception:
                failed += 1
        await areply(message, f"✅ ارسال همگانی به کاربران پی‌وی تمام شد.\nموفق: {sent} | ناموفق: {failed}")
        return True

    if action == "addbotadmin":
        if sender not in config.OWNER_IDS:
            return True
        db.add_bot_admin(text)
        await areply(message, "✅ ادمین پنل اضافه شد.")
        return True

    if action == "delbotadmin":
        if sender not in config.OWNER_IDS:
            return True
        db.remove_bot_admin(text)
        await areply(message, "✅ ادمین پنل حذف شد.")
        return True

    return True
