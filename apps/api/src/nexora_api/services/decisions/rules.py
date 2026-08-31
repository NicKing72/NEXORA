"""Documented deterministic rules that generate non-executing recommendations."""

# ruff: noqa: E501 - Spanish recommendation copy is clearer as complete sentences.

from __future__ import annotations

from nexora_api.services.decisions.catalog import ACTION_LABELS
from nexora_api.services.decisions.ranking import evidence_level

OPERATIONAL_LIMITATIONS = [
    "No existe una posición de inventario operacional actual confirmada.",
    "No se dispone de lead time, MOQ, costos ni nivel de servicio objetivo suficientes.",
    "No es posible calcular una cantidad óptima con los datos actualmente disponibles.",
]


def _candidate(
    *,
    stable_key: str,
    priority: str,
    action_type: str,
    summary: str,
    rationale: str,
    support: float,
    evidence: list[dict[str, object]],
    limitations: list[str] | None = None,
    signal_ids: list[str] | None = None,
    impact_ids: list[str] | None = None,
    provenance: dict[str, object] | None = None,
) -> dict[str, object]:
    score = round(max(0.0, min(1.0, support)), 4)
    return {
        "stable_key": stable_key,
        "priority": priority,
        "action_type": action_type,
        "title": ACTION_LABELS[action_type],
        "summary": summary,
        "rationale": rationale,
        "support_score": score,
        "evidence_level": evidence_level(score),
        "evidence": evidence,
        "limitations": limitations or [],
        "context_signal_ids": signal_ids or [],
        "context_impact_ids": impact_ids or [],
        "provenance": {
            "rule_version": "decision_rules_v1",
            "causal_claim": False,
            "automatic_execution": False,
            **(provenance or {}),
        },
    }


def _forecast_support(champion: dict[str, object]) -> float:
    stability = champion.get("stability", {})
    label = stability.get("label") if isinstance(stability, dict) else None
    stability_points = {"high": 0.25, "moderate": 0.16, "low": 0.08}.get(str(label), 0.04)
    fold_points = min(0.2, int(champion.get("fold_count", 0)) * 0.04)
    return 0.5 + stability_points + fold_points


def forecast_candidates(evidence: dict[str, object]) -> list[dict[str, object]]:
    summary = evidence["forecast_summary"]
    champion = evidence["champion"]
    assert isinstance(summary, dict) and isinstance(champion, dict)
    trajectory = summary.get("trajectory_delta")
    support = _forecast_support(champion)
    source = [
        {
            "evidence_type": "official_forecast",
            "source_id": None,
            "description": "Trayectoria del pronóstico oficial dentro de su horizonte.",
            "snapshot": {"forecast_summary": summary, "champion": champion},
        }
    ]
    output: list[dict[str, object]] = []
    if trajectory is None:
        output.append(
            _candidate(
                stable_key="forecast:unknown",
                priority="medium",
                action_type="manual_review_required",
                summary="El cambio relativo del horizonte no puede calcularse porque el primer valor es cero.",
                rationale="La trayectoria requiere revisión descriptiva antes de apoyar una decisión.",
                support=0.3,
                evidence=source,
                limitations=[
                    "El cambio porcentual no es matemáticamente válido con baseline inicial cero."
                ],
            )
        )
    elif trajectory >= 0.10:
        output.append(
            _candidate(
                stable_key="forecast:strong_increase",
                priority="high",
                action_type="prepare_supply",
                summary=f"El pronóstico oficial aumenta {trajectory * 100:.1f}% dentro del horizonte.",
                rationale="La trayectoria prevista amerita revisar capacidad y abastecimiento, sin calcular órdenes automáticas.",
                support=support,
                evidence=source,
                limitations=OPERATIONAL_LIMITATIONS,
            )
        )
    elif trajectory >= 0.03:
        output.append(
            _candidate(
                stable_key="forecast:mild_increase",
                priority="medium",
                action_type="investigate_demand_increase",
                summary=f"El pronóstico oficial presenta un incremento leve de {trajectory * 100:.1f}%.",
                rationale="Conviene verificar si el patrón se sostiene antes de ajustar planes operativos.",
                support=support,
                evidence=source,
            )
        )
    elif trajectory <= -0.10:
        output.append(
            _candidate(
                stable_key="forecast:strong_drop",
                priority="high",
                action_type="investigate_demand_drop",
                summary=f"El pronóstico oficial desciende {abs(trajectory) * 100:.1f}% dentro del horizonte.",
                rationale="El descenso previsto requiere revisión comercial y operativa; no se atribuye a una causa específica.",
                support=support,
                evidence=source,
            )
        )
    elif trajectory <= -0.03:
        output.append(
            _candidate(
                stable_key="forecast:mild_drop",
                priority="medium",
                action_type="investigate_demand_drop",
                summary=f"El pronóstico oficial presenta un descenso leve de {abs(trajectory) * 100:.1f}%.",
                rationale="Se recomienda observar el patrón y contrastarlo con información operativa disponible.",
                support=support,
                evidence=source,
            )
        )
    else:
        output.append(
            _candidate(
                stable_key="forecast:stable",
                priority="low",
                action_type="maintain_plan",
                summary="La trayectoria prevista permanece dentro de ±3% durante el horizonte.",
                rationale="No se observa un cambio direccional suficiente para escalar la revisión del plan.",
                support=support,
                evidence=source,
            )
        )

    width = summary.get("mean_relative_interval_width_95")
    if isinstance(width, (int, float)) and width >= 0.25:
        priority = "high" if width >= 0.50 else "medium"
        output.append(
            _candidate(
                stable_key="forecast:uncertainty",
                priority=priority,
                action_type="manual_review_required" if priority == "high" else "monitor",
                summary=f"El ancho medio del intervalo 95% equivale a {width * 100:.1f}% del pronóstico.",
                rationale="La incertidumbre limita la precisión con la que puede traducirse el forecast a una acción operativa.",
                support=min(0.8, support),
                evidence=source,
                limitations=[
                    "Los intervalos expresan incertidumbre predictiva y no límites operativos."
                ],
            )
        )
    return output


