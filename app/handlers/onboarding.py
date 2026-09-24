from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.keyboards.onboarding import (
    BTN_EXPERIENCED,
    BTN_NOVICE,
    BTN_START,
    continue_keyboard,
    experience_level_keyboard,
    experienced_menu_keyboard,
    novice_menu_keyboard,
)
from app.models.analysis_type import ANALYSIS_TYPE_DESCRIPTIONS, ANALYSIS_TYPE_LABELS

router = Router()

NOVICE_HELP_TEXT = (
    "<b>С чего начать инвестировать</b>\n\n"
    "1. Инвестировать самостоятельно можно с 18 лет (до этого — только через "
    "родителя или опекуна)\n"
    "2. Открой брокерский счёт — это делается онлайн за 10-15 минут в приложении "
    "брокера, например «Т-Инвестиции», «Альфа-Инвестиции», «БКС Мир инвестиций» "
    "или «Сбер Инвестор»\n"
    "3. Для налоговых льгот можно выбрать ИИС (индивидуальный инвестиционный счёт) "
    "вместо обычного брокерского\n"
    "4. Начинай с суммы, которую не страшно потерять — рынок не гарантирует доходность\n\n"
    "<i>Это общая информация, а не индивидуальная инвестиционная рекомендация.</i>"
)

ANALYSIS_TYPES_TEXT = "<b>Какие виды анализа доступны</b>\n\n" + "\n".join(
    f"- <b>{ANALYSIS_TYPE_LABELS[atype]}</b> — {description}"
    for atype, description in ANALYSIS_TYPE_DESCRIPTIONS.items()
)


@router.message(F.text == BTN_START)
async def handle_start_button(message: Message) -> None:
    await message.answer(
        "Расскажи о себе — так я пойму, с чего лучше начать:",
        reply_markup=experience_level_keyboard(),
    )


@router.message(F.text == BTN_NOVICE)
async def handle_novice(message: Message) -> None:
    await message.answer("Хорошо, начнём с основ 🌱", reply_markup=ReplyKeyboardRemove())
    await message.answer("Выбери, что интересно:", reply_markup=novice_menu_keyboard())


@router.message(F.text == BTN_EXPERIENCED)
async def handle_experienced(message: Message) -> None:
    await message.answer("Отлично, сразу к делу.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Что выбираешь?", reply_markup=experienced_menu_keyboard())


@router.callback_query(F.data == "onboarding:novice_help")
async def handle_novice_help(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(NOVICE_HELP_TEXT, reply_markup=continue_keyboard())


@router.callback_query(F.data == "onboarding:analysis_types")
async def handle_analysis_types(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(ANALYSIS_TYPES_TEXT)


@router.callback_query(F.data == "onboarding:start_analysis")
async def handle_start_analysis(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Напиши название компании, которую хочешь проанализировать 🙂")
