import pytest

from app.db import database
from app.services import company_data


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "test.db"))


async def test_cache_hit_skips_fetching(monkeypatch):
    await database.init_db()
    cached_data = {"company_name": "Лукойл", "news": [], "moex": None, "sector": None}
    await database.save_company_cache("Лукойл", cached_data, source="test")

    async def _should_not_be_called(*args, **kwargs):
        raise AssertionError("fetch_raw_company_data не должен вызываться при попадании в кэш")

    monkeypatch.setattr(company_data, "fetch_raw_company_data", _should_not_be_called)

    result = await company_data.get_company_data("Лукойл")

    assert result == cached_data


async def test_cache_miss_fetches_and_saves_with_sector(monkeypatch):
    await database.init_db()

    async def fake_fetch_raw(company_name):
        return {"company_name": company_name, "news": [{"title": "Новость"}], "moex": None}

    async def fake_identify_sector(company_name):
        return "Нефтегазовая отрасль"

    async def fake_fetch_sector_news(sector_name):
        return [{"title": f"Новость про {sector_name}"}]

    monkeypatch.setattr(company_data, "fetch_raw_company_data", fake_fetch_raw)
    monkeypatch.setattr(company_data, "identify_sector", fake_identify_sector)
    monkeypatch.setattr(company_data, "fetch_sector_news_snippets", fake_fetch_sector_news)

    result = await company_data.get_company_data("Лукойл")

    assert result["company_name"] == "Лукойл"
    assert result["sector"] == {
        "name": "Нефтегазовая отрасль",
        "news": [{"title": "Новость про Нефтегазовая отрасль"}],
    }

    # И сохранилось в кэш
    cached = await database.get_cached_company_data("Лукойл")
    assert cached == result


async def test_sector_fetch_failure_does_not_break_company_analysis(monkeypatch):
    await database.init_db()

    async def fake_fetch_raw(company_name):
        return {"company_name": company_name, "news": [], "moex": None}

    async def fake_identify_sector(company_name):
        raise RuntimeError("ИИ недоступен")

    monkeypatch.setattr(company_data, "fetch_raw_company_data", fake_fetch_raw)
    monkeypatch.setattr(company_data, "identify_sector", fake_identify_sector)

    result = await company_data.get_company_data("Лукойл")

    assert result["sector"] is None
    assert result["company_name"] == "Лукойл"
