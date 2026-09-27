from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models.analysis_type import ANALYSIS_TYPE_EMOJI, ANALYSIS_TYPE_LABELS


def analysis_type_keyboard(include_new_company: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{ANALYSIS_TYPE_EMOJI[atype]} {label}",
                callback_data=f"analysis:{atype.value}",
            )
        ]
        for atype, label in ANALYSIS_TYPE_LABELS.items()
    ]
    if include_new_company:
        buttons.append(
            [InlineKeyboardButton(text="🔎 Другая компания", callback_data="onboarding:start_analysis")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
