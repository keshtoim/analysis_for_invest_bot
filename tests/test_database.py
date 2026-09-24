from datetime import datetime, timedelta

import pytest

from app.db import database


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))


async def test_upsert_user_inserts_then_updates():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    await database.upsert_user(user_id=1, username="alice2", first_name="Alice")

    import aiosqlite

    async with aiosqlite.connect(database.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = 1") as cursor:
            rows = await cursor.fetchall()

    assert len(rows) == 1
    assert rows[0]["username"] == "alice2"


async def test_company_cache_miss_returns_none():
    await database.init_db()
    assert await database.get_cached_company_data("Тест") is None


async def test_company_cache_hit_returns_saved_data():
    await database.init_db()
    data = {"company_name": "Лукойл", "news": [], "moex": None, "sector": None}
    await database.save_company_cache("Лукойл", data, source="test")

    cached = await database.get_cached_company_data("Лукойл")

    assert cached == data


async def test_expired_company_cache_is_ignored(monkeypatch):
    await database.init_db()
    data = {"company_name": "Лукойл", "news": [], "moex": None, "sector": None}
    await database.save_company_cache("Лукойл", data, source="test")

    # Переводим expires_at в прошлое напрямую в БД, минуя CACHE_TTL_HOURS
    import aiosqlite

    past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(database.DB_PATH) as db:
        await db.execute(
            "UPDATE company_cache SET expires_at = ? WHERE company_query = ?",
            (past, "Лукойл"),
        )
        await db.commit()

    assert await database.get_cached_company_data("Лукойл") is None


async def test_save_company_cache_upserts_by_query():
    await database.init_db()
    await database.save_company_cache("Лукойл", {"v": 1}, source="test")
    await database.save_company_cache("Лукойл", {"v": 2}, source="test")

    import aiosqlite

    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM company_cache") as cursor:
            (count,) = await cursor.fetchone()

    assert count == 1
    assert await database.get_cached_company_data("Лукойл") == {"v": 2}
