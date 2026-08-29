"""Deterministic coverage for Demand Explorer and canonical series construction."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pandas as pd
from fastapi.testclient import TestClient

from nexora_api.services.data_studio.storage import StorageService
from nexora_api.services.series.analysis import pattern_summary


def prepare_ready_csv(client: TestClient, content: str, filename: str = "series.csv") -> dict:
    uploaded = client.post(
        "/api/v1/datasets/upload",
        files={"file": (filename, content.encode("utf-8"), "text/csv")},
    )
    assert uploaded.status_code == 201, uploaded.text
    dataset = uploaded.json()
    mappings = [
        {"column_name": mapping["column_name"], "role": mapping["role"]}
        for mapping in dataset["mappings"]
    ]
    saved = client.put(
        f"/api/v1/datasets/{dataset['id']}/mappings", json={"mappings": mappings}
    )
    assert saved.status_code == 200, saved.text
    validated = client.post(f"/api/v1/datasets/{dataset['id']}/validate")
    assert validated.status_code == 200, validated.text
    assert validated.json()["report"]["has_critical_errors"] is False
    ready = client.post(f"/api/v1/datasets/{dataset['id']}/ready")
    assert ready.status_code == 200, ready.text
    return ready.json()["dataset"]


def profile(client: TestClient, dataset_id: str, **params: str) -> dict:
    response = client.get(f"/api/v1/series/datasets/{dataset_id}/profile", params=params)
    assert response.status_code == 200, response.text
    return response.json()


MULTI_DIMENSION_CSV = (
    "date,product,category,location,demand,price,stock,promotion\n"
    "2025-01-06,A,Core,North,2,10,9,0\n"
    "2025-01-06,A,Core,North,3,12,8,1\n"
    "2025-01-06,A,Core,South,5,11,7,0\n"
    "2025-01-06,B,Plus,North,7,20,6,0\n"
    "2025-01-07,A,Core,North,4,10,5,0\n"
    "2025-01-07,A,Core,South,6,12,4,0\n"
    "2025-01-07,B,Plus,North,8,20,3,0\n"
)


def test_lists_only_ready_datasets_and_dimensions(client: TestClient) -> None:
    unready = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("draft.csv", b"date,demand\n2025-01-01,1\n", "text/csv")},
    ).json()
    ready = prepare_ready_csv(client, MULTI_DIMENSION_CSV)

    datasets = client.get("/api/v1/series/datasets")
    assert datasets.status_code == 200
    assert [dataset["id"] for dataset in datasets.json()] == [ready["id"]]
    assert unready["id"] not in {dataset["id"] for dataset in datasets.json()}

    dimensions = client.get(f"/api/v1/series/datasets/{ready['id']}/dimensions").json()
    assert [item["value"] for item in dimensions["products"]] == ["A", "B"]
    assert [item["value"] for item in dimensions["locations"]] == ["North", "South"]
    assert [item["value"] for item in dimensions["categories"]] == ["Core", "Plus"]
    assert dimensions["available_frequencies"] == [
        "auto",
        "original",
        "daily",
        "weekly",
        "monthly",
    ]


def test_builds_one_sku_location_and_sums_transactions(client: TestClient) -> None:
    dataset = prepare_ready_csv(client, MULTI_DIMENSION_CSV)
    result = profile(client, dataset["id"], product="A", location="North", frequency="daily")

    assert [point["date"] for point in result["points"]] == ["2025-01-06", "2025-01-07"]
    assert [point["demand"] for point in result["points"]] == [5.0, 4.0]
    assert result["points"][0]["price"] == 11.2
    assert result["points"][0]["stock"] == 8.0
    assert result["points"][0]["promotion"] is True
    assert result["selection"]["price_method"] == "demand_weighted_mean"
    assert result["selection"]["data_cutoff"] == "2025-01-07"
    assert result["selection"]["is_aggregated"] is False
    assert result["points"][0]["coverage_ratio"] == 1.0
    assert result["points"][0]["is_partial"] is False


def test_aggregates_one_sku_across_locations(client: TestClient) -> None:
    dataset = prepare_ready_csv(client, MULTI_DIMENSION_CSV)
    result = profile(client, dataset["id"], product="A", frequency="daily")

    assert [point["demand"] for point in result["points"]] == [10.0, 10.0]
    assert result["selection"]["is_aggregated"] is True
    assert result["selection"]["aggregation_note"] == "dimensions"


def test_aggregates_all_products_and_category_filter(client: TestClient) -> None:
    dataset = prepare_ready_csv(client, MULTI_DIMENSION_CSV)
    all_series = profile(client, dataset["id"], frequency="daily")
    core_series = profile(client, dataset["id"], category="Core", frequency="daily")

    assert [point["demand"] for point in all_series["points"]] == [17.0, 18.0]
    assert [point["demand"] for point in core_series["points"]] == [10.0, 10.0]


def test_daily_to_weekly_and_monthly_uses_sum(client: TestClient) -> None:
    start = date(2025, 1, 6)
    rows = ["date,product,location,demand"]
    rows.extend(f"{start + timedelta(days=index)},A,North,1" for index in range(14))
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")

    weekly = profile(client, dataset["id"], product="A", location="North", frequency="weekly")
    monthly = profile(client, dataset["id"], product="A", location="North", frequency="monthly")
    assert [point["demand"] for point in weekly["points"]] == [7.0, 7.0]
    assert weekly["points"][0]["date"] == "2025-01-06"
    assert [point["demand"] for point in monthly["points"]] == [14.0]
    assert monthly["points"][0]["date"] == "2025-01-01"


def test_series_dates_are_sorted(client: TestClient) -> None:
    dataset = prepare_ready_csv(
        client,
        "date,demand\n2025-01-03,3\n2025-01-01,1\n2025-01-02,2\n",
    )
    result = profile(client, dataset["id"], frequency="daily")
    assert [point["date"] for point in result["points"]] == [
        "2025-01-01",
        "2025-01-02",
        "2025-01-03",
    ]


def test_same_date_for_different_products_is_not_a_false_duplicate(client: TestClient) -> None:
    uploaded = client.post(
        "/api/v1/datasets/upload",
        files={
            "file": (
                "dimensions.csv",
                b"date,product,location,demand\n2025-01-01,A,N,2\n2025-01-01,B,N,3\n",
                "text/csv",
            )
        },
    ).json()
    validation = client.post(f"/api/v1/datasets/{uploaded['id']}/validate").json()
    assert "duplicate_dates" not in {issue["code"] for issue in validation["issues"]}


def test_statistics_cv_zeros_and_missing_are_correct(client: TestClient) -> None:
    dataset = prepare_ready_csv(
        client,
        "date,demand\n2025-01-01,0\n2025-01-02,2\n2025-01-03,4\n2025-01-04,\n",
    )
    result = profile(client, dataset["id"], frequency="daily")
    statistics = result["statistics"]["series"]
    quality = result["statistics"]["underlying_quality"]

    assert statistics["periods"] == 4
    assert statistics["valid_periods"] == 3
    assert statistics["total_demand"] == 6.0
    assert statistics["mean_demand"] == 2.0
    assert statistics["median_demand"] == 2.0
    assert statistics["minimum_demand"] == 0.0
    assert statistics["maximum_demand"] == 4.0
    assert math.isclose(statistics["standard_deviation"], math.sqrt(8 / 3), rel_tol=1e-5)
    assert math.isclose(statistics["coefficient_of_variation"], math.sqrt(8 / 3) / 2, rel_tol=1e-5)
    assert statistics["zero_demand_periods"] == 1
    assert statistics["completely_missing_periods"] == 1
    assert quality["zero_demand_observations"] == 1
    assert quality["missing_demand_values"] == 1


def test_stockout_and_outlier_events_follow_quality_audit(client: TestClient) -> None:
    rows = ["date,product,location,demand,stock"]
    for index in range(10):
        demand = 100 if index == 8 else 10
        stock = 20
        if index == 9:
            demand, stock = 0, 0
        rows.append(f"2025-01-{index + 1:02d},A,North,{demand},{stock}")
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")
    result = profile(client, dataset["id"], product="A", location="North", frequency="daily")

    assert result["points"][8]["events"]["outlier"] == 1
    assert result["points"][9]["events"]["stockout"] == 1
    quality = result["statistics"]["underlying_quality"]
    assert quality["outlier_observations"] == 2
    assert quality["possible_stockout_observations"] == 1


def test_daily_seasonality_candidate_and_holt_winters_eligibility(client: TestClient) -> None:
    start = date(2025, 1, 6)
    pattern = [10, 14, 18, 22, 18, 8, 6]
    rows = ["date,demand"]
    rows.extend(
        f"{start + timedelta(days=index)},{pattern[index % 7]}" for index in range(28)
    )
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")
    result = profile(client, dataset["id"], frequency="daily")

    assert result["seasonality"]["candidate_period"] == 7
    assert result["seasonality"]["candidate_label"] == "weekly"
    assert result["seasonality"]["evidence"] == "high"
    assert result["holt_winters"]["compatible"] is True
    assert result["holt_winters"]["complete_cycles"] == 4
    assert result["holt_winters"]["recommendation"] == "favorable"


def test_holt_winters_is_ineligible_with_short_monthly_history(client: TestClient) -> None:
    rows = ["date,demand"]
    rows.extend(f"2025-{month:02d}-01,{month}" for month in range(1, 10))
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")
    result = profile(client, dataset["id"], frequency="original")

    assert result["selection"]["resolved_frequency"] == "monthly"
    assert result["seasonality"]["candidate_period"] == 12
    assert result["holt_winters"]["compatible"] is False
    assert result["holt_winters"]["required_observations"] == 24


def test_weekly_coverage_distinguishes_complete_and_partial_periods(
    client: TestClient,
) -> None:
    start = date(2025, 1, 6)
    rows = ["date,product,location,demand"]
    rows.extend(f"{start + timedelta(days=index)},A,North,10" for index in range(10))
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")

    result = profile(client, dataset["id"], product="A", location="North", frequency="weekly")
    complete, partial = result["points"]
    assert complete["expected_source_periods"] == 7
    assert complete["observed_source_periods"] == 7
    assert complete["coverage_ratio"] == 1.0
    assert complete["is_partial"] is False
    assert partial["expected_source_periods"] == 7
    assert partial["observed_source_periods"] == 3
    assert math.isclose(partial["coverage_ratio"], 3 / 7, rel_tol=1e-5)
    assert partial["is_partial"] is True


def test_monthly_coverage_uses_calendar_day_count(client: TestClient) -> None:
    start = date(2025, 1, 1)
    rows = ["date,demand"]
    rows.extend(f"{start + timedelta(days=index)},1" for index in range(34))
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")

    result = profile(client, dataset["id"], frequency="monthly")
    january, february = result["points"]
    assert january["expected_source_periods"] == 31
    assert january["observed_source_periods"] == 31
    assert january["is_partial"] is False
    assert february["expected_source_periods"] == 28
    assert february["observed_source_periods"] == 3
    assert math.isclose(february["coverage_ratio"], 3 / 28, rel_tol=1e-5)
    assert february["is_partial"] is True


def test_partial_edge_does_not_contaminate_pattern_or_distribution(
    client: TestClient,
) -> None:
    start = date(2025, 1, 6)
    rows = ["date,demand"]
    for index in range(24):
        demand = 100 if index >= 21 else 10
        rows.append(f"{start + timedelta(days=index)},{demand}")
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")

    result = profile(client, dataset["id"], frequency="weekly")
    assert [point["demand"] for point in result["points"]] == [70.0, 70.0, 70.0, 300.0]
    assert result["points"][-1]["is_partial"] is True
    assert result["pattern"]["trend"] == "stable"
    assert result["pattern"]["excluded_partial_periods"] == 1
    assert result["statistics"]["series"]["coefficient_of_variation"] == 0.0
    assert result["statistics"]["series"]["total_demand"] == 510.0


def test_partial_period_does_not_count_toward_complete_seasonal_cycles(
    client: TestClient,
) -> None:
    start = date(2024, 1, 1)
    days = 103 * 7 + 3
    rows = ["date,demand"]
    rows.extend(f"{start + timedelta(days=index)},10" for index in range(days))
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")

    result = profile(client, dataset["id"], frequency="weekly")
    assert len(result["points"]) == 104
    assert result["points"][-1]["is_partial"] is True
    assert result["holt_winters"]["eligible_periods"] == 103
    assert result["holt_winters"]["complete_cycles"] == 1
    assert result["holt_winters"]["compatible"] is False


def test_aggregated_series_separates_source_quality_from_period_outcomes(
    client: TestClient,
) -> None:
    start = date(2025, 2, 3)
    values = [10, None, 0, 10, None, 10, 10]
    rows = ["date,demand,stock"]
    for index, demand in enumerate(values):
        demand_text = "" if demand is None else str(demand)
        stock = 0 if demand == 0 else 10
        rows.append(f"{start + timedelta(days=index)},{demand_text},{stock}")
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")

    result = profile(client, dataset["id"], frequency="weekly")
    series = result["statistics"]["series"]
    quality = result["statistics"]["underlying_quality"]
    assert series["completely_missing_periods"] == 0
    assert series["zero_demand_periods"] == 0
    assert quality["missing_demand_values"] == 2
    assert quality["zero_demand_observations"] == 1
    assert quality["affected_periods"]["missing"] == 1
    assert quality["affected_periods"]["zero"] == 1
    assert quality["possible_stockout_observations"] == 1
    assert result["points"][0]["events"]["missing"] == 2
    assert result["points"][0]["events"]["stockout"] == 1


def test_trend_classification_has_stable_slight_and_signed_directions() -> None:
    increasing = pattern_summary(pd.Series([96 + (8 / 9) * index for index in range(10)]))
    decreasing = pattern_summary(pd.Series([104 - (8 / 9) * index for index in range(10)]))
    stable = pattern_summary(pd.Series([99.5 + (1 / 9) * index for index in range(10)]))

    assert increasing["trend"] == "increasing_slight"
    assert math.isclose(increasing["approximate_change_percent"], 8.0, rel_tol=1e-5)
    assert decreasing["trend"] == "decreasing_slight"
    assert math.isclose(decreasing["approximate_change_percent"], -8.0, rel_tol=1e-5)
    assert stable["trend"] == "stable"
    assert math.isclose(stable["approximate_change_percent"], 1.0, rel_tol=1e-5)


def test_holt_winters_can_be_technically_compatible_but_limited(
    client: TestClient,
) -> None:
    start = date(2024, 1, 1)
    rows = ["date,demand"]
    rows.extend(
        f"{start + timedelta(days=index)},{10 + (index % 7)}"
        for index in range(104 * 7)
    )
    dataset = prepare_ready_csv(client, "\n".join(rows) + "\n")

    result = profile(client, dataset["id"], frequency="weekly")
    assert result["holt_winters"]["compatible"] is True
    assert result["holt_winters"]["complete_cycles"] == 2
    assert result["holt_winters"]["recommendation"] == "limited"


def test_profile_does_not_modify_original_or_canonical_file(
    client: TestClient, storage: StorageService
) -> None:
    dataset = prepare_ready_csv(client, MULTI_DIMENSION_CSV)
    original = storage.resolve_owned_path(f"uploads/{dataset['id']}.csv")
    canonical = storage.resolve_owned_path(f"processed/{dataset['id']}.csv")
    before = (original.read_bytes(), canonical.read_bytes())

    profile(client, dataset["id"], product="A", location="North", frequency="weekly")

    assert (original.read_bytes(), canonical.read_bytes()) == before


def test_health_remains_available_with_series_engine(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
