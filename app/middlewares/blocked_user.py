import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.db.database import is_user_blocked

BLOCKED_TEXT = "🚫 Доступ к боту ограничен."

# Блокировка — редкое админ-действие, без срочности секунда-в-секунду.
# TTL-кэш вместо похода в sqlite на каждый update; после /block_user
# применяется в пределах этого окна, а не мгновенно.
CACHE_TTL_SECONDS = 15
# Без периодической чистки _cache рос бы бессрочно — запись на каждого
# уникального юзера, который хоть раз написал боту, никогда не удаляется.
SWEEP_EVERY_N_WRITES = 200
_cache: dict[int, tuple[bool, float]] = {}
_writes_since_sweep = 0


def _sweep_expired(now: float) -> None:
    expired = [user_id for user_id, (_, ts) in _cache.items() if now - ts >= CACHE_TTL_SECONDS]
    for user_id in expired:
        del _cache[user_id]


async def _is_blocked_cached(user_id: int) -> bool:
    global _writes_since_sweep

    now = time.monotonic()
    cached = _cache.get(user_id)
    if cached is not None and now - cached[1] < CACHE_TTL_SECONDS:
        return cached[0]

    blocked = await is_user_blocked(user_id)
    _cache[user_id] = (blocked, now)

    _writes_since_sweep += 1
    if _writes_since_sweep >= SWEEP_EVERY_N_WRITES:
        _writes_since_sweep = 0
        _sweep_expired(now)

    return blocked


class BlockedUserMiddleware(BaseMiddleware):
    """Глобально режет любое взаимодействие с заблокированным юзером."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None and await _is_blocked_cached(user.id):
            if isinstance(event, CallbackQuery):
                await event.answer(BLOCKED_TEXT, show_alert=True)
            elif isinstance(event, Message):
                await event.answer(BLOCKED_TEXT)
            return None

        return await handler(event, data)
