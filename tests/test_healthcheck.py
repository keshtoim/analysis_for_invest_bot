import time

import pytest

from app import healthcheck


@pytest.fixture(autouse=True)
def _use_temp_heartbeat(tmp_path, monkeypatch):
    monkeypatch.setattr(healthcheck, "HEARTBEAT_PATH", str(tmp_path / "heartbeat"))


def test_no_heartbeat_file_is_not_alive():
    assert healthcheck.is_alive() is False


def test_fresh_heartbeat_is_alive():
    with open(healthcheck.HEARTBEAT_PATH, "w", encoding="utf-8") as f:
        f.write(str(time.time()))

    assert healthcheck.is_alive() is True


def test_stale_heartbeat_is_not_alive():
    with open(healthcheck.HEARTBEAT_PATH, "w", encoding="utf-8") as f:
        f.write(str(time.time() - healthcheck.MAX_AGE_SECONDS - 1))

    assert healthcheck.is_alive() is False


def test_corrupted_heartbeat_is_not_alive():
    with open(healthcheck.HEARTBEAT_PATH, "w", encoding="utf-8") as f:
        f.write("не число")

    assert healthcheck.is_alive() is False
