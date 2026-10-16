from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from app.db import database
from app.handlers.common import cmd_start
from app.keyboards.main_menu import BTN_ANALYSIS
from app.keyboards.onboarding import BTN_START


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))


def _fake_message(user_id: int) -> MagicMock:
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = user_id
    message.from_user.username = "alice"
    message.from_user.first_name = "Alice"
    return message


async def test_new_user_gets_start_keyboard():
    await database.init_db()
    message = _fake_message(1)

    await cmd_start(message)

    keyboard = message.answer.call_args.kwargs["reply_markup"]
    assert keyboard.keyboard[0][0].text == BTN_START


async def test_returning_user_gets_main_menu_keyboard():
    await database.init_db()
    await database.upsert_user(user_id=1, username="alice", first_name="Alice")
    message = _fake_message(1)

    await cmd_start(message)

    keyboard = message.answer.call_args.kwargs["reply_markup"]
    assert keyboard.keyboard[0][0].text == BTN_ANALYSIS
