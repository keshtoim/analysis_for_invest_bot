from app.models.analysis_type import AnalysisType
from app.services import ai_provider


def test_format_company_data_with_full_data():
    data = {
        "company_name": "Лукойл",
        "moex": {"ticker": "LKOH", "last_price": 5438, "change_percent": -0.85,
                  "market_cap": 3_780_000_000_000, "currency": "RUB"},
        "news": [{"title": "Заголовок", "snippet": "Сниппет"}],
        "sector": {"name": "Нефтегазовая отрасль", "news": [{"title": "Сектор", "snippet": "Что-то"}]},
    }

    text = ai_provider._format_company_data(data)

    assert "LKOH" in text
    assert "Заголовок" in text
    assert "Нефтегазовая отрасль" in text
    assert "Сектор" in text


def test_format_company_data_handles_missing_moex_and_sector():
    data = {"company_name": "Тест", "moex": None, "news": [], "sector": None}

    text = ai_provider._format_company_data(data)

    assert "не торгуется на бирже" in text
    assert "не найдены" in text
    assert "не определён" in text


def test_build_prompt_includes_company_name_and_html_rules():
    data = {"company_name": "Лукойл", "moex": None, "news": [], "sector": None}

    prompt = ai_provider._build_prompt(AnalysisType.SWOT, data)

    assert "Лукойл" in prompt
    assert "SWOT" in prompt
    assert "HTML-разметкой" in prompt


def test_build_prompt_covers_every_analysis_type():
    data = {"company_name": "Тест", "moex": None, "news": [], "sector": None}

    for atype in AnalysisType:
        assert ai_provider._build_prompt(atype, data) is not None


async def test_generate_analysis_calls_ai_with_built_prompt(monkeypatch):
    captured = {}

    async def fake_call_ai(prompt, max_tokens=1024):
        captured["prompt"] = prompt
        return "готовый ответ"

    monkeypatch.setattr(ai_provider, "_call_ai", fake_call_ai)

    result = await ai_provider.generate_analysis(
        {"company_name": "Лукойл", "moex": None, "news": [], "sector": None},
        AnalysisType.SWOT,
    )

    assert result == "готовый ответ"
    assert "Лукойл" in captured["prompt"]


async def test_identify_sector_strips_response(monkeypatch):
    async def fake_call_ai(prompt, max_tokens=1024):
        return "  Банковский сектор  \n"

    monkeypatch.setattr(ai_provider, "_call_ai", fake_call_ai)

    sector = await ai_provider.identify_sector("Сбербанк")

    assert sector == "Банковский сектор"
