"""Versioned mathematical catalog for models already supported by Forecast Core."""

from __future__ import annotations

from nexora_api.core.exceptions import DataStudioError
from nexora_api.models.dataset import ForecastModelResult

MODEL_CATALOG_VERSION = "forecast_model_catalog_v1"

MODEL_CATALOG: dict[str, dict[str, object]] = {
    "naive": {
        "name": "Naive / último valor",
        "family": "Línea base",
        "formula": "ŷ(t+h) = y(t)",
        "patterns": ["nivel reciente"],
        "inputs": ["última observación válida"],
        "strengths": ["simple", "auditable", "referencia mínima"],
        "limitations": ["no representa tendencia ni estacionalidad"],
    },
    "seasonal_naive": {
        "name": "Naive estacional",
        "family": "Línea base estacional",
        "formula": "ŷ(t+h) = y(t+h-m)",
        "patterns": ["repetición del último ciclo estacional"],
        "inputs": ["último ciclo completo", "periodo estacional m"],
        "strengths": ["preserva el patrón estacional observado"],
        "limitations": ["no adapta nivel ni tendencia entre ciclos"],
    },
    "moving_average": {
        "name": "Promedio móvil",
        "family": "Promedio local",
        "formula": "ŷ(t+h) = (1/w) Σ y(t-i), i=0…w-1",
        "patterns": ["nivel local suavizado"],
        "inputs": ["últimas w observaciones", "ventana w"],
        "strengths": ["estable ante ruido puntual", "interpretación directa"],
        "limitations": ["produce una trayectoria constante", "responde con retraso a cambios"],
    },
    "ses": {
        "name": "Suavizamiento exponencial simple (SES)",
        "family": "Suavizamiento exponencial",
        "formula": "L(t) = αy(t) + (1-α)L(t-1); ŷ(t+h) = L(t)",
        "patterns": ["nivel sin tendencia ni estacionalidad"],
        "inputs": ["histórico continuo", "parámetro α"],
        "strengths": ["pondera más las observaciones recientes"],
        "limitations": ["no representa tendencia ni estacionalidad"],
    },
    "holt": {
        "name": "Holt aditivo",
        "family": "Suavizamiento exponencial con tendencia",
        "formula": "L(t)=αy(t)+(1-α)(L(t-1)+T(t-1)); T(t)=βΔL+(1-β)T(t-1); ŷ(t+h)=L(t)+hT(t)",
        "patterns": ["nivel", "tendencia aditiva"],
        "inputs": ["histórico continuo", "parámetros α y β"],
        "strengths": ["representa tendencia lineal local"],
        "limitations": [
            "no representa estacionalidad",
            "la tendencia puede extrapolarse en exceso",
        ],
    },
    "holt_winters_additive": {
        "name": "Holt-Winters aditivo",
        "family": "Suavizamiento exponencial estacional",
        "formula": "ŷ(t+h) = L(t) + hT(t) + S(t+h-mk)",
        "patterns": ["nivel", "tendencia aditiva", "estacionalidad de amplitud estable"],
        "inputs": ["histórico continuo", "periodo m", "parámetros α, β y γ"],
        "strengths": ["separa nivel, tendencia y ciclo aditivo"],
        "limitations": [
            "requiere al menos dos ciclos",
            "supone amplitud estacional aproximadamente estable",
        ],
    },
    "holt_winters_multiplicative": {
        "name": "Holt-Winters multiplicativo",
        "family": "Suavizamiento exponencial estacional",
        "formula": "ŷ(t+h) = (L(t) + hT(t)) × S(t+h-mk)",
        "patterns": ["nivel", "tendencia aditiva", "estacionalidad proporcional"],
        "inputs": ["histórico continuo y positivo", "periodo m", "parámetros α, β y γ"],
        "strengths": ["representa amplitud estacional proporcional al nivel"],
        "limitations": ["no admite ceros o negativos", "requiere al menos dos ciclos"],
    },
}


def list_definitions() -> list[dict[str, object]]:
    return [{"key": key, **value} for key, value in MODEL_CATALOG.items()]


def require_definition(model_name: str) -> dict[str, object]:
    definition = MODEL_CATALOG.get(model_name)
    if definition is None:
        raise DataStudioError(
            "explanation_model_not_found",
            "The requested model does not have an explanation definition.",
            404,
        )
    return {"key": model_name, "catalog_version": MODEL_CATALOG_VERSION, **definition}


def explain_model(model: ForecastModelResult) -> dict[str, object]:
    name = str(model.model_name)
    parameters = dict(model.parameters or {})
    return {
        **require_definition(name),
        "parameters": parameters,
        "parameters_available": bool(parameters),
        "engine": parameters.get("engine"),
        "parameter_source": parameters.get("parameter_source"),
    }
