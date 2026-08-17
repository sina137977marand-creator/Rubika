# -*- coding: utf-8 -*-
"""
لایه دیتابیس (SQLite).
توجه: در روبیکا آیدی چت‌ها و کاربران رشته (GUID) هستن، نه عدد - پس همه‌جا TEXT استفاده شده.
"""
import sqlite3
import os
import time
import threading
from contextlib import contextmanager

import config

os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
_local = threading.local()


def get_conn():
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(config.DB_PATH, timeout=30)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL;")
    return _local.conn


@contextmanager
def cursor():
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def init_db():
    with cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            group_id TEXT PRIMARY KEY,
            title TEXT,
            owner_id TEXT,
            activated INTEGER DEFAULT 0,
            anti_link INTEGER DEFAULT 0,
            anti_forward INTEGER DEFAULT 0,
            anti_gif INTEGER DEFAULT 0,
            anti_photo INTEGER DEFAULT 0,
            anti_mention INTEGER DEFAULT 0,
            anti_spam INTEGER DEFAULT 1,
            anti_flood INTEGER DEFAULT 1,
            anti_sticker INTEGER DEFAULT 0,
            anti_video INTEGER DEFAULT 0,
            anti_voice INTEGER DEFAULT 0,
            auto_accept_join_requests INTEGER DEFAULT 0,
            welcome_enabled INTEGER DEFAULT 1,
            welcome_text TEXT,
            rules_text TEXT,
            locked INTEGER DEFAULT 0,
            activated_at INTEGER
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS group_admins (
            group_id TEXT, user_id TEXT, full_name TEXT,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            group_id TEXT, user_id TEXT,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS muted_users (
            group_id TEXT, user_id TEXT, until_ts INTEGER,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            group_id TEXT, user_id TEXT, count INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS recent_messages (
            group_id TEXT, message_id TEXT, ts INTEGER
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_recent_group ON recent_messages(group_id)")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS pv_users (
            user_id TEXT PRIMARY KEY, full_name TEXT, first_seen INTEGER
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS known_groups (
            group_id TEXT PRIMARY KEY, title TEXT
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS mandatory_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT, channel_guid TEXT, title TEXT
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_admins (
            user_id TEXT PRIMARY KEY
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_scores (
            group_id TEXT, user_id TEXT, full_name TEXT, score INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS active_quiz (
            group_id TEXT PRIMARY KEY, question TEXT, correct_answer TEXT
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            group_id TEXT, user_id TEXT, bio TEXT, title TEXT, origin TEXT,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS group_members_seen (
            group_id TEXT, user_id TEXT, first_seen INTEGER, last_seen INTEGER,
            message_count INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            group_id TEXT, user_id TEXT, balance INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, user_id)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS message_index (
            group_id TEXT, message_id TEXT, sender_id TEXT, ts INTEGER,
            PRIMARY KEY (group_id, message_id)
        )""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_msgindex_group ON message_index(group_id)")

    _migrate_new_columns()


def _migrate_new_columns():
    """برای دیتابیس‌های قدیمی‌تر که ستون‌های جدید رو ندارن (ارتقای نسخه)."""
    new_columns = {
        "anti_sticker": "INTEGER DEFAULT 0",
        "anti_video": "INTEGER DEFAULT 0",
        "anti_voice": "INTEGER DEFAULT 0",
        "auto_accept_join_requests": "INTEGER DEFAULT 0",
        "activated_at": "INTEGER",
    }
    with cursor() as cur:
        cur.execute("PRAGMA table_info(groups)")
        existing = {row["name"] for row in cur.fetchall()}
        for col, col_type in new_columns.items():
            if col not in existing:
                try:
                    cur.execute(f"ALTER TABLE groups ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

        # آپدیت متن خوش‌آمدگویی پیش‌فرض قدیمی به فرمت جدید (فقط اگه کسی سفارشی‌ش نکرده)
        try:
            old_default = "سلام {name} خوش اومدی به «{group_title}» 🌹"
            cur.execute(
                "UPDATE groups SET welcome_text=? WHERE welcome_text=?",
                (config.DEFAULT_WELCOME_TEXT, old_default),
            )
        except Exception:
            pass


# ---------------- GROUPS ----------------

def get_group(group_id, title=None):
    with cursor() as cur:
        cur.execute("SELECT * FROM groups WHERE group_id=?", (group_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO groups (group_id, title, welcome_text, rules_text) VALUES (?,?,?,?)",
                (group_id, title or "", config.DEFAULT_WELCOME_TEXT, config.DEFAULT_RULES_TEXT),
            )
            cur.execute("INSERT OR IGNORE INTO known_groups (group_id, title) VALUES (?,?)",
                        (group_id, title or ""))
            cur.execute("SELECT * FROM groups WHERE group_id=?", (group_id,))
            row = cur.fetchone()
        elif title and title != row["title"]:
            cur.execute("UPDATE groups SET title=? WHERE group_id=?", (title, group_id))
            cur.execute("UPDATE known_groups SET title=? WHERE group_id=?", (title, group_id))
        return dict(row)


def update_group(group_id, **fields):
    if not fields:
        return
    keys = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [group_id]
    with cursor() as cur:
        cur.execute(f"UPDATE groups SET {keys} WHERE group_id=?", values)


def list_activated_groups():
    with cursor() as cur:
        cur.execute("SELECT group_id, title FROM groups WHERE activated=1")
        return [dict(r) for r in cur.fetchall()]


def list_all_known_groups():
    with cursor() as cur:
        cur.execute("SELECT group_id, title FROM known_groups")
        return [dict(r) for r in cur.fetchall()]


# ---------------- ADMIN/OWNER (سیستم دسترسی داخلی ربات) ----------------

def set_group_owner(group_id, user_id):
    with cursor() as cur:
        cur.execute("UPDATE groups SET owner_id=? WHERE group_id=?", (user_id, group_id))


def is_group_owner(group_id, user_id):
    if user_id in config.OWNER_IDS:
        return True
    with cursor() as cur:
        cur.execute("SELECT owner_id FROM groups WHERE group_id=?", (group_id,))
        row = cur.fetchone()
        return bool(row and row["owner_id"] == user_id)


def add_group_admin(group_id, user_id, full_name=""):
    with cursor() as cur:
        cur.execute("""INSERT OR REPLACE INTO group_admins (group_id, user_id, full_name)
                       VALUES (?,?,?)""", (group_id, user_id, full_name))


def remove_group_admin(group_id, user_id):
    with cursor() as cur:
        cur.execute("DELETE FROM group_admins WHERE group_id=? AND user_id=?", (group_id, user_id))


def is_group_admin(group_id, user_id):
    if is_group_owner(group_id, user_id):
        return True
    with cursor() as cur:
        cur.execute("SELECT 1 FROM group_admins WHERE group_id=? AND user_id=?", (group_id, user_id))
        return cur.fetchone() is not None


def list_group_admins(group_id):
    with cursor() as cur:
        cur.execute("SELECT user_id, full_name FROM group_admins WHERE group_id=?", (group_id,))
        return [dict(r) for r in cur.fetchall()]


# ---------------- BAN / MUTE (نرم) ----------------

def ban_user(group_id, user_id):
    with cursor() as cur:
        cur.execute("INSERT OR IGNORE INTO banned_users (group_id, user_id) VALUES (?,?)",
                    (group_id, user_id))


def unban_user(group_id, user_id):
    with cursor() as cur:
        cur.execute("DELETE FROM banned_users WHERE group_id=? AND user_id=?", (group_id, user_id))


def is_banned(group_id, user_id):
    with cursor() as cur:
        cur.execute("SELECT 1 FROM banned_users WHERE group_id=? AND user_id=?", (group_id, user_id))
        return cur.fetchone() is not None


def mute_user(group_id, user_id, until_ts):
    with cursor() as cur:
        cur.execute("""INSERT INTO muted_users (group_id, user_id, until_ts) VALUES (?,?,?)
                       ON CONFLICT(group_id, user_id) DO UPDATE SET until_ts=excluded.until_ts""",
                    (group_id, user_id, until_ts))


def unmute_user(group_id, user_id):
    with cursor() as cur:
        cur.execute("DELETE FROM muted_users WHERE group_id=? AND user_id=?", (group_id, user_id))


def is_muted(group_id, user_id):
    with cursor() as cur:
        cur.execute("SELECT until_ts FROM muted_users WHERE group_id=? AND user_id=?", (group_id, user_id))
        row = cur.fetchone()
        if not row:
            return False
        if row["until_ts"] and row["until_ts"] < int(time.time()):
            cur.execute("DELETE FROM muted_users WHERE group_id=? AND user_id=?", (group_id, user_id))
            return False
        return True


# ---------------- WARNS ----------------

def add_warn(group_id, user_id):
    with cursor() as cur:
        cur.execute("""INSERT INTO warns (group_id, user_id, count) VALUES (?,?,1)
                       ON CONFLICT(group_id, user_id) DO UPDATE SET count = count + 1""",
                    (group_id, user_id))
        cur.execute("SELECT count FROM warns WHERE group_id=? AND user_id=?", (group_id, user_id))
        return cur.fetchone()["count"]


def reset_warn(group_id, user_id):
    with cursor() as cur:
        cur.execute("DELETE FROM warns WHERE group_id=? AND user_id=?", (group_id, user_id))


# ---------------- RECENT MESSAGES (پاکسازی) ----------------

def log_message(group_id, message_id):
    with cursor() as cur:
        cur.execute("INSERT INTO recent_messages (group_id, message_id, ts) VALUES (?,?,?)",
                    (group_id, message_id, int(time.time())))
        cur.execute("""
            DELETE FROM recent_messages WHERE group_id=? AND message_id NOT IN (
                SELECT message_id FROM recent_messages WHERE group_id=?
                ORDER BY ts DESC LIMIT ?
            )""", (group_id, group_id, config.MAX_CLEAN_MESSAGES))


def get_recent_message_ids(group_id, limit):
    with cursor() as cur:
        cur.execute("""SELECT message_id FROM recent_messages WHERE group_id=?
                       ORDER BY ts DESC LIMIT ?""", (group_id, limit))
        return [r["message_id"] for r in cur.fetchall()]


def clear_recent_messages(group_id):
    with cursor() as cur:
        cur.execute("DELETE FROM recent_messages WHERE group_id=?", (group_id,))


# ---------------- PV USERS ----------------

def register_pv_user(user_id, full_name):
    with cursor() as cur:
        cur.execute("""INSERT INTO pv_users (user_id, full_name, first_seen) VALUES (?,?,?)
                       ON CONFLICT(user_id) DO UPDATE SET full_name=excluded.full_name""",
                    (user_id, full_name or "", int(time.time())))


def list_pv_users():
    with cursor() as cur:
        cur.execute("SELECT user_id FROM pv_users")
        return [r["user_id"] for r in cur.fetchall()]


# ---------------- MANDATORY CHANNELS ----------------

def add_mandatory_channel(channel_guid, title=""):
    with cursor() as cur:
        cur.execute("INSERT INTO mandatory_channels (channel_guid, title) VALUES (?,?)",
                    (channel_guid, title))


def remove_mandatory_channel(channel_guid):
    with cursor() as cur:
        cur.execute("DELETE FROM mandatory_channels WHERE channel_guid=?", (channel_guid,))


def list_mandatory_channels():
    with cursor() as cur:
        cur.execute("SELECT * FROM mandatory_channels")
        return [dict(r) for r in cur.fetchall()]


# ---------------- BOT ADMINS (پنل کلی ربات) ----------------

def add_bot_admin(user_id):
    with cursor() as cur:
        cur.execute("INSERT OR IGNORE INTO bot_admins (user_id) VALUES (?)", (user_id,))


def remove_bot_admin(user_id):
    with cursor() as cur:
        cur.execute("DELETE FROM bot_admins WHERE user_id=?", (user_id,))


def list_bot_admins():
    with cursor() as cur:
        cur.execute("SELECT user_id FROM bot_admins")
        return [r["user_id"] for r in cur.fetchall()]


def is_bot_admin(user_id):
    if user_id in config.OWNER_IDS:
        return True
    with cursor() as cur:
        cur.execute("SELECT 1 FROM bot_admins WHERE user_id=?", (user_id,))
        return cur.fetchone() is not None


# ---------------- QUIZ ----------------

def add_quiz_score(group_id, user_id, full_name, points=1):
    with cursor() as cur:
        cur.execute("""INSERT INTO quiz_scores (group_id, user_id, full_name, score) VALUES (?,?,?,?)
                       ON CONFLICT(group_id, user_id) DO UPDATE SET
                       score = score + excluded.score, full_name = excluded.full_name""",
                    (group_id, user_id, full_name, points))


def top_quiz_scores(group_id, limit=10):
    with cursor() as cur:
        cur.execute("""SELECT full_name, score FROM quiz_scores WHERE group_id=?
                       ORDER BY score DESC LIMIT ?""", (group_id, limit))
        return [dict(r) for r in cur.fetchall()]


def set_active_quiz(group_id, question, correct_answer):
    with cursor() as cur:
        cur.execute("""INSERT INTO active_quiz (group_id, question, correct_answer) VALUES (?,?,?)
                       ON CONFLICT(group_id) DO UPDATE SET
                       question=excluded.question, correct_answer=excluded.correct_answer""",
                    (group_id, question, correct_answer))


def get_active_quiz(group_id):
    with cursor() as cur:
        cur.execute("SELECT * FROM active_quiz WHERE group_id=?", (group_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def clear_active_quiz(group_id):
    with cursor() as cur:
        cur.execute("DELETE FROM active_quiz WHERE group_id=?", (group_id,))


# ---------------- پروفایل کاربر (بیو/لقب/اصل) ----------------

def get_user_profile(group_id, user_id):
    with cursor() as cur:
        cur.execute("SELECT * FROM user_profiles WHERE group_id=? AND user_id=?", (group_id, user_id))
        row = cur.fetchone()
        if row is None:
            return {"group_id": group_id, "user_id": user_id, "bio": None, "title": None, "origin": None}
        return dict(row)


def update_user_profile(group_id, user_id, **fields):
    if not fields:
        return
    with cursor() as cur:
        cur.execute("INSERT OR IGNORE INTO user_profiles (group_id, user_id) VALUES (?,?)",
                    (group_id, user_id))
        keys = ", ".join(f"{k}=?" for k in fields)
        values = list(fields.values()) + [group_id, user_id]
        cur.execute(f"UPDATE user_profiles SET {keys} WHERE group_id=? AND user_id=?", values)


# ---------------- اعضای شناخته‌شده / آمار پیام ----------------

def touch_member(group_id, user_id) -> bool:
    """
    ثبت/به‌روزرسانی فعالیت کاربر در گروه. خروجی True یعنی این اولین باریه که
    این کاربر رو تو این گروه دیدیم (برای تریگر خوش‌آمدگویی استفاده میشه).
    """
    now = int(time.time())
    with cursor() as cur:
        cur.execute("SELECT 1 FROM group_members_seen WHERE group_id=? AND user_id=?",
                    (group_id, user_id))
        is_new = cur.fetchone() is None
        if is_new:
            cur.execute("""INSERT INTO group_members_seen
                           (group_id, user_id, first_seen, last_seen, message_count)
                           VALUES (?,?,?,?,1)""", (group_id, user_id, now, now))
        else:
            cur.execute("""UPDATE group_members_seen SET last_seen=?, message_count=message_count+1
                           WHERE group_id=? AND user_id=?""", (now, group_id, user_id))
        return is_new


def member_count(group_id):
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) c FROM group_members_seen WHERE group_id=?", (group_id,))
        return cur.fetchone()["c"]


def total_messages(group_id):
    with cursor() as cur:
        cur.execute("SELECT COALESCE(SUM(message_count),0) s FROM group_members_seen WHERE group_id=?",
                    (group_id,))
        return cur.fetchone()["s"]


def user_message_count(group_id, user_id):
    with cursor() as cur:
        cur.execute("SELECT message_count FROM group_members_seen WHERE group_id=? AND user_id=?",
                    (group_id, user_id))
        row = cur.fetchone()
        return row["message_count"] if row else 0


def user_rank(group_id, user_id):
    with cursor() as cur:
        cur.execute("""SELECT user_id FROM group_members_seen WHERE group_id=?
                       ORDER BY message_count DESC""", (group_id,))
        ids = [r["user_id"] for r in cur.fetchall()]
        if user_id not in ids:
            return None, len(ids)
        return ids.index(user_id) + 1, len(ids)


def list_known_member_ids(group_id, limit=200):
    with cursor() as cur:
        cur.execute("""SELECT user_id FROM group_members_seen WHERE group_id=?
                       ORDER BY last_seen DESC LIMIT ?""", (group_id, limit))
        return [r["user_id"] for r in cur.fetchall()]


def set_group_activated_at(group_id):
    with cursor() as cur:
        cur.execute("UPDATE groups SET activated_at=? WHERE group_id=? AND activated_at IS NULL",
                    (int(time.time()), group_id))


# ---------------- موجودی (اقتصاد گروه) ----------------

def get_balance(group_id, user_id):
    with cursor() as cur:
        cur.execute("SELECT balance FROM balances WHERE group_id=? AND user_id=?", (group_id, user_id))
        row = cur.fetchone()
        return row["balance"] if row else 0


def change_balance(group_id, user_id, delta):
    with cursor() as cur:
        cur.execute("""INSERT INTO balances (group_id, user_id, balance) VALUES (?,?,?)
                       ON CONFLICT(group_id, user_id) DO UPDATE SET balance = balance + excluded.balance""",
                    (group_id, user_id, delta))
        cur.execute("SELECT balance FROM balances WHERE group_id=? AND user_id=?", (group_id, user_id))
        return cur.fetchone()["balance"]


# ---------------- ایندکس پیام‌ها (برای پیدا کردن فرستنده‌ی پیام ریپلای‌شده) ----------------
# نکته: چون bot.get_message در این نسخه از rubka جواب درست نمی‌ده، خودمون هر پیامی
# که تو گروه رد میشه رو با فرستنده‌ش ذخیره می‌کنیم تا بعداً برای ریپلای قابل جست‌وجو باشه.

MAX_MESSAGE_INDEX_PER_GROUP = 5000


def index_message(group_id, message_id, sender_id):
    if not message_id or not sender_id:
        return
    now = int(time.time())
    with cursor() as cur:
        cur.execute("""INSERT INTO message_index (group_id, message_id, sender_id, ts) VALUES (?,?,?,?)
                       ON CONFLICT(group_id, message_id) DO UPDATE SET sender_id=excluded.sender_id, ts=excluded.ts""",
                    (group_id, message_id, sender_id, now))
        cur.execute("""
            DELETE FROM message_index WHERE group_id=? AND message_id NOT IN (
                SELECT message_id FROM message_index WHERE group_id=?
                ORDER BY ts DESC LIMIT ?
            )""", (group_id, group_id, MAX_MESSAGE_INDEX_PER_GROUP))


def get_message_sender(group_id, message_id):
    if not message_id:
        return None
    with cursor() as cur:
        cur.execute("SELECT sender_id FROM message_index WHERE group_id=? AND message_id=?",
                    (group_id, str(message_id)))
        row = cur.fetchone()
        return row["sender_id"] if row else None
