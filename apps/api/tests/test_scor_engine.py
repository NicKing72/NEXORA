"""Quantitative SCOR calculations, benchmarking, persistence, and anti-leakage."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from nexora_api.services.scor.benchmarking import gap_score
from nexora_api.services.scor.calculator import aggregate_monthly_ratio, calculate_metric
from nexora_api.services.scor.criticality import determine_critical_process, process_scores
from nexora_api.services.scor.definitions import METRICS


@pytest.mark.parametrize(
    ("metric_id", "values", "metadata", "expected"),
    [
        ("P01", {"actual_units_6m": 120, "forecast_units_6m": 100}, {}, 120),
        ("P02", {"average_inventory_value": 100, "cogs_6m": 600}, {}, 30),
        ("P04", {"planning_cost_6m": 20, "sales_6m": 1000}, {}, 2),
        ("S01", {"supplier_orders_on_time_6m": 92, "supplier_orders_total_6m": 100}, {}, 92),
        ("S02", {"rejected_units_6m": 3, "received_units_6m": 100}, {}, 3),
        ("S03", {"supplier_lead_time_days_total": 80, "supplier_orders_total_6m": 10}, {}, 8),
        ("S04", {"sustainable_supplier_increase_30d_pct": 18}, {}, 18),
        ("S05", {"procurement_operating_cost_6m": 40, "sales_6m": 1000}, {}, 4),
        ("M01", {"completed_as_planned_6m": 95, "total_planned_6m": 100}, {}, 95),
        (
            "M02",
            {"processing_time_total": 600, "processed_orders_total": 10},
            {"time_unit": "minutos"},
            60,
        ),
        ("M03", {"occupied_capacity": 80, "maximum_design_capacity": 100}, {}, 80),
        (
            "M04",
            {
                "supply_chain_revenue_6m": 1200,
                "total_supply_chain_cost_6m": 1000,
                "logistics_fixed_assets_value": 800,
            },
            {},
            25,
        ),
        ("M05", {"inventory_holding_cost_6m": 15, "inventory_value": 100}, {}, 15),
        ("D01", {"deliveries_on_time_6m": 90, "dispatched_orders_6m": 100}, {}, 90),
        ("D02", {"complete_deliveries_6m": 91, "dispatched_orders_6m": 100}, {}, 91),
        ("D03", {"damage_free_deliveries_6m": 92, "dispatched_orders_6m": 100}, {}, 92),
        ("D04", {"correctly_invoiced_orders_6m": 93, "dispatched_orders_6m": 100}, {}, 93),
        ("D07", {"registered_logistics_losses_6m": 20, "revenue_6m": 1000}, {}, 2),
        (
            "D08",
            {"freight_distribution_cost_6m": 500, "transported_units_6m": 100},
            {"currency": "PEN"},
            5,
        ),
        ("R01", {"returned_units_6m": 5, "sold_units_6m": 100}, {}, 5),
        ("R02", {"return_processing_days_total": 40, "returns_processed_total": 20}, {}, 2),
        ("R03", {"salvaged_or_reconditioned_units_6m": 8, "returned_units_6m": 10}, {}, 80),
        (
            "R04",
            {"reverse_logistics_operating_cost_6m": 500, "returned_units_6m": 10},
            {"currency": "USD"},
            50,
        ),
    ],
)
def test_catalog_metric_calculations(
    metric_id: str, values: dict[str, object], metadata: dict[str, object], expected: float
) -> None:
    result = calculate_metric(metric_id, values, metadata=metadata)
    assert result.evidence_status == "complete"
    assert result.result == pytest.approx(expected)


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ({"days_receivable": 30, "inventory_days": 40, "days_payable": 20}, 50),
        ({"days_receivable": 10, "inventory_days": 15, "days_payable": 40}, -15),
    ],
)
def test_cash_to_cash_can_be_positive_or_negative(
    values: dict[str, object], expected: float
) -> None:
    assert calculate_metric("P03", values).result == expected


def test_pof_multiplies_complete_components_instead_of_averaging() -> None:
    dependencies = {
        metric_id: calculate_metric(metric_id, values)
        for metric_id, values in {
            "D01": {"deliveries_on_time_6m": 90, "dispatched_orders_6m": 100},
            "D02": {"complete_deliveries_6m": 80, "dispatched_orders_6m": 100},
            "D03": {"damage_free_deliveries_6m": 95, "dispatched_orders_6m": 100},
            "D04": {"correctly_invoiced_orders_6m": 100, "dispatched_orders_6m": 100},
        }.items()
    }
    result = calculate_metric("D05", {}, dependencies=dependencies)
    assert result.result == pytest.approx(68.4)
    assert result.result != pytest.approx((90 + 80 + 95 + 100) / 4)
    assert result.details["method"] == "product_not_average"
    dependencies.pop("D04")
    assert calculate_metric("D05", {}, dependencies=dependencies).evidence_status == "incomplete"


@pytest.mark.parametrize(
    ("values", "method", "expected"),
    [
        ({"observed_total": 36}, "observed_total", 36),
        ({"order_lead_time": 12, "make_time": 8, "delivery_time": 20}, "component_sum", 40),
    ],
)
def test_ofct_preserves_exclusive_method(
    values: dict[str, object], method: str, expected: float
) -> None:
    result = calculate_metric("D06", values, metadata={"time_unit": "horas"})
    assert result.method == method
    assert result.result == expected


def test_missing_zero_negative_and_not_applicable_are_not_zero_results() -> None:
    zero = calculate_metric("S01", {"supplier_orders_on_time_6m": 0, "supplier_orders_total_6m": 0})
    missing = calculate_metric("S01", {"supplier_orders_total_6m": 10})
    negative = calculate_metric(
        "S01", {"supplier_orders_on_time_6m": -1, "supplier_orders_total_6m": 10}
    )
    unavailable = calculate_metric("S04", {}, not_applicable=True)
    assert (zero.evidence_status, zero.result) == ("insufficient_evidence", None)
    assert (missing.evidence_status, missing.result) == ("incomplete", None)
    assert (negative.evidence_status, negative.result) == ("invalid", None)
    assert (unavailable.evidence_status, unavailable.result) == ("not_applicable", None)


def test_six_month_ratio_uses_sum_totals_not_mean_percentages() -> None:
    monthly = [
        {"actual_units_6m": 10, "forecast_units_6m": 100},
        {"actual_units_6m": 90, "forecast_units_6m": 100},
        {"actual_units_6m": 20, "forecast_units_6m": 50},
        {"actual_units_6m": 80, "forecast_units_6m": 100},
        {"actual_units_6m": 30, "forecast_units_6m": 50},
        {"actual_units_6m": 70, "forecast_units_6m": 100},
    ]
    numerator, denominator = aggregate_monthly_ratio(
        monthly, "actual_units_6m", "forecast_units_6m"
    )
    result = calculate_metric("P01", {}, monthly_values=monthly)
    average_monthly_percentage = (
        sum(month["actual_units_6m"] / month["forecast_units_6m"] * 100 for month in monthly) / 6
    )
    assert result.result == pytest.approx(numerator / denominator * 100)
    assert result.result != pytest.approx(average_monthly_percentage)
    assert result.details["aggregation"] == "ratio_of_sums"


def test_p01_normal_result_and_calculated_percentage_above_100_are_preserved() -> None:
    normal = calculate_metric("P01", {"actual_units_6m": 90, "forecast_units_6m": 100})
    above = calculate_metric("P01", {"actual_units_6m": 125, "forecast_units_6m": 100})
    assert normal.result == 90
    assert above.result == 125


def test_direct_percentage_input_outside_declared_range_is_invalid() -> None:
    result = calculate_metric("S04", {"sustainable_supplier_increase_30d_pct": 101})
    assert result.evidence_status == "invalid"
    assert result.reason == "percentage_out_of_range:sustainable_supplier_increase_30d_pct"


def test_monthly_input_requires_exactly_six_complete_periods() -> None:
    monthly = [{"actual_units_6m": 10, "forecast_units_6m": 12}] * 5
    result = calculate_metric("P01", {}, monthly_values=monthly)
    assert result.evidence_status == "invalid"
    assert result.reason == "six_complete_months_required"


def test_incompatible_time_units_are_not_converted_silently() -> None:
    picking = calculate_metric(
        "M02",
        {"processing_time_total": 10, "processed_orders_total": 2},
        metadata={"time_unit": "días"},
    )
    ofct = calculate_metric("D06", {"observed_total": 10}, metadata={"time_unit": "minutos"})
    assert picking.evidence_status == "invalid"
    assert ofct.evidence_status == "invalid"


def test_currency_per_unit_requires_explicit_currency() -> None:
    result = calculate_metric(
        "D08", {"freight_distribution_cost_6m": 100, "transported_units_6m": 10}
    )
    assert result.evidence_status == "incomplete"
    assert result.reason == "missing_currency"


def test_ofct_rejects_observed_and_component_methods_together() -> None:
    result = calculate_metric(
        "D06",
        {"observed_total": 20, "order_lead_time": 5, "make_time": 5, "delivery_time": 10},
        metadata={"time_unit": "horas"},
    )
    assert result.evidence_status == "invalid"
    assert result.reason == "observed_and_components_are_mutually_exclusive"


@pytest.mark.parametrize(
    ("value", "kwargs", "expected_score", "expected_status"),
    [
        (80, {"direction": "higher_is_better", "target": 100}, 20, "evaluated"),
        (12, {"direction": "lower_is_better", "target": 10}, 20, "evaluated"),
        (85, {"direction": "target_range", "minimum": 80, "maximum": 90}, 0, "evaluated"),
        (95, {"direction": "target_range", "minimum": 80, "maximum": 90}, 50, "evaluated"),
        (80, {"direction": "higher_is_better"}, None, "invalid_target"),
        (4, {"direction": "lower_is_better", "target": 0}, 100, "evaluated"),
    ],
)
def test_gap_score_directions_range_and_missing_target(
    value: float,
    kwargs: dict[str, object],
    expected_score: float | None,
    expected_status: str,
) -> None:
    result = gap_score(value, **kwargs)
    assert result.score == expected_score
    assert result.status == expected_status


def test_process_score_coverage_criticality_and_tie() -> None:
    metrics = []
    for definition in METRICS:
        score = 60 if definition.process == "DELIVER" else 20
        metrics.append(
            {
                "metric_id": definition.id,
                "evidence_status": "complete",
                "gap_score": score,
                "target_weight": 1,
            }
        )
    processes = process_scores(metrics, 0.5)
    critical = determine_critical_process(processes, profile_id="profile", minimum_coverage=0.5)
    assert critical["selected_process"] == "DELIVER"
    tied = [dict(item, weighted_gap_score=50.0) for item in processes]
    tie = determine_critical_process(tied, profile_id="profile", minimum_coverage=0.5)
    assert tie["status"] == "tie"
    assert len(tie["tied_processes"]) == 5
    insufficient = determine_critical_process(processes[:1], profile_id=None, minimum_coverage=0.5)
    assert insufficient["status"] == "insufficient_evidence"


def test_demo_api_is_deterministic_auditable_and_persistent(client: TestClient) -> None:
    first = client.post("/api/v1/scor/demo/regenerate")
    assert first.status_code == 200, first.text
    result = first.json()
    assessment = result["assessment"]
    assert assessment["status"] == "calculated"
    assert len(assessment["metrics"]) == 26
    assert len(assessment["processes"]) == 5
    assert assessment["criticality"]["status"] in {"candidate", "tie"}
    pof = next(item for item in assessment["metrics"] if item["metric_id"] == "D05")
    assert pof["calculation_details"]["method"] == "product_not_average"
    assert "denominator_zero" in assessment["warnings"]
    assert any(item["evidence_status"] == "not_applicable" for item in assessment["metrics"])
    assert result["benchmark_profile"]["is_official_scor"] is False
    profiles = client.get("/api/v1/scor/benchmark-profiles").json()
    tie_profile = next(item for item in profiles if "empate controlado" in item["name"])
    tie_result = client.post(
        f"/api/v1/scor/assessments/{assessment['id']}/benchmark",
        json={"benchmark_profile_id": tie_profile["id"]},
    )
    assert tie_result.status_code == 200
    assert tie_result.json()["criticality"]["status"] == "tie"
    assert len(tie_result.json()["criticality"]["tied_processes"]) == 5
    first = client.post("/api/v1/scor/demo/regenerate")
    assessment = first.json()["assessment"]
    retrieved = client.get(f"/api/v1/scor/assessments/{assessment['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == assessment
    assert client.get(f"/api/v1/scor/assessments/{assessment['id']}/metrics").status_code == 200
    assert client.get(f"/api/v1/scor/assessments/{assessment['id']}/processes").status_code == 200
    assert client.get(f"/api/v1/scor/assessments/{assessment['id']}/criticality").status_code == 200
    second = client.post("/api/v1/scor/demo/regenerate").json()
    assert second["assessment"]["id"] == assessment["id"]
    assert [item["result_value"] for item in second["assessment"]["metrics"]] == [
        item["result_value"] for item in assessment["metrics"]
    ]


def test_partial_benchmark_coverage_is_visible_and_blocks_criticality(client: TestClient) -> None:
    profile = client.post(
        "/api/v1/scor/benchmark-profiles",
        json={
            "name": "Meta parcial",
            "profile_type": "company_target",
            "source": "Dirección de operaciones",
            "minimum_process_coverage": 0.5,
            "targets": [
                {
                    "metric_id": "S01",
                    "direction": "higher_is_better",
                    "target": 95,
                    "weight": 1,
                    "source": "SLA interno",
                }
            ],
        },
    )
    assert profile.status_code == 201, profile.text
    assert client.get(f"/api/v1/scor/benchmark-profiles/{profile.json()['id']}").status_code == 200
    payload = {
        "name": "Cobertura parcial",
        "benchmark_profile_id": profile.json()["id"],
        "period_start": "2026-01-01T00:00:00Z",
        "period_end": "2026-06-30T23:59:59Z",
        "cutoff": "2026-07-01T00:00:00Z",
        "source_name": "Empresa",
        "metric_inputs": [
            {
                "metric_id": "S01",
                "values": {"supplier_orders_on_time_6m": 90, "supplier_orders_total_6m": 100},
                "available_at": "2026-07-01T00:00:00Z",
            }
        ],
    }
    created = client.post("/api/v1/scor/assessments", json=payload)
    calculated = client.post(f"/api/v1/scor/assessments/{created.json()['id']}/calculate")
    assert calculated.status_code == 200
    result = calculated.json()
    source = next(item for item in result["processes"] if item["process"] == "SOURCE")
    assert source["benchmark_coverage"] == pytest.approx(0.2)
    assert result["criticality"]["status"] == "insufficient_evidence"


@pytest.mark.parametrize(
    ("start", "end", "cutoff"),
    [
        ("2026-06-30T00:00:00Z", "2026-01-01T00:00:00Z", "2026-07-01T00:00:00Z"),
        ("2026-01-01T00:00:00Z", "2026-06-30T00:00:00Z", "2026-06-01T00:00:00Z"),
    ],
)
def test_invalid_assessment_dates_are_rejected(
    client: TestClient, start: str, end: str, cutoff: str
) -> None:
    response = client.post(
        "/api/v1/scor/assessments",
        json={
            "name": "Periodo inválido",
            "period_start": start,
            "period_end": end,
            "cutoff": cutoff,
            "source_name": "Empresa",
            "metric_inputs": [],
        },
    )
    assert response.status_code == 422


def test_calculation_audit_is_recoverable_after_reload(client: TestClient) -> None:
    assessment = client.post("/api/v1/scor/demo/regenerate").json()["assessment"]
    reloaded = client.get(f"/api/v1/scor/assessments/{assessment['id']}").json()
    actions = [item["action"] for item in reloaded["audit"]]
    assert actions == ["created", "calculated"]
    assert reloaded["metric_inputs"]
    assert all(item["algorithm_version"] == "scor_diagnostic_v1" for item in reloaded["metrics"])


def test_manual_assessment_without_benchmark_never_forces_critical_process(
    client: TestClient,
) -> None:
    payload = {
        "name": "Manual",
        "period_start": "2026-01-01T00:00:00Z",
        "period_end": "2026-06-30T23:59:59Z",
        "cutoff": "2026-07-01T00:00:00Z",
        "source_name": "Acumulados empresa",
        "metric_inputs": [
            {
                "metric_id": "S01",
                "values": {"supplier_orders_on_time_6m": 90, "supplier_orders_total_6m": 100},
                "available_at": "2026-07-01T00:00:00Z",
            }
        ],
    }
    created = client.post("/api/v1/scor/assessments", json=payload)
    assert created.status_code == 201, created.text
    calculated = client.post(f"/api/v1/scor/assessments/{created.json()['id']}/calculate")
    assert calculated.status_code == 200
    assert calculated.json()["criticality"]["status"] == "insufficient_evidence"
    assert calculated.json()["criticality"]["selected_process"] is None


def test_temporal_leakage_input_is_blocked(client: TestClient) -> None:
    payload = {
        "name": "Leakage",
        "period_start": "2026-01-01T00:00:00Z",
        "period_end": "2026-06-30T00:00:00Z",
        "cutoff": "2026-07-01T00:00:00Z",
        "source_name": "Manual",
        "metric_inputs": [
            {
                "metric_id": "P01",
                "values": {"actual_units_6m": 10, "forecast_units_6m": 9},
                "available_at": "2026-07-02T00:00:00Z",
            }
        ],
    }
    response = client.post("/api/v1/scor/assessments", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "scor_temporal_leakage_blocked"


def _forecast(client: TestClient) -> tuple[dict, str]:
    start = date(2025, 1, 1)
    rows = ["date,product,location,demand,stock"]
    for index in range(70):
        rows.append(f"{start + timedelta(days=index)},A,North,{20 + index % 7},50")
    dataset = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("scor.csv", ("\n".join(rows) + "\n").encode(), "text/csv")},
    ).json()
    client.post(f"/api/v1/datasets/{dataset['id']}/validate")
    client.post(f"/api/v1/datasets/{dataset['id']}/ready")
    forecast = client.post(
        "/api/v1/forecast-runs",
        json={
            "dataset_id": dataset["id"],
            "product": "A",
            "location": "North",
            "frequency": "daily",
            "horizon": 200,
        },
    )
    assert forecast.status_code == 201, forecast.text
    return forecast.json(), dataset["id"]


def test_forecast_association_compatible_incompatible_and_immutable(client: TestClient) -> None:
    forecast, dataset_id = _forecast(client)
    before = client.get(f"/api/v1/forecast-runs/{forecast['id']}").json()
    payload = {
        "name": "Asociado",
        "source_dataset_id": dataset_id,
        "forecast_run_id": forecast["id"],
        "period_start": forecast["forecast_points"][0]["timestamp"] + "T00:00:00Z",
        "period_end": forecast["forecast_points"][-1]["timestamp"] + "T00:00:00Z",
        "cutoff": datetime.now(UTC).isoformat(),
        "source_name": "Empresa",
        "metric_inputs": [],
    }
    compatible = client.post("/api/v1/scor/assessments", json=payload)
    assert compatible.status_code == 201, compatible.text
    payload["source_dataset_id"] = "00000000-0000-0000-0000-000000000000"
    incompatible = client.post("/api/v1/scor/assessments", json=payload)
    assert incompatible.status_code == 409
    assert incompatible.json()["error"]["code"] == "scor_forecast_incompatible"
    assert client.get(f"/api/v1/forecast-runs/{forecast['id']}").json() == before


def test_definitions_profiles_lists_and_health_remain_available(client: TestClient) -> None:
    assert len(client.get("/api/v1/scor/definitions").json()) == 26
    assert client.get("/api/v1/scor/assessments").status_code == 200
    assert client.get("/api/v1/scor/benchmark-profiles").status_code == 200
    assert client.get("/health").json()["status"] == "ok"
