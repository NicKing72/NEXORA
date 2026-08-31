# Integración Portafolio → Decision Engine

## Alcance

Milestone 7B incorpora un `PortfolioRun` oficial como fuente **opcional** de evidencia para Decision Engine. La integración prioriza revisiones: no calcula compras, inventario óptimo, transferencias, EOQ, safety stock ni ejecución logística. El Priority Score de NEXORA es descriptivo y no representa una probabilidad de ruptura.

La lógica queda separada en `services/decisions/portfolio_evidence.py`, que valida compatibilidad y congela evidencia, y `portfolio_support.py`, que centraliza fórmula, umbrales, recomendaciones y refuerzos. Forecast Core, Series Engine y Portfolio Engine no se recalculan.

## Compatibilidad y anti-leakage

Un Portafolio es elegible si es oficial, pertenece al mismo dataset, contiene exactamente el `forecast_run_id`, frecuencia, horizonte y dimensiones de la serie, y cumple:

```text
created_at <= decision_cutoff
available_at <= decision_cutoff
portfolio.cutoff <= decision_cutoff
```

Los demos desacoplados no pueden mezclarse con decisiones reales. El `source_snapshot.portfolio` congela cabecera, ranking completo, inputs operativos, faltantes, cobertura, riesgo, score, versión y procedencia. Cambios o nuevos runs posteriores no alteran decisiones históricas.

## Support Score versionado

La versión es `decision_portfolio_support_v1`. Para la posición del forecast seleccionado:

```text
P = clamp(priority_score / 100, 0, 1)
R = 1.00 crítico; 0.80 alto; 0.50 medio; 0.25 bajo; 0 desconocido
C = 1.00 score completo; 0.60 score parcial
D = proporción disponible entre inventario actual, en tránsito, stock de seguridad y lead time
K = max(0.40, 1 - 0.10 × (rank - 1))
S_portfolio = 0.40P + 0.25R + 0.15C + 0.10D + 0.10K
```

Los umbrales centralizados son: posición prioritaria `rank <= 3`, variabilidad material `>= 0.25` y refuerzo máximo `0.20`. Una cobertura crítica/alta puede originar revisión. Datos faltantes originan una solicitud de completar evidencia y nunca se convierten en cero. La variabilidad solo origina revisión cuando el score es completo.

Las reglas legacy compatibles pueden reforzarse:

```text
delta_portfolio = min(0.20, 0.20 × S_portfolio)
support_final = min(1, support_previo + delta_portfolio)
```

Solo riesgo crítico/alto con score completo puede elevar un nivel la prioridad. Se persisten soporte previo, contribución, regla y posición. El orden es: reglas legacy → SCOR opcional → Portafolio opcional → ranking estable. Sin Portafolio, la semántica legacy permanece intacta.

## API, UI y persistencia

`POST /api/v1/decisions/preflight` y `POST /api/v1/decisions` aceptan `portfolio_run_id`. El preflight lista únicamente Portafolios compatibles y muestra el seleccionado. `GET /api/v1/decisions/recommendations/{id}/portfolio-evidence` devuelve solo evidencia congelada de Portafolio.

Centro de Decisiones muestra selector, resumen de posición/riesgo/cobertura, contador y badges para recomendaciones originadas, reforzadas o que solicitan datos. El detalle enlaza al Portafolio. Desde un Portfolio Run oficial puede abrirse Centro de Decisiones conservando `forecast_run_id` y `portfolio_run_id` exactos.

El handoff resuelve el Portfolio exclusivamente por UUID dentro de los runs compatibles con el Forecast solicitado; nunca infiere por etiqueta, posición ni orden de respuesta. Un UUID inexistente o incompatible mantiene **Sin evidencia de Portafolio**, expone un aviso controlado y no selecciona otro run como fallback. La selección manual sincroniza ambos IDs en la URL, de modo que una recarga F5 reconstruye exactamente la misma selección y su snapshot histórico.

## Limitaciones y QA

La integración no demuestra causalidad, no usa datos posteriores al corte y no ejecuta operaciones. Una posición alta solo ordena atención relativa. Cobertura no calculable permanece como tal.

Para QA: crear dos Portafolios oficiales compatibles; abrir **Analizar en Centro de Decisiones** y comprobar que se selecciona el UUID solicitado, independientemente del orden; probar UUID inexistente, incompatible y ausencia de UUID sin fallback; realizar una selección manual y recargar con F5; verificar snapshot y navegación inversa; generar con y sin Portafolio y combinar opcionalmente Scenario y SCOR; confirmar que Forecast/Portfolio permanecen intactos.
