from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.analysis_menu import analysis_type_keyboard
from app.models.analysis_type import AnalysisType
from app.services.ai_provider import generate_analysis
from app.services.company_data import get_company_data
from app.utils.html import escape_html, strip_html
from app.utils.logger import logger

router = Router()

SEND_RETRIES = 2


@router.message(F.text)
async def handle_company_name(message: Message, state: FSMContext) -> None:
    company_name = message.text.strip()
    await state.update_data(company_name=company_name)
    await message.answer(
        f"Выбери вид анализа для «{escape_html(company_name)}»:",
        reply_markup=analysis_type_keyboard(),
    )


async def _safe_answer(callback: CallbackQuery, text: str, **kwargs) -> bool:
    """Отправляет ответ с ретраем на временные сетевые сбои Telegram."""
    for attempt in range(1, SEND_RETRIES + 1):
        try:
            await callback.message.answer(text, **kwargs)
            return True
        except TelegramNetworkError as exc:
            logger.warning("Сетевая ошибка Telegram (попытка %s/%s): %s", attempt, SEND_RETRIES, exc)
    return False


@router.callback_query(F.data.startswith("analysis:"))
async def handle_analysis_choice(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    company_name = data.get("company_name")
    await callback.answer()

    if not company_name:
        await _safe_answer(callback, "Сначала отправь название компании.")
        return

    analysis_type = AnalysisType(callback.data.split(":", 1)[1])

    if not await _safe_answer(callback, f"Собираю данные по «{escape_html(company_name)}»…"):
        return

    try:
        company_data = await get_company_data(company_name)
        analysis_text = await generate_analysis(company_data, analysis_type)
    except Exception:
        logger.exception("Не удалось получить анализ для «%s»", company_name)
        await _safe_answer(
            callback,
            "Не получилось собрать анализ 😕 Источники данных или ИИ сейчас недоступны — "
            "попробуй, пожалуйста, через пару минут.",
        )
        return

    try:
        await callback.message.answer(analysis_text)
    except TelegramBadRequest:
        # Модель вернула HTML, который Telegram не принял — шлём как обычный текст
        await _safe_answer(callback, strip_html(analysis_text), parse_mode=None)
    except TelegramNetworkError as exc:
        logger.warning("Сетевая ошибка Telegram при отправке анализа: %s", exc)
        await _safe_answer(
            callback,
            "Анализ готов, но не получилось его отправить из-за сетевого сбоя. Попробуй ещё раз.",
        )
