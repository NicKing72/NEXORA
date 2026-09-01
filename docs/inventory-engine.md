# Inventory & Replenishment Engine auditable

## Alcance y arquitectura

El motor consume un `ForecastRun` persistido y, opcionalmente, un `ScenarioRun`, `PortfolioRun` y `DecisionRun` compatibles. Nunca recalcula Forecast Core, modifica fuentes, ejecuta órdenes ni convierte ausencias en cero. La lógica reside en `services/inventory/`: compatibilidad, demanda, cobertura, safety stock, reorder, EOQ, replenishment, riesgo, snapshots y orquestación permanecen separadas.

`InventoryRun` congela UUID, cutoff, fuentes, supuestos, cobertura, warnings y versión. `InventoryItem` conserva inputs, fórmulas sustituidas, resultados, restricciones, evidencia, faltantes y explicación. Los históricos se leen desde ese snapshot aunque cambien después las fuentes.

## Fórmulas versionadas

- Cobertura física: `on_hand / demanda promedio por periodo`.
- Cobertura con tránsito: `(on_hand + in_transit) / promedio`; es una vista separada. El tránsito solo entra a reposición si el usuario lo declara elegible.
- Demanda en lead time: suma de puntos persistidos durante un lead time expresado en la unidad exacta de la frecuencia (`days`, `weeks`, `months`). No hay conversión ambigua.
- Safety stock calculado: `SS = z × σ_period × √lead_time`. Los z-scores soportados son 90%=1.2816, 95%=1.6449, 97.5%=1.96 y 99%=2.3263. `σ_period` se deriva del intervalo 95% persistido. Un valor declarado tiene precedencia y queda marcado como `declared`.
- Punto de reorden: `ROP = demanda durante lead time + safety stock`. Si falta cualquiera, no se calcula; nunca se supone `SS=0`.
- EOQ: `√((2 × D × S) / H)`. `D` se anualiza explícitamente con 365/52/12 periodos. `H` puede ser declarado por unidad/año o derivarse de tasa y costo unitario declarados.
- Necesidad neta: `forecast + safety stock + compromisos + backorders - on_hand - tránsito elegible`. Después se aplican, en orden, MOQ, múltiplo de lote y capacidad. Se conservan cantidad cruda y restringida.

## Riesgo, temporalidad y límites

El riesgo es descriptivo: crítico ante faltante o cobertura inferior al lead time; alto hasta 25% por encima; medio ante exceso superior a la demanda del horizonte; bajo sin esas señales; desconocido sin inventario evaluable. No es una probabilidad.

Todo recurso e input debe estar disponible al cutoff. UUID inexistentes o incompatibles se rechazan sin fallback. Scenario puede ser la trayectoria condicionada; Portfolio y Decision solo aportan procedencia en 10A. No existe integración automática con Decision Engine ni Reporting Engine.

## API y QA

La API versionada expone definiciones, preflight, creación, listado, detalle, items, resumen, evidencia y demo bajo `/api/v1/inventory`. La demo determinística cubre riesgo crítico, inventario suficiente, exceso, EOQ calculable/no calculable, safety stock declarado/calculado, MOQ, tránsito y datos insuficientes sin crear Forecast Runs.

QA manual: abrir `/inventory`, probar demo, seleccionar cada caso y reconstruir fórmulas; crear un análisis real con inputs parciales; verificar que los vacíos siguen ausentes; recargar el `inventory_run_id` y confirmar que Forecast, Scenario, Portfolio, cutoff, supuestos e inputs se restauran por sus valores congelados; abrir una pestaña limpia; y validar 1440, 1024, 900 y 720 px.

## Cierre de Milestone 10A

El QA manual final quedó aprobado el 1 de septiembre de 2026. El caso condicionado verificó forecast 3141.1, coberturas 1.91/2.29, demanda en lead time 442.8, safety stock 60, ROP 502.8, EOQ 583.34 y cantidad limitada a 800. También se confirmó preflight 6/6, persistencia exacta tras F5, pestaña nueva limpia y ausencia de errores de consola o hydration mismatch. Las correcciones 10A.1 y 10A.2 normalizan el estado inicial de Reporting y aseguran que el frontend use la API Inventory actual y prepare el demo mediante UUID compatibles explícitos.
