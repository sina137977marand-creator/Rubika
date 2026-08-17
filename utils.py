# -*- coding: utf-8 -*-
import re
import inspect
import logging

import config
import database as db

logger = logging.getLogger(__name__)

LINK_REGEX = re.compile(
    r"(https?://|www\.|rubika\.ir/|@[a-zA-Z0-9_]{5,})", re.IGNORECASE
)
MENTION_REGEX = re.compile(r"@[a-zA-Z0-9_]{5,}")

# اعداد تاس به‌صورت ایموجی واقعی صفحه تاس
DICE_FACES = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}

# تشخیص این‌که یه متن فقط یه عبارت ریاضیه (برای محاسبه‌ی خودکار بدون نیاز به دستور «حساب»)
MATH_EXPR_REGEX = re.compile(r"^[\d۰-۹\s\.\+\-\*/×÷\^\(\)]+$")
_HAS_OPERATOR_REGEX = re.compile(r"[\+\-\*/×÷\^]")

_chat_type_cache = {}


def looks_like_math_expression(text: str) -> bool:
    """
    True اگه متن چیزی شبیه یه عبارت ریاضی خالص باشه (فقط عدد/عملگر/پرانتز) و
    حداقل یک عملگر داشته باشه (که یه عدد ساده مثل «۵» یا آیدی عددی رو حساب نکنه).
    """
    t = (text or "").strip()
    if not t or len(t) > 200:
        return False
    if not MATH_EXPR_REGEX.match(t):
        return False
    if not _HAS_OPERATOR_REGEX.search(t):
        return False
    return True


async def acall(func, *args, **kwargs):
    """
    فراخوانی امن یک متد از کتابخونه rubka.
    نسخه‌ی نصب‌شده کاملاً async هست (rubka.asynco)، پس هر متدی از bot یا message
    باید await بشه. این تابع هم async و هم sync رو پشتیبانی می‌کنه تا اگه نسخه‌ی
    شما رفتار متفاوتی داشت، کد از کار نیفته.
    """
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


async def areply(message, text, **kwargs):
    return await acall(message.reply, text, **kwargs)


def _guess_type_from_prefix(chat_id: str) -> str:
    cid = str(chat_id or "")
    if cid.startswith("g0"):
        return "Group"
    if cid.startswith("c0"):
        return "Channel"
    if cid.startswith("u0") or cid.startswith("b0"):
        return "User"
    return "Unknown"


async def get_chat_type(bot, chat_id: str) -> str:
    if chat_id in _chat_type_cache:
        return _chat_type_cache[chat_id]

    chat_type = None
    try:
        info = await acall(bot.get_chat, chat_id)
        raw = info if isinstance(info, dict) else getattr(info, "__dict__", {})
        for key in ("type", "chat_type", "abs_object", "object_type"):
            val = raw.get(key) if isinstance(raw, dict) else None
            if val:
                chat_type = str(val)
                break
        if not chat_type and isinstance(raw, dict):
            nested = raw.get("data") or raw.get("chat")
            if isinstance(nested, dict):
                chat_type = nested.get("type") or nested.get("chat_type")
    except Exception as e:
        logger.warning("get_chat برای %s خطا داد: %s", chat_id, e)

    if not chat_type:
        chat_type = _guess_type_from_prefix(chat_id)

    _chat_type_cache[chat_id] = chat_type
    return chat_type


def is_group_chat(message) -> bool:
    """
    تست واقعی نشون داد شیء message مستقیماً فیلد is_group داره - قابل‌اعتمادتر و
    سریع‌تر از حدس زدن پیشوند GUID یا صدا زدن API برای هر پیام.
    """
    val = getattr(message, "is_group", None)
    if val is not None:
        return bool(val)
    return _guess_type_from_prefix(getattr(message, "chat_id", "")) == "Group"


def is_private_chat(message) -> bool:
    val = getattr(message, "is_private", None)
    if val is not None:
        return bool(val)
    return _guess_type_from_prefix(getattr(message, "chat_id", "")) in ("User",)


async def is_admin_or_owner(group_id: str, user_id: str) -> bool:
    return db.is_group_admin(group_id, user_id)


def contains_link(text: str, message=None) -> bool:
    if message is not None:
        val = getattr(message, "is_link", None)
        if val is not None:
            if val:
                return True
    if not text:
        return False
    return bool(LINK_REGEX.search(text))


def contains_mention(text: str, message=None) -> bool:
    if message is not None:
        val = getattr(message, "is_mention", None) or getattr(message, "is_username", None)
        if val:
            return True
    if not text:
        return False
    return bool(MENTION_REGEX.search(text))


