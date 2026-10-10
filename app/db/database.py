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

# Сектор переиспользуется между компаниями (если ещё свежий) — поэтому
# отдельная сущность, а не вложенный JSON внутри company. Аналогично
# news вынесены в свои таблицы вместо повторяющейся группы в блобе.
CREATE_SECTORS_TABLE = """
CREATE TABLE IF NOT EXISTS sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    fetched_at TEXT,
    expires_at TEXT
)
"""

CREATE_COMPANIES_TABLE = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sector_id INTEGER REFERENCES sectors(id),
    fetched_at TEXT,
    expires_at TEXT
)
"""

CREATE_COMPANY_NEWS_TABLE = """
CREATE TABLE IF NOT EXISTS company_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    title TEXT,
    snippet TEXT,
    url TEXT
)
"""

CREATE_SECTOR_NEWS_TABLE = """
CREATE TABLE IF NOT EXISTS sector_news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_id INTEGER NOT NULL REFERENCES sectors(id),
    title TEXT,
    snippet TEXT,
    url TEXT
)
"""

CREATE_COMPANY_MARKET_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS company_market_data (
    company_id INTEGER PRIMARY KEY REFERENCES companies(id),
    ticker TEXT,
    last_price REAL,
    change_percent REAL,
    market_cap REAL,
    currency TEXT
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

# Лог для /stats — отдельно от companies, потому что кэш не растёт при
# повторных запросах одной и той же компании (там UPSERT), а сюда пишется
# каждый успешно выполненный анализ.
CREATE_ANALYSIS_REQUESTS_TABLE = """
CREATE TABLE IF NOT EXISTS analysis_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    analysis_type TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


