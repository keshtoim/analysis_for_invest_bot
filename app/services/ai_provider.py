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
        "на основе данных ниже, кратко и по делу, на русском языке.\n\n"
        "Ответ пойдёт в Telegram-сообщение с HTML-разметкой, поэтому:\n"
        "- Используй только теги <b>...</b> и <i>...</i>, никакого Markdown "
        "(никаких #, ##, **, ---, таблиц)\n"
        "- Названия разделов оформляй как <b>Strengths</b>, <b>Weaknesses</b>, "
        "<b>Opportunities</b>, <b>Threats</b> на отдельной строке\n"
        "- Пункты внутри раздела — с новой строки через «- », без вложенных списков\n"
        "- Символы <, >, & в обычном тексте не используй\n\n"
        "Данные о компании:\n{data}"
    ),
}

_anthropic_client: AsyncAnthropic | None = None
_openai_client: AsyncOpenAI | None = None


def _format_company_data(data: dict) -> str:
    """Компактный текст вместо repr(dict) — экономит токены и понятнее модели."""
    lines = []

    moex = data.get("moex")
    if moex:
        lines.append(
            f"MOEX: тикер {moex.get('ticker')}, цена {moex.get('last_price')} "
            f"{moex.get('currency') or ''}, изменение {moex.get('change_percent')}%"
        )
    else:
        lines.append("MOEX: компания не торгуется на бирже или не найдена")

    news = data.get("news") or []
    if news:
        lines.append("Новости:")
        for item in news:
            lines.append(f"- {item.get('title')}: {item.get('snippet')}")
    else:
        lines.append("Новости: не найдены")

    return "\n".join(lines)


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
        data=_format_company_data(company_data),
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
