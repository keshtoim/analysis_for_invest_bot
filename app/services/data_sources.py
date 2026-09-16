import asyncio
import xml.etree.ElementTree as ET

import aiohttp
from bs4 import BeautifulSoup

from app.utils.logger import logger

GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"
MOEX_SEARCH_URL = "https://iss.moex.com/iss/securities.json"
MOEX_MARKETDATA_URL = "https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}.json"

# MOEX-акции на основной секции (TQBR и аналоги) торгуются в рублях
MOEX_CURRENCY = "RUB"
MOEX_SHARE_TYPES = ("common_share", "preferred_share")

NEWS_RESULTS_LIMIT = 5
HTTP_TIMEOUT = aiohttp.ClientTimeout(total=10)
USER_AGENT = "Mozilla/5.0 (compatible; analysis_for_invest_bot/1.0)"


async def fetch_news_snippets(company_name: str) -> list[dict]:
    """Бесплатный RSS-фид Google News — без ключа, без анти-бот капчи."""
    params = {"q": company_name, "hl": "ru", "gl": "RU", "ceid": "RU:ru"}
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            async with session.get(GOOGLE_NEWS_RSS_URL, params=params, timeout=HTTP_TIMEOUT) as response:
                xml_text = await response.text()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Не удалось получить новости для %s: %s", company_name, exc)
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.warning("Не удалось разобрать RSS новостей для %s: %s", company_name, exc)
        return []

    results = []
    for item in root.findall("./channel/item")[:NEWS_RESULTS_LIMIT]:
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        description_html = item.findtext("description") or ""
        snippet = BeautifulSoup(description_html, "html.parser").get_text(strip=True)
        results.append(
            {
                "title": title,
                "snippet": snippet,
                "url": (item.findtext("link") or "").strip(),
            }
        )
    return results


def _pick_share_security(columns: list[str], rows: list[list]) -> dict | None:
    candidates = [dict(zip(columns, row)) for row in rows]
    # Ищем именно акцию (не индекс/фьючерс/облигацию), с приоритетом обычной акции
    for share_type in MOEX_SHARE_TYPES:
        for candidate in candidates:
            if candidate.get("type") == share_type and candidate.get("is_traded") == 1:
                return candidate
    return None


async def fetch_moex_data(company_name: str) -> dict | None:
    """Данные по акции с Мосбиржи (публичный ISS API, без ключа)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                MOEX_SEARCH_URL,
                params={"q": company_name, "iss.meta": "off"},
                timeout=HTTP_TIMEOUT,
            ) as response:
                search_data = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Не удалось найти %s на MOEX: %s", company_name, exc)
        return None

    securities = search_data.get("securities", {})
    security = _pick_share_security(securities.get("columns", []), securities.get("data", []))
    if security is None:
        return None

    ticker = security.get("secid")
    board = security.get("marketprice_boardid") or security.get("primary_boardid")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                MOEX_MARKETDATA_URL.format(ticker=ticker),
                params={"iss.meta": "off"},
                timeout=HTTP_TIMEOUT,
            ) as response:
                market_data = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Не удалось получить котировки %s с MOEX: %s", ticker, exc)
        return {"ticker": ticker, "name": security.get("name")}

    marketdata = market_data.get("marketdata", {})
    md_columns = marketdata.get("columns", [])
    md_rows = [dict(zip(md_columns, row)) for row in marketdata.get("data", [])]
    if not md_rows:
        return {"ticker": ticker, "name": security.get("name")}

    market_row = next((row for row in md_rows if row.get("BOARDID") == board), md_rows[0])
    return {
        "ticker": ticker,
        "name": security.get("name"),
        "last_price": market_row.get("LAST"),
        "change_percent": market_row.get("LASTTOPREVPRICE"),
        "currency": MOEX_CURRENCY,
    }


async def fetch_raw_company_data(company_name: str) -> dict:
    """Собирает информацию о компании из открытых источников (новости + MOEX)."""
    news, moex_data = await asyncio.gather(
        fetch_news_snippets(company_name),
        fetch_moex_data(company_name),
    )
    return {
        "company_name": company_name,
        "news": news,
        "moex": moex_data,
    }
