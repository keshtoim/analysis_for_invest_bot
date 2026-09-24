import pytest

from app.handlers import analysis
from app.models.analysis_type import ANALYSIS_TYPE_LABELS


@pytest.fixture(autouse=True)
def _reset_flood_state():
    analysis._last_analysis_request.clear()


def test_first_request_is_not_flooding():
    assert analysis._is_flooding(user_id=1) is False


def test_immediate_second_request_is_flooding():
    analysis._is_flooding(user_id=1)
    assert analysis._is_flooding(user_id=1) is True


def test_different_users_do_not_affect_each_other():
    analysis._is_flooding(user_id=1)
    assert analysis._is_flooding(user_id=2) is False


def test_menu_text_contains_company_name_and_all_types():
    text = analysis._analysis_type_menu_text("Лукойл")

    assert "Лукойл" in text
    for label in ANALYSIS_TYPE_LABELS.values():
        assert label in text


def test_menu_text_escapes_company_name():
    text = analysis._analysis_type_menu_text("<script>")

    assert "<script>" not in text
    assert "&lt;script&gt;" in text
