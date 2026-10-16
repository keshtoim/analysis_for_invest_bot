from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message

from app.middlewares.maintenance import MaintenanceMiddleware
from app.services import maintenance
from app.utils import auth


@pytest.fixture(autouse=True)
def _use_temp_flag_and_owner(tmp_path, monkeypatch):
    test_file = tmp_path / "maintenance"
    monkeypatch.setattr(maintenance, "_file", test_file)
    monkeypatch.setattr(maintenance, "_on", False)
    monkeypatch.setattr(auth, "OWNER_CHAT_ID", "1")


def _fake_user(user_id: int) -> MagicMock:
    user = MagicMock()
    user.id = user_id
    return user


async def test_non_owner_is_blocked_during_maintenance():
    maintenance.toggle()

    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    handler = AsyncMock()

    middleware = MaintenanceMiddleware()
    result = await middleware(handler, message, {"event_from_user": _fake_user(2)})

    handler.assert_not_called()
    message.answer.assert_awaited_once_with(maintenance.NOTICE)
    assert result is None


async def test_owner_passes_through_during_maintenance():
    maintenance.toggle()

    message = MagicMock(spec=Message)
    handler = AsyncMock(return_value="handled")

    middleware = MaintenanceMiddleware()
    result = await middleware(handler, message, {"event_from_user": _fake_user(1)})

    handler.assert_awaited_once()
    assert result == "handled"


async def test_everyone_passes_through_when_maintenance_off():
    message = MagicMock(spec=Message)
    handler = AsyncMock(return_value="handled")

    middleware = MaintenanceMiddleware()
    result = await middleware(handler, message, {"event_from_user": _fake_user(2)})

    handler.assert_awaited_once()
    assert result == "handled"


async def test_callback_query_shows_alert_during_maintenance():
    maintenance.toggle()

    callback = MagicMock(spec=CallbackQuery)
    callback.answer = AsyncMock()
    handler = AsyncMock()

    middleware = MaintenanceMiddleware()
    await middleware(handler, callback, {"event_from_user": _fake_user(2)})

    handler.assert_not_called()
    callback.answer.assert_awaited_once_with(maintenance.NOTICE, show_alert=True)


async def test_missing_event_from_user_is_blocked_during_maintenance():
    maintenance.toggle()

    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    handler = AsyncMock()

    middleware = MaintenanceMiddleware()
    result = await middleware(handler, message, {})

    handler.assert_not_called()
    assert result is None
