# -*- coding: utf-8 -*-
"""
پروفایل کاربر (بیو/لقب/اصل)، ابزارهای سرگرمی (فونت/فال/تاریخ)، آمار و تگ.
"""
import random
import datetime
import logging

import database as db
from utils import areply, safe_name, acall
from handlers.ui import title, DIVIDER

logger = logging.getLogger(__name__)

WEEKDAYS_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]


def _gregorian_to_jalali(gy, gm, gd):
    """تبدیل میلادی به شمسی (الگوریتم استاندارد و متن‌باز، بدون نیاز به کتابخانه جانبی)."""
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1
    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    for i in range(gm2):
        g_day_no += g_days_in_month[i]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd2
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    jm, jd = 12, j_day_no + 1
    for i in range(11):
        if j_day_no < j_days_in_month[i]:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= j_days_in_month[i]
    return jy, jm, jd


async def date_command(bot, message):
    now = datetime.datetime.now()
    jy, jm, jd = _gregorian_to_jalali(now.year, now.month, now.day)
    weekday_fa = WEEKDAYS_FA[now.weekday()]
    text = (
        f"{title('تاریخ و ساعت', '📅')}\n"
        f"🌙 شمسی: {weekday_fa} {jd} {JALALI_MONTHS[jm-1]} {jy}\n"
        f"🌍 میلادی: {now.strftime('%Y-%m-%d')}\n"
        f"⏰ ساعت: {now.strftime('%H:%M:%S')}"
    )
    await areply(message, text)


# ---------------- فال ----------------

FAL_MESSAGES = [
    "امروز روز خوبیه برای شروع یه کار جدید. دلت رو به دریا بزن! 🌊",
    "یه خبر خوش تو راهه، فقط کمی صبر لازمه. ⏳",
    "امروز با کسی که مدت‌هاست حرف نزدی صحبت کن، خوشحال میشه. ☎️",
    "قدم‌های کوچیک امروز، نتیجه‌های بزرگ فردا میشن. 🌱",
    "یکی داره بهت فکر می‌کنه؛ شاید خودتم ندونی کی! 💭",
    "امروز روز خوبیه برای عذرخواهی از کسی که دلخورش کردی. 🕊",
    "یه فرصت طلایی داره میاد سمتت، چشمات رو باز نگه دار. ✨",
    "امروز به خودت سخت نگیر، آروم باش. 🌸",
    "پولی که منتظرشی داره میاد، فقط یکم دیر شده. 💰",
    "یه سفر کوتاه یا یه دیدار قدیمی تو راهه. 🧳",
    "امروز حرف دلت رو بزن، جوابش بهتر از چیزیه که فکر می‌کنی. 💌",
    "کسی که ازش ناامید بودی، غافلگیرت می‌کنه. 🎁",
    "امروز روز پرانرژی‌ایه، از فرصتش استفاده کن. ⚡️",
    "یه تصمیم قدیمی داره جواب می‌ده، صبور باش. 🕰",
    "لبخندت امروز روز یکی رو می‌سازه، بی‌دریغ لبخند بزن. 😊",
    "یه پیشنهاد خوب تو راهه، خوب فکر کن قبول کنی. 🤝",
    "امروز حواست به خرج‌هات باشه! 💸",
    "یه دوست قدیمی بهت سر می‌زنه یا خبر می‌ده. 👋",
    "کارایی که عقب انداختی رو امروز شروع کن، انرژیش رو داری. 💪",
    "امروز روز مناسبیه برای یادگیری یه چیز جدید. 📚",
    "صبر کن، جواب سوالت خیلی زود میاد. ❓",
    "یکی قراره ازت تشکر کنه، لبخند بزن و بپذیرش. 🙏",
    "امروز حسادت دیگران رو نادیده بگیر و راهت رو برو. 🚶",
    "یه خبر غیرمنتظره خوشحالت می‌کنه. 🎉",
    "دلت رو به چیزای کوچیک خوش کن، زندگی از همینا ساخته شده. 🍀",
    "امروز کمی استراحت کن، لیاقتشو داری. 🛌",
    "یه فرصت شغلی یا درسی جدید داره باز میشه. 🚪",
    "به حرف دلت گوش کن، عقلت هم باهاش موافقه. ❤️",
    "امروز روزیه که باید به خودت افتخار کنی. 🏆",
    "یه چیزی که گم کرده بودی پیدا میشه. 🔍",
]


