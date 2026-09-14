from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.analysis_menu import analysis_type_keyboard
from app.models.analysis_type import ANALYSIS_TYPE_LABELS, AnalysisType
from app.services.ai_provider import generate_analysis
from app.services.company_data import get_company_data

router = Router()


@router.message(F.text)
async def handle_company_name(message: Message, state: FSMContext) -> None:
    company_name = message.text.strip()
    await state.update_data(company_name=company_name)
    await message.answer(
        f"Выбери вид анализа для «{company_name}»:",
        reply_markup=analysis_type_keyboard(),
    )


@router.callback_query(F.data.startswith("analysis:"))
async def handle_analysis_choice(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    company_name = data.get("company_name")
    await callback.answer()

    if not company_name:
        await callback.message.answer("Сначала отправь название компании.")
        return

    analysis_type = AnalysisType(callback.data.split(":", 1)[1])

    if analysis_type != AnalysisType.SWOT:
        await callback.message.answer(
            f"{ANALYSIS_TYPE_LABELS[analysis_type]} пока в разработке — доступен только SWOT."
        )
        return

    await callback.message.answer(f"Собираю данные по «{company_name}»…")
    company_data = await get_company_data(company_name)
    analysis_text = await generate_analysis(company_data, analysis_type)
    await callback.message.answer(analysis_text)
