from app.handlers import subscription


def test_is_owner_true_for_matching_id(monkeypatch):
    monkeypatch.setattr(subscription, "OWNER_CHAT_ID", "12345")
    assert subscription._is_owner(12345) is True


def test_is_owner_false_for_other_id(monkeypatch):
    monkeypatch.setattr(subscription, "OWNER_CHAT_ID", "12345")
    assert subscription._is_owner(999) is False


def test_is_owner_false_when_not_configured(monkeypatch):
    monkeypatch.setattr(subscription, "OWNER_CHAT_ID", "")
    assert subscription._is_owner(12345) is False


def _empty_stats() -> dict:
    return {
        "total_users": 0,
        "new_users_24h": 0,
        "new_users_7d": 0,
        "total_requests": 0,
        "requests_24h": 0,
        "requests_7d": 0,
        "active_users_7d": 0,
        "top_companies": [],
        "requests_by_type": [],
        "cached_companies": 0,
        "active_subscriptions": 0,
        "blocked_users": 0,
        "bot_alive": True,
    }


def test_format_stats_includes_key_numbers():
    stats = _empty_stats()
    stats.update(total_users=5, total_requests=10, cached_companies=3, active_subscriptions=1)

    text = subscription._format_stats(stats)

    assert "5" in text
    assert "10" in text
    assert "Бот жив (heartbeat): да" in text


def test_format_stats_renders_top_companies_and_types():
    stats = _empty_stats()
    stats["top_companies"] = [("Лукойл", 3), ("Сбербанк", 1)]
    stats["requests_by_type"] = [("swot", 2), ("pestel", 1)]

    text = subscription._format_stats(stats)

    assert "Лукойл: 3" in text
    assert "Сбербанк: 1" in text
    assert "SWOT: 2" in text
    assert "PESTEL: 1" in text


def test_format_stats_escapes_company_names():
    stats = _empty_stats()
    stats["top_companies"] = [("<script>", 1)]

    text = subscription._format_stats(stats)

    assert "<script>" not in text
    assert "&lt;script&gt;" in text


def test_format_stats_falls_back_for_unknown_type():
    stats = _empty_stats()
    stats["requests_by_type"] = [("unknown_type", 1)]

    text = subscription._format_stats(stats)

    assert "unknown_type: 1" in text


def test_format_stats_includes_blocked_count():
    stats = _empty_stats()
    stats["blocked_users"] = 2

    text = subscription._format_stats(stats)

    assert "Заблокировано: 2" in text
