# Registro de desarrollo asistido por IA — Kardex

## Objetivo recibido

El prompt inicial solicitó Milestone 10B completo sobre NEXORA v0.14.0: maestro persistente de productos, Kardex cronológico, valorización PEPS/FIFO y promedio ponderado, cámara y lector USB, integración explícita con Inventory 10A, exportación XLSX, demo reproducible, pruebas, documentación y QA local. También prohibió reescribir módulos existentes, inventar stock, usar servicios externos, editar destructivamente movimientos o alterar Forecast Core.

## Rol y contexto técnico

La IA actuó como ingeniero de implementación y auditoría sobre el monorepo existente. Recibió como contexto Next.js/TypeScript, FastAPI/SQLAlchemy/SQLite, contratos de Inventory 10A, reglas de persistencia por UUID y el sistema visual/i18n en español.

## Decisiones de arquitectura

- Se mantuvo Inventory 10A como motor separado y retrocompatible.
- Se modelaron `InventoryProduct`, `KardexMovement` y `KardexAllocation`.
- Se eligió `Decimal` con seis decimales y snapshots posteriores a cada movimiento.
- Se prohibieron movimientos retroactivos; las correcciones se expresan como ajustes.
- FIFO persiste asignaciones; promedio móvil conserva el valor contable proporcional.
- La fuente Kardex requiere elección explícita y compatibilidad exacta con la serie.
- La cámara usa procesamiento local: API nativa primero y ZXing como fallback.
- La exportación XLSX se genera en backend con `openpyxl` ya disponible.

## Trabajo realizado

1. Se verificó `main`, working tree limpio y correspondencia exacta entre HEAD y `v0.14.0`.
2. Se inspeccionaron modelos, servicios, rutas, pruebas, frontend Inventory, navegación, estilos, i18n y configuración.
3. Se ejecutaron 24 pruebas base de Inventory y 25 pruebas frontend antes de modificar.
4. Se añadieron persistencia, servicios contables, API, integración 10A y demo.
5. Se añadió `@zxing/browser` exclusivamente como fallback local de lectura.
6. Se creó la navegación interna y las vistas Resumen, Kardex, Movimientos, Productos y Reabastecimiento.
7. Se agregaron pruebas backend y frontend específicas.

## Problemas y correcciones reales

- El ejecutable `python` no estaba en PATH durante la verificación inicial; se utilizó el intérprete ya existente `.venv\Scripts\python.exe` sin modificar el entorno.
- Las primeras pruebas de movimientos usaban fechas anteriores al saldo inicial creado en tiempo actual y activaron correctamente la protección retroactiva; las fechas de prueba se corrigieron para representar movimientos posteriores.
- La multiplicación de una salida por un promedio ya redondeado podía introducir una deriva de 0.000010. Se corrigió calculando el valor de salida proporcionalmente desde el valor y stock previos, manteniendo `Decimal` y la trazabilidad del promedio.
- Una base SQLite local había creado la tabla de productos antes de incorporarse `forecast_product_reference`; `create_all` no altera tablas existentes. Se añadió una migración aditiva e idempotente que incorpora únicamente esa columna y conserva los datos runtime.
- El primer QA de F5 confirmó la persistencia del movimiento, pero no restauraba el producto visible porque la URL solo conservaba la vista. Se añadió `product_id` explícito y resolución por UUID exacto, sin fallback posicional.
- El servidor de desarrollo cambió automáticamente `next-env.d.ts` hacia tipos de desarrollo. Se restauró su referencia de producción; no forma parte del diseño del milestone.

## Pruebas y verificación

Se añadieron casos para unicidad, barcode, entradas/salidas, stock negativo, ajustes, orden, preview inmutable, promedio móvil, FIFO multicapa/parcial, saldo ausente frente a cero real, resumen, demo repetible, XLSX e integración Kardex → Inventory. En frontend se cubren navegación limpia, handoff 10A, selección exacta tras F5, dirección de movimientos, símbolo EAN-13 y cierre de todos los tracks de cámara.

El QA real validó búsqueda por SKU/barcode, código desconocido, preview y confirmación append-only, promedio ponderado, asignaciones FIFO, regeneración demo, recuperación por UUID después de F5, stock Kardex explícito en preflight de Reabastecimiento y ausencia de overflow global a 1440, 1024, 900 y 720 px. La cámara se abrió únicamente por acción del usuario; el navegador de automatización no expuso un dispositivo/permiso utilizable, por lo que la lectura óptica final debe comprobarse en Chrome o Brave con cámara física. No se observaron errores de consola ni hydration mismatch.
