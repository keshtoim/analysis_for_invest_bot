import re


def escape_html(text: str) -> str:
    """Экранирует текст перед вставкой в сообщение Telegram с parse_mode=HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_html(text: str) -> str:
    """Убирает HTML-теги — запасной вариант, если Telegram не принял разметку."""
    return re.sub(r"<[^>]+>", "", text)
