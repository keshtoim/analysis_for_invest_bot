from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.constants import DISCLAIMER_TEXT
from app.db.database import upsert_user
from app.keyboards.onboarding import start_keyboard
from app.models.analysis_type import ANALYSIS_TYPE_DESCRIPTIONS, ANALYSIS_TYPE_LABELS

router = Router()

START_TEXT = (
    "Привет!\n\n"
    "<b>Что умеет этот бот?</b>\n\n"
    "Присылаешь название компании — бот собирает свежие новости и биржевые данные "
    "(MOEX) и разбирает её по одной из пяти методик: SWOT, PESTEL, 5 сил Портера, "
    "финансовые мультипликаторы или обзор сектора.\n\n"
    "Сектор компании ИИ определяет сам и учитывает его контекст в каждом анализе — "
    "не только саму компанию, но и рынок вокруг неё.\n\n"
    f"<i>{DISCLAIMER_TEXT}</i>"
)

HELP_TEXT = (
    "Я анализирую компании по открытым источникам (новости, данные MOEX) с помощью ИИ.\n\n"
    "Как пользоваться: напиши название компании, затем выбери вид анализа:\n"
    + "\n".join(
        f"- <b>{ANALYSIS_TYPE_LABELS[atype]}</b> — {description}"
        for atype, description in ANALYSIS_TYPE_DESCRIPTIONS.items()
    )
    + "\n\nСтатус подписки — /subscription."
    + f"\n\n<i>{DISCLAIMER_TEXT}</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    await message.answer(START_TEXT, reply_markup=start_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
