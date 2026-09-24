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

_HTML_RULES = (
    "Ответ пойдёт в Telegram-сообщение с HTML-разметкой, поэтому:\n"
    "- Используй только теги <b>...</b> и <i>...</i>, никакого Markdown "
    "(никаких #, ##, **, ---, таблиц)\n"
    "- Пункты внутри раздела — с новой строки через «- », без вложенных списков\n"
    "- Символы <, >, & в обычном тексте не используй"
)

_SECTOR_CONTEXT_NOTE = "Учитывай также контекст сектора компании (см. данные ниже)."

_ANALYSIS_INSTRUCTIONS = {
    AnalysisType.SWOT: (
        'Составь SWOT-анализ компании "{company_name}".\n'
        "Названия разделов оформляй как <b>Strengths</b>, <b>Weaknesses</b>, "
        f"<b>Opportunities</b>, <b>Threats</b> на отдельной строке.\n{_SECTOR_CONTEXT_NOTE}"
    ),
    AnalysisType.PESTEL: (
        'Составь PESTEL-анализ компании "{company_name}".\n'
        "Названия разделов оформляй как <b>Political</b>, <b>Economic</b>, "
        "<b>Social</b>, <b>Technological</b>, <b>Environmental</b>, <b>Legal</b> "
        f"на отдельной строке.\n{_SECTOR_CONTEXT_NOTE}"
    ),
    AnalysisType.PORTER_FIVE_FORCES: (
        'Составь анализ 5 сил Портера для компании "{company_name}".\n'
        "Названия разделов оформляй как <b>Competitive Rivalry</b>, "
        "<b>Supplier Power</b>, <b>Buyer Power</b>, <b>Threat of Substitution</b>, "
        f"<b>Threat of New Entry</b> на отдельной строке.\n{_SECTOR_CONTEXT_NOTE}"
    ),
    AnalysisType.FINANCIAL_MULTIPLES: (
        'Оцени компанию "{company_name}" по финансовым мультипликаторам '
        "(P/E, P/B, P/S, долговая нагрузка и т.д.) на основе данных ниже.\n"
        "Если мультипликатор посчитать нельзя из-за нехватки данных — прямо "
        "напиши об этом, не выдумывай цифры. Раздел <b>Мультипликаторы</b> — "
        f"что удалось оценить, раздел <b>Ограничения</b> — чего не хватило.\n{_SECTOR_CONTEXT_NOTE}"
    ),
    AnalysisType.SECTOR_OVERVIEW: (
        'Составь обзор сектора (отрасли), в котором работает компания "{company_name}" — '
        "не самой компании, а рынка вокруг неё.\n"
        "Названия разделов оформляй как <b>Market Overview</b>, <b>Trends</b>, "
        "<b>Regulation</b>, <b>Key Players</b> на отдельной строке."
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
            f"{moex.get('currency') or ''}, изменение {moex.get('change_percent')}%, "
            f"капитализация {moex.get('market_cap')} {moex.get('currency') or ''}"
        )
    else:
        lines.append("MOEX: компания не торгуется на бирже или не найдена")

    news = data.get("news") or []
    if news:
        lines.append("Новости о компании:")
        for item in news:
            lines.append(f"- {item.get('title')}: {item.get('snippet')}")
    else:
        lines.append("Новости о компании: не найдены")

    sector = data.get("sector")
    if sector:
        lines.append(f"Сектор: {sector.get('name')}")
        sector_news = sector.get("news") or []
        if sector_news:
            lines.append("Новости сектора:")
            for item in sector_news:
                lines.append(f"- {item.get('title')}: {item.get('snippet')}")
        else:
            lines.append("Новости сектора: не найдены")
    else:
        lines.append("Сектор: не определён")

    return "\n".join(lines)


def _build_prompt(analysis_type: AnalysisType, company_data: dict) -> str | None:
    instruction = _ANALYSIS_INSTRUCTIONS.get(analysis_type)
    if instruction is None:
        return None

    task = instruction.format(company_name=company_data.get("company_name", ""))
    return (
        f"Ты — финансовый аналитик. {task}\n"
        "Пиши кратко и по делу, на русском языке.\n\n"
        f"{_HTML_RULES}\n\n"
        f"Данные о компании:\n{_format_company_data(company_data)}"
    )


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


async def _call_ai(prompt: str, max_tokens: int = 1024) -> str:
    if AI_PROVIDER == "openai":
        # OpenAI-совместимый шлюз (например, Timeweb AI Gateway), отдающий Claude
        response = await _get_openai_client().chat.completions.create(
            model=OPENAI_MODEL,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    response = await _get_anthropic_client().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def generate_analysis(company_data: dict, analysis_type: AnalysisType) -> str:
    prompt = _build_prompt(analysis_type, company_data)
    if prompt is None:
        return f"Анализ типа {analysis_type.value} пока не реализован."
    return await _call_ai(prompt)


async def identify_sector(company_name: str) -> str:
    """Короткий отдельный запрос к ИИ — определяет отрасль/сектор компании."""
    prompt = (
        f'Назови отрасль (сектор экономики) компании "{company_name}" одним коротким '
        "словосочетанием на русском языке, без пояснений и знаков препинания в конце. "
        'Например: "Нефтегазовая отрасль", "Розничная торговля", "Банковский сектор".'
    )
    sector = await _call_ai(prompt, max_tokens=20)
    return sector.strip()
