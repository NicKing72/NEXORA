# Reporting Engine auditable

## Propósito y límites

Reporting Engine convierte resultados ya persistidos de NEXORA en un informe reproducible. No vuelve a entrenar modelos, recalcula Forecast Core, modifica runs de origen, ejecuta recomendaciones ni transforma datos faltantes en cero. El resumen ejecutivo es determinístico y separa hechos, recomendaciones, incertidumbres, faltantes y limitaciones; no utiliza una LLM ni afirma causalidad.

## Arquitectura

La implementación reside en `apps/api/src/nexora_api/services/reports/`:

- `compatibility.py` resuelve UUID explícitos y valida relaciones y cortes.
- `snapshot.py` serializa evidencia persistida sin leer de nuevo la serie ni ejecutar motores.
- `sections.py` construye las doce secciones modulares.
- `executive.py` redacta el resumen determinístico.
- `rendering.py` genera HTML, JSON y CSV desde el snapshot.
- `service.py` coordina preflight, persistencia, historial y demo.

`ReportRun` conserva alcance, fuentes, corte, versión, warnings y el snapshot completo. `ReportSection` conserva orden, contenido, referencias y completitud. Un Report Run histórico siempre se reconstruye desde estos campos congelados.

## Tipos y compatibilidad

El mismo motor configura reportes `integrated`, `forecast`, `decisions`, `scor` y `portfolio`. Forecast es obligatorio para los reportes integrado y de pronóstico; Forecast y Decision lo son para decisiones; SCOR y Portfolio son respectivamente obligatorios en sus reportes específicos. Las demás capas son opcionales.

Las relaciones explícitas tienen prioridad: Scenario, Decision y Explanation deben referenciar el Forecast solicitado; Portfolio debe contenerlo; SCOR debe coincidir por Forecast o dataset; y las capas de una Explanation deben coincidir con su snapshot. Nunca se sustituye un UUID inexistente o incompatible por “el primero disponible”.

## Seguridad temporal y completitud

Toda fuente debe cumplir `created_at <= report_cutoff` y, cuando existe, `available_at <= report_cutoff`. También se validan `data_cutoff`, `executed_at`, `calculated_at`, `decision_cutoff` y los cortes propios aplicables. El preflight no persiste nada.

La cobertura cuenta las seis capas posibles: Forecast, Scenario, SCOR, Portfolio, Decision y Explanation. Se muestra como completa, parcial o insuficiente; es cobertura documental, no probabilidad de corrección. Una fuente ausente permanece “No incluida”.

## API y exportación

- `GET /api/v1/reports/definitions`
- `POST /api/v1/reports/preflight`
- `POST /api/v1/reports`
- `POST /api/v1/reports/demo/regenerate`
- `GET /api/v1/reports`
- `GET /api/v1/reports/{id}`
- `GET /api/v1/reports/{id}/sections`
- `GET /api/v1/reports/{id}/sources`
- `GET /api/v1/reports/{id}/summary`
- `GET /api/v1/reports/{id}/export?format=html|json|csv`

HTML ofrece una vista imprimible; JSON conserva el documento auditable completo; CSV incluye metadata y filas tabulares persistidas de Forecast, SCOR, Portfolio y Decision. Todos identifican el Report Run y su versión.

## Demo, historial y QA

La demo usa un UUID determinístico y un snapshot sintético desacoplado; no crea ni modifica Forecast Runs oficiales. `/reports?report_run_id=<UUID>` recupera exactamente un histórico después de F5. Una pestaña nueva en `/reports` no hereda otro contexto.

QA manual: validar un Forecast solo; crear un integrado con capas compatibles; confirmar warnings por capas ausentes; abrir HTML/JSON/CSV; recargar; reabrir desde historial; comprobar handoffs de ida y vuelta y probar 1440, 1024, 900 y 720 px sin overflow global.

Milestone 9A quedó validado manualmente con las seis capas del reporte demo, exportaciones HTML/JSON/CSV, recuperación exacta por `report_run_id` después de F5, historial pasivo y una nueva pestaña sin selección heredada. El cierre no identificó bloqueadores funcionales.

## Limitaciones actuales

No se genera PDF nativo para evitar una dependencia pesada: la vista HTML puede imprimirse como PDF desde el navegador. El reporte representa snapshots persistidos y no ofrece edición colaborativa, firma digital, programación automática, correo ni almacenamiento cloud.
