# -*- coding: utf-8 -*-
"""
تنظیمات اصلی ربات مدیریت گروه روبیکا
"""
import os

# توکن ربات - از @BotFather روبیکا (داخل خود روبیکا) بگیرید
BOT_TOKEN = os.getenv("BOT_TOKEN", "CBCFFI0NJTUOFXNGLXOMSTYZFSYIVLLATGYEHYODFHYOGTMVMHWUUCRWTXNSXGCY")

# chat_id عددی/رشته‌ای مالک اصلی ربات (شما).
# اولین بار که با ربات در پی‌وی صحبت کنید، با دستور /whoami می‌تونید chat_id خودتون رو ببینید
# و بعد اینجا قرارش بدید.
OWNER_IDS = [
    "u0I13nW088018e359efe8afc6e553fb6",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "bot.db")

DEFAULT_WELCOME_TEXT = "سلام کاربر {name} خوش اومدی به «{group_title}» 🌹"
DEFAULT_RULES_TEXT = "قوانینی هنوز ثبت نشده. با /setrules می‌تونید ثبت کنید."

ACTIVATION_KEYWORDS = ["فعالسازی", "فعال سازی"]

MAX_DICE_COUNT = 50
MAX_WARN_COUNT = 3          # بعد از این تعداد اخطار، کاربر به‌صورت خودکار «بن نرم» می‌شود
MAX_CLEAN_MESSAGES = 100

# آیا برای استفاده از ربات در پی‌وی، عضویت در کانال‌های اجباری لازمه؟
FORCE_JOIN_IN_PV = True
# آیا برای پیام دادن داخل گروه هم عضویت اجباری چک بشه؟ (هزینه‌ی API بیشتر داره)
FORCE_JOIN_IN_GROUPS = False
