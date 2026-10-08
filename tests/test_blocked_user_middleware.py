from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message

from app.db import database
from app.middlewares import blocked_user as blocked_user_middleware_module
from app.middlewares.blocked_user import BLOCKED_TEXT, BlockedUserMiddleware


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))
    blocked_user_middleware_module._cache.clear()


def _fake_user(user_id: int) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


async def test_blocked_message_is_short_circuited():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    await database.block_user(1)

    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    handler = AsyncMock()

    middleware = BlockedUserMiddleware()
    result = await middleware(handler, message, {"event_from_user": _fake_user(1)})

    handler.assert_not_called()
    message.answer.assert_awaited_once_with(BLOCKED_TEXT)
    assert result is None


async def test_blocked_callback_shows_alert():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    await database.block_user(1)

    callback = MagicMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    handler = AsyncMock()

    middleware = BlockedUserMiddleware()
    await middleware(handler, callback, {"event_from_user": _fake_user(1)})

    handler.assert_not_called()
    callback.answer.assert_awaited_once_with(BLOCKED_TEXT, show_alert=True)


async def test_not_blocked_user_passes_through():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")

    message = MagicMock(spec=Message)
    handler = AsyncMock(return_value="handled")

    middleware = BlockedUserMiddleware()
    result = await middleware(handler, message, {"event_from_user": _fake_user(1)})

    handler.assert_awaited_once()
    assert result == "handled"


async def test_missing_event_from_user_passes_through():
    handler = AsyncMock(return_value="handled")
    message = MagicMock(spec=Message)

    middleware = BlockedUserMiddleware()
    result = await middleware(handler, message, {})

    handler.assert_awaited_once()
    assert result == "handled"


async def test_block_status_is_cached_between_calls(monkeypatch):
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")

    spy = AsyncMock(wraps=database.is_user_blocked)
    monkeypatch.setattr(blocked_user_middleware_module, "is_user_blocked", spy)

    assert await blocked_user_middleware_module._is_blocked_cached(1) is False
    assert await blocked_user_middleware_module._is_blocked_cached(1) is False

    spy.assert_awaited_once()


async def test_block_status_cache_expires_after_ttl(monkeypatch):
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    monkeypatch.setattr(blocked_user_middleware_module, "CACHE_TTL_SECONDS", 0)

    assert await blocked_user_middleware_module._is_blocked_cached(1) is False

    await database.block_user(1)

    assert await blocked_user_middleware_module._is_blocked_cached(1) is True
