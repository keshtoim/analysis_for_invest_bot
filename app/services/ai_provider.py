from app.config import AI_PROVIDER


async def get_company_analysis(company_name: str) -> str:
    """Формирует анализ компании через выбранного AI-провайдера (openai/anthropic)."""
    # TODO: реализовать вызов ИИ и подстановку данных из data_sources
    return f"Анализ компании «{company_name}» пока не реализован (провайдер: {AI_PROVIDER})."
