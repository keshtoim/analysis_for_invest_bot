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
