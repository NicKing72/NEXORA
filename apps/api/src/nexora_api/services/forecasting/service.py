"""Application service orchestrating Forecast Core without duplicating Series Engine logic."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session, selectinload

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import (
    ForecastFoldResult,
    ForecastModelResult,
    ForecastPoint,
    ForecastRun,
)
from nexora_api.services.data_studio.storage import StorageService
from nexora_api.services.forecasting.backtesting import (
    assess_model_backtest_evaluability,
    evaluate_models,
)
from nexora_api.services.forecasting.intervals import empirical_intervals
from nexora_api.services.forecasting.models import MODEL_NAMES, fit_and_forecast, model_eligibility
from nexora_api.services.forecasting.preprocessing import PreparedSeries, prepare_training_series
from nexora_api.services.forecasting.ranking import rank_models
from nexora_api.services.series.engine import RequestFrequency, build_series_profile

DEFAULT_HORIZONS = {"daily": 30, "weekly": 12, "monthly": 12}
MAX_FORECAST_HORIZON = 365


def _profile(
    db: Session,
    storage: StorageService,
    *,
    dataset_id: str,
    product: str | None,
    location: str | None,
    category: str | None,
    frequency: RequestFrequency,
) -> dict[str, object]:
    return build_series_profile(
        db,
        dataset_id,
        storage,
        product=product,
        location=location,
        category=category,
        frequency=frequency,
    )


def _resolved_horizon(profile: dict[str, object], requested: int | None) -> int:
    frequency = str(profile["selection"]["resolved_frequency"])  # type: ignore[index]
    horizon = requested or DEFAULT_HORIZONS.get(frequency, 12)
    if horizon <= 0 or horizon > MAX_FORECAST_HORIZON:
        raise DataStudioError(
            "invalid_forecast_horizon",
            f"Forecast horizon must be between 1 and {MAX_FORECAST_HORIZON} periods.",
        )
    return horizon


def _eligibility(
    profile: dict[str, object], prepared: PreparedSeries, requested_horizon: int
) -> list[dict[str, object]]:
    frequency = str(profile["selection"]["resolved_frequency"])  # type: ignore[index]
    period = profile["seasonality"]["candidate_period"]  # type: ignore[index]
    seasonal_eligible = bool(profile["holt_winters"]["compatible"])  # type: ignore[index]
    summaries: list[dict[str, object]] = []
    for model_name in MODEL_NAMES:
        final_eligible, final_reason = model_eligibility(
            model_name,
            prepared.series,
            frequency=frequency,
            seasonal_period=period if isinstance(period, int) else None,
            seasonal_eligible=seasonal_eligible,
            continuous=prepared.continuous,
        )
        backtest = (
            assess_model_backtest_evaluability(
                model_name,
                prepared.series,
                frequency=frequency,
                requested_horizon=requested_horizon,
                seasonal_period=period if isinstance(period, int) else None,
                seasonal_eligible=seasonal_eligible,
            )
            if final_eligible
            else {
                "evaluable": False,
                "reason": final_reason,
                "evaluable_folds": 0,
                "total_folds": 0,
            }
        )
        summaries.append(
            {
                # Backward-compatible aliases remain while explicit semantics are exposed.
                "eligible": final_eligible,
                "reason": final_reason,
                "final_fit_eligible": final_eligible,
                "final_fit_reason": final_reason,
                "backtest_evaluable": backtest["evaluable"],
                "backtest_reason": backtest["reason"],
                "evaluable_folds": backtest["evaluable_folds"],
                "total_folds": backtest["total_folds"],
                "model_name": model_name,
            }
        )
    return summaries


def build_preflight(
    db: Session,
    storage: StorageService,
    *,
    dataset_id: str,
    product: str | None = None,
    location: str | None = None,
    category: str | None = None,
    frequency: RequestFrequency = "auto",
    horizon: int | None = None,
) -> dict[str, object]:
    profile = _profile(
        db,
        storage,
        dataset_id=dataset_id,
        product=product,
        location=location,
        category=category,
        frequency=frequency,
    )
    prepared = prepare_training_series(profile)
    resolved_horizon = _resolved_horizon(profile, horizon)
    return {
        "selection": profile["selection"],
        "horizon": resolved_horizon,
        "data_cutoff": str(profile["selection"]["data_cutoff"]),  # type: ignore[index]
        "training_cutoff": prepared.summary["training_cutoff"],
        "preprocessing": prepared.summary,
        "interpolation_audit": prepared.interpolation_audit,
        "warnings": prepared.warnings,
        "seasonality": profile["seasonality"],
        "holt_winters": profile["holt_winters"],
        "quality": profile["statistics"]["underlying_quality"],  # type: ignore[index]
        "model_eligibility": _eligibility(profile, prepared, resolved_horizon),
    }


def _utc_timestamp(timestamp: pd.Timestamp) -> datetime:
    value = timestamp.to_pydatetime()
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def future_index(cutoff: pd.Timestamp, frequency: str, horizon: int) -> pd.DatetimeIndex:
    aliases = {
        "hourly": "h",
        "daily": "D",
        "weekly": "W-MON",
        "monthly": "MS",
        "quarterly": "QS",
        "yearly": "YS",
    }
    alias = aliases.get(frequency)
    if alias is None:
        raise DataStudioError(
            "unsupported_forecast_frequency",
            "The selected frequency cannot generate an unambiguous future index.",
        )
    if frequency == "hourly":
        start = cutoff + pd.Timedelta(hours=1)
    elif frequency == "daily":
        start = cutoff + pd.Timedelta(days=1)
    elif frequency == "weekly":
        start = cutoff + pd.Timedelta(days=7)
    elif frequency == "monthly":
        start = cutoff + pd.offsets.MonthBegin(1)
    elif frequency == "quarterly":
        start = cutoff + pd.offsets.QuarterBegin(startingMonth=1)
    else:
        start = cutoff + pd.offsets.YearBegin(1)
    return pd.date_range(start=start, periods=horizon, freq=alias)


def _persist_models(
    db: Session, run: ForecastRun, results: list[dict[str, object]]
) -> dict[str, ForecastModelResult]:
    persisted: dict[str, ForecastModelResult] = {}
    for result in results:
        model = ForecastModelResult(
            run_id=run.id,
            model_name=str(result["model_name"]),
            eligible=bool(result["eligible"]),
            status=str(result["status"]),
            failure_reason=result.get("failure_reason"),
            parameters=dict(result.get("parameters", {})),
            metrics=dict(result.get("metrics", {})),
            stability=dict(result.get("stability", {})),
            rank=result.get("rank"),
        )
        db.add(model)
        db.flush()
        for fold in result.get("folds", []):
            db.add(
                ForecastFoldResult(
                    model_result_id=model.id,
                    fold_index=int(fold["fold_index"]),
                    train_start=_utc_timestamp(fold["train_start"]),
                    train_end=_utc_timestamp(fold["train_end"]),
                    validation_start=_utc_timestamp(fold["validation_start"]),
                    validation_end=_utc_timestamp(fold["validation_end"]),
                    training_observations=int(fold["training_observations"]),
                    validation_observations=int(fold["validation_observations"]),
                    metrics=dict(fold["metrics"]),
                    actual_values=list(fold["actual_values"]),
                    forecast_values=list(fold["forecast_values"]),
                )
            )
        persisted[model.model_name] = model
    return persisted


def execute_forecast_run(
    db: Session,
    storage: StorageService,
    *,
    dataset_id: str,
    product: str | None = None,
    location: str | None = None,
    category: str | None = None,
    frequency: RequestFrequency = "auto",
    horizon: int | None = None,
) -> ForecastRun:
    """Run temporal model comparison, persist audit artifacts, and forecast with Champion."""
    profile = _profile(
        db,
        storage,
        dataset_id=dataset_id,
        product=product,
        location=location,
        category=category,
        frequency=frequency,
    )
    prepared = prepare_training_series(profile)
    if int(prepared.series.notna().sum()) < 6:
        raise DataStudioError(
            "insufficient_forecast_history",
            "At least six valid periods are required for temporal evaluation.",
        )
    resolved_frequency = str(profile["selection"]["resolved_frequency"])  # type: ignore[index]
    resolved_horizon = _resolved_horizon(profile, horizon)
    seasonal_period_value = profile["seasonality"]["candidate_period"]  # type: ignore[index]
    seasonal_period = seasonal_period_value if isinstance(seasonal_period_value, int) else None
    seasonal_eligible = bool(profile["holt_winters"]["compatible"])  # type: ignore[index]
    results, validation_horizon = evaluate_models(
        prepared.series,
        frequency=resolved_frequency,
        requested_horizon=resolved_horizon,
        seasonal_period=seasonal_period,
        seasonal_eligible=seasonal_eligible,
        continuous=prepared.continuous,
    )
    ranked, champion_reason = rank_models(results)
    champion = next((item for item in ranked if item.get("rank") == 1), None)
    training_cutoff_text = str(prepared.summary["training_cutoff"])
    visible_period_cutoff = max(pd.Timestamp(point["date"]) for point in profile["points"])
    source_cutoff = pd.Timestamp(profile["selection"]["data_cutoff"])  # type: ignore[index]
    run = ForecastRun(
        id=str(uuid4()),
        dataset_id=dataset_id,
        product=product,
        location=location,
        category=category,
        frequency=resolved_frequency,
        requested_horizon=resolved_horizon,
        validation_horizon=validation_horizon,
        data_cutoff=_utc_timestamp(source_cutoff),
        preprocessing_summary={
            **prepared.summary,
            "interpolation_audit": prepared.interpolation_audit,
            "training_cutoff": training_cutoff_text,
        },
        seasonality_candidate=seasonal_period,
        seasonality_evidence=str(profile["seasonality"]["evidence"]),  # type: ignore[index]
        status="running",
        champion_model=str(champion["model_name"]) if champion else None,
        champion_reason=champion_reason,
        warnings=prepared.warnings,
    )
    db.add(run)
    db.flush()
    persisted = _persist_models(db, run, ranked)
    if champion is None:
        run.status = "failed"
        run.warnings = [*run.warnings, "no_model_completed_backtesting"]
        db.commit()
        return run
    try:
        final_fit = fit_and_forecast(
            str(champion["model_name"]),
            prepared.series,
            resolved_horizon,
            frequency=resolved_frequency,
            seasonal_period=seasonal_period,
            seasonal_eligible=seasonal_eligible,
            continuous=prepared.continuous,
        )
    except (ValueError, RuntimeError, ArithmeticError) as error:
        run.status = "failed"
        run.warnings = [*run.warnings, "champion_final_fit_failed"]
        model = persisted[str(champion["model_name"])]
        model.status = "failed"
        model.failure_reason = str(error)
        db.commit()
        return run
    champion_model = persisted[str(champion["model_name"])]
    champion_model.parameters = final_fit.parameters
    residuals = list(champion.get("residuals", []))
    interval = empirical_intervals(final_fit.values, residuals)
    future_dates = future_index(visible_period_cutoff, resolved_frequency, resolved_horizon)
    for index, timestamp in enumerate(future_dates):
        db.add(
            ForecastPoint(
                run_id=run.id,
                timestamp=_utc_timestamp(timestamp),
                forecast=round(float(final_fit.values[index]), 6),
                lower_80=interval["lower_80"][index],
                upper_80=interval["upper_80"][index],
                lower_95=interval["lower_95"][index],
                upper_95=interval["upper_95"][index],
            )
        )
    run.preprocessing_summary = {
        **run.preprocessing_summary,
        "interval_method": interval["method"],
        "interval_residual_count": interval["residual_count"],
    }
    run.status = "completed"
    db.commit()
    db.refresh(run)
    return run


def _run_query(db: Session):
    return db.query(ForecastRun).options(
        selectinload(ForecastRun.points),
        selectinload(ForecastRun.model_results).selectinload(ForecastModelResult.folds),
    )


def require_run(db: Session, run_id: str) -> ForecastRun:
    run = _run_query(db).filter(ForecastRun.id == run_id).one_or_none()
    if run is None:
        raise DataStudioError("forecast_run_not_found", "The forecast run does not exist.", 404)
    return run


def _date_text(value: datetime) -> str:
    return value.astimezone(UTC).date().isoformat()


def serialize_fold(fold: ForecastFoldResult) -> dict[str, object]:
    return {
        "id": fold.id,
        "fold_index": fold.fold_index,
        "train_start": _date_text(fold.train_start),
        "train_end": _date_text(fold.train_end),
        "validation_start": _date_text(fold.validation_start),
        "validation_end": _date_text(fold.validation_end),
        "training_observations": fold.training_observations,
        "validation_observations": fold.validation_observations,
        "metrics": fold.metrics,
        "actual_values": fold.actual_values,
        "forecast_values": fold.forecast_values,
    }


def serialize_model(model: ForecastModelResult, include_folds: bool = True) -> dict[str, object]:
    backtest_evaluable = bool(model.folds)
    return {
        "id": model.id,
        "model_name": model.model_name,
        "eligible": model.eligible,
        "final_fit_eligible": model.eligible,
        "backtest_evaluable": backtest_evaluable,
        "backtest_reason": None if backtest_evaluable else model.failure_reason,
        "status": model.status,
        "failure_reason": model.failure_reason,
        "parameters": model.parameters,
        "metrics": model.metrics,
        "stability": model.stability,
        "rank": model.rank,
        "folds": [
            serialize_fold(fold)
            for fold in sorted(model.folds, key=lambda item: item.fold_index)
        ]
        if include_folds
        else [],
    }


def serialize_point(point: ForecastPoint) -> dict[str, object]:
    return {
        "timestamp": _date_text(point.timestamp),
        "forecast": point.forecast,
        "lower_80": point.lower_80,
        "upper_80": point.upper_80,
        "lower_95": point.lower_95,
        "upper_95": point.upper_95,
    }


def serialize_run(
    db: Session, run: ForecastRun, storage: StorageService, *, include_details: bool = True
) -> dict[str, object]:
    profile = _profile(
        db,
        storage,
        dataset_id=run.dataset_id,
        product=run.product,
        location=run.location,
        category=run.category,
        frequency=run.frequency,  # type: ignore[arg-type]
    )
    models = sorted(
        run.model_results,
        key=lambda item: (item.rank is None, item.rank or 999, item.model_name),
    )
    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "selection": profile["selection"],
        "frequency": run.frequency,
        "requested_horizon": run.requested_horizon,
        "validation_horizon": run.validation_horizon,
        "created_at": run.created_at,
        "data_cutoff": _date_text(run.data_cutoff),
        "training_cutoff": run.preprocessing_summary.get("training_cutoff"),
        "preprocessing": run.preprocessing_summary,
        "seasonality_candidate": run.seasonality_candidate,
        "seasonality_evidence": run.seasonality_evidence,
        "status": run.status,
        "champion_model": run.champion_model,
        "champion_reason": run.champion_reason,
        "warnings": run.warnings,
        "history": profile["points"] if include_details else [],
        "models": [serialize_model(model, include_folds=include_details) for model in models],
        "forecast_points": [
            serialize_point(point) for point in sorted(run.points, key=lambda item: item.timestamp)
        ],
    }


def list_runs(db: Session) -> list[dict[str, object]]:
    runs = db.query(ForecastRun).order_by(ForecastRun.created_at.desc()).limit(50).all()
    return [
        {
            "id": run.id,
            "dataset_id": run.dataset_id,
            "frequency": run.frequency,
            "requested_horizon": run.requested_horizon,
            "created_at": run.created_at,
            "data_cutoff": _date_text(run.data_cutoff),
            "status": run.status,
            "champion_model": run.champion_model,
        }
        for run in runs
    ]
