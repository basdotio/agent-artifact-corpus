import test from "node:test";
import assert from "node:assert/strict";
import { hexToOklch, resolveExplicit, validateRequest, validateBrief, InputError } from "./explicit.ts";
import type { Brief } from "./types.ts";

const brief = (explicit: Brief["explicit"]): Brief => ({
  id: "aizome",
  name: "藍染",
  tone: "静かで落ち着いた印象。",
  needsJapanese: true,
  state: { product: "p", audience: "a", mood: ["calm"], references: "", avoid: "" },
  explicit,
});

void test("hexToOklch", () => {
  const b = hexToOklch("#0000ff");
  assert.ok(Math.abs(b.l - 0.452) <= 0.002);
  assert.ok(Math.abs(b.c - 0.313) <= 0.002);
  assert.ok(Math.abs(b.h - 264.05) <= 0.1);
  const w = hexToOklch("#FFFFFF");
  assert.ok(Math.abs(w.l - 1) <= 0.002);
  assert.ok(w.c < 0.0001);
  assert.equal(w.h, 0);
});

void test("brandColor の解決", () => {
  const r = resolveExplicit({ prompt: "x", brandColor: "#1e40af" }, null);
  assert.deepEqual(r.skip, ["brand_hue", "chroma"]);
  assert.equal(r.sources["color.brandHue"], "explicit");
  assert.ok(typeof r.fixed.brandHue === "number");
  const g = resolveExplicit({ prompt: "x", brandColor: "#808080" }, null);
  assert.deepEqual(g.skip, ["chroma"]);
  assert.equal(g.fixed.brandChroma, 0.04);
  assert.equal(g.fixed.brandHue, undefined);
});

void test("baseMode は request が brief より優先", () => {
  const b = brief({ brandColor: null, baseMode: "dark" });
  assert.equal(resolveExplicit({ prompt: "x", baseMode: "light" }, b).fixed.baseMode, "light");
  const r = resolveExplicit({ prompt: "x" }, b);
  assert.equal(r.fixed.baseMode, "dark");
  assert.deepEqual(r.skip, ["base_mode"]);
  assert.equal(r.sources.baseMode, "explicit");
});

void test("fonts 3 つで font_pair を省く", () => {
  const three = resolveExplicit({ prompt: "x", fonts: { heading: "A", body: "B", mono: "C" } }, null);
  assert.deepEqual(three.skip, ["font_pair"]);
  assert.equal(three.sources["font.mono"], "explicit");
  const two = resolveExplicit({ prompt: "x", fonts: { heading: "A", body: "B" } }, null);
  assert.deepEqual(two.skip, []);
  assert.deepEqual(two.fixed.fonts, { heading: "A", body: "B" });
});

void test("validateRequest の不正", () => {
  assert.throws(() => validateRequest({ prompt: "" }), InputError);
  assert.throws(() => validateRequest({ prompt: "a".repeat(2001) }), InputError);
  assert.throws(() => validateRequest({ prompt: "x", brandColor: "#12345" }), InputError);
  assert.deepEqual(validateRequest({ prompt: " x ", extra: 1 }), { prompt: "x" });
});

void test("validateBrief", () => {
  const ok = brief({ brandColor: "#1e40af", baseMode: null });
  assert.deepEqual(validateBrief(ok), ok);
  assert.throws(() => validateBrief({ ...ok, id: "Aizome" }), InputError);
});
