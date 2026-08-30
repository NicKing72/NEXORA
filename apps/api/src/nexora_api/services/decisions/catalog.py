"""Extensible action catalog and stable tie-break order."""

ACTION_ORDER = (
    "review_stockout_risk",
    "manual_review_required",
    "prepare_supply",
    "prepare_capacity",
    "review_replenishment",
    "investigate_demand_increase",
    "investigate_demand_drop",
    "review_inventory_policy",
    "review_promotion_plan",
    "review_price_change",
    "maintain_plan",
    "monitor",
)

ACTION_LABELS = {
    "monitor": "Monitorear evolución",
    "maintain_plan": "Mantener el plan bajo observación",
    "prepare_supply": "Preparar revisión de abastecimiento",
    "prepare_capacity": "Revisar preparación de capacidad",
    "review_replenishment": "Revisar el plan de reposición",
    "review_inventory_policy": "Revisar la política de inventario",
    "investigate_demand_drop": "Investigar el descenso de demanda",
    "investigate_demand_increase": "Investigar el incremento de demanda",
    "review_stockout_risk": "Revisar riesgo de ruptura de stock",
    "review_promotion_plan": "Revisar el plan promocional",
    "review_price_change": "Revisar el cambio de precio",
    "manual_review_required": "Revisión manual requerida",
}

PRIORITY_WEIGHT = {"critical": 4, "high": 3, "medium": 2, "low": 1}
