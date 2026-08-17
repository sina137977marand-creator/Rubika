# -*- coding: utf-8 -*-
import database as db
from utils import areply, safe_name
from handlers.moderation import _get_target_from_reply
from handlers.ui import title


async def increase_balance_command(bot, message, amount_text: str):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن، مثلاً: افزایش موجودی 500")
        return
    amount_text = amount_text.strip()
    if not amount_text.isdigit():
        await areply(message, "مقدار رو به‌صورت عدد بنویس. مثال: افزایش موجودی 500")
        return
    amount = int(amount_text)
    new_balance = db.change_balance(message.chat_id, target, amount)
    name = await safe_name(bot, target, group_id=message.chat_id)
    await areply(
        message,
        f"{title('افزایش موجودی', '💰')}\n"
        f"مبلغ {amount} به موجودی {name} اضافه شد.\n"
        f"موجودی فعلی: {new_balance}",
    )


async def decrease_balance_command(bot, message, amount_text: str):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات.")
        return
    target = await _get_target_from_reply(bot, message)
    if not target:
        await areply(message, "روی پیام کاربر مورد نظر ریپلای کن، مثلاً: کسر موجودی 500")
        return
    amount_text = amount_text.strip()
    if not amount_text.isdigit():
        await areply(message, "مقدار رو به‌صورت عدد بنویس. مثال: کسر موجودی 500")
        return
    amount = int(amount_text)
    new_balance = db.change_balance(message.chat_id, target, -amount)
    name = await safe_name(bot, target, group_id=message.chat_id)
    await areply(
        message,
        f"{title('کسر موجودی', '💸')}\n"
        f"مبلغ {amount} از موجودی {name} کسر شد.\n"
        f"موجودی فعلی: {new_balance}",
    )


async def balance_command(bot, message):
    balance = db.get_balance(message.chat_id, message.sender_id)
    name = await safe_name(bot, message.sender_id, group_id=message.chat_id)
    await areply(message, f"{title('موجودی شما', '💳')}\n👤 {name}\n💰 موجودی دقیق: {balance}")
