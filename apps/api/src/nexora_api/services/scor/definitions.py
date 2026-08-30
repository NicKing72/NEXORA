"""Versioned KPI catalog; the single source of truth for API and UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass

ENGINE_VERSION = "scor_diagnostic_v1"
PROCESSES = {
    "PLAN": "Planificación",
    "SOURCE": "Abastecimiento",
    "MAKE": "Producción / Almacenaje",
    "DELIVER": "Distribución",
    "RETURN": "Retorno",
}


@dataclass(frozen=True)
class InputDefinition:
    id: str
    label: str
    required: bool = True
    nonnegative: bool = True
    direct_percentage: bool = False


@dataclass(frozen=True)
class MetricDefinition:
    id: str
    process: str
    attribute: str
    display_name: str
    formula: str
    inputs: tuple[InputDefinition, ...]
    unit: str
    method: str
    desired_direction: str
    source_type: str = "aggregated_raw_data"
    version: str = ENGINE_VERSION
    numerator_key: str | None = None
    denominator_key: str | None = None
    factor: float = 1.0

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["process_label"] = PROCESSES[self.process]
        return payload


def field(id_: str, label: str, **kwargs: object) -> InputDefinition:
    return InputDefinition(id_, label, **kwargs)


def ratio(
    id_: str,
    process: str,
    attribute: str,
    name: str,
    numerator: tuple[str, str],
    denominator: tuple[str, str],
    *,
    factor: float = 100.0,
    unit: str = "%",
    direction: str = "higher_is_better",
) -> MetricDefinition:
    return MetricDefinition(
        id_,
        process,
        attribute,
        name,
        f"({numerator[0]} / {denominator[0]}) × {factor:g}",
        (field(*numerator), field(*denominator)),
        unit,
        "ratio_of_sums",
        direction,
        numerator_key=numerator[0],
        denominator_key=denominator[0],
        factor=factor,
    )


METRICS: tuple[MetricDefinition, ...] = (
    ratio(
        "P01",
        "PLAN",
        "reliability",
        "Precisión del Pronóstico de Demanda",
        ("actual_units_6m", "Unidades reales"),
        ("forecast_units_6m", "Unidades pronosticadas"),
    ),
    ratio(
        "P02",
        "PLAN",
        "asset_management",
        "Días de Inventario Promedio / Cobertura",
        ("average_inventory_value", "Valor promedio de inventario"),
        ("cogs_6m", "Costo de ventas del periodo"),
        factor=180,
        unit="días",
        direction="lower_is_better",
    ),
    MetricDefinition(
        "P03",
        "PLAN",
        "asset_management",
        "Ciclo de Conversión de Efectivo / Cash-to-Cash",
        "days_receivable + inventory_days - days_payable",
        (
            field("days_receivable", "Días de cuentas por cobrar"),
            field("inventory_days", "Días de inventario"),
            field("days_payable", "Días de cuentas por pagar"),
        ),
        "días",
        "sum_subtract",
        "lower_is_better",
    ),
    ratio(
        "P04",
        "PLAN",
        "cost",
        "Costo de Planificación",
        ("planning_cost_6m", "Costo de planificación"),
        ("sales_6m", "Ventas del periodo"),
        direction="lower_is_better",
    ),
    ratio(
        "S01",
        "SOURCE",
        "reliability",
        "Entregas a Tiempo del Proveedor",
        ("supplier_orders_on_time_6m", "Órdenes recibidas a tiempo"),
        ("supplier_orders_total_6m", "Órdenes totales del proveedor"),
    ),
    ratio(
        "S02",
        "SOURCE",
        "reliability",
        "Tasa de Defectos en Recepción",
        ("rejected_units_6m", "Unidades rechazadas"),
        ("received_units_6m", "Unidades recibidas"),
        direction="lower_is_better",
    ),
    ratio(
        "S03",
        "SOURCE",
        "responsiveness",
        "Lead Time del Proveedor",
        ("supplier_lead_time_days_total", "Días acumulados de lead time"),
        ("supplier_orders_total_6m", "Órdenes totales del proveedor"),
        factor=1,
        unit="días",
        direction="lower_is_better",
    ),
    MetricDefinition(
        "S04",
        "SOURCE",
        "agility",
        "Adaptabilidad de la Cadena / Upside Adaptability",
        "sustainable_supplier_increase_30d_pct",
        (
            field(
                "sustainable_supplier_increase_30d_pct",
                "Incremento sostenible declarado a 30 días",
                direct_percentage=True,
            ),
        ),
        "%",
        "direct",
        "higher_is_better",
        source_type="measured_or_declared",
    ),
    ratio(
        "S05",
        "SOURCE",
        "cost",
        "Costo de Abastecimiento",
        ("procurement_operating_cost_6m", "Costo operativo de abastecimiento"),
        ("sales_6m", "Ventas del periodo"),
        direction="lower_is_better",
    ),
    ratio(
        "M01",
        "MAKE",
        "reliability",
        "Cumplimiento del Plan de Producción / Picking",
        ("completed_as_planned_6m", "Órdenes completadas según plan"),
        ("total_planned_6m", "Órdenes planificadas"),
    ),
    ratio(
        "M02",
        "MAKE",
        "responsiveness",
        "Tiempo de Ciclo de Picking / Producción",
        ("processing_time_total", "Tiempo total de procesamiento"),
        ("processed_orders_total", "Órdenes procesadas"),
        factor=1,
        unit="time_unit",
        direction="lower_is_better",
    ),
    ratio(
        "M03",
        "MAKE",
        "asset_management",
        "Utilización de la Capacidad del Almacén",
        ("occupied_capacity", "Capacidad ocupada"),
        ("maximum_design_capacity", "Capacidad máxima de diseño"),
    ),
    MetricDefinition(
        "M04",
        "MAKE",
        "asset_management",
        "Retorno sobre Activos Fijos Logísticos / ROFA",
        "((supply_chain_revenue_6m - total_supply_chain_cost_6m) / "
        "logistics_fixed_assets_value) × 100",
        (
            field("supply_chain_revenue_6m", "Ingresos de cadena"),
            field("total_supply_chain_cost_6m", "Costo total de cadena"),
            field("logistics_fixed_assets_value", "Activos fijos logísticos"),
        ),
        "%",
        "rofa",
        "higher_is_better",
    ),
    ratio(
        "M05",
        "MAKE",
        "cost",
        "Costo de Mantenimiento de Inventario",
        ("inventory_holding_cost_6m", "Costo de mantenimiento de inventario"),
        ("inventory_value", "Valor de inventario"),
        direction="lower_is_better",
    ),
    ratio(
        "D01",
        "DELIVER",
        "reliability",
        "Tasa de Entregas a Tiempo",
        ("deliveries_on_time_6m", "Entregas a tiempo"),
        ("dispatched_orders_6m", "Órdenes despachadas"),
    ),
    ratio(
        "D02",
        "DELIVER",
        "reliability",
        "Tasa de Entregas Completas",
        ("complete_deliveries_6m", "Entregas completas"),
        ("dispatched_orders_6m", "Órdenes despachadas"),
    ),
    ratio(
        "D03",
        "DELIVER",
        "reliability",
        "Tasa de Entregas Sin Daños",
        ("damage_free_deliveries_6m", "Entregas sin daños"),
        ("dispatched_orders_6m", "Órdenes despachadas"),
    ),
    ratio(
        "D04",
        "DELIVER",
        "reliability",
        "Tasa de Facturación Correcta",
        ("correctly_invoiced_orders_6m", "Órdenes facturadas correctamente"),
        ("dispatched_orders_6m", "Órdenes despachadas"),
    ),
    MetricDefinition(
        "D05",
        "DELIVER",
        "reliability",
        "Cumplimiento Perfecto del Pedido / POF",
        "(D01_decimal × D02_decimal × D03_decimal × D04_decimal) × 100",
        (),
        "%",
        "dependent_product",
        "higher_is_better",
    ),
    MetricDefinition(
        "D06",
        "DELIVER",
        "responsiveness",
        "Tiempo de Ciclo Total / OFCT",
        "observed_total OR order_lead_time + make_time + delivery_time",
        (
            field("observed_total", "Tiempo total observado", required=False),
            field("order_lead_time", "Lead time del pedido", required=False),
            field("make_time", "Tiempo de preparación", required=False),
            field("delivery_time", "Tiempo de entrega", required=False),
        ),
        "time_unit",
        "exclusive_choice",
        "lower_is_better",
    ),
    ratio(
        "D07",
        "DELIVER",
        "risk",
        "Valor en Riesgo de la Cadena",
        ("registered_logistics_losses_6m", "Pérdidas logísticas registradas"),
        ("revenue_6m", "Ingresos del periodo"),
        direction="lower_is_better",
    ),
    ratio(
        "D08",
        "DELIVER",
        "cost",
        "Costo de Transporte y Distribución",
        ("freight_distribution_cost_6m", "Costo de transporte y distribución"),
        ("transported_units_6m", "Unidades transportadas"),
        factor=1,
        unit="currency/unit",
        direction="lower_is_better",
    ),
    ratio(
        "R01",
        "RETURN",
        "reliability",
        "Tasa de Devoluciones de Clientes",
        ("returned_units_6m", "Unidades devueltas"),
        ("sold_units_6m", "Unidades vendidas"),
        direction="lower_is_better",
    ),
    ratio(
        "R02",
        "RETURN",
        "responsiveness",
        "Tiempo de Procesamiento de Devolución",
        ("return_processing_days_total", "Días acumulados de procesamiento"),
        ("returns_processed_total", "Devoluciones procesadas"),
        factor=1,
        unit="días",
        direction="lower_is_better",
    ),
    ratio(
        "R03",
        "RETURN",
        "asset_management",
        "Tasa de Recuperación de Mermas",
        ("salvaged_or_reconditioned_units_6m", "Unidades recuperadas o reacondicionadas"),
        ("returned_units_6m", "Unidades devueltas"),
    ),
    ratio(
        "R04",
        "RETURN",
        "cost",
        "Costo de Logística Inversa",
        ("reverse_logistics_operating_cost_6m", "Costo operativo de logística inversa"),
        ("returned_units_6m", "Unidades devueltas"),
        factor=1,
        unit="currency/unit",
        direction="lower_is_better",
    ),
)

BY_ID = {metric.id: metric for metric in METRICS}


def catalog() -> list[dict[str, object]]:
    return [metric.as_dict() for metric in METRICS]
