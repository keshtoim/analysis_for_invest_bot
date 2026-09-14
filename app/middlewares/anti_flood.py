import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.config import ANTI_FLOOD_COOLDOWN_SECONDS


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._last_request: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        now = time.monotonic()
        last = self._last_request.get(event.from_user.id, 0.0)
        if now - last < ANTI_FLOOD_COOLDOWN_SECONDS:
            await event.answer("Слишком часто — подожди пару секунд и попробуй снова.")
            return None

        self._last_request[event.from_user.id] = now
        return await handler(event, data)
