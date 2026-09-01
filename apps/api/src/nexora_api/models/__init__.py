"""Domain model registry imported before SQLAlchemy initializes metadata."""

from nexora_api.db.base import Base
from nexora_api.models.context import ContextImpactEstimate, ContextSignal, ContextSignalAudit
from nexora_api.models.dataset import (
    ColumnMapping,
    DataQualityIssue,
    DataQualityReport,
    Dataset,
    DatasetColumn,
    DataTransformation,
    ForecastFoldResult,
    ForecastModelResult,
    ForecastPoint,
    ForecastRun,
)
from nexora_api.models.decision import (
    DecisionAudit,
    DecisionEvidence,
    DecisionRecommendation,
    DecisionRun,
)
from nexora_api.models.explanation import ExplanationEvidence, ExplanationRun
from nexora_api.models.inventory import InventoryItem, InventoryRun
from nexora_api.models.portfolio import PortfolioItem, PortfolioRun
from nexora_api.models.report import ReportRun, ReportSection
from nexora_api.models.scenario import (
    ScenarioAssumption,
    ScenarioAudit,
    ScenarioPoint,
    ScenarioRun,
)
from nexora_api.models.scor import (
    ScorAssessmentRun,
    ScorAudit,
    ScorBenchmarkProfile,
    ScorBenchmarkTarget,
    ScorMetricInput,
    ScorMetricResult,
    ScorProcessResult,
)

__all__ = [
    "Base",
    "ColumnMapping",
    "ContextSignal",
    "ContextSignalAudit",
    "ContextImpactEstimate",
    "DataQualityIssue",
    "DataQualityReport",
    "DataTransformation",
    "Dataset",
    "DatasetColumn",
    "DecisionAudit",
    "DecisionEvidence",
    "DecisionRecommendation",
    "DecisionRun",
    "ForecastFoldResult",
    "ForecastModelResult",
    "ForecastPoint",
    "ForecastRun",
    "ExplanationEvidence",
    "ExplanationRun",
    "InventoryItem",
    "InventoryRun",
    "PortfolioItem",
    "PortfolioRun",
    "ReportRun",
    "ReportSection",
    "ScenarioAssumption",
    "ScenarioAudit",
    "ScenarioPoint",
    "ScenarioRun",
    "ScorAssessmentRun",
    "ScorAudit",
    "ScorBenchmarkProfile",
    "ScorBenchmarkTarget",
    "ScorMetricInput",
    "ScorMetricResult",
    "ScorProcessResult",
]
