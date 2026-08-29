"""End-to-end persistence and retrieval for a compact forecast run."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient


def _ready_series(client: TestClient) -> dict:
    start = date(2025, 1, 1)
    pattern = [10, 14, 18, 22, 17, 9, 7]
    rows = ["date,product,location,demand,stock"]
    for index in range(70):
        demand = pattern[index % 7] + index * 0.05
        rows.append(f"{start + timedelta(days=index)},A,North,{demand},20")
    upload = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("forecast.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
    )
    assert upload.status_code == 201
    dataset = upload.json()
    mappings = [
        {"column_name": item["column_name"], "role": item["role"]} for item in dataset["mappings"]
    ]
    assert (
        client.put(
            f"/api/v1/datasets/{dataset['id']}/mappings", json={"mappings": mappings}
        ).status_code
        == 200
    )
    assert client.post(f"/api/v1/datasets/{dataset['id']}/validate").status_code == 200
    assert client.post(f"/api/v1/datasets/{dataset['id']}/ready").status_code == 200
    return dataset


def _request(dataset_id: str) -> dict:
    return {
        "dataset_id": dataset_id,
        "product": "A",
        "location": "North",
        "frequency": "daily",
        "horizon": 7,
    }


def test_preflight_exposes_training_decisions(client: TestClient) -> None:
    dataset = _ready_series(client)
    response = client.post("/api/v1/forecast-runs/preflight", json=_request(dataset["id"]))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["preprocessing"]["training_periods"] == 70
    assert result["seasonality"]["candidate_period"] == 7
    assert result["data_cutoff"] == result["training_cutoff"] == "2025-03-11"
    assert len(result["model_eligibility"]) == 7
    additive = next(
        model
        for model in result["model_eligibility"]
        if model["model_name"] == "holt_winters_additive"
    )
    assert additive["final_fit_eligible"] is True
    assert additive["backtest_evaluable"] is True
    assert additive["evaluable_folds"] == 5


def test_forecast_run_and_all_artifacts_persist(client: TestClient) -> None:
    dataset = _ready_series(client)
    response = client.post("/api/v1/forecast-runs", json=_request(dataset["id"]))
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["status"] == "completed"
    assert result["champion_model"]
    assert len(result["models"]) == 7
    assert any(model["folds"] for model in result["models"] if model["status"] == "succeeded")
    assert len(result["forecast_points"]) == 7
    assert result["forecast_points"][0]["timestamp"] == "2025-03-12"

    retrieved = client.get(f"/api/v1/forecast-runs/{result['id']}")
    leaderboard = client.get(f"/api/v1/forecast-runs/{result['id']}/leaderboard")
    points = client.get(f"/api/v1/forecast-runs/{result['id']}/points")
    assert retrieved.status_code == leaderboard.status_code == points.status_code == 200
    assert retrieved.json()["id"] == result["id"]
    assert retrieved.json()["training_cutoff"] == result["training_cutoff"]
    assert len(leaderboard.json()) == 7
    assert points.json() == result["forecast_points"]

    champion = next(model for model in result["models"] if model["rank"] == 1)
    runner_up = next(model for model in result["models"] if model["rank"] == 2)
    expected_reason = (
        "near_tie_bias_stability"
        if runner_up["metrics"]["wmape"] - champion["metrics"]["wmape"] < 0.005
        else "lowest_wmape"
    )
    assert result["champion_reason"] == expected_reason
    assert champion["parameters"]["engine"]
    assert champion["parameters"]["parameter_source"]
    assert champion["final_fit_eligible"] is True
    assert champion["backtest_evaluable"] is True
    detail = client.get(f"/api/v1/forecast-runs/{result['id']}/models/{champion['id']}")
    folds = client.get(f"/api/v1/forecast-runs/{result['id']}/models/{champion['id']}/folds")
    assert detail.status_code == folds.status_code == 200
    assert detail.json()["model_name"] == result["champion_model"]
    assert detail.json()["rank"] == 1
    assert retrieved.json()["champion_reason"] == expected_reason
    assert folds.json()


def test_forecast_run_timestamp_is_utc_and_cutoff_is_correct(client: TestClient) -> None:
    dataset = _ready_series(client)
    result = client.post("/api/v1/forecast-runs", json=_request(dataset["id"])).json()
    created_at = datetime.fromisoformat(result["created_at"])
    assert created_at.tzinfo is not None
    assert created_at.astimezone(UTC).utcoffset() == timedelta(0)
    assert result["data_cutoff"] == "2025-03-11"
    assert result["training_cutoff"] == "2025-03-11"


def test_invalid_horizon_is_rejected(client: TestClient) -> None:
    dataset = _ready_series(client)
    payload = {**_request(dataset["id"]), "horizon": 0}
    assert client.post("/api/v1/forecast-runs", json=payload).status_code == 422


def test_weekly_forecast_starts_after_visible_partial_period(client: TestClient) -> None:
    start = date(2025, 1, 6)
    rows = ["date,product,location,demand"]
    rows.extend(
        f"{start + timedelta(days=index)},A,North,10" for index in range(52)
    )
    upload = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("partial.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
    ).json()
    client.post(f"/api/v1/datasets/{upload['id']}/validate")
    client.post(f"/api/v1/datasets/{upload['id']}/ready")
    result = client.post(
        "/api/v1/forecast-runs",
        json={
            "dataset_id": upload["id"],
            "product": "A",
            "location": "North",
            "frequency": "weekly",
            "horizon": 2,
        },
    ).json()
    assert result["preprocessing"]["excluded_partial_periods"] == 1
    assert result["preprocessing"]["training_cutoff"] == "2025-02-17"
    assert result["data_cutoff"] == "2025-02-26"
    assert result["training_cutoff"] == "2025-02-17"
    assert result["forecast_points"][0]["timestamp"] == "2025-03-03"


def test_seasonal_model_without_enough_fold_history_is_not_a_runtime_failure(
    client: TestClient,
) -> None:
    start = date(2024, 1, 1)
    rows = ["date,product,location,demand"]
    rows.extend(
        f"{start + timedelta(days=index)},A,North,{10 + (index % 7)}"
        for index in range(731)
    )
    upload = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("weekly.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
    ).json()
    client.post(f"/api/v1/datasets/{upload['id']}/validate")
    client.post(f"/api/v1/datasets/{upload['id']}/ready")
    request = {
        "dataset_id": upload["id"],
        "product": "A",
        "location": "North",
        "frequency": "weekly",
        "horizon": 12,
    }
    preflight = client.post("/api/v1/forecast-runs/preflight", json=request).json()
    preflight_seasonal = next(
        model
        for model in preflight["model_eligibility"]
        if model["model_name"] == "holt_winters_additive"
    )
    assert preflight_seasonal["final_fit_eligible"] is True
    assert preflight_seasonal["backtest_evaluable"] is False
    assert preflight_seasonal["backtest_reason"] == "insufficient_fold_seasonal_history"
    assert preflight_seasonal["evaluable_folds"] == 0
    assert preflight_seasonal["total_folds"] == 5
    assert preflight["data_cutoff"] == "2025-12-31"
    assert preflight["training_cutoff"] == "2025-12-22"

    result = client.post("/api/v1/forecast-runs", json=request).json()
    seasonal = next(
        model for model in result["models"] if model["model_name"] == "holt_winters_additive"
    )
    assert seasonal["eligible"] is True
    assert seasonal["final_fit_eligible"] is True
    assert seasonal["backtest_evaluable"] is False
    assert seasonal["status"] == "not_evaluable"
    assert seasonal["failure_reason"] == "insufficient_fold_seasonal_history"
    assert seasonal["backtest_reason"] == "insufficient_fold_seasonal_history"
    assert result["data_cutoff"] == "2025-12-31"
    assert result["training_cutoff"] == "2025-12-22"
    assert result["forecast_points"][0]["timestamp"] == "2026-01-05"
    assert result["forecast_points"][-1]["timestamp"] == "2026-03-23"

    retrieved = client.get(f"/api/v1/forecast-runs/{result['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["training_cutoff"] == "2025-12-22"
    assert retrieved.json()["data_cutoff"] == "2025-12-31"


def test_health_remains_operational_with_forecast_core(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
