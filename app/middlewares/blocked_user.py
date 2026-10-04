from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.db.database import is_user_blocked

BLOCKED_TEXT = "🚫 Доступ к боту ограничен."


class BlockedUserMiddleware(BaseMiddleware):
    """Глобально режет любое взаимодействие с заблокированным юзером."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and await is_user_blocked(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer(BLOCKED_TEXT, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(BLOCKED_TEXT)
            return None

        return await handler(event, data)
