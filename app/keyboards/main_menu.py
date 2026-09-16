from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📊 Начать анализ", callback_data="menu:start_analysis")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
