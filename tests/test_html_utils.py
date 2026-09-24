from app.utils.html import escape_html, sanitize_telegram_html, strip_html


def test_escape_html_escapes_special_chars():
    assert escape_html("<b>Tom & Jerry</b>") == "&lt;b&gt;Tom &amp; Jerry&lt;/b&gt;"


def test_escape_html_leaves_plain_text_untouched():
    assert escape_html("Лукойл") == "Лукойл"


def test_strip_html_removes_tags():
    assert strip_html("<b>Strengths</b>\n- <i>пункт</i>") == "Strengths\n- пункт"


def test_strip_html_on_plain_text():
    assert strip_html("без тегов") == "без тегов"


def test_sanitize_keeps_allowed_tags():
    assert sanitize_telegram_html("<b>Strengths</b>") == "<b>Strengths</b>"


def test_sanitize_strips_disallowed_tags_but_keeps_text():
    assert sanitize_telegram_html("<h1>Заголовок</h1><ul><li>пункт</li></ul>") == "Заголовокпункт"


def test_sanitize_closes_unclosed_tag():
    assert sanitize_telegram_html("<b>Strengths") == "<b>Strengths</b>"


def test_sanitize_ignores_stray_closing_tag():
    assert sanitize_telegram_html("Strengths</b>") == "Strengths"


def test_sanitize_repairs_overlapping_tags():
    # <b>bold <i>italic</b> still italic?</i> — некорректная вложенность
    result = sanitize_telegram_html("<b>bold <i>italic</b> still italic?</i>")
    assert result == "<b>bold <i>italic</i></b> still italic?"


def test_sanitize_escapes_stray_angle_brackets():
    assert sanitize_telegram_html("5 < 10 и 10 > 5") == "5 &lt; 10 и 10 &gt; 5"


def test_sanitize_repairs_markdown_bold():
    assert sanitize_telegram_html("**Strengths**") == "<b>Strengths</b>"


def test_sanitize_strips_markdown_headers_and_hr():
    text = "## Strengths\n---\nПункт"
    assert sanitize_telegram_html(text) == "Strengths\n\nПункт"


def test_sanitize_drops_link_without_href():
    assert sanitize_telegram_html('<a>текст</a>') == "текст"


def test_sanitize_keeps_link_with_href():
    result = sanitize_telegram_html('<a href="https://example.com">текст</a>')
    assert result == '<a href="https://example.com">текст</a>'
