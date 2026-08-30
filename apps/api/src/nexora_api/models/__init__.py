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
from nexora_api.models.scenario import (
    ScenarioAssumption,
    ScenarioAudit,
    ScenarioPoint,
    ScenarioRun,
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
    "ForecastFoldResult",
    "ForecastModelResult",
    "ForecastPoint",
    "ForecastRun",
    "ScenarioAssumption",
    "ScenarioAudit",
    "ScenarioPoint",
    "ScenarioRun",
]
