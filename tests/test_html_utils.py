from app.utils.html import escape_html, strip_html


def test_escape_html_escapes_special_chars():
    assert escape_html("<b>Tom & Jerry</b>") == "&lt;b&gt;Tom &amp; Jerry&lt;/b&gt;"


def test_escape_html_leaves_plain_text_untouched():
    assert escape_html("Лукойл") == "Лукойл"


def test_strip_html_removes_tags():
    assert strip_html("<b>Strengths</b>\n- <i>пункт</i>") == "Strengths\n- пункт"


def test_strip_html_on_plain_text():
    assert strip_html("без тегов") == "без тегов"
