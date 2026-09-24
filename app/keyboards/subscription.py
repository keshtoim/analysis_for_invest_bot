from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def subscription_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔓 Оформить подписку", callback_data="subscription:purchase")],
        ]
    )
