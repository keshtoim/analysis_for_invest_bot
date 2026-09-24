import time

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.config import ANTI_FLOOD_COOLDOWN_SECONDS
from app.keyboards.analysis_menu import analysis_type_keyboard
from app.models.analysis_type import (
    ANALYSIS_TYPE_DESCRIPTIONS,
    ANALYSIS_TYPE_EMOJI,
    ANALYSIS_TYPE_LABELS,
    AnalysisType,
)
from app.services.ai_provider import generate_analysis
from app.services.company_data import get_company_data
from app.utils.html import escape_html, strip_html
from app.utils.logger import logger

router = Router()

SEND_RETRIES = 2
FOOTER_TEXT = (
    "<i>Анализ сформирован автоматически и не является индивидуальной "
    "инвестиционной рекомендацией.</i>"
)

_last_analysis_request: dict[int, float] = {}


def _analysis_type_menu_text(company_name: str) -> str:
    lines = [f"Выбери вид анализа для «{escape_html(company_name)}»:", ""]
    lines += [
        f"{ANALYSIS_TYPE_EMOJI[atype]} <b>{ANALYSIS_TYPE_LABELS[atype]}</b> — {description}"
        for atype, description in ANALYSIS_TYPE_DESCRIPTIONS.items()
    ]
    return "\n".join(lines)


@router.message(F.text)
async def handle_company_name(message: Message, state: FSMContext) -> None:
    company_name = message.text.strip()
    await state.update_data(company_name=company_name)
    await message.answer(
        _analysis_type_menu_text(company_name),
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


def _is_flooding(user_id: int) -> bool:
    now = time.monotonic()
    last = _last_analysis_request.get(user_id, 0.0)
    if now - last < ANTI_FLOOD_COOLDOWN_SECONDS:
        return True
    _last_analysis_request[user_id] = now
    return False


@router.callback_query(F.data.startswith("analysis:"))
async def handle_analysis_choice(callback: CallbackQuery, state: FSMContext) -> None:
    if _is_flooding(callback.from_user.id):
        await callback.answer("Слишком часто — подожди пару секунд и попробуй снова.", show_alert=True)
        return

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

    title = f"<b>{ANALYSIS_TYPE_EMOJI[analysis_type]} {ANALYSIS_TYPE_LABELS[analysis_type]}: {escape_html(company_name)}</b>\n\n"
    full_text = f"{title}{analysis_text}\n\n{FOOTER_TEXT}"

    try:
        await callback.message.answer(full_text)
    except TelegramBadRequest:
        # Модель вернула HTML, который Telegram не принял — шлём как обычный текст
        if not await _safe_answer(callback, strip_html(full_text), parse_mode=None):
            return
    except TelegramNetworkError as exc:
        logger.warning("Сетевая ошибка Telegram при отправке анализа: %s", exc)
        await _safe_answer(
            callback,
            "Анализ готов, но не получилось его отправить из-за сетевого сбоя. Попробуй ещё раз.",
        )
        return

    await _safe_answer(
        callback,
        f"Хочешь ещё один вид анализа для «{escape_html(company_name)}»?",
        reply_markup=analysis_type_keyboard(),
    )
