from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.db.database import log_message


class MessageLoggingMiddleware(BaseMiddleware):
    """Пишет текст каждого входящего сообщения — под /user_history владельца."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            await log_message(event.from_user.id, event.text)

        return await handler(event, data)
