# Kardex & Barcode Inventory Traceability Engine

## Arquitectura

Milestone 10B amplía Inventario sin sustituir Inventory Engine 10A. `InventoryProduct` conserva el maestro de SKU; `KardexMovement` es append-only y congela el saldo posterior; `KardexAllocation` registra cada capa de entrada consumida por una salida PEPS/FIFO. La lógica vive en `services/kardex/` y FastAPI es la única fuente de verdad. El frontend solo captura, presenta y solicita previews.

Una corrección histórica se registra mediante ajuste positivo o negativo. Se rechazan movimientos anteriores al último confirmado para evitar revalorizar silenciosamente movimientos posteriores.

## Movimientos y saldo

Entradas: saldo inicial, compra, producción, devolución de cliente, transferencia y ajuste positivo. Salidas: venta, consumo productivo, devolución a proveedor, transferencia y ajuste negativo. Toda cantidad es positiva; el tipo determina su dirección. Una salida que exceda el saldo se rechaza.

Sin movimientos, el saldo es desconocido (`null`), no cero. Un movimiento que agota el inventario sí produce cero real. Cantidades y valores usan `Decimal` con seis decimales internos; la interfaz y XLSX redondean solo para presentación.

## Valorización

Promedio ponderado móvil para una entrada:

`nuevo promedio = (valor anterior + cantidad entrada × costo entrada) / nuevo stock`

Las salidas consumen la proporción valorizada vigente inmediatamente antes del movimiento. PEPS/FIFO consume las capas por fecha, creación e ID estables. Cada asignación congela movimiento de entrada, cantidad, costo y total; no se reconstruye visualmente en el navegador.

## Barcode, cámara y lector USB

El buscador acepta UUID, SKU o barcode y ejecuta la búsqueda al presionar Enter, por lo que funciona con lectores USB que se comportan como teclado. La cámara se activa solamente al pulsar **Escanear código**, solicita `getUserMedia`, prefiere cámara trasera, usa `BarcodeDetector` nativo y recurre localmente a `@zxing/browser`. Al cerrar, detectar un código o desmontar la vista se detienen controles y todos los tracks.

La cámara procesa el código localmente en el navegador y no envía imágenes a servicios externos. No se guardan frames. Un código desconocido nunca crea un producto sin confirmación.

## Integración con Inventory 10A

El análisis de reabastecimiento conserva `manual` como fuente predeterminada. El usuario puede elegir explícitamente `kardex` y un UUID de producto compatible. Backend valida producto/referencia de demanda, ubicación, categoría, `timestamp <= cutoff` y `created_at <= cutoff`. El snapshot congela el movimiento, saldo, valorización y procedencia usados. Una selección Kardex no sobrescribe un stock manual: ambas fuentes simultáneas se rechazan.

## API y exportación

`/api/v1/kardex` expone maestro, lookup, balances, movimientos, preview, resumen, demo y exportación `.xlsx`. El libro contiene hojas **Kardex** y **Resumen** y utiliza exactamente resultados persistidos del backend, sin fórmulas contables alternativas.

## Demo y límites

La demo determinística crea BEB-001 (promedio ponderado), ALI-002 (FIFO) y HOG-003, con EAN-13 de rango interno `200…`. La vista Resumen renderiza tarjetas EAN-13 escaneables localmente para una presentación sin Internet. Restablecerla elimina únicamente recursos marcados `is_demo` y vuelve a usar UUID fijos. BEB-001 conserva una referencia explícita hacia la serie demo NX-101 para probar reabastecimiento sin inferencia por posición.

Este milestone no gestiona lotes físicos, vencimientos, series, multi-moneda, impuestos, reservas concurrentes, compras reales ni optimización automática. Tampoco reabre movimientos confirmados ni altera Forecast Runs.

## QA manual

1. Abra `/inventory`, restablezca el demo y busque `BEB-001` o `2000000000015`.
2. Revise el promedio de 100 @ 10 más 50 @ 12 y la salida de 30.
3. Revise `ALI-002`: la salida de 120 consume 100 @ 8 y 20 @ 9.5.
4. Registre un movimiento, confirme el preview, recargue y verifique que la URL conserva el producto por UUID y recupera el mismo Kardex.
5. Pruebe el campo con teclado/lector USB y luego el escáner de cámara.
6. Exporte el XLSX y abra ambas hojas.
7. Desde BEB-001 abra Reabastecimiento, elija Kardex y valide la procedencia del saldo.