async def fal_command(bot, message):
    await areply(message, f"{title('فال امروز شما', '🔮')}\n{random.choice(FAL_MESSAGES)}")


# ---------------- فونت ----------------

_FONT_MAPS = [
    ("𝗯𝗼𝗹𝗱 آ ب پ ت", str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗏𝗪𝗫𝗬𝗭𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    )),
    ("𝓼𝓬𝓻𝓲𝓹𝓽", str.maketrans(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩"
    )),
]


def _apply_font_latin(text: str, mapping) -> str:
    return text.translate(mapping)


async def font_command(bot, message, text: str):
    text = text.strip()
    if not text:
        await areply(message, "متن مورد نظرت رو بعد از دستور بنویس.\nمثال: فونت سلام")
        return

    lines = [title("فونت‌های شیک", "🔠")]
    # استایل‌های Latin (روی حروف انگلیسی/اعداد اثر می‌ذاره)
    for name, mapping in _FONT_MAPS:
        styled = _apply_font_latin(text, mapping)
        lines.append(f"▫️ {styled}")
    # استایل‌های تزئینی که برای فارسی هم خوب کار می‌کنن (چون کاراکترهای فارسی رو دست نمی‌زنن)
    decorative = [
        f"『 {text} 』",
        f"⋆ {text} ⋆",
        f"«{text}»",
        f"彡 {text} 彡",
        f"◈ {text} ◈",
        f"✦ {text} ✦",
    ]
    for d in decorative:
        lines.append(f"▫️ {d}")
    await areply(message, "\n".join(lines))


# ---------------- بیو / لقب / اصل ----------------

async def bio_command(bot, message, text: str):
    text = text.strip()
    if text:
        db.update_user_profile(message.chat_id, message.sender_id, bio=text)
        await areply(message, "✅ بیوی شما ثبت شد.")
        return
    profile = db.get_user_profile(message.chat_id, message.sender_id)
    if profile.get("bio"):
        await areply(message, f"📝 بیوی شما:\n{profile['bio']}")
    else:
        await areply(message, "بیویی ثبت نکردی. برای ثبت: بیو <متن>")


async def delete_bio_command(bot, message):
    db.update_user_profile(message.chat_id, message.sender_id, bio=None)
    await areply(message, "✅ بیوی شما حذف شد.")


async def title_command(bot, message, text: str):
    text = text.strip()
    if text:
        db.update_user_profile(message.chat_id, message.sender_id, title=text)
        await areply(message, f"✅ لقب شما به «{text}» تغییر کرد.")
        return
    profile = db.get_user_profile(message.chat_id, message.sender_id)
    if profile.get("title"):
        await areply(message, f"🏷 لقب شما: {profile['title']}")
    else:
        await areply(message, "لقبی ثبت نکردی. برای ثبت: لقب <متن>")


async def delete_title_command(bot, message):
    db.update_user_profile(message.chat_id, message.sender_id, title=None)
    await areply(message, "✅ لقب شما حذف شد.")


async def origin_command(bot, message, text: str):
    text = text.strip()
    if text:
        db.update_user_profile(message.chat_id, message.sender_id, origin=text)
        await areply(message, f"✅ اصالت شما به «{text}» تغییر کرد.")
        return
    profile = db.get_user_profile(message.chat_id, message.sender_id)
    if profile.get("origin"):
        await areply(message, f"📍 اصالت شما: {profile['origin']}")
    else:
        await areply(message, "اصالتی ثبت نکردی. برای ثبت: اصل <متن>")


async def delete_origin_command(bot, message):
    db.update_user_profile(message.chat_id, message.sender_id, origin=None)
    await areply(message, "✅ اصالت شما حذف شد.")


# ---------------- آمار ----------------

