import re
from html.parser import HTMLParser


def escape_html(text: str) -> str:
    """Экранирует текст перед вставкой в сообщение Telegram с parse_mode=HTML."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def strip_html(text: str) -> str:
    """Убирает HTML-теги — запасной вариант, если Telegram не принял разметку."""
    return re.sub(r"<[^>]+>", "", text)


TELEGRAM_ALLOWED_TAGS = {"b", "i", "u", "s", "code", "pre", "a"}

_MD_HR_RE = re.compile(r"^[ \t]*[-*]{3,}[ \t]*$", re.MULTILINE)
_MD_HEADER_RE = re.compile(r"^[ \t]*#{1,6}[ \t]*", re.MULTILINE)
_MD_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _repair_markdown_leftovers(text: str) -> str:
    """Страховка на случай, если модель всё же не удержалась на чистом HTML."""
    text = _MD_HR_RE.sub("", text)
    text = _MD_HEADER_RE.sub("", text)
    text = _MD_BOLD_RE.sub(r"<b>\1</b>", text)
    return text


class _TelegramHTMLSanitizer(HTMLParser):
    """Оставляет только теги из TELEGRAM_ALLOWED_TAGS, балансирует их и
    экранирует остальной текст. Никогда не бросает исключение."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._out: list[str] = []
        self._open_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in TELEGRAM_ALLOWED_TAGS:
            return
        if tag == "a":
            href = next((value for name, value in attrs if name == "href" and value), None)
            if href is None:
                return
            self._out.append(f'<a href="{escape_html(href)}">')
        else:
            self._out.append(f"<{tag}>")
        self._open_stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in TELEGRAM_ALLOWED_TAGS or tag not in self._open_stack:
            return
        # Закрываем всё, что открыто позже — на случай перехлёста тегов
        while self._open_stack:
            open_tag = self._open_stack.pop()
            self._out.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data: str) -> None:
        self._out.append(escape_html(data))

    def get_sanitized(self) -> str:
        while self._open_stack:
            self._out.append(f"</{self._open_stack.pop()}>")
        return "".join(self._out)


def sanitize_telegram_html(text: str) -> str:
    """Гарантирует валидный Telegram HTML: только разрешённые теги, они
    сбалансированы, остальное — экранированный обычный текст."""
    text = _repair_markdown_leftovers(text)
    parser = _TelegramHTMLSanitizer()
    parser.feed(text)
    parser.close()
    return parser.get_sanitized()
