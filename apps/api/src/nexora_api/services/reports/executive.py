"""Deterministic executive narrative built from frozen report evidence."""

from __future__ import annotations


def _count_high(decision: dict[str, object] | None) -> tuple[int, int]:
    if not decision:
        return 0, 0
    recommendations = decision.get("recommendations", [])
    if not isinstance(recommendations, list):
        return 0, 0
    high = sum(
        isinstance(item, dict) and item.get("priority") in {"high", "critical"}
        for item in recommendations
    )
    return len(recommendations), high


def build_executive_summary(sources: dict[str, object]) -> dict[str, object]:
    forecast = sources.get("forecast") if isinstance(sources.get("forecast"), dict) else None
    scenario = sources.get("scenario") if isinstance(sources.get("scenario"), dict) else None
    scor = sources.get("scor") if isinstance(sources.get("scor"), dict) else None
    portfolio = sources.get("portfolio") if isinstance(sources.get("portfolio"), dict) else None
    decision = sources.get("decision") if isinstance(sources.get("decision"), dict) else None
    explanation = (
        sources.get("explanation") if isinstance(sources.get("explanation"), dict) else None
    )
    facts: list[str] = []
    uncertainties: list[str] = []
    missing: list[str] = []
    limitations: list[str] = []

    if forecast:
        selection = forecast.get("selection", {})
        product = selection.get("product") if isinstance(selection, dict) else None
        location = selection.get("location") if isinstance(selection, dict) else None
        facts.append(
            f"Se incluyó el Forecast Run {forecast.get('id')} de {product or 'serie agregada'}"
            f" en {location or 'todas las ubicaciones'}, con frecuencia "
            f"{forecast.get('frequency')}."
        )
        facts.append(f"El Champion persistido fue {forecast.get('champion_model')}.")
        limitations.append("El pronóstico describe demanda prevista y no garantiza demanda futura.")
    else:
        missing.append("No se incluyó un Forecast Run.")
    if scenario:
        delta = scenario.get("summary", {})
        relative = delta.get("relative_delta") if isinstance(delta, dict) else None
        detail = (
            f" ({float(relative) * 100:+.1f}% frente al baseline)"
            if relative is not None
            else ""
        )
        facts.append(f"Se incorporó un escenario condicionado{detail}.")
        limitations.append("El escenario es hipotético y no sustituye el forecast oficial.")
    if scor:
        facts.append("Se incorporó un diagnóstico SCOR cuantitativo persistido.")
        limitations.append("SCOR describe brechas bajo las métricas y metas configuradas.")
    if portfolio:
        facts.append(
            f"El Portafolio incluyó {portfolio.get('number_of_series', 0)} series priorizadas."
        )
        limitations.append("Portafolio prioriza revisión; no calcula cantidades óptimas.")
    total, high = _count_high(decision)
    if decision:
        facts.append(
            f"Decision Center aportó {total} recomendaciones; {high} fueron alta o crítica."
        )
        limitations.append("Las recomendaciones apoyan revisión y no ejecutan órdenes.")
    if explanation:
        facts.append("La explicación reconstruye el modelo y la evidencia ya almacenados.")
        limitations.append("La explicación no crea una interpretación causal.")
    if decision and isinstance(decision.get("warnings"), list):
        uncertainties.extend(str(item) for item in decision["warnings"])
    if forecast and isinstance(forecast.get("warnings"), list):
        uncertainties.extend(str(item) for item in forecast["warnings"])
    if not uncertainties:
        uncertainties.append("La incertidumbre se limita a la evidencia persistida disponible.")
    if not missing:
        missing.append(
            "Los valores ausentes de las fuentes permanecen ausentes; "
            "no se sustituyeron por cero."
        )
    return {
        "facts": facts,
        "recommendations": [
            item.get("title")
            for item in (decision.get("recommendations", []) if decision else [])[:5]
            if isinstance(item, dict)
        ],
        "uncertainties": uncertainties,
        "missing_data": missing,
        "limitations": list(dict.fromkeys(limitations)),
        "causal_claims": False,
        "generated_deterministically": True,
    }
