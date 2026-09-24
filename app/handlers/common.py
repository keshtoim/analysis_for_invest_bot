from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.db.database import upsert_user
from app.keyboards.onboarding import start_keyboard
from app.models.analysis_type import ANALYSIS_TYPE_LABELS

router = Router()

HELP_TEXT = (
    "Я анализирую компании по открытым источникам (новости, данные MOEX) с помощью ИИ.\n\n"
    "Как пользоваться: напиши название компании, затем выбери вид анализа:\n"
    + "\n".join(f"- {label}" for label in ANALYSIS_TYPE_LABELS.values())
    + "\n\n<i>Анализ формируется автоматически и не является индивидуальной "
    "инвестиционной рекомендацией.</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await message.answer(
        "Привет! Я помогу разобраться в компаниях перед тем, как инвестировать.",
        reply_markup=start_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
