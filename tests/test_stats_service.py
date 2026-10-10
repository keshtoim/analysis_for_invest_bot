import pytest

from app.db import database
from app.services import stats_service


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(stats_service, "DB_PATH", str(tmp_path / "test.db"))


async def test_stats_on_empty_db():
    await database.init_db()

    stats = await stats_service.get_stats()

    assert stats["total_users"] == 0
    assert stats["total_requests"] == 0
    assert stats["active_users_7d"] == 0
    assert stats["top_companies"] == []
    assert stats["requests_by_type"] == []
    assert stats["cached_companies"] == 0
    assert stats["active_subscriptions"] == 0
    assert stats["blocked_users"] == 0


async def test_stats_counts_users_and_requests():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    await database.upsert_user(user_id=2, username="bob", first_name="Bob")

    await database.log_analysis_request(1, "Лукойл", "swot")
    await database.log_analysis_request(1, "Лукойл", "pestel")
    await database.log_analysis_request(2, "Сбербанк", "swot")

    stats = await stats_service.get_stats()

    assert stats["total_users"] == 2
    assert stats["new_users_24h"] == 2
    assert stats["total_requests"] == 3
    assert stats["requests_24h"] == 3
    assert stats["active_users_7d"] == 2


async def test_stats_top_companies_ordered_by_count():
    await database.init_db()
    for _ in range(3):
        await database.log_analysis_request(1, "Лукойл", "swot")
    await database.log_analysis_request(1, "Сбербанк", "swot")

    stats = await stats_service.get_stats()

    # Имя компании в БД нормализовано (strip+casefold)
    assert stats["top_companies"][0] == ("лукойл", 3)
    assert stats["top_companies"][1] == ("сбербанк", 1)


async def test_stats_requests_by_type():
    await database.init_db()
    await database.log_analysis_request(1, "Лукойл", "swot")
    await database.log_analysis_request(1, "Лукойл", "swot")
    await database.log_analysis_request(1, "Лукойл", "pestel")

    stats = await stats_service.get_stats()

    by_type = dict(stats["requests_by_type"])
    assert by_type["swot"] == 2
    assert by_type["pestel"] == 1


async def test_stats_counts_active_subscriptions():
    await database.init_db()
    await database.grant_subscription(1, days=30)

    stats = await stats_service.get_stats()

    assert stats["active_subscriptions"] == 1


async def test_stats_counts_blocked_users():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    await database.upsert_user(user_id=2, username="bob", first_name="Bob")
    await database.block_user(1)

    stats = await stats_service.get_stats()

    assert stats["blocked_users"] == 1
