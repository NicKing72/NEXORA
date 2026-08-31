# Integración SCOR → Decision Engine

## Alcance

Milestone 6B incorpora el Diagnóstico SCOR como una fuente **opcional** de evidencia cuantitativa. No reemplaza las reglas de forecast, contexto, escenario ni disponibilidad de inputs operativos. No ejecuta acciones, optimiza la cadena, altera Forecast Runs ni convierte una brecha frente a una meta en causalidad.

La integración se divide en dos servicios:

- `services/decisions/scor_evidence.py` valida compatibilidad y tiempo, y prepara el snapshot inmutable.
- `services/decisions/scor_support.py` centraliza umbrales, scoring, recomendaciones y refuerzos.

`evidence.py`, `rules.py` y `service.py` solo orquestan estos contratos. Las rutas API y React no recalculan KPI ni duplican reglas SCOR.

## Compatibilidad y seguridad temporal

Un diagnóstico puede seleccionarse cuando coincide exactamente con el `dataset_id` o `forecast_run_id`, o cuando declara alcance de entidad. El demo v0.8.0 conserva compatibilidad mediante su seed fija; nuevos demos declaran el alcance explícitamente.

Para un `decision_cutoff = T` se exige:

1. estado `calculated`;
2. `assessment.cutoff <= T`;
3. `max(created_at, calculated_at) <= T`;
4. `period_end <= T`;
5. inputs con `available_at <= assessment.cutoff`.

Aplicar otro perfil vuelve a calcular el diagnóstico y actualiza `calculated_at`; por ello el nuevo resultado no puede influir retroactivamente. Cada Decision Run persiste el cutoff usado. No se consulta el diagnóstico vivo al recuperar una decisión histórica.

## Snapshot de evidencia

El `source_snapshot.scor` congela identificación, entidad, periodo, perfil de metas, resumen, criticidad, procesos, KPI, resultados, unidades, metas, Gap Score, cobertura, estado de evidencia, versión de cálculo, procedencia, disponibilidad y cutoff de decisión. Cada recomendación guarda además la porción exacta utilizada en `DecisionEvidence` con tipos `scor_metric`, `scor_reinforcement`, `scor_data_quality` o `scor_process_criticality`.

Cambios posteriores de metas, inputs o cálculo no reescriben el snapshot ni el Support Score histórico.

## Reglas y Support Score

La configuración versionada es `decision_scor_support_v1`:

- brecha moderada: `15 / 100`;
- brecha alta: `35 / 100`;
- cobertura mínima del proceso: `0.50`;
- refuerzo máximo sobre soporte legacy: `0.20`.

Para un KPI completo y evaluable:

```text
G = clamp(gap_score / 100, 0, 1)
C = clamp(process_benchmark_coverage, 0, 1)
K = 1.00 si es candidato único; 0.85 si está empatado; 0.70 en otro caso
S_scor = 0.50G + 0.25C + 0.15E + 0.10K
E = 1 únicamente con evidence_status = complete
```

Un KPI incompleto, insuficiente, inválido o no aplicable obtiene `S_scor = 0` como evidencia de brecha. Los no aplicables se excluyen; los demás pueden originar una solicitud separada para completar datos, con soporte deliberadamente inferior a `0.35`.

Solo un KPI con brecha ≥15 y cobertura ≥0.50 genera revisión por brecha. Brecha ≥35 y `S_scor >= 0.65` puede producir prioridad alta. Un empate de procesos se conserva como empate; jamás se elige un ganador artificial.

Cuando una regla legacy es compatible con el proceso, SCOR puede reforzarla:

```text
delta_scor = min(0.20, 0.20 × S_scor)
support_final = min(1, support_legacy + delta_scor)
```

Se persisten soporte base, contribución SCOR, KPI, diagnóstico y versión. Sin `scor_assessment_id`, la lista, soporte, prioridad y orden legacy permanecen exactamente iguales.

## API y UI

`POST /api/v1/decisions/preflight` y `POST /api/v1/decisions` aceptan `scor_assessment_id` opcional y explícito. El preflight devuelve diagnósticos compatibles y el resumen del seleccionado. `GET /api/v1/decisions/recommendations/{id}/scor-evidence` devuelve solo la evidencia SCOR congelada.

Centro de Decisiones muestra selector, cobertura, KPI completos/insuficientes, perfil, candidato o empate, contador y badges de origen. El detalle presenta evidencia auditable y enlaza al diagnóstico original. Diagnóstico SCOR enlaza al Centro de Decisiones con el ID seleccionado.

## Limitaciones

El NEXORA Gap Score no es un score oficial SCOR y las metas demo no son estándares oficiales. Una brecha describe distancia frente a una meta configurada; no identifica causas. La integración no calcula cantidades óptimas, safety stock, EOQ, órdenes, producción, rutas, proveedores ni ejecución logística. Los inputs ausentes permanecen ausentes.

## QA manual 6B

1. Probar Centro de Decisiones sin SCOR y comparar el comportamiento legacy.
2. Seleccionar el diagnóstico principal, generar y revisar recomendaciones originadas/reforzadas.
3. Abrir “Evidencia SCOR utilizada” y comprobar snapshot, versión y navegación.
4. Aplicar el perfil de empate, volver a analizar y confirmar que no se fuerza ganador.
5. Revisar el KPI incompleto y la recomendación de completar evidencia.
6. Cambiar un estado, recargar con F5 y recuperar el análisis desde historial.
