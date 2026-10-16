from app.config import OWNER_CHAT_ID


def is_owner(user_id: int) -> bool:
    return bool(OWNER_CHAT_ID) and str(user_id) == str(OWNER_CHAT_ID)
