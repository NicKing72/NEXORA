"""Build ordered report sections from a frozen source snapshot."""

from __future__ import annotations

from nexora_api.services.reports.executive import build_executive_summary

LABELS = {
    "cover": "Portada y alcance",
    "executive": "Resumen ejecutivo",
    "forecast": "Evidencia del pronóstico",
    "validation": "Validación y Champion",
    "context_scenario": "Contexto y escenario",
    "scor": "Diagnóstico SCOR",
    "portfolio": "Portafolio operativo",
    "decisions": "Centro de Decisiones",
    "explanation": "Explicabilidad",
    "risks": "Riesgos, incertidumbre y faltantes",
    "provenance": "Procedencia y auditoría",
    "limitations": "Limitaciones",
}


def _reference(source_type: str, source: object) -> list[dict[str, object]]:
    if not isinstance(source, dict):
        return []
    return [{"source_type": source_type, "source_id": source.get("id")}]


def _section(
    section_type: str,
    position: int,
    payload: dict[str, object],
    references: list[dict[str, object]],
    completeness: str = "complete",
) -> dict[str, object]:
    return {
        "section_type": section_type,
        "position": position,
        "payload": {"title": LABELS[section_type], **payload},
        "source_references": references,
        "completeness": completeness,
    }


def build_sections(
    *,
    report_type: str,
    title: str,
    cutoff: str,
    sources: dict[str, object],
    coverage: dict[str, object],
    limitations: list[str],
    warnings: list[str],
    is_demo: bool = False,
) -> list[dict[str, object]]:
    forecast = sources.get("forecast")
    scenario = sources.get("scenario")
    scor = sources.get("scor")
    portfolio = sources.get("portfolio")
    decision = sources.get("decision")
    explanation = sources.get("explanation")
    executive = build_executive_summary(sources)
    sections = [
        _section(
            "cover",
            1,
            {
                "report_title": title,
                "report_type": report_type,
                "report_cutoff": cutoff,
                "dataset": sources.get("dataset"),
                "coverage": coverage,
                "is_demo": is_demo,
            },
            [],
        ),
        _section("executive", 2, executive, [], str(coverage["status"])),
    ]
    if isinstance(forecast, dict):
        sections.extend(
            [
                _section(
                    "forecast",
                    3,
                    {
                        "scope": forecast.get("selection", {}),
                        "frequency": forecast.get("frequency"),
                        "horizon": forecast.get("horizon"),
                        "points": forecast.get("forecast_points", []),
                        "warnings": forecast.get("warnings", []),
                    },
                    _reference("forecast_run", forecast),
                ),
                _section(
                    "validation",
                    4,
                    {
                        "champion_model": forecast.get("champion_model"),
                        "champion_reason": forecast.get("champion_reason"),
                        "models": forecast.get("models", []),
                    },
                    _reference("forecast_run", forecast),
                ),
            ]
        )
    if isinstance(scenario, dict):
        sections.append(
            _section(
                "context_scenario",
                5,
                {
                    "scenario": scenario,
                    "context_evidence": (
                        decision.get("source_snapshot", {}).get("context_signals", [])
                        if isinstance(decision, dict)
                        and isinstance(decision.get("source_snapshot"), dict)
                        else []
                    ),
                    "official_forecast_modified": False,
                },
                _reference("scenario_run", scenario),
            )
        )
    if isinstance(scor, dict):
        sections.append(_section("scor", 6, {"assessment": scor}, _reference("scor", scor)))
    if isinstance(portfolio, dict):
        sections.append(
            _section("portfolio", 7, {"portfolio": portfolio}, _reference("portfolio", portfolio))
        )
    if isinstance(decision, dict):
        sections.append(
            _section("decisions", 8, {"decision": decision}, _reference("decision", decision))
        )
    if isinstance(explanation, dict):
        sections.append(
            _section(
                "explanation",
                9,
                {"explanation": explanation},
                _reference("explanation", explanation),
            )
        )
    sections.extend(
        [
            _section(
                "risks",
                10,
                {
                    "warnings": warnings,
                    "uncertainties": executive["uncertainties"],
                    "missing_data": executive["missing_data"],
                },
                [],
                "partial" if warnings else "complete",
            ),
            _section(
                "provenance",
                11,
                {
                    "report_cutoff": cutoff,
                    "sources": {
                        key: value.get("id") if isinstance(value, dict) else None
                        for key, value in sources.items()
                        if key != "dataset"
                    },
                    "recalculated": False,
                    "snapshot_immutable": True,
                },
                [],
            ),
            _section("limitations", 12, {"items": limitations}, [], "partial"),
        ]
    )
    return sorted(sections, key=lambda item: int(item["position"]))
