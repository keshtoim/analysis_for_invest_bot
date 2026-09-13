from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.database import upsert_user
from app.keyboards.main_menu import main_menu_keyboard

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await message.answer(
        "Привет! Отправь название компании, чтобы получить её анализ.",
        reply_markup=main_menu_keyboard(),
    )
