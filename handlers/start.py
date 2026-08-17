# -*- coding: utf-8 -*-
import database as db
from force_join import missing_channels, build_join_text
from utils import is_private_chat
from handlers.ui import title, DIVIDER

HELP_TEXT = f"""{title('راهنمای کامل دستورات', '📖')}

🔓 <b>فعال‌سازی</b>
▫️ من رو ادمین گروه کن، بعد یک ادمین بگه: فعالسازی
▫️ تنظیمات — نمایش و تغییر تنظیمات گروه
▫️ شناسایی — دیدن chat_id و اسمی که ربات از تو می‌بینه (برای رفع اشکال)

{DIVIDER}
🛡 <b>مدیریت</b> (نسخه نرم)
▫️ بن (ریپلای) / آنبن (ریپلای)
▫️ سکوت [دقیقه] (ریپلای) / آنسکوت (ریپلای)
▫️ افزودن ادمین (ریپلای) / حذف ادمین (ریپلای) — فقط مالک گروه
▫️ وارن (ریپلای) / آنوارن (ریپلای)
▫️ پاکسازی [تعداد]

{DIVIDER}
🎲 <b>سرگرمی</b>
▫️ تاس یا تاس 10 (تا ۵۰ تا) — با ایموجی واقعی تاس
▫️ شیر یا خط
▫️ کوییز (+۳۵ سوال) — جواب رو با شماره گزینه بده
▫️ امتیازات
▫️ حقیقت / جرات / جرات یا حقیقت (+۳۰ مورد هرکدوم)
▫️ حساب <عبارت> — یا فقط عبارت ریاضی رو مستقیم بفرست، مثل: 5+5+10

{DIVIDER}
👤 <b>پروفایل و آمار</b>
▫️ بیو [متن] / حذف بیو
▫️ لقب [متن] / حذف لقب
▫️ اصل [متن] / حذف اصل
▫️ فونت <متن>
▫️ فال
▫️ تاریخ
▫️ آمار من (یا ریپلای رو کسی دیگه)
▫️ آمار گروه
▫️ تگ [پیام دلخواه] — فقط ادمین‌ها

{DIVIDER}
💰 <b>اقتصاد گروه</b>
▫️ موجودی — دیدن موجودی خودت
▫️ افزایش موجودی <عدد> (ریپلای) — فقط ادمین
▫️ کسر موجودی <عدد> (ریپلای) — فقط ادمین

{DIVIDER}
⚙️ <b>تنظیمات</b>
▫️ تنظیمات
▫️ setwelcome <متن> / setrules <متن> / rules

مدیریت کلی ربات (مخصوص مالک ربات): panel
"""


async def start_command(bot, message):
    chat_id = message.chat_id
    if is_private_chat(message):
        name = None
        try:
            name = await bot.get_name(chat_id)
        except Exception:
            pass
        db.register_pv_user(chat_id, name or "")
        missing = await missing_channels(bot, chat_id, scope="pv")
        if missing:
            await message.reply(build_join_text(missing))
            return

    groups = db.list_activated_groups()
    all_groups = db.list_all_known_groups()
    pv_users = db.list_pv_users()

    text = (
        f"{title('به ربات مدیریت گروه خوش اومدی', '💎')}\n\n"
        "🎯 <b>امکانات ویژه:</b>\n"
        "🔹 ضداسپم و قفل لینک/فوروارد/گیف/عکس/استیکر/ویدیو/صدا\n"
        "🔹 بن و سکوت با ریپلای، سیستم اخطار، پاکسازی گروه\n"
        "🔹 بازی و سرگرمی: تاس، شیر‌یاخط، کوییز، جرأت یا حقیقت\n"
        "🔹 پروفایل کامل: بیو، لقب، اصالت، فونت، فال، تاریخ\n"
        "🔹 آمار دقیق کاربر و گروه + سیستم اقتصادی (موجودی)\n"
        "🔹 ماشین‌حساب هوشمند، خوش‌آمدگویی، قوانین گروه\n"
        "🔹 عضویت اجباری کانال و پنل مدیریت کامل\n"
        f"{DIVIDER}\n"
        f"{title('آمار کامل ربات', '📊')}\n"
        f"🔵 گروه‌های فعال‌شده: {len(groups)}\n"
        f"⚪️ کل گروه‌هایی که ربات عضوشونه: {len(all_groups)}\n"
        f"🟢 کاربران پی‌وی: {len(pv_users)}\n"
        f"{DIVIDER}\n\n"
        "برای فعال‌سازی، من رو ادمین گروهت کن و بنویس «فعالسازی».\n"
        "برای راهنمای کامل بنویس: راهنما\n"
        "برای پنل مدیریت (مخصوص مالک ربات): panel"
    )
    await message.reply(text)


async def help_command(bot, message):
    await message.reply(HELP_TEXT)


async def whoami_command(bot, message):
    from utils import safe_name
    name = await safe_name(bot, message.sender_id)
    await message.reply(f"chat_id شما: {message.sender_id}\nاسمی که ربات می‌بینه: {name}")


async def checkjoin_command(bot, message):
    missing = await missing_channels(bot, message.sender_id, scope="pv")
    if missing:
        await message.reply("هنوز عضو همه‌ی کانال‌ها نشدی:\n\n" + build_join_text(missing))
    else:
        await message.reply("✅ عضویت تایید شد! برای دیدن امکانات بنویس: راهنما")