def parse_hhmm(text: str):
    m = re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", text.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))



async def safe_delete(bot, chat_id, message_id):
    try:
        await acall(bot.delete_message, chat_id, message_id)
        return True
    except Exception:
        return False


_BAD_NAME_VALUES = {"null", "none", "undefined", "nan", "false", ""}


async def safe_name(bot, chat_id, group_id=None):
    """
    اسم واقعی کاربر رو می‌گیره.
    نکته‌ی مهم (از تست واقعی روی گروه): get_name/get_chat با آیدی خام یک عضو
    گروه (u0...) اغلب INVALID_INPUT می‌ده - این متدها ظاهراً فقط برای چتی که
    خودِ ربات مستقیم با اون کاربر داره (پی‌وی) جواب می‌دن. برای عضو یک گروه،
    راه درست‌تر get_chat_member(group_id, user_id) هست چون ربات واقعاً عضو
    اون گروهه و مجازه اطلاعات اعضاش رو ببینه.
    """
    def _is_valid(v):
        return isinstance(v, str) and v.strip() and v.strip().lower() not in _BAD_NAME_VALUES

    def _extract_from_dict(d):
        if not isinstance(d, dict):
            return None
        # اول اسم کامل (نام+نام‌خانوادگی) رو امتحان کن
        first = d.get("first_name") or ""
        last = d.get("last_name") or ""
        combined = f"{first} {last}".strip()
        if _is_valid(combined):
            return combined
        # بعد کلیدهای تکی محتمل
        for key in ("first_name", "name", "display_name", "title", "username"):
            val = d.get(key)
            if _is_valid(val):
                return val.strip()
        # بعد شیء تو در تو (user/member/chat/data)
        for nested_key in ("user", "member", "chat", "data"):
            nested = d.get(nested_key)
            if isinstance(nested, dict):
                found = _extract_from_dict(nested)
                if found:
                    return found
        return None

    # روش اول: اگه تو یک گروه هستیم، از طریق عضویت همون گروه اسم رو بگیریم
    if group_id:
        for method_name in ("get_chat_member", "get_chat_members"):
            method = getattr(bot, method_name, None)
            if not method:
                continue
            try:
                result = await acall(method, group_id, chat_id)
                found = _extract_from_dict(result)
                if found:
                    return found
                logger.warning(
                    "⚠️ %s برای %s تو گروه %s جواب داد ولی اسمی توش پیدا نشد: %r",
                    method_name, chat_id, group_id, result,
                )
            except Exception:
                logger.exception("❌ %s برای %s تو گروه %s با خطا مواجه شد.", method_name, chat_id, group_id)

    # روش دوم: get_name مستقیم (برای پی‌وی یا اگه روش اول کار نکرد)
    try:
        name = await acall(bot.get_name, chat_id)
        if _is_valid(name):
            return name.strip()
        logger.warning("⚠️ get_name برای %s مقدار نامعتبر برگردوند: %r", chat_id, name)
    except Exception:
        logger.exception("❌ get_name برای %s با خطا مواجه شد.", chat_id)

    # روش سوم: get_username یا get_chat مستقیم
    for method_name in ("get_username", "get_chat"):
        method = getattr(bot, method_name, None)
        if not method:
            continue
        try:
            result = await acall(method, chat_id)
            if _is_valid(result):
                return result.strip()
            found = _extract_from_dict(result)
            if found:
                return found
        except Exception:
            logger.exception("❌ %s هم برای %s با خطا مواجه شد.", method_name, chat_id)

    return "کاربر"


def guess_message_kind(message) -> str:
    """
    نوع پیام برای فیلترها. طبق تست واقعی روی نسخه‌ی نصب‌شده‌ی rubka (8.1.10)،
    شیء Message این فیلدهای بولی مستقیم رو داره: is_photo, is_video, is_gif,
    is_voice, is_music, is_audio, is_forwarded, و شیء sticker/forwarded_from.
    این‌ها قابل‌اعتمادتر از حدس زدن ساختار raw_data هستن.
    """
    if getattr(message, "is_forwarded", False) or getattr(message, "forwarded_from", None):
        return "forward"
    if getattr(message, "sticker", None):
        return "sticker"
    if getattr(message, "is_gif", False):
        return "gif"
    if getattr(message, "is_photo", False):
        return "photo"
    if getattr(message, "is_video", False):
        return "video"
    if getattr(message, "is_voice", False) or getattr(message, "is_music", False) or getattr(message, "is_audio", False):
        return "voice"
    if getattr(message, "is_document", False):
        return "file"
    return "text"