def scenario_candidates(evidence: dict[str, object]) -> list[dict[str, object]]:
    scenario = evidence.get("scenario_snapshot")
    if not isinstance(scenario, dict):
        return []
    summary = scenario.get("summary", {})
    assert isinstance(summary, dict)
    delta = summary.get("relative_delta")
    warnings = [str(item) for item in scenario.get("warnings", [])]
    assumptions = scenario.get("assumptions", [])
    types = {str(item.get("type")) for item in assumptions if isinstance(item, dict)}
    source = [
        {
            "evidence_type": "hypothetical_scenario",
            "source_id": str(scenario["id"]),
            "description": "Comparación condicionada; no sustituye al pronóstico oficial.",
            "snapshot": scenario,
        }
    ]
    output: list[dict[str, object]] = []
    if isinstance(delta, (int, float)) and abs(delta) >= 0.03:
        strong = abs(delta) >= 0.10
        critical = abs(delta) >= 0.25
        if delta > 0:
            action = "prepare_capacity"
            summary_text = f"El escenario condicionado supera al baseline en {delta * 100:.1f}%."
        else:
            action = "review_inventory_policy"
            summary_text = (
                f"El escenario condicionado queda {abs(delta) * 100:.1f}% bajo el baseline."
            )
        output.append(
            _candidate(
                stable_key=f"scenario:delta:{action}",
                priority="critical" if critical else "high" if strong else "medium",
                action_type=action,
                summary=summary_text,
                rationale="La diferencia procede de supuestos explícitos y sirve para revisar preparación, no para reemplazar el forecast.",
                support=0.72 if not warnings else 0.62,
                evidence=source,
                limitations=[
                    "El escenario es hipotético y depende de los supuestos seleccionados."
                ],
                provenance={"scenario_is_hypothetical": True},
            )
        )
    if "stock_restriction" in types or "sales_potentially_censored" in warnings:
        magnitude = abs(float(delta)) if isinstance(delta, (int, float)) else 0.0
        output.append(
            _candidate(
                stable_key="scenario:stock_restriction",
                priority="critical" if magnitude >= 0.20 else "high",
                action_type="review_stockout_risk",
                summary="El escenario incluye una restricción de disponibilidad que puede censurar las ventas observables.",
                rationale="La restricción no demuestra una reducción de demanda ni permite estimar ventas perdidas.",
                support=0.74,
                evidence=source,
                limitations=OPERATIONAL_LIMITATIONS,
                provenance={"demand_censoring_possible": True, "scenario_is_hypothetical": True},
            )
        )
    if any("overlapping" in warning for warning in warnings):
        output.append(
            _candidate(
                stable_key="scenario:overlap",
                priority="medium",
                action_type="manual_review_required",
                summary="El escenario contiene supuestos solapados aplicados en el orden declarado.",
                rationale="La interacción entre supuestos debe revisarse antes de usar el resultado como apoyo operativo.",
                support=0.58,
                evidence=source,
                limitations=["No se resolvieron interacciones causales entre supuestos."],
            )
        )
    return output


def _context_action(signal_type: str) -> str:
    if "promotion" in signal_type or signal_type == "campaign":
        return "review_promotion_plan"
    if "price" in signal_type:
        return "review_price_change"
    if signal_type == "stockout":
        return "review_stockout_risk"
    return "monitor"


