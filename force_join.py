# -*- coding: utf-8 -*-
import config
import database as db
from utils import acall


async def missing_channels(bot, user_chat_id: str, scope: str = "pv"):
    if scope == "pv" and not config.FORCE_JOIN_IN_PV:
        return []
    if scope == "group" and not config.FORCE_JOIN_IN_GROUPS:
        return []

    channels = db.list_mandatory_channels()
    missing = []
    for ch in channels:
        try:
            joined = await acall(bot.check_join, ch["channel_guid"], user_chat_id)
            if not joined:
                missing.append(ch)
        except Exception:
            # اگه چک عضویت خطا داد (مثلاً ربات ادمین کانال نیست) به نفع کاربر عبور می‌کنیم
            continue
    return missing


def build_join_text(missing):
    lines = ["برای استفاده از ربات، ابتدا عضو کانال(های) زیر بشو و بعد دوباره پیام بده:"]
    for ch in missing:
        title = ch["title"] or ch["channel_guid"]
        lines.append(f"• {title} — {ch['channel_guid']}")
    return "\n".join(lines)
