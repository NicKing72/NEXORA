# Explanation Engine

## Alcance

Explanation Engine reconstruye un `ForecastRun` persistido; nunca reentrena, reranquea ni modifica modelos, puntos, intervalos o folds. `ExplanationRun` congela alcance, dataset, Champion, comparación, backtesting, salida futura, limitaciones y capas posteriores. `ExplanationEvidence` conserva siete fragmentos auditables con fuente, ID, metadata y procedencia.

La explicación diferencia pronóstico oficial, contexto, escenario hipotético, diagnóstico SCOR, Portafolio y recomendación. Una asociación histórica no se presenta como causalidad.

## Arquitectura

- `explanation_evidence.py`: valida el Forecast Run y construye el snapshot.
- `model_explanation.py`: catálogo matemático `forecast_model_catalog_v1`.
- `comparison.py`: reproduce ranking, métricas y folds persistidos.
- `forecast_explanation.py`: resume puntos e intervalos sin recalcularlos.
- `decision_context.py`: valida y separa Scenario, SCOR, Portfolio y Decision.
- `service.py`: persiste y recupera Explanation Runs inmutables.

El catálogo cubre exactamente `naive`, `seasonal_naive`, `moving_average`, `ses`, `holt`, `holt_winters_additive` y `holt_winters_multiplicative`. Las fórmulas describen los adaptadores existentes en Forecast Core. Los parámetros se muestran únicamente cuando fueron persistidos.

## Selección, tendencia e intervalos

El orden y Champion proceden de `rank` y `champion_reason`; la explicación no ejecuta un nuevo desempate. WMAPE, MAE, RMSE, MAPE, sMAPE, bias, estabilidad y observaciones se leen del resultado persistido. La proximidad al Champion usa la misma tolerancia histórica de 0.005 WMAPE (0.5 puntos porcentuales), solo como dato explicativo.

La trayectoria futura `forecast_output_trend_v1` compara primer y último punto. Un cambio absoluto menor de 3% es estable; los demás son crecientes o decrecientes. Si el primer valor es cero y no ambos son cero, se declara mixta. Es una descripción, no una causa.

Los intervalos conservan límites y amplitudes de los puntos oficiales. Cuando el método persistido es `pooled_out_of_sample_residual_quantiles`, se describen como intervalos empíricos; no garantizan cobertura futura.

## Seguridad temporal

El corte exige:

```text
forecast.created_at <= explanation_cutoff
forecast.data_cutoff <= explanation_cutoff
forecast.training_cutoff <= explanation_cutoff, cuando existe
source.created_at <= explanation_cutoff
source.available_at/calculated_at/executed_at <= explanation_cutoff
```

Scenario debe pertenecer al Forecast y dataset. SCOR debe ser calculado y compatible. Portfolio debe ser oficial, contener el Forecast y respetar su cutoff. Decision debe referenciar el mismo Forecast. La navegación desde Centro de Decisiones toma las fuentes congeladas del `DecisionRun`, no la procedencia parcial de una recomendación individual. Cuando se envían juntos Decision y Portfolio, el UUID del Portafolio debe coincidir exactamente con el asociado al análisis; nunca se sustituye por otro compatible. Cambios posteriores no alteran una Explanation Run histórica.

El retorno hacia Centro de Decisiones serializa explícitamente `forecast_run_id`, `scenario_run_id`, `scor_assessment_id`, `portfolio_run_id` y `decision_run_id` disponibles en el snapshot. Centro de Decisiones recupera el `DecisionRun` exacto, contrasta los UUID solicitados con sus fuentes congeladas y conserva la URL para que F5 sea determinístico. Una referencia inexistente o incompatible produce un aviso controlado y nunca activa el primer recurso compatible.

Después de resolver satisfactoriamente el preflight, la última URL contextual de Centro de Decisiones se conserva en `sessionStorage`. El sidebar usa ese destino únicamente dentro de la pestaña actual; no propaga parámetros a otras secciones ni restaura el contexto en una sesión nueva. Un acceso directo a `/decision-center` continúa siendo una entrada limpia.

## API

- `GET /api/v1/explanations/definitions`
- `POST /api/v1/explanations/preflight`
- `POST /api/v1/explanations`
- `GET /api/v1/explanations`
- `GET /api/v1/explanations/{id}`
- `GET /api/v1/explanations/{id}/evidence`
- `GET /api/v1/explanations/{id}/models`
- `GET /api/v1/explanations/{id}/backtesting`
- `GET /api/v1/explanations/{id}/forecast`
- `GET /api/v1/explanations/{id}/provenance`

## Limitaciones

La versión histórica de Forecast Core no se inventa si no fue persistida. La serie histórica completa tampoco se reconstruye dentro del snapshot: se conserva metadata de preparación, resultados de folds y puntos futuros oficiales. Explanation Engine no demuestra causalidad, no garantiza resultados, no modifica el forecast y no ejecuta decisiones.

## QA manual

Abra `/model-explain`, seleccione un Forecast Run, genere la explicación y revise Champion, tabla, modelo, cinco folds, puntos, intervalos, procedencia y límites. Recargue con F5 y recupere el mismo ID desde historial. Desde Centro de Decisiones use **Ver explicación del pronóstico** y confirme que Forecast, Scenario, SCOR, Portfolio y Decision permanecen como capas separadas.

## Cierre de Milestone 8A

Milestone 8A quedó validado manualmente junto con sus correcciones de contexto. 8A.1 preserva el Portafolio realmente asociado en el handoff hacia Explanation Engine; 8A.2 reconstruye por UUID exacto Forecast, Scenario, SCOR, Portafolio y Decision al regresar al Centro de Decisiones; y 8A.3 conserva ese workspace únicamente durante la navegación global de la pestaña actual. Se verificaron recuperación histórica y F5 deterministas, roundtrip bidireccional, ausencia de fallback ante UUID inválidos o incompatibles y apertura limpia de `/decision-center` en una pestaña nueva. Los snapshots, la procedencia y las protecciones anti-leakage permanecen inmutables, sin recalcular ni modificar el pronóstico oficial.
