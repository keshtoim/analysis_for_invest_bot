from app.db.database import get_cached_company_data, save_company_cache
from app.services.data_sources import fetch_raw_company_data

SOURCE_NAME = "mock"


async def get_company_data(company_name: str) -> dict:
    cached = await get_cached_company_data(company_name)
    if cached is not None:
        return cached

    raw_data = await fetch_raw_company_data(company_name)
    await save_company_cache(company_name, raw_data, source=SOURCE_NAME)
    return raw_data
