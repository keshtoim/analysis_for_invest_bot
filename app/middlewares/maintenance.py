from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.services import maintenance
from app.utils.auth import is_owner


class MaintenanceMiddleware(BaseMiddleware):
    """Пока включён режим техработ — всем, кроме владельца, отвечаем «вернусь
    позже» и не пускаем дальше. Владелец работает как обычно (в т.ч. чтобы
    выключить режим)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if maintenance.is_on() and (user is None or not is_owner(user.id)):
            if isinstance(event, CallbackQuery):
                await event.answer(maintenance.NOTICE, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(maintenance.NOTICE)
            return None

        return await handler(event, data)
