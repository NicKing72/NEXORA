"""Versioned, deterministic SCOR support rules for non-executing decisions."""

from __future__ import annotations

from copy import deepcopy

from nexora_api.services.decisions.catalog import ACTION_LABELS
from nexora_api.services.decisions.ranking import evidence_level

SCOR_SUPPORT_RULE_VERSION = "decision_scor_support_v1"
SCOR_THRESHOLDS = {
    "moderate_gap": 15.0,
    "high_gap": 35.0,
    "minimum_process_coverage": 0.5,
    "maximum_reinforcement": 0.2,
}

PROCESS_ACTION = {
    "PLAN": "review_scor_plan",
    "SOURCE": "review_scor_source",
    "MAKE": "review_scor_make",
    "DELIVER": "review_scor_deliver",
    "RETURN": "review_scor_return",
}

REINFORCEMENT_ACTIONS = {
    "PLAN": {"maintain_plan", "investigate_demand_increase", "investigate_demand_drop"},
    "SOURCE": {"prepare_supply", "review_replenishment"},
    "MAKE": {"prepare_capacity", "manual_review_required"},
    "DELIVER": {"monitor", "manual_review_required"},
    "RETURN": {"review_inventory_policy", "manual_review_required"},
}


def scor_metric_support(metric: dict[str, object], criticality: dict[str, object]) -> float:
    """0.50 gap + 0.25 coverage + 0.15 evidence + 0.10 criticality."""
    if metric.get("evidence_status") != "complete" or metric.get("gap_score") is None:
        return 0.0
    gap = max(0.0, min(1.0, float(metric["gap_score"]) / 100))
    coverage = max(0.0, min(1.0, float(metric.get("process_coverage", 0))))
    process = str(metric["process"])
    selected = criticality.get("selected_process")
    tied = {str(item) for item in criticality.get("tied_processes", [])}
    criticality_factor = 1.0 if process == selected else 0.85 if process in tied else 0.7
    return round(0.50 * gap + 0.25 * coverage + 0.15 + 0.10 * criticality_factor, 4)


def _evidence_item(
    scor: dict[str, object], metric: dict[str, object], evidence_type: str = "scor_metric"
) -> dict[str, object]:
    return {
        "evidence_type": evidence_type,
        "source_id": str(scor["scor_assessment_id"]),
        "description": (
            f"Evidencia SCOR congelada: {metric['metric_id']} · {metric['metric_name']}."
        ),
        "snapshot": {
            "assessment": {
                "scor_assessment_id": scor["scor_assessment_id"],
                "assessment_name": scor["assessment_name"],
                "entity": scor["entity"],
                "period_start": scor["period_start"],
                "period_end": scor["period_end"],
                "calculated_at": scor["calculated_at"],
                "available_at": scor["available_at"],
                "benchmark_profile_id": scor["benchmark_profile_id"],
                "benchmark_profile_name": scor["benchmark_profile_name"],
                "criticality": scor["criticality"],
                "calculation_version": scor["calculation_version"],
                "provenance": scor["provenance"],
                "decision_cutoff": scor["decision_cutoff"],
            },
            "metric": metric,
            "support_rule_version": SCOR_SUPPORT_RULE_VERSION,
            "causal_claim": False,
        },
    }


def _candidate(
    *,
    key: str,
    priority: str,
    action: str,
    summary: str,
    rationale: str,
    support: float,
    scor: dict[str, object],
    evidence: list[dict[str, object]],
    origin: str,
    limitations: list[str] | None = None,
) -> dict[str, object]:
    score = round(max(0.0, min(1.0, support)), 4)
    return {
        "stable_key": key,
        "priority": priority,
        "action_type": action,
        "title": ACTION_LABELS[action],
        "summary": summary,
        "rationale": rationale,
        "support_score": score,
        "evidence_level": evidence_level(score),
        "evidence": evidence,
        "limitations": limitations
        or [
            "La brecha frente a una meta configurada no demuestra causalidad.",
            "La recomendación no ejecuta ni optimiza operaciones automáticamente.",
        ],
        "context_signal_ids": [],
        "context_impact_ids": [],
        "provenance": {
            "rule_version": SCOR_SUPPORT_RULE_VERSION,
            "scor_assessment_id": scor["scor_assessment_id"],
            "scor_support_contribution": score,
            "scor_origin": origin,
            "causal_claim": False,
            "automatic_execution": False,
        },
    }


