from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from app.db import database
from app.middlewares.message_logger import MessageLoggingMiddleware


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))


def _fake_message(user_id: int, text: str | None) -> MagicMock:
    message = MagicMock(spec=Message)
    message.text = text
    message.from_user = MagicMock()
    message.from_user.id = user_id
    return message


async def test_logs_message_text_and_calls_handler():
    await database.init_db()
    handler = AsyncMock(return_value="handled")
    message = _fake_message(1, "Лукойл")

    middleware = MessageLoggingMiddleware()
    result = await middleware(handler, message, {})

    handler.assert_awaited_once()
    assert result == "handled"
    history = await database.get_user_messages(1)
    assert [m["text"] for m in history] == ["Лукойл"]


async def test_skips_logging_for_non_text_message():
    await database.init_db()
    handler = AsyncMock(return_value="handled")
    message = _fake_message(1, None)

    middleware = MessageLoggingMiddleware()
    await middleware(handler, message, {})

    assert await database.get_user_messages(1) == []
