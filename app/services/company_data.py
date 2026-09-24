from app.db.database import get_cached_company_data, save_company_cache
from app.services.ai_provider import identify_sector
from app.services.data_sources import fetch_raw_company_data, fetch_sector_news_snippets
from app.utils.logger import logger

SOURCE_NAME = "google_news+moex"


async def _fetch_sector_data(company_name: str) -> dict | None:
    try:
        sector_name = await identify_sector(company_name)
        if not sector_name:
            return None
        sector_news = await fetch_sector_news_snippets(sector_name)
    except Exception:
        logger.exception("Не удалось определить/собрать данные сектора для «%s»", company_name)
        return None

    return {"name": sector_name, "news": sector_news}


async def get_company_data(company_name: str) -> dict:
    cached = await get_cached_company_data(company_name)
    if cached is not None:
        return cached

    raw_data = await fetch_raw_company_data(company_name)
    raw_data["sector"] = await _fetch_sector_data(company_name)

    await save_company_cache(company_name, raw_data, source=SOURCE_NAME)
    return raw_data
