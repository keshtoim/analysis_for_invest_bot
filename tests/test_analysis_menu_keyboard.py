from app.keyboards.analysis_menu import analysis_type_keyboard
from app.models.analysis_type import AnalysisType


def _flat_buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_default_keyboard_has_no_new_company_button():
    buttons = _flat_buttons(analysis_type_keyboard())

    assert len(buttons) == len(AnalysisType)
    assert all(b.callback_data.startswith("analysis:") for b in buttons)


def test_keyboard_with_new_company_appends_extra_button():
    buttons = _flat_buttons(analysis_type_keyboard(include_new_company=True))

    assert len(buttons) == len(AnalysisType) + 1
    assert buttons[-1].callback_data == "onboarding:start_analysis"
    assert "Другая компания" in buttons[-1].text
