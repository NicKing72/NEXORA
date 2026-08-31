# Decision Engine

## Alcance y arquitectura

Decision Engine es una capa de apoyo, no de ejecución. Consume snapshots inmutables de un `ForecastRun` completado, su Champion, puntos e intervalos; opcionalmente incorpora un `ScenarioRun` y un diagnóstico SCOR compatible; y consulta señales e impactos contextuales disponibles al corte. La lógica vive en `services/decisions/`: `evidence.py` prepara evidencia temporalmente segura, `scor_evidence.py` aísla el contrato SCOR, `scor_support.py` aplica scoring versionado, `rules.py` genera candidatos, `ranking.py` los ordena, `catalog.py` define acciones y `service.py` orquesta persistencia y lifecycle. Las rutas permanecen delgadas.

El flujo conserva las categorías semánticas: hechos observados, pronóstico oficial, evidencia contextual, escenario hipotético y recomendación. Ninguna ejecución escribe sobre Forecast Core, Context Engine o Scenario Engine.

## Reglas y metodología

Las reglas `decision_rules_v1` son determinísticas:

- La trayectoria del forecast compara primer y último punto: menos de 3% mantiene el plan; 3–10% activa investigación leve; desde 10% prioriza preparación o investigación.
- El ancho medio relativo del intervalo 95% genera monitoreo desde 25% y revisión manual desde 50%.
- Un escenario con delta absoluto desde 3% se revisa; desde 10% recibe prioridad alta y desde 25%, crítica. Sigue marcado como hipotético.
- Una restricción de disponibilidad genera revisión de ruptura de stock. No estima ventas perdidas ni la interpreta como menor demanda causal.
- Los impactos contextuales solo orientan la revisión. El score 0–100 de Context Impact se normaliza a 0–1 antes de combinarlo con la confianza de la señal.
- Una señal sin impacto o analogía evaluable solo produce monitoreo.
- Siempre se declara la falta de inventario actual, lead time, MOQ, costos y nivel de servicio; por eso nunca se calcula una cantidad óptima.
- SCOR es opcional. KPI completos con brecha ≥15/100 y cobertura de proceso ≥50% pueden añadir revisiones o reforzar reglas compatibles. KPI incompletos, insuficientes o no aplicables nunca se usan como resultados válidos. La fórmula completa está en `docs/scor-decision-integration.md`.

El soporte queda entre 0 y 1. Su nivel es `insufficient` (<0.35), `low` (0.35–0.59), `moderate` (0.60–0.79) o `high` (≥0.80). El ranking ordena prioridad (`critical`, `high`, `medium`, `low`), soporte descendente, orden estable del catálogo y clave estable. Así los empates son reproducibles.

## Seguridad temporal y procedencia

`decision_cutoff` limita todas las fuentes. Un Forecast Run o Scenario Run creado/ejecutado después del corte se rechaza. Solo se incluyen señales con `available_at <= decision_cutoff`. Un impacto exige `estimated_at <= decision_cutoff` y un `data_cutoff` que no exceda el corte de datos del forecast. Las analogías se reconstruyen con las mismas reglas de alcance y disponibilidad. SCOR exige diagnóstico calculado, periodo no posterior al corte y `max(created_at, calculated_at) <= decision_cutoff`; sus inputs ya fueron bloqueados si no estaban disponibles al cutoff del diagnóstico.

Cada recomendación persiste forecast, escenario opcional, señales, impactos, cutoff, regla, soporte, limitaciones y snapshots de evidencia. Su lifecycle es `open`, `acknowledged`, `under_review`, `dismissed` o `resolved`; cada transición genera un `DecisionAudit`. Descartar no elimina registros.

## Persistencia y API

SQLite conserva `DecisionRun`, `DecisionRecommendation`, `DecisionEvidence` y `DecisionAudit`. Un run guarda el snapshot fuente y un resumen; la evidencia de cada recomendación permite reconstruir por qué apareció.

- `POST /api/v1/decisions/preflight`
- `POST /api/v1/decisions`
- `GET /api/v1/decisions`
- `GET /api/v1/decisions/{run_id}`
- `GET /api/v1/decisions/{run_id}/recommendations`
- `GET /api/v1/decisions/{run_id}/compare`
- `GET /api/v1/decisions/recommendations/{id}`
- `GET /api/v1/decisions/recommendations/{id}/evidence`
- `GET /api/v1/decisions/recommendations/{id}/scor-evidence`
- `PATCH /api/v1/decisions/recommendations/{id}/status`

## Limitaciones

No hay ejecución automática, optimización de inventario, cantidades de compra, causalidad, ML, LLM ni fuentes externas. El escenario no sustituye el forecast oficial. Las asociaciones contextuales y brechas SCOR no prueban causas. Las recomendaciones dependen de la cobertura, incertidumbre y fuentes disponibles al corte. El Gap Score es interno de NEXORA, no oficial SCOR.

## QA manual

1. Complete un Forecast Run y, opcionalmente, un escenario.
2. Abra `/decision-center`, elija el forecast, cutoff y escenario.
3. Revise el preflight y genere el análisis.
4. Confirme prioridad, evidencia, limitaciones y comparación oficial vs condicionada.
5. Cambie un estado, recargue con F5 y recupere el run desde el historial.
6. Verifique que Forecast Lab y Scenario Lab conservan sus valores originales.

### Cierre de Milestone 5B

El QA manual de Milestone 5B fue aprobado el 30 de agosto de 2026. Se confirmó que un análisis puede recuperarse después de F5 desde **Análisis anteriores**, que la recomendación **Revisar el plan promocional** conserva el estado **Reconocida** y que su evidencia, soporte, procedencia y explicación permanecen intactos. El historial mantiene como ejecuciones auditables independientes el análisis sobre baseline oficial de 9 recomendaciones y el análisis condicionado por escenario de 12 recomendaciones; ninguno sustituye ni modifica el Forecast Run oficial.