def generate_scor_candidates(scor: dict[str, object]) -> list[dict[str, object]]:
    metrics = [item for item in scor.get("metrics", []) if isinstance(item, dict)]
    criticality = scor.get("criticality", {})
    assert isinstance(criticality, dict)
    eligible = [
        item
        for item in metrics
        if item.get("evidence_status") == "complete"
        and isinstance(item.get("gap_score"), (int, float))
        and float(item["gap_score"]) >= SCOR_THRESHOLDS["moderate_gap"]
        and float(item.get("process_coverage", 0)) >= SCOR_THRESHOLDS["minimum_process_coverage"]
    ]
    eligible.sort(key=lambda item: (-float(item["gap_score"]), str(item["metric_id"])))
    output: list[dict[str, object]] = []
    for metric in eligible[:5]:
        score = scor_metric_support(metric, criticality)
        high = float(metric["gap_score"]) >= SCOR_THRESHOLDS["high_gap"] and score >= 0.65
        process = str(metric["process"])
        output.append(
            _candidate(
                key=f"scor:metric:{metric['metric_id']}",
                priority="high" if high else "medium",
                action=PROCESS_ACTION[process],
                summary=(
                    f"{metric['metric_id']} presenta una brecha NEXORA de "
                    f"{float(metric['gap_score']):.1f}/100 frente a la meta configurada."
                ),
                rationale=(
                    f"El proceso {process} muestra distancia cuantitativa que amerita revisión; "
                    "no se interpreta como causa demostrada."
                ),
                support=score,
                scor=scor,
                evidence=[_evidence_item(scor, metric)],
                origin="originated",
            )
        )

    incomplete = [
        item
        for item in metrics
        if item.get("evidence_status") in {"incomplete", "insufficient_evidence", "invalid"}
    ]
    if incomplete:
        snapshot = {
            "metric_id": "SCOR_DATA_QUALITY",
            "metric_name": "Cobertura de evidencia SCOR",
            "process": "MULTIPLE",
            "evidence_status": "insufficient_evidence",
            "affected_metrics": [
                {
                    "metric_id": item["metric_id"],
                    "process": item["process"],
                    "status": item["evidence_status"],
                    "reason": item.get("reason"),
                }
                for item in incomplete
            ],
            "gap_score": None,
            "process_coverage": 0,
        }
        output.append(
            _candidate(
                key="scor:evidence:incomplete",
                priority="medium" if len(incomplete) >= 2 else "low",
                action="complete_scor_evidence",
                summary=f"{len(incomplete)} KPI SCOR no cuentan con evidencia calculable completa.",
                rationale=(
                    "Los KPI incompletos no se utilizaron como resultados válidos "
                    "ni elevaron soporte."
                ),
                support=min(0.32, 0.18 + 0.04 * len(incomplete)),
                scor=scor,
                evidence=[_evidence_item(scor, snapshot, "scor_data_quality")],
                origin="evidence_request",
                limitations=[
                    "No se fabricaron valores para inputs faltantes o denominadores cero.",
                    "Los KPI no aplicables fueron excluidos de la priorización.",
                ],
            )
        )

    process_scores = [
        item for item in criticality.get("process_scores", []) if isinstance(item, dict)
    ]
    worst_gap = max(
        (
            float(item["weighted_gap_score"])
            for item in process_scores
            if item.get("weighted_gap_score") is not None
        ),
        default=0.0,
    )
    if (
        criticality.get("status") in {"candidate", "tie"}
        and worst_gap >= SCOR_THRESHOLDS["moderate_gap"]
    ):
        tied = [str(item) for item in criticality.get("tied_processes", [])]
        selected = criticality.get("selected_process")
        label = " · ".join(tied) if tied else str(selected)
        relevant_processes = set(tied) if tied else {str(selected)}
        relevant_scores = [
            item for item in process_scores if str(item.get("process")) in relevant_processes
        ]
        metric = {
            "metric_id": "SCOR_PROCESS",
            "metric_name": "Criticidad por proceso",
            "process": label,
            "raw_result": None,
            "unit": "gap_score",
            "target": {},
            "gap_score": worst_gap,
            "evidence_status": "complete",
            "process_coverage": min(
                (float(item.get("benchmark_coverage", 0)) for item in relevant_scores),
                default=0,
            ),
            "criticality_status": criticality.get("status"),
            "selected_process": selected,
            "tied_processes": tied,
            "process_scores": relevant_scores,
            "calculation_version": scor["calculation_version"],
        }
        output.append(
            _candidate(
                key="scor:criticality",
                priority="high"
                if worst_gap >= SCOR_THRESHOLDS["high_gap"] and not tied
                else "medium",
                action="review_scor_critical",
                summary=(
                    f"El diagnóstico identifica {label} como "
                    f"{'empate de criticidad' if tied else 'eslabón crítico candidato'}."
                ),
                rationale=(
                    "La priorización usa brechas ponderadas y cobertura; "
                    "un empate nunca fuerza ganador."
                ),
                support=min(0.85, 0.45 + worst_gap / 250),
                scor=scor,
                evidence=[_evidence_item(scor, metric, "scor_process_criticality")],
                origin="originated",
            )
        )
    return output


