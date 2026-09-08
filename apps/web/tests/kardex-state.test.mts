import assert from "node:assert/strict";
import test from "node:test";

import { encodeEan13 } from "../lib/ean13.ts";
import { inventoryProductIdFromSearch, inventorySectionFromSearch, isInboundMovement, stopMediaStream } from "../lib/kardex-state.ts";

test("a new Inventory tab starts at the clean summary", () => {
  assert.equal(inventorySectionFromSearch(""), "summary");
});

test("a persisted 10A Inventory Run opens replenishment without changing its UUID", () => {
  assert.equal(inventorySectionFromSearch("inventory_run_id=123e4567-e89b-12d3-a456-426614174000"), "replenishment");
});

test("internal Inventory views are parsed explicitly", () => {
  assert.equal(inventorySectionFromSearch("view=kardex"), "kardex");
  assert.equal(inventorySectionFromSearch("view=movements"), "movements");
  assert.equal(inventorySectionFromSearch("view=unknown"), "summary");
});

test("an exact product selection survives F5 without positional fallback", () => {
  assert.equal(inventoryProductIdFromSearch("view=kardex&product_id=product-2"), "product-2");
  assert.equal(inventoryProductIdFromSearch("view=kardex"), null);
});

test("movement direction controls whether unit cost is requested", () => {
  assert.equal(isInboundMovement("PURCHASE_IN"), true);
  assert.equal(isInboundMovement("POSITIVE_ADJUSTMENT"), true);
  assert.equal(isInboundMovement("SALE_OUT"), false);
  assert.equal(isInboundMovement("NEGATIVE_ADJUSTMENT"), false);
});

test("camera cleanup stops every MediaStream track", () => {
  let stopped = 0;
  const stream = {
    getTracks: () => [{ stop: () => { stopped += 1; } }, { stop: () => { stopped += 1; } }],
  } as unknown as MediaStream;
  stopMediaStream(stream);
  assert.equal(stopped, 2);
  stopMediaStream(null);
});

test("the demo renders a scannable 95-module EAN-13 symbol", () => {
  const encoded = encodeEan13("2000000000015");
  assert.equal(encoded?.length, 95);
  assert.equal(encoded?.startsWith("101"), true);
  assert.equal(encoded?.slice(45, 50), "01010");
  assert.equal(encoded?.endsWith("101"), true);
  assert.equal(encodeEan13("not-an-ean"), null);
});
