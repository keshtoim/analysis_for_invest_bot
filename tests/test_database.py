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
    data = {
        "company_name": "Лукойл",
        "news": [{"title": "Новость", "snippet": "Текст", "url": "https://x"}],
        "moex": {"ticker": "LKOH", "last_price": 5438, "change_percent": -0.85,
                  "market_cap": 3_780_000_000_000, "currency": "RUB"},
        "sector": {"name": "Нефтегазовая отрасль", "news": [{"title": "Сектор", "snippet": "С", "url": "u"}]},
    }
    await database.save_company_cache("Лукойл", data)

    cached = await database.get_cached_company_data("Лукойл")

    # Имя сектора в БД нормализовано (strip+casefold) — остальное совпадает как есть
    assert cached["sector"]["name"] == "нефтегазовая отрасль"
    assert cached["sector"]["news"] == data["sector"]["news"]
    assert cached["news"] == data["news"]
    assert cached["moex"] == data["moex"]
    assert cached["company_name"] == "Лукойл"


async def test_company_cache_hit_is_case_and_whitespace_insensitive():
    await database.init_db()
    data = {"company_name": "Лукойл", "news": [], "moex": None, "sector": None}
    await database.save_company_cache("Лукойл", data)

    # Попадание в кэш не зависит от регистра/пробелов; company_name в ответе —
    # это регистр текущего запроса, а не исходного (БД хранит нормализованный ключ).
    by_upper = await database.get_cached_company_data(" ЛУКОЙЛ ")
    assert by_upper == {**data, "company_name": "ЛУКОЙЛ"}

    by_lower = await database.get_cached_company_data("лукойл")
    assert by_lower == {**data, "company_name": "лукойл"}


async def test_expired_company_cache_is_ignored():
    await database.init_db()
    data = {"company_name": "Лукойл", "news": [], "moex": None, "sector": None}
    await database.save_company_cache("Лукойл", data)

    # Переводим expires_at в прошлое напрямую в БД, минуя CACHE_TTL_HOURS
    import aiosqlite

    past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(database.DB_PATH) as db:
        await db.execute(
            "UPDATE companies SET expires_at = ? WHERE name = ?",
            (past, database._normalize_name("Лукойл")),
        )
        await db.commit()

    assert await database.get_cached_company_data("Лукойл") is None


async def test_save_company_cache_upserts_by_query():
    await database.init_db()
    await database.save_company_cache("Лукойл", {"news": [{"title": "Старая"}], "moex": None, "sector": None})
    await database.save_company_cache("Лукойл", {"news": [{"title": "Новая"}], "moex": None, "sector": None})

    import aiosqlite

    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM companies") as cursor:
            (count,) = await cursor.fetchone()

    assert count == 1
    cached = await database.get_cached_company_data("Лукойл")
    assert cached["news"] == [{"title": "Новая", "snippet": None, "url": None}]


async def test_fresh_sector_is_reused_between_companies():
    await database.init_db()
    sector_news = [{"title": "Сектор", "snippet": "С", "url": "u"}]
    await database.save_company_cache(
        "Лукойл", {"news": [], "moex": None, "sector": {"name": "Нефтегаз", "news": sector_news}}
    )
    await database.save_company_cache(
        "Роснефть", {"news": [], "moex": None, "sector": {"name": "Нефтегаз", "news": []}}
    )

    import aiosqlite

    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM sectors") as cursor:
            (sector_count,) = await cursor.fetchone()

    assert sector_count == 1  # один и тот же свежий сектор, не задвоился
    rosneft = await database.get_cached_company_data("Роснефть")
    assert rosneft["sector"]["news"] == sector_news  # новости не затёрлись пустым списком


async def test_expired_sector_is_refreshed():
    await database.init_db()
    await database.save_company_cache(
        "Лукойл", {"news": [], "moex": None, "sector": {"name": "Нефтегаз", "news": [{"title": "Старое"}]}}
    )

    import aiosqlite

    past = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    async with aiosqlite.connect(database.DB_PATH) as db:
        await db.execute("UPDATE sectors SET expires_at = ?", (past,))
        await db.commit()

    new_news = [{"title": "Свежее", "snippet": None, "url": None}]
    await database.save_company_cache(
        "Роснефть", {"news": [], "moex": None, "sector": {"name": "Нефтегаз", "news": new_news}}
    )

    rosneft = await database.get_cached_company_data("Роснефть")
    assert rosneft["sector"]["news"] == new_news


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


async def test_get_user_messages_empty_for_unknown_user():
    await database.init_db()
    assert await database.get_user_messages(1) == []


async def test_log_message_appears_in_history():
    await database.init_db()
    await database.log_message(1, "Лукойл")
    await database.log_message(1, "Сбербанк")

    history = await database.get_user_messages(1)

    assert [m["text"] for m in history] == ["Лукойл", "Сбербанк"]


async def test_get_user_messages_oldest_first_within_limit():
    await database.init_db()
    for i in range(5):
        await database.log_message(1, f"msg{i}")

    history = await database.get_user_messages(1, limit=3)

    assert [m["text"] for m in history] == ["msg2", "msg3", "msg4"]


async def test_get_user_messages_scoped_to_user():
    await database.init_db()
    await database.log_message(1, "от юзера 1")
    await database.log_message(2, "от юзера 2")

    history = await database.get_user_messages(1)

    assert [m["text"] for m in history] == ["от юзера 1"]


async def test_grant_subscription_logs_event():
    await database.init_db()
    await database.grant_subscription(1, days=30, source="prodamus", external_id="ext-1")

    events = await database.get_subscription_events(1)

    assert len(events) == 1
    assert events[0]["action"] == "grant"
    assert events[0]["source"] == "prodamus"
    assert events[0]["external_id"] == "ext-1"


async def test_revoke_subscription_logs_event():
    await database.init_db()
    await database.grant_subscription(1, days=30)
    await database.revoke_subscription(1)

    events = await database.get_subscription_events(1)

    assert [e["action"] for e in events] == ["grant", "revoke"]


async def test_subscription_events_scoped_to_user():
    await database.init_db()
    await database.grant_subscription(1, days=30)
    await database.grant_subscription(2, days=30)

    events = await database.get_subscription_events(1)

    assert len(events) == 1
