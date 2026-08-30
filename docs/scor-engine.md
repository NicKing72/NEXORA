# SCOR Diagnostic Engine

## Propósito y límites

Milestone 6A convierte acumulados logísticos en evidencia cuantitativa auditable para `PLAN`, `SOURCE`, `MAKE`, `DELIVER` y `RETURN`. Calcula indicadores y, solo cuando existe un perfil explícito de metas con cobertura suficiente, identifica un **eslabón crítico candidato**. No optimiza compras, inventarios, producción, transporte ni almacenes; tampoco ejecuta decisiones, afirma causalidad o altera el pronóstico oficial.

El **NEXORA Gap Score** es una metodología propia de distancia a metas configuradas. No es un score oficial del modelo SCOR y las metas demo no son benchmarks oficiales.

## Arquitectura

- `definitions.py`: catálogo versionado, procesos, atributos, inputs, fórmulas, unidades y dirección deseada.
- `validation.py`: seguridad numérica, temporal, de unidades y evidencia.
- `calculator.py`: cálculo reconstruible desde inputs brutos.
- `benchmarking.py`: evaluación opcional contra metas.
- `criticality.py`: cobertura, score ponderado por proceso y empate explícito.
- `service.py`: orquestación, persistencia, anti-leakage y serialización.
- `demo.py`: assessment y perfiles demo idempotentes con UUID estables.

Las rutas FastAPI son delgadas y los contratos se validan con Pydantic. SQLite persiste `ScorAssessmentRun`, `ScorMetricInput`, `ScorMetricResult`, `ScorProcessResult`, `ScorBenchmarkProfile`, `ScorBenchmarkTarget` y `ScorAudit`.

## Catálogo y fórmulas

| Proceso | KPI |
|---|---|
| PLAN | P01 precisión; P02 cobertura; P03 cash-to-cash; P04 costo de planificación |
| SOURCE | S01 entregas a tiempo; S02 defectos; S03 lead time; S04 adaptabilidad declarada; S05 costo |
| MAKE | M01 cumplimiento; M02 ciclo; M03 capacidad; M04 ROFA; M05 mantenimiento de inventario |
| DELIVER | D01 a tiempo; D02 completas; D03 sin daños; D04 facturación; D05 POF; D06 OFCT; D07 pérdidas/ingresos; D08 costo por unidad |
| RETURN | R01 devoluciones; R02 procesamiento; R03 recuperación; R04 costo por unidad |

Las fórmulas exactas y el schema de cada input se exponen en `GET /api/v1/scor/definitions`. Las razones matemáticas conservan numerador, denominador, ratio decimal cuando aplica, fórmula sustituida, unidad y versión del motor.

### Regla semestral

Cuando se suministran seis observaciones mensuales para un ratio, se calcula:

```text
sum(numeradores) / sum(denominadores)
```

Nunca se promedian porcentajes mensuales. Deben existir exactamente seis meses completos; no se imputan meses ausentes.

POF multiplica D01–D04 expresados como decimales y no usa un promedio. OFCT acepta exclusivamente un total observado o la suma declarada de componentes. ROFA conserva beneficio, activos, ratio decimal y porcentaje. Los resultados calculados pueden superar 100%; solo los inputs declarados como porcentaje directo se validan en 0–100.

## Estados de evidencia

- `complete`: todos los inputs y unidades requeridos son válidos.
- `incomplete`: falta un input o metadata imprescindible.
- `insufficient_evidence`: el denominador es cero u otra limitación impide calcular.
- `invalid`: tipo, rango, signo, fecha o unidad incompatible.
- `not_applicable`: el usuario declaró explícitamente que no aplica.

Ausente nunca significa cero. No se generan `NaN` o infinito, no se capan resultados y no se convierten unidades silenciosamente.

## Benchmarking y NEXORA Gap Score

Los perfiles aceptan metas empresariales, SLA contractuales, históricos internos, definiciones manuales o demo. Cada target registra dirección, peso, fuente y notas.

- `higher_is_better`: `max(0, (target - value) / |target| × 100)`.
- `lower_is_better`: `max(0, (value - target) / |target| × 100)`; un target cero usa regla explícita 0/100.
- `target_range`: distancia al límite más cercano dividida entre la amplitud del rango.

El resultado se limita a 0–100 para comparar brechas, no para alterar el KPI bruto. El score de proceso es el promedio ponderado de métricas completas con target y peso válidos. Se publica cobertura de datos, cobertura de benchmark, contribuyentes y confianza.

Un eslabón crítico candidato requiere perfil activo, cobertura mínima por proceso y al menos dos procesos comparables. Gana la mayor brecha ponderada. Scores exactamente iguales producen un empate persistido; no existe desempate artificial. Sin evidencia suficiente, el motor no selecciona proceso.

## Procedencia, cutoff y forecasting

Cada input registra fuente, metadata, procedencia, `available_at` y fecha de creación. El assessment registra periodo, cutoff, dataset opcional y versión. Un dato con `available_at > cutoff` se rechaza.

La relación con `ForecastRun` es opcional y de solo lectura. Requiere run completado, dataset compatible, forecast originado antes del periodo evaluado, disponibilidad anterior al cutoff y cobertura completa del periodo. SCOR no reentrena modelos ni modifica puntos, Champion, folds, métricas o intervalos.

## API

```text
GET  /api/v1/scor/definitions
GET  /api/v1/scor/assessments
POST /api/v1/scor/assessments
GET  /api/v1/scor/assessments/{id}
POST /api/v1/scor/assessments/{id}/calculate
GET  /api/v1/scor/assessments/{id}/metrics
GET  /api/v1/scor/assessments/{id}/processes
GET  /api/v1/scor/assessments/{id}/criticality
GET  /api/v1/scor/benchmark-profiles
POST /api/v1/scor/benchmark-profiles
GET  /api/v1/scor/benchmark-profiles/{id}
POST /api/v1/scor/assessments/{id}/benchmark
POST /api/v1/scor/demo/regenerate
```

## Demo y entrada empresarial

**Regenerar demo** recrea de forma determinística un semestre, un assessment y dos perfiles: metas internas sintéticas y empate controlado. Incluye valores normales, datos faltantes, denominador cero, un KPI no aplicable, POF, targets y criticidad. Repetir la acción conserva los UUID y resultados.

**Nuevo diagnóstico** solicita inputs brutos acumulados, nunca porcentajes finales cuando existe una fórmula. Los campos vacíos permanecen ausentes. Una futura importación puede usar el mismo contrato tabular: `metric_id`, inputs del catálogo, unidad/moneda, fuente, periodo y `available_at`.

## Limitaciones actuales

No incluye EOQ, safety stock, cantidades óptimas, emisión de órdenes, rutas, vehículos, control de máquinas, modificación de inventario, ML nuevo, LLM, scraping, APIs externas ni automatización. La asociación con Forecast Run no deriva automáticamente P01 todavía: sus acumulados pueden ingresarse manualmente después de validar la asociación. Decision Engine no consume el diagnóstico en 6A.

## Cierre de Milestone 6A

La QA manual aprobó el flujo completo de `/scor-diagnostic`: 26 KPI en los cinco procesos, reconstrucción numérica de P01, detalle auditable, estados incompleto/insuficiente/no aplicable, criticidad DELIVER con el perfil principal, empate explícito sin ganador forzado, persistencia tras F5 y entrada manual basada en datos brutos. También se verificaron el comportamiento responsive y la regla visible de que los campos vacíos permanecen ausentes. El alcance cerrado sigue siendo diagnóstico cuantitativo; no incorpora optimización ni ejecución automática.
