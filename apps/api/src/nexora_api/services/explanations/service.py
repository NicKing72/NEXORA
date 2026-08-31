"""Orchestration and persistence for immutable forecast explanations."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.explanation import ExplanationEvidence, ExplanationRun
from nexora_api.services.explanations import EXPLANATION_VERSION
from nexora_api.services.explanations.explanation_evidence import prepare_snapshot


def preflight(db: Session, **request: object) -> dict[str, object]:
    snapshot = prepare_snapshot(db, **request)  # type: ignore[arg-type]
    layers = snapshot["layers"]
    return {
        "forecast_run_id": snapshot["forecast"]["id"],
        "dataset_id": snapshot["dataset"]["id"],
        "cutoff": snapshot["cutoff"],
        "scope": snapshot["scope"],
        "champion": snapshot["champion"],
        "available_layers": {
            key: value is not None for key, value in layers.items()
        },
        "limitations": snapshot["limitations"],
        "warnings": snapshot["warnings"],
    }


def create_run(db: Session, **request: object) -> ExplanationRun:
    snapshot = prepare_snapshot(db, **request)  # type: ignore[arg-type]
    forecast = snapshot.pop("forecast_run")
    source_snapshot = {
        "scope": snapshot["scope"],
        "dataset": snapshot["dataset"],
        "forecast": snapshot["forecast"],
        "champion": snapshot["champion"],
        "comparison": snapshot["comparison"],
        "backtesting": snapshot["backtesting"],
        "forecast_output": snapshot["forecast_output"],
        "layers": snapshot["layers"],
        "provenance": {
            "forecast_run_id": forecast.id,
            "dataset_id": forecast.dataset_id,
            "explanation_cutoff": snapshot["cutoff"].isoformat(),
            "forecast_created_at": forecast.created_at.isoformat(),
            "forecast_core_version": snapshot["forecast"].get("calculation_version"),
            "explanation_version": EXPLANATION_VERSION,
            "sources_remain_separate": True,
        },
    }
    run = ExplanationRun(
        id=str(uuid4()),
        forecast_run_id=forecast.id,
        dataset_id=forecast.dataset_id,
        series_id=str(snapshot["series_id"]),
        frequency=forecast.frequency,
        horizon=forecast.requested_horizon,
        champion_model=str(forecast.champion_model),
        cutoff=snapshot["cutoff"],
        version=EXPLANATION_VERSION,
        status="completed",
        created_from=str(snapshot["created_from"]),
        source_snapshot=source_snapshot,
        limitations_snapshot=list(snapshot["limitations"]),
    )
    db.add(run)
    db.flush()
    evidence_specs = [
        ("dataset", "dataset", forecast.dataset_id, "Dataset utilizado", snapshot["dataset"]),
        ("forecast", "forecast_run", forecast.id, "Forecast Run oficial", snapshot["forecast"]),
        ("champion", "forecast_model", forecast.id, "Modelo Champion", snapshot["champion"]),
        (
            "comparison",
            "forecast_run",
            forecast.id,
            "Comparación persistida",
            {"models": snapshot["comparison"]},
        ),
        (
            "backtesting",
            "forecast_run",
            forecast.id,
            "Validación histórica",
            snapshot["backtesting"],
        ),
        (
            "forecast_output",
            "forecast_run",
            forecast.id,
            "Pronóstico e intervalos",
            snapshot["forecast_output"],
        ),
        ("downstream_layers", "mixed", None, "Capas posteriores separadas", snapshot["layers"]),
    ]
    for evidence_type, source_type, source_id, label, value in evidence_specs:
        db.add(
            ExplanationEvidence(
                explanation_run_id=run.id,
                evidence_type=evidence_type,
                source_type=source_type,
                source_id=source_id,
                label=label,
                value_snapshot=value,
                metadata_snapshot={"frozen": True, "version": EXPLANATION_VERSION},
                provenance={
                    "captured_at_cutoff": snapshot["cutoff"].isoformat(),
                    "recalculated": False,
                },
            )
        )
    db.commit()
    return require_run(db, run.id)


def _query(db: Session):
    return db.query(ExplanationRun).options(selectinload(ExplanationRun.evidence))


def require_run(db: Session, run_id: str) -> ExplanationRun:
    run = _query(db).filter(ExplanationRun.id == run_id).one_or_none()
    if run is None:
        raise DataStudioError(
            "explanation_run_not_found", "The explanation run does not exist.", 404
        )
    return run


def serialize_evidence(item: ExplanationEvidence) -> dict[str, object]:
    return {
        "id": item.id,
        "evidence_type": item.evidence_type,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "label": item.label,
        "value": item.value_snapshot,
        "metadata": item.metadata_snapshot,
        "provenance": item.provenance,
        "created_at": item.created_at,
    }


def serialize_run(run: ExplanationRun, *, details: bool = True) -> dict[str, object]:
    response = {
        "id": run.id,
        "forecast_run_id": run.forecast_run_id,
        "dataset_id": run.dataset_id,
        "series_id": run.series_id,
        "frequency": run.frequency,
        "horizon": run.horizon,
        "champion_model": run.champion_model,
        "cutoff": run.cutoff,
        "version": run.version,
        "status": run.status,
        "created_from": run.created_from,
        "created_at": run.created_at,
    }
    if details:
        response.update(
            {
                "available_at": run.available_at,
                "source_snapshot": run.source_snapshot,
                "limitations": run.limitations_snapshot,
                "evidence": [
                    serialize_evidence(item)
                    for item in sorted(run.evidence, key=lambda evidence: evidence.id)
                ],
            }
        )
    return response


def list_runs(db: Session) -> list[dict[str, object]]:
    runs = _query(db).order_by(ExplanationRun.created_at.desc()).limit(50).all()
    return [serialize_run(run, details=False) for run in runs]


def model_view(run: ExplanationRun) -> dict[str, object]:
    return {
        "champion": run.source_snapshot.get("champion", {}),
        "comparison": run.source_snapshot.get("comparison", []),
    }


def backtesting_view(run: ExplanationRun) -> dict[str, object]:
    return dict(run.source_snapshot.get("backtesting", {}))


def forecast_view(run: ExplanationRun) -> dict[str, object]:
    return dict(run.source_snapshot.get("forecast_output", {}))


def provenance_view(run: ExplanationRun) -> dict[str, object]:
    return {
        "sources": {
            "provenance": run.source_snapshot.get("provenance", {}),
            "scope": run.source_snapshot.get("scope", {}),
            "layers": run.source_snapshot.get("layers", {}),
        },
        "limitations": run.limitations_snapshot,
    }
