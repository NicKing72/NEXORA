"""Deterministic six-month academic SCOR diagnostic demo."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from nexora_api.models.scor import ScorAssessmentRun, ScorBenchmarkProfile
from nexora_api.schemas.scor import (
    ScorAssessmentCreate,
    ScorBenchmarkProfileCreate,
    ScorBenchmarkTargetCreate,
    ScorMetricInputPayload,
)
from nexora_api.services.scor.calculator import Calculation, calculate_metric
from nexora_api.services.scor.definitions import METRICS
from nexora_api.services.scor.service import (
    calculate_assessment,
    create_assessment,
    create_profile,
    require_assessment,
    require_profile,
)

NAMESPACE = UUID("2f8fe5e7-88fd-4e02-a2f0-6426c8246f06")
DEMO_ASSESSMENT_ID = str(uuid5(NAMESPACE, "nexora-scor-demo-assessment-v1"))
DEMO_PROFILE_ID = str(uuid5(NAMESPACE, "nexora-scor-demo-profile-v1"))
DEMO_TIE_PROFILE_ID = str(uuid5(NAMESPACE, "nexora-scor-demo-tie-profile-v1"))
PERIOD_START = datetime(2026, 1, 1, tzinfo=UTC)
PERIOD_END = datetime(2026, 6, 30, 23, 59, 59, tzinfo=UTC)
CUTOFF = datetime(2026, 7, 1, 12, tzinfo=UTC)


def _input(
    metric_id: str,
    values: dict[str, object],
    *,
    metadata: dict[str, object] | None = None,
    not_applicable: bool = False,
    monthly: list[dict[str, object]] | None = None,
) -> ScorMetricInputPayload:
    return ScorMetricInputPayload(
        metric_id=metric_id,
        values=values,
        monthly_values=monthly or [],
        metadata=metadata or {},
        source="NEXORA demo SCOR determinístico",
        provenance={"demo_seed": 6001, "accumulation_months": 6},
        not_applicable=not_applicable,
        available_at=CUTOFF,
    )


def demo_inputs() -> list[ScorMetricInputPayload]:
    return [
        _input(
            "P01",
            {},
            monthly=[
                {"actual_units_6m": value[0], "forecast_units_6m": value[1]}
                for value in [
                    (900, 1000),
                    (1200, 1000),
                    (800, 1000),
                    (1100, 1000),
                    (1000, 1000),
                    (1250, 1000),
                ]
            ],
        ),
        _input("P02", {"average_inventory_value": 420000, "cogs_6m": 2100000}),
        _input("P03", {"days_receivable": 34, "inventory_days": 36, "days_payable": 28}),
        _input("P04", {"planning_cost_6m": 92000, "sales_6m": 4200000}),
        _input("S01", {"supplier_orders_on_time_6m": 184, "supplier_orders_total_6m": 200}),
        _input("S02", {"received_units_6m": 18400}),
        _input("S03", {"supplier_lead_time_days_total": 1680, "supplier_orders_total_6m": 200}),
        _input("S04", {}, not_applicable=True),
        _input("S05", {"procurement_operating_cost_6m": 146000, "sales_6m": 4200000}),
        _input("M01", {"completed_as_planned_6m": 1120, "total_planned_6m": 1200}),
        _input(
            "M02",
            {"processing_time_total": 86400, "processed_orders_total": 1200},
            metadata={"time_unit": "minutos"},
        ),
        _input(
            "M03",
            {"occupied_capacity": 8200, "maximum_design_capacity": 10000},
            metadata={"capacity_unit": "posiciones pallet"},
        ),
        _input(
            "M04",
            {
                "supply_chain_revenue_6m": 4200000,
                "total_supply_chain_cost_6m": 3500000,
                "logistics_fixed_assets_value": 2800000,
            },
        ),
        _input("M05", {"inventory_holding_cost_6m": 118000, "inventory_value": 820000}),
        _input("D01", {"deliveries_on_time_6m": 870, "dispatched_orders_6m": 1000}),
        _input("D02", {"complete_deliveries_6m": 900, "dispatched_orders_6m": 1000}),
        _input("D03", {"damage_free_deliveries_6m": 930, "dispatched_orders_6m": 1000}),
        _input("D04", {"correctly_invoiced_orders_6m": 950, "dispatched_orders_6m": 1000}),
        _input(
            "D06",
            {"order_lead_time": 12, "make_time": 8, "delivery_time": 28},
            metadata={"time_unit": "horas"},
        ),
        _input("D07", {"registered_logistics_losses_6m": 126000, "revenue_6m": 4200000}),
        _input(
            "D08",
            {"freight_distribution_cost_6m": 310000, "transported_units_6m": 52000},
            metadata={"currency": "PEN"},
        ),
        _input("R01", {"returned_units_6m": 310, "sold_units_6m": 52000}),
        _input("R02", {"return_processing_days_total": 520, "returns_processed_total": 260}),
        _input("R03", {"salvaged_or_reconditioned_units_6m": 0, "returned_units_6m": 0}),
        _input(
            "R04",
            {"reverse_logistics_operating_cost_6m": 58000, "returned_units_6m": 310},
            metadata={"currency": "PEN"},
        ),
    ]


def demo_profile_payload() -> ScorBenchmarkProfileCreate:
    targets = [
        ("P01", "higher_is_better", 95),
        ("P02", "lower_is_better", 30),
        ("P03", "lower_is_better", 35),
        ("P04", "lower_is_better", 2),
        ("S01", "higher_is_better", 95),
        ("S03", "lower_is_better", 7),
        ("S05", "lower_is_better", 3),
        ("M01", "higher_is_better", 96),
        ("M02", "lower_is_better", 60),
        ("M03", "target_range", None),
        ("M04", "higher_is_better", 30),
        ("M05", "lower_is_better", 12),
        ("D01", "higher_is_better", 96),
        ("D02", "higher_is_better", 97),
        ("D03", "higher_is_better", 98),
        ("D04", "higher_is_better", 98),
        ("D05", "higher_is_better", 90),
        ("D06", "lower_is_better", 36),
        ("D07", "lower_is_better", 1.5),
        ("D08", "lower_is_better", 5),
        ("R01", "lower_is_better", 0.5),
        ("R02", "lower_is_better", 1.5),
        ("R04", "lower_is_better", 160),
    ]
    payloads = []
    for metric_id, direction, target in targets:
        payloads.append(
            ScorBenchmarkTargetCreate(
                metric_id=metric_id,
                direction=direction,
                target=target,
                optional_min=75 if metric_id == "M03" else None,
                optional_max=90 if metric_id == "M03" else None,
                weight=1.25 if metric_id in {"D01", "D02", "D05"} else 1,
                source="Meta demo configurada por NEXORA",
                notes="Ejemplo académico; no es estándar oficial SCOR.",
            )
        )
    return ScorBenchmarkProfileCreate(
        name="Metas internas demo — seis meses",
        profile_type="demo",
        source="NEXORA demo",
        notes="Perfil sintético reproducible. No representa benchmark oficial SCOR.",
        minimum_process_coverage=0.5,
        targets=payloads,
    )


def demo_tie_profile_payload() -> ScorBenchmarkProfileCreate:
    """Profile whose targets equal the reproducible observations, producing a real tie."""
    inputs = {item.metric_id: item for item in demo_inputs()}
    calculations: dict[str, Calculation] = {}
    targets: list[ScorBenchmarkTargetCreate] = []
    for definition in METRICS:
        item = inputs.get(definition.id)
        result = calculate_metric(
            definition.id,
            item.values if item else {},
            monthly_values=item.monthly_values if item else [],
            metadata=item.metadata if item else {},
            dependencies=calculations,
            not_applicable=item.not_applicable if item else False,
        )
        calculations[definition.id] = result
        if result.evidence_status != "complete" or result.result is None:
            continue
        targets.append(
            ScorBenchmarkTargetCreate(
                metric_id=definition.id,
                direction="higher_is_better",
                target=max(result.result, 0.000001),
                weight=1,
                source="Meta demo de empate controlado",
                notes="Target igual al valor demo para probar empates sin forzar un ganador.",
            )
        )
    return ScorBenchmarkProfileCreate(
        name="Metas demo — empate controlado",
        profile_type="demo",
        source="NEXORA demo",
        notes="Caso reproducible de empate. No representa benchmark oficial SCOR.",
        minimum_process_coverage=0.5,
        targets=targets,
    )


def regenerate_demo(db: Session) -> tuple[ScorAssessmentRun, ScorBenchmarkProfile]:
    existing_assessment = (
        db.query(ScorAssessmentRun).filter(ScorAssessmentRun.id == DEMO_ASSESSMENT_ID).one_or_none()
    )
    if existing_assessment:
        db.delete(existing_assessment)
        db.commit()
    existing_profile = (
        db.query(ScorBenchmarkProfile)
        .filter(ScorBenchmarkProfile.id == DEMO_PROFILE_ID)
        .one_or_none()
    )
    profile = existing_profile or create_profile(
        db, demo_profile_payload(), profile_id=DEMO_PROFILE_ID
    )
    existing_tie_profile = (
        db.query(ScorBenchmarkProfile)
        .filter(ScorBenchmarkProfile.id == DEMO_TIE_PROFILE_ID)
        .one_or_none()
    )
    if existing_tie_profile is None:
        create_profile(db, demo_tie_profile_payload(), profile_id=DEMO_TIE_PROFILE_ID)
    assessment = create_assessment(
        db,
        ScorAssessmentCreate(
            name="Diagnóstico SCOR demo — Semestre I 2026",
            company_name="NEXORA Demo Logistics",
            benchmark_profile_id=profile.id,
            period_start=PERIOD_START,
            period_end=PERIOD_END,
            cutoff=CUTOFF,
            source_name="Dataset SCOR demo determinístico",
            source_metadata={
                "demo_seed": 6001,
                "period_rule": "six_complete_months",
                "official_scor_benchmark": False,
                "scope_type": "entity",
            },
            metric_inputs=demo_inputs(),
        ),
        assessment_id=DEMO_ASSESSMENT_ID,
    )
    calculate_assessment(db, assessment.id)
    return require_assessment(db, assessment.id), require_profile(db, profile.id)
