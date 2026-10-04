from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message

from app.db import database
from app.middlewares.blocked_user import BLOCKED_TEXT, BlockedUserMiddleware


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))


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