async def user_stats_command(bot, message):
    from handlers.moderation import _get_target_from_reply
    target = await _get_target_from_reply(bot, message) or message.sender_id
    chat_id = message.chat_id
    name = await safe_name(bot, target, group_id=chat_id)
    profile = db.get_user_profile(chat_id, target)
    msg_count = db.user_message_count(chat_id, target)
    rank, total = db.user_rank(chat_id, target)
    balance = db.get_balance(chat_id, target)

    lines = [title(f"آمار {name}", "👤")]
    lines.append(f"💬 تعداد پیام‌ها: {msg_count}")
    if rank:
        lines.append(f"🏅 رتبه فعالیت: {rank} از {total}")
    lines.append(f"💰 موجودی: {balance}")
    if profile.get("title"):
        lines.append(f"🏷 لقب: {profile['title']}")
    if profile.get("origin"):
        lines.append(f"📍 اصالت: {profile['origin']}")
    if profile.get("bio"):
        lines.append(f"📝 بیو: {profile['bio']}")
    await areply(message, "\n".join(lines))


async def group_stats_command(bot, message):
    chat_id = message.chat_id
    group = db.get_group(chat_id)
    members = db.member_count(chat_id)
    total_msgs = db.total_messages(chat_id)

    lines = [title("آمار گروه", "📊")]
    lines.append(f"👥 اعضای شناخته‌شده توسط ربات: {members}")
    lines.append(f"💬 مجموع پیام‌های ثبت‌شده: {total_msgs}")
    if group.get("activated_at"):
        jy, jm, jd = _gregorian_to_jalali(*datetime.datetime.fromtimestamp(group["activated_at"]).timetuple()[:3])
        lines.append(f"📅 تاریخ فعال‌سازی: {jd} {JALALI_MONTHS[jm-1]} {jy}")
    active_settings = []
    from handlers.group_admin_actions import TOGGLE_FIELDS
    for field, label in TOGGLE_FIELDS.items():
        if group.get(field):
            active_settings.append(label)
    lines.append(DIVIDER)
    lines.append("⚙️ تنظیمات فعال:")
    lines.append(" | ".join(active_settings) if active_settings else "هیچ‌کدوم")
    await areply(message, "\n".join(lines))


# ---------------- تگ ----------------

async def tag_command(bot, message, extra_text: str = ""):
    if not db.is_group_admin(message.chat_id, message.sender_id):
        await areply(message, "⛔️ فقط ادمین‌های ربات می‌تونن تگ کنن.")
        return
    ids = db.list_known_member_ids(message.chat_id, limit=50)
    if not ids:
        await areply(message, "هنوز هیچ عضوی رو نمی‌شناسم (کسی پیام نداده).")
        return

    header = extra_text.strip() or "🏷 توجه اعضای گروه:"

    # اسم واقعی هر عضو رو می‌گیریم و متن نهایی + محدوده‌ی هر اسم (برای منشن واقعی) رو می‌سازیم
    names = []
    for uid in ids:
        n = await safe_name(bot, uid, group_id=message.chat_id)
        names.append(n or "کاربر")

    body_parts = []
    metadata = []
    cursor_pos = 0
    for uid, name in zip(ids, names):
        if body_parts:
            body_parts.append(" ")
            cursor_pos += 1
        start = cursor_pos
        body_parts.append(name)
        cursor_pos += len(name)
        metadata.append({
            "type": "MentionText",
            "from_index": start,
            "length": len(name),
            "mention_text_object_guid": uid,
            "mention_text_object_type": "User",
        })
    body_text = f"{header}\n\n{''.join(body_parts)}"

    # چند شکل محتمل از پارامتر متادیتا رو امتحان می‌کنیم (مستندات عمومی rubka
    # دقیق مشخص نکرده اسم پارامتر و ساختار دقیق چیه).
    attempts = [
        {"metadata": metadata},
        {"text_metadata": metadata},
        {"meta_data_parts": metadata},
        {"mention_user_ids": ids},
    ]
    for kwargs in attempts:
        try:
            await acall(bot.send_message, message.chat_id, body_text, **kwargs)
            return
        except TypeError:
            continue
        except Exception:
            logger.exception("ارسال تگ با پارامتر %s شکست خورد.", list(kwargs.keys())[0])
            continue

    # اگه هیچ‌کدوم از روش‌های منشن واقعی کار نکرد، حداقل اسم‌ها رو به‌صورت متن می‌فرستیم
    logger.warning("⚠️ هیچ‌کدوم از روش‌های منشن واقعی برای تگ کار نکرد؛ فقط اسم فرستاده شد.")
    await areply(message, body_text)
