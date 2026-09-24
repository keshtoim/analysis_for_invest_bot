from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_START = "📈 Начать"
BTN_NOVICE = "🌱 Только начинаю"
BTN_EXPERIENCED = "💼 Уже инвестирую"


def start_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_START)]],
        resize_keyboard=True,
    )


def experience_level_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_NOVICE), KeyboardButton(text=BTN_EXPERIENCED)]],
        resize_keyboard=True,
    )


def novice_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧭 С чего начать", callback_data="onboarding:novice_help")],
            [InlineKeyboardButton(text="📊 Анализ компаний", callback_data="onboarding:start_analysis")],
        ]
    )


def experienced_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Анализ компаний", callback_data="onboarding:start_analysis")],
            [InlineKeyboardButton(text="📋 Виды анализа", callback_data="onboarding:analysis_types")],
        ]
    )
