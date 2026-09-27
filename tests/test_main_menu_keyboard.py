from app.keyboards.main_menu import BTN_ANALYSIS, main_menu_keyboard
from app.keyboards.profile import BTN_PROFILE


def test_main_menu_has_analysis_before_profile():
    keyboard = main_menu_keyboard()
    texts = [button.text for row in keyboard.keyboard for button in row]

    assert texts == [BTN_ANALYSIS, BTN_PROFILE]
