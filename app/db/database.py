import json
from datetime import datetime, timedelta

import aiosqlite

from app.config import CACHE_TTL_HOURS, DB_PATH

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_blocked INTEGER NOT NULL DEFAULT 0
)
"""

CREATE_COMPANY_CACHE_TABLE = """
CREATE TABLE IF NOT EXISTS company_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_query TEXT NOT NULL UNIQUE,
    source TEXT,
    raw_data TEXT,
    fetched_at TEXT,
    expires_at TEXT
)
"""

# source/external_id — под будущий вебхук любого из платёжных сервисов
# (Prodamus/Paywall.tech/Lava.top); пока заполняются только вручную ("manual").
CREATE_SUBSCRIPTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    plan TEXT NOT NULL DEFAULT 'default',
    source TEXT,
    external_id TEXT,
    granted_at TEXT,
    expires_at TEXT
)
"""

# Лог для /stats — отдельно от company_cache, потому что кэш не растёт при
# повторных запросах одной и той же компании (там UPSERT), а сюда пишется
# каждый успешно выполненный анализ.
CREATE_ANALYSIS_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


async def _ensure_users_is_blocked_column(db: aiosqlite.Connection) -> None:
    """Для БД, созданных до появления блокировки — ALTER TABLE не умеет IF NOT EXISTS."""
    async with db.execute("PRAGMA table_info(users)") as cursor:
        columns = [row[1] async for row in cursor]
    if "is_blocked" not in columns:
        await db.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER NOT NULL DEFAULT 0")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_COMPANY_CACHE_TABLE)
        await db.execute(CREATE_SUBSCRIPTIONS_TABLE)
        await db.execute(CREATE_ANALYSIS_REQUESTS_TABLE)
        await _ensure_users_is_blocked_column(db)
        await db.commit()


async def upsert_user(user_id: int, username: str | None, first_name: str | None) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name
            """,
            (user_id, username, first_name),
        )
        await db.commit()


async def get_cached_company_data(company_query: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT raw_data, expires_at FROM company_cache WHERE company_query = ?",
            (company_query,),
        ) as cursor:
            row = await cursor.fetchone()

    if row is None or datetime.fromisoformat(row["expires_at"]) < datetime.utcnow():
        return None
    return json.loads(row["raw_data"])


async def save_company_cache(company_query: str, raw_data: dict, source: str) -> None:
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=CACHE_TTL_HOURS)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO company_cache (company_query, source, raw_data, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(company_query) DO UPDATE SET
                source = excluded.source,
                raw_data = excluded.raw_data,
                fetched_at = excluded.fetched_at,
                expires_at = excluded.expires_at
            """,
            (company_query, source, json.dumps(raw_data), now.isoformat(), expires_at.isoformat()),
        )
        await db.commit()


async def grant_subscription(
    user_id: int,
    days: int,
    plan: str = "default",
    source: str = "manual",
    external_id: str | None = None,
) -> None:
    now = datetime.utcnow()
    expires_at = now + timedelta(days=days)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO subscriptions (user_id, plan, source, external_id, granted_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                plan = excluded.plan,
                source = excluded.source,
                external_id = excluded.external_id,
                granted_at = excluded.granted_at,
                expires_at = excluded.expires_at
            """,
            (user_id, plan, source, external_id, now.isoformat(), expires_at.isoformat()),
        )
        await db.commit()


async def get_subscription(user_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return dict(row) if row else None


async def revoke_subscription(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM subscriptions WHERE user_id = ?", (user_id,))
        await db.commit()


async def block_user(user_id: int) -> bool:
    """True, если юзер с таким user_id вообще найден (и заблокирован)."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount > 0


async def unblock_user(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))
        await db.commit()
        return cursor.rowcount > 0


async def is_user_blocked(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT is_blocked FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
    return bool(row and row[0])


async def log_analysis_request(user_id: int, company_name: str, analysis_type: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO analysis_requests (user_id, company_name, analysis_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, company_name, analysis_type, datetime.utcnow().isoformat()),
        )
        await db.commit()