def reinforce_legacy_candidates(
    candidates: list[dict[str, object]], scor: dict[str, object]
) -> list[dict[str, object]]:
    metrics = [item for item in scor.get("metrics", []) if isinstance(item, dict)]
    criticality = scor.get("criticality", {})
    assert isinstance(criticality, dict)
    best_by_process: dict[str, dict[str, object]] = {}
    for metric in metrics:
        if (
            metric.get("evidence_status") != "complete"
            or not isinstance(metric.get("gap_score"), (int, float))
            or float(metric["gap_score"]) < SCOR_THRESHOLDS["moderate_gap"]
            or float(metric.get("process_coverage", 0))
            < SCOR_THRESHOLDS["minimum_process_coverage"]
        ):
            continue
        process = str(metric["process"])
        if process not in best_by_process or float(metric["gap_score"]) > float(
            best_by_process[process]["gap_score"]
        ):
            best_by_process[process] = metric

    output: list[dict[str, object]] = []
    priority_up = {"low": "medium", "medium": "high", "high": "high", "critical": "critical"}
    for original in candidates:
        candidate = deepcopy(original)
        matched = next(
            (
                metric
                for process, metric in best_by_process.items()
                if str(candidate["action_type"]) in REINFORCEMENT_ACTIONS[process]
            ),
            None,
        )
        if matched is None:
            output.append(candidate)
            continue
        metric_support = scor_metric_support(matched, criticality)
        contribution = round(
            min(SCOR_THRESHOLDS["maximum_reinforcement"], 0.20 * metric_support), 4
        )
        base = float(candidate["support_score"])
        candidate["support_score"] = round(min(1.0, base + contribution), 4)
        candidate["evidence_level"] = evidence_level(float(candidate["support_score"]))
        if float(matched["gap_score"]) >= SCOR_THRESHOLDS["high_gap"] and metric_support >= 0.65:
            candidate["priority"] = priority_up[str(candidate["priority"])]
        candidate["evidence"].append(_evidence_item(scor, matched, "scor_reinforcement"))
        candidate["limitations"] = list(candidate["limitations"]) + [
            "La evidencia SCOR refuerza la revisión, pero no demuestra causalidad."
        ]
        candidate["provenance"] = {
            **candidate["provenance"],
            "base_support_score": base,
            "scor_support_contribution": contribution,
            "scor_assessment_id": scor["scor_assessment_id"],
            "scor_metric_id": matched["metric_id"],
            "scor_origin": "reinforced",
            "scor_rule_version": SCOR_SUPPORT_RULE_VERSION,
        }
        output.append(candidate)
    return output
