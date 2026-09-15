from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import (
    AI_PROVIDER,
    ANTHROPIC_API_KEY,
    CLAUDE_MODEL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
)
from app.models.analysis_type import AnalysisType

_PROMPTS = {
    AnalysisType.SWOT: (
        'Ты — финансовый аналитик. Составь SWOT-анализ компании "{company_name}" '
        "на основе данных ниже. Структурируй ответ по разделам Strengths, Weaknesses, "
        "Opportunities, Threats, кратко и по делу, на русском языке.\n\n"
        "Данные о компании:\n{data}"
    ),
}

_anthropic_client: AsyncAnthropic | None = None
_openai_client: AsyncOpenAI | None = None


def _get_anthropic_client() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic_client


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL or None)
    return _openai_client


async def generate_analysis(company_data: dict, analysis_type: AnalysisType) -> str:
    prompt_template = _PROMPTS.get(analysis_type)
    if prompt_template is None:
        return f"Анализ типа {analysis_type.value} пока не реализован."

    prompt = prompt_template.format(
        company_name=company_data.get("company_name", ""),
        data=company_data,
    )

    if AI_PROVIDER == "openai":
        # OpenAI-совместимый шлюз (например, Timeweb AI Gateway), отдающий Claude
        response = await _get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    response = await _get_anthropic_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