# Аудит-лог: subscriptions хранит только текущее состояние, без истории
# выдач/отзывов. Пишется при каждом вызове grant_subscription/revoke_subscription.
CREATE_SUBSCRIPTION_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS subscription_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    source TEXT,
    external_id TEXT,
    created_at TEXT NOT NULL
)
"""

CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


async def _ensure_users_is_blocked_column(db: aiosqlite.Connection) -> None:
    """Для БД, созданных до появления блокировки — ALTER TABLE не умеет IF NOT EXISTS."""
    async with db.execute("PRAGMA table_info(users)") as cursor:
        columns = [row[1] async for row in cursor]
    if "is_blocked" not in columns:
        await db.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER NOT NULL DEFAULT 0")


async def _ensure_analysis_requests_schema(db: aiosqlite.Connection) -> None:
    """Старые БД хранили company_name TEXT — переносим на company_id с
    созданием недостающих companies по историческим названиям, не теряя
    накопленную для /stats статистику."""
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_requests'"
    ) as cursor:
        exists = await cursor.fetchone() is not None

    if not exists:
        await db.execute(CREATE_ANALYSIS_REQUESTS_TABLE)
        return

    async with db.execute("PRAGMA table_info(analysis_requests)") as cursor:
        columns = [row[1] async for row in cursor]

    if "company_id" in columns:
        return

    await db.execute("ALTER TABLE analysis_requests RENAME TO analysis_requests_old")
    await db.execute(CREATE_ANALYSIS_REQUESTS_TABLE)

    db.row_factory = aiosqlite.Row
    async with db.execute(
        "SELECT user_id, company_name, analysis_type, created_at FROM analysis_requests_old"
    ) as cursor:
        old_rows = await cursor.fetchall()

    for row in old_rows:
        name = _normalize_name(row["company_name"])
        async with db.execute("SELECT id FROM companies WHERE name = ?", (name,)) as c:
            existing = await c.fetchone()

        if existing is not None:
            company_id = existing[0]
        else:
            insert_cursor = await db.execute("INSERT INTO companies (name) VALUES (?)", (name,))
            company_id = insert_cursor.lastrowid

        await db.execute(
            "INSERT INTO analysis_requests (user_id, company_id, analysis_type, created_at) "
            "VALUES (?, ?, ?, ?)",
            (row["user_id"], company_id, row["analysis_type"], row["created_at"]),
        )

    await db.execute("DROP TABLE analysis_requests_old")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_USERS_TABLE)
        await db.execute(CREATE_SECTORS_TABLE)
        await db.execute(CREATE_COMPANIES_TABLE)
        await db.execute(CREATE_COMPANY_NEWS_TABLE)
        await db.execute(CREATE_SECTOR_NEWS_TABLE)
        await db.execute(CREATE_COMPANY_MARKET_DATA_TABLE)
        await db.execute(CREATE_SUBSCRIPTIONS_TABLE)
        await db.execute(CREATE_MESSAGES_TABLE)
        await db.execute(CREATE_SUBSCRIPTION_EVENTS_TABLE)
        await db.execute("DROP TABLE IF EXISTS company_cache")
        await _ensure_users_is_blocked_column(db)
        await _ensure_analysis_requests_schema(db)
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


def _normalize_name(name: str) -> str:
    """"Лукойл"/"ЛУКОЙЛ"/"лукойл " — один и тот же ключ (компании и сектора)."""
    return name.strip().casefold()


async def get_cached_company_data(company_query: str) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM companies WHERE name = ?", (_normalize_name(company_query),)
        ) as cursor:
            company = await cursor.fetchone()

        if (
            company is None
            or company["expires_at"] is None
            or datetime.fromisoformat(company["expires_at"]) < datetime.utcnow()
        ):
            return None

        company_id = company["id"]

        async with db.execute(
            "SELECT title, snippet, url FROM company_news WHERE company_id = ?", (company_id,)
        ) as cursor:
            news = [dict(row) for row in await cursor.fetchall()]

        async with db.execute(
            "SELECT ticker, last_price, change_percent, market_cap, currency "
            "FROM company_market_data WHERE company_id = ?",
            (company_id,),
        ) as cursor:
            moex_row = await cursor.fetchone()
        moex = dict(moex_row) if moex_row else None

        sector = None
        if company["sector_id"] is not None:
            async with db.execute(
                "SELECT name FROM sectors WHERE id = ?", (company["sector_id"],)
            ) as cursor:
                sector_row = await cursor.fetchone()
            if sector_row is not None:
                async with db.execute(
                    "SELECT title, snippet, url FROM sector_news WHERE sector_id = ?",
                    (company["sector_id"],),
                ) as cursor:
                    sector_news = [dict(row) for row in await cursor.fetchall()]
                sector = {"name": sector_row["name"], "news": sector_news}

    return {
        "company_name": company_query.strip(),
        "news": news,
        "moex": moex,
        "sector": sector,
    }


async def _upsert_sector(
    db: aiosqlite.Connection,
    sector_name: str,
    sector_news: list[dict],
    now: datetime,
    expires_at: datetime,
) -> int:
    name = _normalize_name(sector_name)
    db.row_factory = aiosqlite.Row
    async with db.execute("SELECT id, expires_at FROM sectors WHERE name = ?", (name,)) as cursor:
        existing = await cursor.fetchone()

    if existing is not None and datetime.fromisoformat(existing["expires_at"]) >= now:
        # Сектор ещё свежий (могла освежить другая компания того же сектора) —
        # переиспользуем, новости не трогаем.
        return existing["id"]

    if existing is not None:
        sector_id = existing["id"]
        await db.execute(
            "UPDATE sectors SET fetched_at = ?, expires_at = ? WHERE id = ?",
            (now.isoformat(), expires_at.isoformat(), sector_id),
        )
    else:
        cursor = await db.execute(
            "INSERT INTO sectors (name, fetched_at, expires_at) VALUES (?, ?, ?)",
            (name, now.isoformat(), expires_at.isoformat()),
        )
        sector_id = cursor.lastrowid

    await db.execute("DELETE FROM sector_news WHERE sector_id = ?", (sector_id,))
    if sector_news:
        await db.executemany(
            "INSERT INTO sector_news (sector_id, title, snippet, url) VALUES (?, ?, ?, ?)",
            [(sector_id, item.get("title"), item.get("snippet"), item.get("url")) for item in sector_news],
        )

    return sector_id


async def save_company_cache(company_query: str, raw_data: dict) -> None:
    name = _normalize_name(company_query)
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=CACHE_TTL_HOURS)

    async with aiosqlite.connect(DB_PATH) as db:
        sector_id = None
        sector_data = raw_data.get("sector")
        if sector_data and sector_data.get("name"):
            sector_id = await _upsert_sector(
                db, sector_data["name"], sector_data.get("news") or [], now, expires_at
            )

        await db.execute(
            """
            INSERT INTO companies (name, sector_id, fetched_at, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                sector_id = excluded.sector_id,
                fetched_at = excluded.fetched_at,
                expires_at = excluded.expires_at
            """,
            (name, sector_id, now.isoformat(), expires_at.isoformat()),
        )
        async with db.execute("SELECT id FROM companies WHERE name = ?", (name,)) as cursor:
            company_id = (await cursor.fetchone())[0]

        await db.execute("DELETE FROM company_news WHERE company_id = ?", (company_id,))
        news_items = raw_data.get("news") or []
        if news_items:
            await db.executemany(
                "INSERT INTO company_news (company_id, title, snippet, url) VALUES (?, ?, ?, ?)",
                [(company_id, item.get("title"), item.get("snippet"), item.get("url")) for item in news_items],
            )

        await db.execute("DELETE FROM company_market_data WHERE company_id = ?", (company_id,))
        moex = raw_data.get("moex")
        if moex:
            await db.execute(
                """
                INSERT INTO company_market_data
                    (company_id, ticker, last_price, change_percent, market_cap, currency)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    moex.get("ticker"),
                    moex.get("last_price"),
                    moex.get("change_percent"),
                    moex.get("market_cap"),
                    moex.get("currency"),
                ),
            )

        await db.commit()


async def _log_subscription_event(
    db: aiosqlite.Connection,
    user_id: int,
    action: str,
    source: str | None,
    external_id: str | None,
) -> None:
    await db.execute(
        """
        INSERT INTO subscription_events (user_id, action, source, external_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, action, source, external_id, datetime.utcnow().isoformat()),
    )


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
        await _log_subscription_event(db, user_id, "grant", source, external_id)
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
        await _log_subscription_event(db, user_id, "revoke", source=None, external_id=None)
        await db.commit()


async def get_subscription_events(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT action, source, external_id, created_at FROM subscription_events "
            "WHERE user_id = ? ORDER BY id",
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in rows]


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


async def log_message(user_id: int, text: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO messages (user_id, text, created_at) VALUES (?, ?, ?)",
            (user_id, text, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_user_messages(user_id: int, limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT text, created_at FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
    return [dict(row) for row in reversed(rows)]


async def log_analysis_request(user_id: int, company_name: str, analysis_type: str) -> None:
    name = _normalize_name(company_name)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM companies WHERE name = ?", (name,)) as cursor:
            row = await cursor.fetchone()

        if row is not None:
            company_id = row[0]
        else:
            # На практике get_company_data уже создал запись к этому моменту —
            # но не падаем, если порядок вызовов когда-нибудь поменяется.
            insert_cursor = await db.execute("INSERT INTO companies (name) VALUES (?)", (name,))
            company_id = insert_cursor.lastrowid

        await db.execute(
            """
            INSERT INTO analysis_requests (user_id, company_id, analysis_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, company_id, analysis_type, datetime.utcnow().isoformat()),
        )
        await db.commit()
