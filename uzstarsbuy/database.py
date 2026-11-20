import os
import time
import aiosqlite
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uzbstarsbuy.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                referred_by INTEGER,
                balance REAL DEFAULT 0.0,
                stars_balance INTEGER DEFAULT 0,
                stars_purchased INTEGER DEFAULT 0,
                orders_count INTEGER DEFAULT 0,
                is_blocked INTEGER DEFAULT 0,
                created_at REAL,
                last_active REAL
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                url TEXT,
                chat_id TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                reward_paid INTEGER DEFAULT 0,
                created_at REAL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stars_count INTEGER,
                amount_uzs REAL,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                created_at REAL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Default settings if not exists
        default_settings = [
            ("star_price", "220"),
            ("referal_price", "100"),
            ("support_admin", "@legenda_adminn"),
            ("instagram_url", "https://www.instagram.com/uzbstarsbu?cplk=MXJtb2lzZ3Y2Zmd3Zw=="),
            ("video_guide_url", "https://t.me/legenda_ovoz_ishonch/5"),
            ("webapp_url", "https://liquidstars.vercel.app/"),
            ("card_humo", "4067070028729676"),
            ("card_uzcard", "5614687307720079"),
            ("humo_name", "M/A"),
            ("uzcard_name", "M/A"),
            ("channel_news", "@UZBStarsbuy")
        ]
        for k, v in default_settings:
            await db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

        # Default mandatory channel only if first initialization
        async with db.execute("SELECT value FROM settings WHERE key = 'channels_initialized'") as cur:
            row = await cur.fetchone()
            if not row:
                await db.execute("""
                    INSERT OR IGNORE INTO channels (id, title, url, chat_id, is_active)
                    VALUES (1, '❌ 𝙐𝙕𝘽 | 𝙎𝙏𝘼𝙍𝙎 - 𝙉𝙀𝙒𝙎', 'https://t.me/UZBStarsbuy', '@UZBStarsbuy', 1)
                """)
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('channels_initialized', '1')")

        await db.commit()

async def add_or_update_user(user_id: int, username: Optional[str], first_name: Optional[str], referred_by: Optional[int] = None) -> bool:
    """Returns True if user is newly created, False if already exists"""
    now = time.time()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id, referred_by FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                await db.execute("""
                    UPDATE users SET username = ?, first_name = ?, last_active = ? WHERE user_id = ?
                """, (username, first_name, now, user_id))
                await db.commit()
                return False
            else:
                await db.execute("""
                    INSERT INTO users (user_id, username, first_name, referred_by, created_at, last_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, first_name, referred_by, now, now))
                
                # Check referral
                if referred_by and referred_by != user_id:
                    try:
                        await db.execute("""
                            INSERT INTO referrals (referrer_id, referred_id, created_at)
                            VALUES (?, ?, ?)
                        """, (referred_by, user_id, now))
                        # Add referral bonus to referrer
                        ref_bonus_str = await get_setting("referal_price", "100")
                        ref_bonus = float(ref_bonus_str)
                        await db.execute("""
                            UPDATE users SET balance = balance + ? WHERE user_id = ?
                        """, (ref_bonus, referred_by))
                    except Exception:
                        pass
                await db.commit()
                return True

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_all_user_ids() -> List[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE is_blocked = 0") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

async def get_total_users() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_today_users() -> int:
    today_start = time.time() - (time.time() % 86400)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (today_start,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_active_channels() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM channels WHERE is_active = 1") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def add_channel(title: str, url: str, chat_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO channels (title, url, chat_id, is_active)
            VALUES (?, ?, ?, 1)
        """, (title, url, chat_id))
        await db.commit()

async def delete_channel(channel_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        await db.commit()

async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else default

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()

async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0
