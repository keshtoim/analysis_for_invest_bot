async def fetch_raw_company_data(company_name: str) -> dict:
    """Собирает информацию о компании из открытых источников (новости, отчётность и т.д.)."""
    # TODO: подключить реальные источники (новости/открытые данные)
    return {
        "company_name": company_name,
        "summary": f"Заглушка: реальные источники данных для «{company_name}» пока не подключены.",
    }
