from aiogram import F, Router
from aiogram.types import Message

from app.keyboards.profile import BTN_PROFILE

router = Router()

TARIFF_NAME = "Безлимитный (бесплатно)"


@router.message(F.text == BTN_PROFILE)
async def handle_profile(message: Message) -> None:
    await message.answer(
        "<b>👤 Профиль</b>\n\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"Тариф: {TARIFF_NAME}"
    )
