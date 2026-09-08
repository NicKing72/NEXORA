import { encodeEan13 } from "@/lib/ean13";
import type { InventoryProduct } from "@/lib/kardex-types";

function Ean13Barcode({ value }: { value: string }) {
  const bits = encodeEan13(value);
  if (!bits) return <span className="kd-muted">Formato de demo no representable</span>;
  return (
    <svg className="kd-barcode-svg" viewBox="0 0 111 54" role="img" aria-label={`Código EAN-13 ${value}`}>
      <rect width="111" height="54" fill="#fff" />
      {bits.split("").map((bit, index) => bit === "1" ? (
        <rect key={index} x={8 + index} y="5" width="1" height="37" fill="#050707" />
      ) : null)}
      <text x="55.5" y="50" textAnchor="middle" fontSize="7" fontFamily="monospace" fill="#050707">{value}</text>
    </svg>
  );
}

export function DemoBarcodes({ products }: { products: InventoryProduct[] }) {
  const demoProducts = products.filter((product) => product.is_demo && product.barcode_type === "EAN13" && product.barcode);
  if (!demoProducts.length) return null;
  return (
    <section className="kd-panel kd-demo-barcodes">
      <div className="kd-section-head">
        <div><span>Demostración local</span><h2>Códigos escaneables</h2><p>Muestra una tarjeta ante la cámara o ingresa el código con un lector USB. No corresponden a productos comerciales reales.</p></div>
      </div>
      <div className="kd-barcode-grid">
        {demoProducts.map((product) => (
          <article key={product.id}>
            <strong>{product.sku}</strong>
            <span>{product.name}</span>
            <Ean13Barcode value={product.barcode!} />
          </article>
        ))}
      </div>
    </section>
  );
}
