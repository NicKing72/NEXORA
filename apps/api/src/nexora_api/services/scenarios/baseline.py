"""Prepare an immutable snapshot from an existing persisted ForecastRun."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastRun


def date_text(value: datetime) -> str:
    return value.astimezone(UTC).date().isoformat()


def prepare_baseline(run: ForecastRun) -> dict[str, object]:
    if run.status != "completed" or not run.champion_model or not run.points:
        raise DataStudioError(
            "scenario_baseline_unavailable",
            "El Forecast Run debe estar completado y contener puntos futuros.",
            409,
        )
    points = [
        {
            "timestamp": date_text(point.timestamp),
            "forecast": point.forecast,
            "lower_80": point.lower_80,
            "upper_80": point.upper_80,
            "lower_95": point.lower_95,
            "upper_95": point.upper_95,
        }
        for point in sorted(run.points, key=lambda item: item.timestamp)
    ]
    canonical = json.dumps(points, sort_keys=True, separators=(",", ":"))
    return {
        "forecast_run_id": run.id,
        "point_count": len(points),
        "points_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "points": points,
        "captured_champion": run.champion_model,
        "forecast_warnings": run.warnings,
        "forecast_preprocessing": run.preprocessing_summary,
        "captured_at": datetime.now(UTC).isoformat(),
    }


def verify_snapshot(snapshot: dict[str, object]) -> list[dict[str, object]]:
    raw = snapshot.get("points")
    if not isinstance(raw, list) or not raw:
        raise DataStudioError(
            "scenario_baseline_invalid", "El snapshot del baseline no es válido.", 409
        )
    points = [dict(item) for item in raw if isinstance(item, dict)]
    canonical = json.dumps(points, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    if digest != snapshot.get("points_sha256") or len(points) != snapshot.get("point_count"):
        raise DataStudioError(
            "scenario_baseline_integrity_failed",
            "La verificación de integridad del baseline falló.",
            409,
        )
    return points
