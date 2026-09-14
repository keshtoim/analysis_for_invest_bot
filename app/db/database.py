import json
from datetime import datetime, timedelta

import aiosqlite

from app.config import CACHE_TTL_HOURS, DB_PATH

CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    joined_at TEXT DEFAULT CURRENT_TIMESTAMP
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


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_COMPANY_CACHE_TABLE)
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
