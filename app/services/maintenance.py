"""Режим техработ: бот остаётся живым, но всем кроме владельца отвечает
«вернусь позже». Флаг — файл data/maintenance, переживает перезапуск.
Владелец включает/выключает командой /maintenance.
"""

from pathlib import Path

from app.config import MAINTENANCE_PATH

NOTICE = "🔧 Бот на технических работах, скоро вернусь. Загляни попозже."

_file = Path(MAINTENANCE_PATH)
_on = _file.exists()


def is_on() -> bool:
    return _on


def toggle() -> bool:
    """Переключить и вернуть новое состояние."""
    global _on
    _on = not _on
    if _on:
        _file.parent.mkdir(parents=True, exist_ok=True)
        _file.touch()
    else:
        _file.unlink(missing_ok=True)
    return _on
