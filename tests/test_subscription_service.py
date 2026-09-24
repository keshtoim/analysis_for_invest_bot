from datetime import datetime, timedelta

import pytest

from app.db import database
from app.services import subscription_service


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))


async def test_no_subscription_is_not_subscribed():
    await database.init_db()
    assert await subscription_service.is_subscribed(1) is False


async def test_active_subscription_is_subscribed():
    await database.init_db()
    await database.grant_subscription(1, days=30)

    assert await subscription_service.is_subscribed(1) is True


async def test_expired_subscription_is_not_subscribed():
    await database.init_db()
    await database.grant_subscription(1, days=30)

    import aiosqlite

    past = (datetime.utcnow() - timedelta(days=1)).isoformat()
    async with aiosqlite.connect(database.DB_PATH) as db:
        await db.execute("UPDATE subscriptions SET expires_at = ? WHERE user_id = 1", (past,))
        await db.commit()

    assert await subscription_service.is_subscribed(1) is False
