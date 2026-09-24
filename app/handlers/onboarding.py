from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.keyboards.onboarding import (
    BTN_EXPERIENCED,
    BTN_NOVICE,
    BTN_START,
    experience_level_keyboard,
    experienced_menu_keyboard,
    novice_menu_keyboard,
)
from app.models.analysis_type import ANALYSIS_TYPE_LABELS

router = Router()

NOVICE_HELP_TEXT = (
    "<b>С чего начать инвестировать</b>\n\n"
    "- Инвестировать самостоятельно можно с 18 лет (до этого — только через "
    "родителя или опекуна)\n"
    "- Нужен брокерский счёт — открывается онлайн за 10-15 минут в приложении "
    "брокера, например «Т-Инвестиции», «Альфа-Инвестиции», «БКС Мир инвестиций» "
    "или «Сбер Инвестор»\n"
    "- Для налоговых льгот можно открыть ИИС (индивидуальный инвестиционный счёт) "
    "вместо обычного брокерского\n"
    "- Начинать стоит с суммы, которую не страшно потерять — рынок не гарантирует доходность\n\n"
    "<i>Это общая информация, а не индивидуальная инвестиционная рекомендация.</i>"
)

ANALYSIS_TYPES_TEXT = "<b>Какие виды анализа доступны</b>\n\n" + "\n".join(
    f"- {label}" for label in ANALYSIS_TYPE_LABELS.values()
)


@router.message(F.text == BTN_START)
async def handle_start_button(message: Message) -> None:
    await message.answer(
        "Расскажи о себе, чтобы я подсказал, с чего начать:",
        reply_markup=experience_level_keyboard(),
    )


@router.message(F.text == BTN_NOVICE)
async def handle_novice(message: Message) -> None:
    await message.answer("Понял, начнём с основ.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Что подсказать?", reply_markup=novice_menu_keyboard())


@router.message(F.text == BTN_EXPERIENCED)
async def handle_experienced(message: Message) -> None:
    await message.answer("Отлично, тогда сразу к делу.", reply_markup=ReplyKeyboardRemove())
    await message.answer("Что нужно?", reply_markup=experienced_menu_keyboard())


@router.callback_query(F.data == "onboarding:novice_help")
async def handle_novice_help(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(NOVICE_HELP_TEXT)


@router.callback_query(F.data == "onboarding:analysis_types")
async def handle_analysis_types(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer(ANALYSIS_TYPES_TEXT)


@router.callback_query(F.data == "onboarding:start_analysis")
async def handle_start_analysis(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Напиши название компании, которую хочешь проанализировать 🙂")
