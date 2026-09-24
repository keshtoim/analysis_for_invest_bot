from app.models.analysis_type import (
    ANALYSIS_TYPE_DESCRIPTIONS,
    ANALYSIS_TYPE_EMOJI,
    ANALYSIS_TYPE_LABELS,
    AnalysisType,
)


def test_every_analysis_type_has_a_label():
    for atype in AnalysisType:
        assert atype in ANALYSIS_TYPE_LABELS, f"{atype} без записи в ANALYSIS_TYPE_LABELS"


def test_every_analysis_type_has_a_description():
    for atype in AnalysisType:
        assert atype in ANALYSIS_TYPE_DESCRIPTIONS, f"{atype} без записи в ANALYSIS_TYPE_DESCRIPTIONS"


def test_every_analysis_type_has_an_emoji():
    for atype in AnalysisType:
        assert atype in ANALYSIS_TYPE_EMOJI, f"{atype} без записи в ANALYSIS_TYPE_EMOJI"
