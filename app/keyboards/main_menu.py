from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.keyboards.profile import BTN_PROFILE

BTN_ANALYSIS = "📊 Анализ"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_ANALYSIS), KeyboardButton(text=BTN_PROFILE)]],
        resize_keyboard=True,
    )
