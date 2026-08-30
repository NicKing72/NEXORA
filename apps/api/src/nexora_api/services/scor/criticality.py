"""Process scoring and cautious critical-link selection."""

from __future__ import annotations

from nexora_api.services.scor.definitions import METRICS, PROCESSES


def process_scores(
    metrics: list[dict[str, object]], minimum_coverage: float
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for process in PROCESSES:
        process_metric_ids = {item.id for item in METRICS if item.process == process}
        process_metrics = [item for item in metrics if item["metric_id"] in process_metric_ids]
        complete = [item for item in process_metrics if item["evidence_status"] == "complete"]
        evaluable = [
            item
            for item in complete
            if item.get("gap_score") is not None and float(item.get("target_weight", 0)) > 0
        ]
        total = len(process_metric_ids)
        data_coverage = len(complete) / total if total else 0.0
        benchmark_coverage = len(evaluable) / total if total else 0.0
        total_weight = sum(float(item["target_weight"]) for item in evaluable)
        score = (
            sum(float(item["gap_score"]) * float(item["target_weight"]) for item in evaluable)
            / total_weight
            if total_weight > 0
            else None
        )
        confidence = (
            "high"
            if benchmark_coverage >= 0.8
            else "moderate"
            if benchmark_coverage >= minimum_coverage
            else "insufficient"
        )
        output.append(
            {
                "process": process,
                "process_label": PROCESSES[process],
                "metrics_total": total,
                "metrics_complete": len(complete),
                "metrics_insufficient": sum(
                    item["evidence_status"] in {"incomplete", "insufficient_evidence", "invalid"}
                    for item in process_metrics
                ),
                "metrics_not_applicable": sum(
                    item["evidence_status"] == "not_applicable" for item in process_metrics
                ),
                "metrics_evaluable": len(evaluable),
                "data_coverage": round(data_coverage, 4),
                "benchmark_coverage": round(benchmark_coverage, 4),
                "weighted_gap_score": round(score, 4) if score is not None else None,
                "confidence": confidence,
                "contributors": sorted(
                    (
                        {
                            "metric_id": item["metric_id"],
                            "gap_score": item["gap_score"],
                            "weight": item["target_weight"],
                        }
                        for item in evaluable
                    ),
                    key=lambda item: (-float(item["gap_score"]), str(item["metric_id"])),
                ),
            }
        )
    return output


def determine_critical_process(
    processes: list[dict[str, object]], *, profile_id: str | None, minimum_coverage: float
) -> dict[str, object]:
    if not profile_id:
        return _insufficient("benchmark_profile_missing", processes, minimum_coverage)
    comparable = [
        item
        for item in processes
        if item["weighted_gap_score"] is not None
        and float(item["benchmark_coverage"]) >= minimum_coverage
    ]
    if len(comparable) < 2:
        return _insufficient(
            "at_least_two_comparable_processes_required", processes, minimum_coverage
        )
    ranked = sorted(
        comparable, key=lambda item: (-float(item["weighted_gap_score"]), str(item["process"]))
    )
    worst = float(ranked[0]["weighted_gap_score"])
    tied = [item for item in ranked if abs(float(item["weighted_gap_score"]) - worst) < 1e-9]
    return {
        "status": "tie" if len(tied) > 1 else "candidate",
        "selected_process": None if len(tied) > 1 else tied[0]["process"],
        "tied_processes": [item["process"] for item in tied] if len(tied) > 1 else [],
        "process_scores": ranked,
        "benchmark_profile_id": profile_id,
        "minimum_coverage": minimum_coverage,
        "reason": "worst_weighted_relative_gap" if len(tied) == 1 else "equal_weighted_gap_score",
        "tie_break_reason": "No se fuerza un ganador ante scores iguales."
        if len(tied) > 1
        else None,
        "official_scor_score": False,
    }


def _insufficient(
    reason: str, processes: list[dict[str, object]], minimum: float
) -> dict[str, object]:
    return {
        "status": "insufficient_evidence",
        "selected_process": None,
        "tied_processes": [],
        "process_scores": processes,
        "reason": reason,
        "minimum_coverage": minimum,
        "message": (
            "No existe información de referencia suficiente para determinar "
            "automáticamente el eslabón crítico."
        ),
        "official_scor_score": False,
    }
