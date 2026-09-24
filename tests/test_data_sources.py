from app.services.data_sources import _pick_share_security

COLUMNS = [
    "secid",
    "shortname",
    "regnumber",
    "name",
    "isin",
    "is_traded",
    "emitent_id",
    "emitent_title",
    "emitent_inn",
    "emitent_okpo",
    "type",
    "group",
    "primary_boardid",
    "marketprice_boardid",
]


def _row(secid: str, type_: str, group: str, is_traded: int = 1) -> list:
    return [secid, secid, None, secid, None, is_traded, 770, "Тест", "0", "0", type_, group, "TQBR", "TQBR"]


def test_picks_common_share_even_if_derivative_listed_first():
    # Регрессия: MOEX-поиск по "Лукойл" реально возвращает "Фиксинг МосБиржи" (FIXLKOH,
    # stock_index_pf) раньше самой акции LKOH — раньше это ломало определение тикера.
    rows = [
        _row("FIXLKOH", "stock_index_pf", "stock_index"),
        _row("LKOH", "common_share", "stock_shares"),
        _row("RU000A1059N9", "corporate_bond", "stock_bonds"),
        _row("LKU6", "futures", "futures_forts"),
    ]

    security = _pick_share_security(COLUMNS, rows)

    assert security is not None
    assert security["secid"] == "LKOH"


def test_prefers_common_share_over_preferred_share():
    rows = [
        _row("SBERP", "preferred_share", "stock_shares"),
        _row("SBER", "common_share", "stock_shares"),
    ]

    security = _pick_share_security(COLUMNS, rows)

    assert security["secid"] == "SBER"


def test_falls_back_to_preferred_share_if_no_common_share():
    rows = [_row("SBERP", "preferred_share", "stock_shares")]

    security = _pick_share_security(COLUMNS, rows)

    assert security["secid"] == "SBERP"


def test_ignores_non_traded_shares():
    rows = [_row("DEAD", "common_share", "stock_shares", is_traded=0)]

    assert _pick_share_security(COLUMNS, rows) is None


def test_returns_none_when_no_shares_present():
    rows = [_row("LKU6", "futures", "futures_forts")]

    assert _pick_share_security(COLUMNS, rows) is None


def test_returns_none_for_empty_rows():
    assert _pick_share_security(COLUMNS, []) is None
