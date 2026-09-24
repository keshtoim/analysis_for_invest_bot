from enum import Enum


class AnalysisType(str, Enum):
    SWOT = "swot"
    PESTEL = "pestel"
    PORTER_FIVE_FORCES = "porter"
    FINANCIAL_MULTIPLES = "financial"


ANALYSIS_TYPE_LABELS = {
    AnalysisType.SWOT: "SWOT",
    AnalysisType.PESTEL: "PESTEL",
    AnalysisType.PORTER_FIVE_FORCES: "5 сил Портера",
    AnalysisType.FINANCIAL_MULTIPLES: "Финансовые мультипликаторы",
}

ANALYSIS_TYPE_DESCRIPTIONS = {
    AnalysisType.SWOT: "сильные и слабые стороны, возможности и угрозы",
    AnalysisType.PESTEL: (
        "политические, экономические, социальные, технологические, "
        "экологические и правовые факторы"
    ),
    AnalysisType.PORTER_FIVE_FORCES: (
        "конкуренция, поставщики, покупатели, товары-заменители, барьеры для новых игроков"
    ),
    AnalysisType.FINANCIAL_MULTIPLES: "P/E, P/B, P/S, долговая нагрузка",
}