def context_candidates(evidence: dict[str, object]) -> list[dict[str, object]]:
    impacts = evidence.get("impacts", {})
    analogies = evidence.get("analogies", {})
    signals = evidence.get("signals", [])
    assert isinstance(impacts, dict) and isinstance(analogies, dict)
    output: list[dict[str, object]] = []
    for signal in signals if isinstance(signals, list) else []:
        if not isinstance(signal, dict):
            continue
        signal_id = str(signal["id"])
        signal_type = str(signal["type"])
        impact = impacts.get(signal_id)
        analogy = analogies.get(signal_id)
        confidence = signal.get("confidence")
        confidence_value = float(confidence) if isinstance(confidence, (int, float)) else 0.5
        action = _context_action(signal_type)
        evidence_items = [
            {
                "evidence_type": "context_signal",
                "source_id": signal_id,
                "description": "Señal disponible al corte y relevante por alcance determinístico.",
                "snapshot": signal,
            }
        ]
        if isinstance(impact, dict):
            relative = impact.get("relative_delta")
            raw_score = float(impact.get("evidence_score", 0))
            # Context Impact persists its explainable score on a 0..100 scale;
            # decision support is normalized to 0..1 before ranking.
            score = min(1.0, max(0.0, raw_score / 100.0))
            magnitude = abs(float(relative)) if isinstance(relative, (int, float)) else 0.0
            priority = "high" if score >= 0.8 and magnitude >= 0.10 else "medium"
            evidence_items.append(
                {
                    "evidence_type": "context_impact",
                    "source_id": str(impact["id"]),
                    "description": "Asociación histórica observada; no implica causalidad.",
                    "snapshot": impact,
                }
            )
            output.append(
                _candidate(
                    stable_key=f"context:impact:{signal_id}",
                    priority=priority,
                    action_type=action,
                    summary=f"La señal «{signal['title']}» dispone de evidencia histórica descriptiva.",
                    rationale="La asociación observada se usa para priorizar revisión, no para afirmar que la señal causó el cambio.",
                    support=0.55 * score + 0.45 * confidence_value,
                    evidence=evidence_items,
                    signal_ids=[signal_id],
                    impact_ids=[str(impact["id"])],
                )
            )
        elif isinstance(analogy, dict):
            evidence_items.append(
                {
                    "evidence_type": "historical_analogy",
                    "source_id": signal_id,
                    "description": "Analogía histórica descriptiva disponible al corte.",
                    "snapshot": analogy,
                }
            )
            output.append(
                _candidate(
                    stable_key=f"context:analogy:{signal_id}",
                    priority="medium",
                    action_type=action,
                    summary=f"La señal futura «{signal['title']}» tiene analogías históricas compatibles.",
                    rationale="La analogía orienta una revisión; no predice ni demuestra un efecto causal futuro.",
                    support=min(0.78, 0.45 + 0.08 * int(analogy["comparable_events"])),
                    evidence=evidence_items,
                    signal_ids=[signal_id],
                    impact_ids=[str(item) for item in analogy.get("estimate_ids", [])],
                    limitations=["La analogía histórica no está aplicada al pronóstico oficial."],
                )
            )
        else:
            output.append(
                _candidate(
                    stable_key=f"context:insufficient:{signal_id}",
                    priority="low",
                    action_type="monitor",
                    summary=f"La señal «{signal['title']}» no dispone de evidencia histórica suficiente.",
                    rationale="La señal se conserva para monitoreo sin atribuir impacto sobre demanda.",
                    support=0.25 * confidence_value,
                    evidence=evidence_items,
                    signal_ids=[signal_id],
                    limitations=[
                        "No existe una estimación histórica evaluable disponible al corte."
                    ],
                )
            )
    return output


def missing_input_candidate(evidence: dict[str, object]) -> dict[str, object]:
    missing = [str(item) for item in evidence["missing_operational_inputs"]]
    return _candidate(
        stable_key="inputs:operational",
        priority="medium",
        action_type="manual_review_required",
        summary="Faltan inputs operativos para convertir recomendaciones en cantidades ejecutables.",
        rationale="NEXORA puede priorizar una revisión, pero no calcular compras, capacidad o inventario óptimos.",
        support=0.28,
        evidence=[
            {
                "evidence_type": "data_availability",
                "source_id": None,
                "description": "Inventario y parámetros logísticos no disponibles.",
                "snapshot": {"missing_inputs": missing},
            }
        ],
        limitations=OPERATIONAL_LIMITATIONS,
        provenance={"missing_inputs": missing},
    )


def generate_candidates(evidence: dict[str, object]) -> list[dict[str, object]]:
    legacy = [
        *forecast_candidates(evidence),
        *scenario_candidates(evidence),
        *context_candidates(evidence),
        missing_input_candidate(evidence),
    ]
    scor = evidence.get("scor_snapshot")
    if not isinstance(scor, dict):
        return legacy
    from nexora_api.services.decisions.scor_support import (
        generate_scor_candidates,
        reinforce_legacy_candidates,
    )

    return [*reinforce_legacy_candidates(legacy, scor), *generate_scor_candidates(scor)]
