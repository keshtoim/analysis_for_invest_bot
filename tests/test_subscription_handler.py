from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from app.handlers import subscription
from app.services import maintenance
from app.utils import auth


@pytest.fixture(autouse=True)
def _use_temp_maintenance_flag(tmp_path, monkeypatch):
    test_file = tmp_path / "maintenance"
    monkeypatch.setattr(maintenance, "_file", test_file)
    monkeypatch.setattr(maintenance, "_on", False)


def _fake_message(user_id: int) -> MagicMock:
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.from_user = MagicMock()
    message.from_user.id = user_id
    return message


async def test_maintenance_command_ignored_for_non_owner(monkeypatch):
    monkeypatch.setattr(auth, "OWNER_CHAT_ID", "1")

    await subscription.cmd_maintenance(_fake_message(2))

    assert maintenance.is_on() is False


async def test_maintenance_command_toggles_on_for_owner(monkeypatch):
    monkeypatch.setattr(auth, "OWNER_CHAT_ID", "1")
    message = _fake_message(1)

    await subscription.cmd_maintenance(message)

    assert maintenance.is_on() is True
    message.answer.assert_awaited_once()
    assert "включён" in message.answer.call_args.args[0]


async def test_maintenance_command_toggles_off_on_second_call(monkeypatch):
    monkeypatch.setattr(auth, "OWNER_CHAT_ID", "1")
    message = _fake_message(1)

    await subscription.cmd_maintenance(message)
    await subscription.cmd_maintenance(message)

    assert maintenance.is_on() is False
    assert "выключен" in message.answer.call_args.args[0]


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


def test_chunk_lines_fits_everything_in_one_chunk_when_short():
    lines = ["заголовок", "строка 1", "строка 2"]

    chunks = subscription._chunk_lines(lines, limit=100)

    assert chunks == ["заголовок\nстрока 1\nстрока 2"]


def test_chunk_lines_splits_when_limit_exceeded():
    lines = ["AAAAA", "BBBBB", "CCCCC"]

    chunks = subscription._chunk_lines(lines, limit=11)

    assert chunks == ["AAAAA\nBBBBB", "CCCCC"]
    assert all(len(chunk) <= 11 for chunk in chunks)


def test_chunk_lines_keeps_single_long_line_within_its_own_chunk():
    lines = ["короткая", "x" * 50]

    chunks = subscription._chunk_lines(lines, limit=20)

    assert chunks == ["короткая", "x" * 50]
