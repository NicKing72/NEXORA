"""Versioned Portfolio support rules for non-executing decisions."""

from __future__ import annotations

from copy import deepcopy

from nexora_api.services.decisions.catalog import ACTION_LABELS
from nexora_api.services.decisions.ranking import evidence_level

PORTFOLIO_SUPPORT_RULE_VERSION = "decision_portfolio_support_v1"
PORTFOLIO_THRESHOLDS = {
    "material_variability": 0.25,
    "priority_rank": 3,
    "maximum_reinforcement": 0.20,
}
RISK_FACTOR = {"critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.25, "unknown": 0.0}


def _availability_factor(item: dict[str, object]) -> float:
    values = item.get("operational_inputs", {})
    if not isinstance(values, dict):
        return 0.0
    required = ("current_inventory", "inbound_inventory", "safety_stock", "lead_time")
    available = sum(
        isinstance(values.get(key), dict) and values[key].get("status") == "available"
        for key in required
    )
    return available / len(required)


def portfolio_item_support(item: dict[str, object]) -> tuple[float, dict[str, float]]:
    """0.40 priority + 0.25 risk + 0.15 completeness + 0.10 data + 0.10 rank."""
    priority = max(0.0, min(1.0, float(item.get("priority_score", 0)) / 100))
    risk = RISK_FACTOR.get(str(item.get("risk_level")), 0.0)
    completeness = 1.0 if item.get("score_status") == "complete" else 0.6
    availability = _availability_factor(item)
    rank = max(1, int(item.get("rank", 999)))
    rank_factor = max(0.4, 1.0 - 0.1 * (rank - 1))
    factors = {
        "priority_score": priority,
        "risk": risk,
        "completeness": completeness,
        "operational_availability": availability,
        "ranking": rank_factor,
    }
    score = round(
        0.40 * priority
        + 0.25 * risk
        + 0.15 * completeness
        + 0.10 * availability
        + 0.10 * rank_factor,
        4,
    )
    return score, factors


def _evidence_item(
    portfolio: dict[str, object], item: dict[str, object], evidence_type: str
) -> dict[str, object]:
    score, factors = portfolio_item_support(item)
    return {
        "evidence_type": evidence_type,
        "source_id": str(portfolio["portfolio_run_id"]),
        "description": (
            f"Evidencia de Portafolio congelada: posición #{item['rank']} · "
            f"{item.get('product') or 'serie agregada'}."
        ),
        "snapshot": {
            "portfolio": {
                "portfolio_run_id": portfolio["portfolio_run_id"],
                "cutoff": portfolio["cutoff"],
                "created_at": portfolio["created_at"],
                "available_at": portfolio["available_at"],
                "calculation_version": portfolio["calculation_version"],
                "number_of_series": portfolio["number_of_series"],
                "summary": portfolio["summary"],
                "forecast_run_ids": portfolio["forecast_run_ids"],
                "provenance": portfolio["provenance"],
                "decision_cutoff": portfolio["decision_cutoff"],
            },
            "item": deepcopy(item),
            "portfolio_support_score": score,
            "support_factors": factors,
            "support_formula": "0.40*P + 0.25*R + 0.15*C + 0.10*D + 0.10*K",
            "support_rule_version": PORTFOLIO_SUPPORT_RULE_VERSION,
            "priority_score_is_probability": False,
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
    portfolio: dict[str, object],
    item: dict[str, object],
    evidence_type: str = "portfolio_item",
    origin: str = "originated",
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
        "evidence": [_evidence_item(portfolio, item, evidence_type)],
        "limitations": limitations
        or [
            "El ranking prioriza revisiones y no constituye una decisión obligatoria.",
            "NEXORA no calcula ni ejecuta cantidades de inventario o compra.",
        ],
        "context_signal_ids": [],
        "context_impact_ids": [],
        "provenance": {
            "rule_version": PORTFOLIO_SUPPORT_RULE_VERSION,
            "portfolio_run_id": portfolio["portfolio_run_id"],
            "portfolio_item_id": item["id"],
            "portfolio_rank": item["rank"],
            "portfolio_support_contribution": score,
            "portfolio_origin": origin,
            "causal_claim": False,
            "automatic_execution": False,
        },
    }


def generate_portfolio_candidates(portfolio: dict[str, object]) -> list[dict[str, object]]:
    items = [item for item in portfolio.get("related_items", []) if isinstance(item, dict)]
    output: list[dict[str, object]] = []
    for item in items:
        support, _ = portfolio_item_support(item)
        risk = str(item.get("risk_level"))
        coverage_specific = False
        if risk in {"critical", "high"} and item.get("inventory_coverage") is not None:
            coverage_specific = True
            output.append(
                _candidate(
                    key=f"portfolio:coverage:{item['id']}",
                    priority="high",
                    action="review_portfolio_coverage",
                    summary=(
                        f"La serie ocupa la posición #{item['rank']} y presenta riesgo "
                        f"{risk} por cobertura dentro del horizonte previsto."
                    ),
                    rationale=(
                        "La cobertura calculada amerita revisión operativa; no determina una "
                        "cantidad de compra ni inventario óptimo."
                    ),
                    support=support,
                    portfolio=portfolio,
                    item=item,
                )
            )
        missing = [str(value) for value in item.get("missing_inputs", [])]
        if (
            item.get("score_status") == "partial"
            or item.get("inventory_coverage") is None
            or missing
        ):
            output.append(
                _candidate(
                    key=f"portfolio:data:{item['id']}",
                    priority="medium" if missing else "low",
                    action="complete_portfolio_data",
                    summary=(
                        "La evidencia operativa del Portafolio está incompleta; "
                        f"faltan: {', '.join(missing) if missing else 'inputs para cobertura'}."
                    ),
                    rationale=(
                        "Los faltantes permanecen ausentes y no se utilizaron como cero ni para "
                        "simular riesgo."
                    ),
                    support=min(0.45, support),
                    portfolio=portfolio,
                    item=item,
                    evidence_type="portfolio_data_quality",
                    origin="evidence_request",
                    limitations=[
                        "La cobertura puede permanecer no calculable hasta completar inventario.",
                        "No se fabricaron valores para datos ausentes o no aplicables.",
                    ],
                )
            )
        if (
            int(item.get("rank", 999)) <= PORTFOLIO_THRESHOLDS["priority_rank"]
            and not coverage_specific
        ):
            output.append(
                _candidate(
                    key=f"portfolio:priority:{item['id']}",
                    priority="medium",
                    action="review_portfolio_priority",
                    summary=(
                        f"La serie ocupa la posición prioritaria #{item['rank']} "
                        "del Portafolio."
                    ),
                    rationale=(
                        "El ranking relativo orienta el orden de revisión y no obliga una acción "
                        "empresarial."
                    ),
                    support=support,
                    portfolio=portfolio,
                    item=item,
                )
            )
        variability = item.get("forecast_variability")
        if (
            isinstance(variability, (int, float))
            and variability >= PORTFOLIO_THRESHOLDS["material_variability"]
            and item.get("score_status") == "complete"
        ):
            output.append(
                _candidate(
                    key=f"portfolio:variability:{item['id']}",
                    priority="medium",
                    action="review_portfolio_volatility",
                    summary=(
                        "La variabilidad prevista de la serie alcanza "
                        f"{variability * 100:.1f}%."
                    ),
                    rationale=(
                        "La variabilidad material amerita revisar exposición, "
                        "sin inferir causalidad."
                    ),
                    support=support,
                    portfolio=portfolio,
                    item=item,
                )
            )
    return output


def reinforce_candidates(
    candidates: list[dict[str, object]], portfolio: dict[str, object]
) -> list[dict[str, object]]:
    items = [item for item in portfolio.get("related_items", []) if isinstance(item, dict)]
    if not items:
        return deepcopy(candidates)
    item = items[0]
    support, _ = portfolio_item_support(item)
    risk = str(item.get("risk_level"))
    missing = bool(item.get("missing_inputs")) or item.get("inventory_coverage") is None
    coverage_actions = {
        "prepare_supply",
        "review_replenishment",
        "review_stockout_risk",
        "review_inventory_policy",
    }
    output: list[dict[str, object]] = []
    priority_up = {"low": "medium", "medium": "high", "high": "high", "critical": "critical"}
    for original in candidates:
        candidate = deepcopy(original)
        action = str(candidate["action_type"])
        applies = (risk in {"critical", "high"} and action in coverage_actions) or (
            missing and action == "manual_review_required"
        )
        if not applies:
            output.append(candidate)
            continue
        contribution = round(
            min(PORTFOLIO_THRESHOLDS["maximum_reinforcement"], 0.20 * support), 4
        )
        base = float(candidate["support_score"])
        candidate["support_score"] = round(min(1.0, base + contribution), 4)
        candidate["evidence_level"] = evidence_level(float(candidate["support_score"]))
        if risk in {"critical", "high"} and item.get("score_status") == "complete":
            candidate["priority"] = priority_up[str(candidate["priority"])]
        candidate["evidence"].append(_evidence_item(portfolio, item, "portfolio_reinforcement"))
        candidate["limitations"] = list(candidate["limitations"]) + [
            "La evidencia de Portafolio refuerza la revisión, pero no ejecuta operaciones."
        ]
        candidate["provenance"] = {
            **candidate["provenance"],
            "base_support_score": candidate["provenance"].get(
                "base_support_score", base
            ),
            "support_before_portfolio": base,
            "portfolio_support_contribution": contribution,
            "portfolio_run_id": portfolio["portfolio_run_id"],
            "portfolio_item_id": item["id"],
            "portfolio_rank": item["rank"],
            "portfolio_origin": "reinforced",
            "portfolio_rule_version": PORTFOLIO_SUPPORT_RULE_VERSION,
        }
        output.append(candidate)
    return output
