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


async def test_company_cache_hit_is_case_and_whitespace_insensitive():
    await database.init_db()
    data = {"company_name": "Лукойл", "news": [], "moex": None, "sector": None}
    await database.save_company_cache("Лукойл", data, source="test")

    assert await database.get_cached_company_data(" ЛУКОЙЛ ") == data
    assert await database.get_cached_company_data("лукойл") == data


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
            (past, database._normalize_company_query("Лукойл")),
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


async def test_get_subscription_returns_none_when_absent():
    await database.init_db()
    assert await database.get_subscription(1) is None


async def test_grant_subscription_sets_expiry_in_the_future():
    await database.init_db()
    await database.grant_subscription(1, days=30)

    sub = await database.get_subscription(1)

    assert sub is not None
    assert sub["plan"] == "default"
    assert sub["source"] == "manual"
    assert datetime.fromisoformat(sub["expires_at"]) > datetime.utcnow() + timedelta(days=29)


async def test_grant_subscription_upserts_by_user():
    await database.init_db()
    await database.grant_subscription(1, days=10, source="manual")
    await database.grant_subscription(1, days=30, source="prodamus", external_id="ext-1")

    sub = await database.get_subscription(1)

    assert sub["source"] == "prodamus"
    assert sub["external_id"] == "ext-1"


async def test_revoke_subscription_removes_it():
    await database.init_db()
    await database.grant_subscription(1, days=30)

    await database.revoke_subscription(1)

    assert await database.get_subscription(1) is None


async def test_new_user_is_not_blocked_by_default():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")

    assert await database.is_user_blocked(1) is False


async def test_block_user_sets_flag():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")

    found = await database.block_user(1)

    assert found is True
    assert await database.is_user_blocked(1) is True


async def test_unblock_user_clears_flag():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    await database.block_user(1)

    found = await database.unblock_user(1)

    assert found is True
    assert await database.is_user_blocked(1) is False


async def test_block_user_returns_false_for_unknown_user():
    await database.init_db()
    assert await database.block_user(999) is False


async def test_is_user_blocked_false_for_unknown_user():
    await database.init_db()
    assert await database.is_user_blocked(999) is False


async def test_init_db_is_idempotent_with_is_blocked_column():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    await database.block_user(1)

    # Повторный init_db (как при каждом рестарте бота) не должен ломать данные
    await database.init_db()

    assert await database.is_user_blocked(1) is True
