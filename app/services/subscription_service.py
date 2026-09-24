from datetime import datetime

from app.db.database import get_subscription


async def is_subscribed(user_id: int) -> bool:
    """Платного гейта пока нет нигде в боте — функция готова для будущих проверок."""
    sub = await get_subscription(user_id)
    if sub is None or not sub.get("expires_at"):
        return False
    return datetime.fromisoformat(sub["expires_at"]) > datetime.utcnow()
