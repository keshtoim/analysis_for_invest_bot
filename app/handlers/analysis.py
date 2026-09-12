from aiogram import Router
from aiogram.types import Message

from app.services.ai_provider import get_company_analysis

router = Router()


@router.message()
async def handle_company_name(message: Message) -> None:
    company_name = message.text
    analysis = await get_company_analysis(company_name)
    await message.answer(analysis)
