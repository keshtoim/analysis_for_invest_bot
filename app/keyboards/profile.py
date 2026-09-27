from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_PROFILE = "👤 Профиль"


def profile_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_PROFILE)]],
        resize_keyboard=True,
    )
