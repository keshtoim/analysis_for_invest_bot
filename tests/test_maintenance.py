import pytest

from app.services import maintenance


@pytest.fixture(autouse=True)
def _use_temp_file(tmp_path, monkeypatch):
    test_file = tmp_path / "maintenance"
    monkeypatch.setattr(maintenance, "_file", test_file)
    monkeypatch.setattr(maintenance, "_on", test_file.exists())


def test_is_off_by_default():
    assert maintenance.is_on() is False


def test_toggle_turns_on_and_creates_flag_file():
    result = maintenance.toggle()

    assert result is True
    assert maintenance.is_on() is True
    assert maintenance._file.exists()


def test_toggle_twice_turns_off_and_removes_flag_file():
    maintenance.toggle()
    result = maintenance.toggle()

    assert result is False
    assert maintenance.is_on() is False
    assert not maintenance._file.exists()


def test_toggle_creates_parent_directory_if_missing(tmp_path, monkeypatch):
    nested_file = tmp_path / "nested" / "maintenance"
    monkeypatch.setattr(maintenance, "_file", nested_file)
    monkeypatch.setattr(maintenance, "_on", False)

    maintenance.toggle()

    assert nested_file.exists()
