from anthropic import AsyncAnthropic

from app.config import AI_PROVIDER, ANTHROPIC_API_KEY, CLAUDE_MODEL
from app.models.analysis_type import AnalysisType

_PROMPTS = {
    AnalysisType.SWOT: (
        'Ты — финансовый аналитик. Составь SWOT-анализ компании "{company_name}" '
        "на основе данных ниже. Структурируй ответ по разделам Strengths, Weaknesses, "
        "Opportunities, Threats, кратко и по делу, на русском языке.\n\n"
        "Данные о компании:\n{data}"
    ),
}

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _client


async def generate_analysis(company_data: dict, analysis_type: AnalysisType) -> str:
    if AI_PROVIDER != "anthropic":
        return "Провайдер OpenAI пока не подключён, используй ANTHROPIC."

    prompt_template = _PROMPTS.get(analysis_type)
    if prompt_template is None:
        return f"Анализ типа {analysis_type.value} пока не реализован."

    prompt = prompt_template.format(
        company_name=company_data.get("company_name", ""),
        data=company_data,
    )

    response = await _get_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
