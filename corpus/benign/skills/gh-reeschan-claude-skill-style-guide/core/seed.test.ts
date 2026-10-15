import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { applyOverrides, lerpLevel, LEVELS, toSeedResult, validateEstimate } from "./seed.ts";
import { resolveExplicit, InputError } from "./explicit.ts";
import { ESTIMATE_KEYS } from "./questions.ts";
import { validateSeed } from "./generate-theme.ts";
import type { Brief, Estimate, FontPair } from "./types.ts";

const want = validateSeed(JSON.parse(readFileSync(fileURLToPath(new URL("../examples/seeds/aizome.json", import.meta.url)), "utf8")));
const c = (choice: string, confidence = 0.9, probabilities?: Record<string, number>) => ({
  type: "choice" as const,
  choice,
  confidence,
  probabilities: probabilities ?? { [choice]: confidence },
});
const sc = (score: number, confidence = 0.9) => ({ type: "score" as const, score, confidence });
const mkEst = (): Estimate => ({
  brand_hue: c("blue"),
  neutral_tint: c("warm"),
  accent_scheme: c("complementary"),
  base_mode: c("light"),
  font_mood: c("humanist"),
  shadow: c("soft"),
  use_accent: { type: "noul", noul: 0.8 },
  chroma: sc(2),
  contrast: sc(2),
  radius: sc(1),
  density: sc(2),
  formality: sc(3),
});
const brief: Brief = {
  id: "aizome",
  name: want.name,
  tone: want.tone,
  needsJapanese: true,
  state: { product: "p", audience: "a", mood: ["calm"], references: "", avoid: "" },
  explicit: { brandColor: null, baseMode: null },
};
const pair: FontPair = {
  id: "zen-kaku-gothic-new+noto-sans-jp",
  heading: "Zen Kaku Gothic New",
  body: "Noto Sans JP",
  mono: "JetBrains Mono",
  mood: "humanist",
  japanese: true,
  formality: 2.5,
  description: "d",
  weights: { heading: [500], body: [400] },
};
// 答えの値を型で確かめて取り出す
const scoreAt = (e: Estimate, k: string): number => {
  const a = e[k];
  assert.ok(a?.type === "score", `${k} は score`);
  return a.score;
};
const choiceAt = (e: Estimate, k: string): string => {
  const a = e[k];
  assert.ok(a?.type === "choice", `${k} は choice`);
  return a.choice;
};
const make = (est: Estimate, req: Parameters<typeof resolveExplicit>[0] = { prompt: "x" }) =>
  toSeedResult({ brief, resolved: resolveExplicit(req, brief), estimate: est, fontPair: pair, estimateSource: "jev" });

void test("aizome 相当のシードが一致する", () => {
  const r = make(mkEst());
  assert.equal(r.seed.font.pairId, pair.id);
  const got = structuredClone(r.seed);
  delete got.font.pairId;
  assert.deepStrictEqual(got, want);
});

void test("lerpLevel の補間と範囲外", () => {
  assert.equal(lerpLevel([0, 4, 8, 12, 20], 3.5), 16);
  assert.equal(lerpLevel(LEVELS.radiusPx, 2.5), 10);
  assert.equal(lerpLevel(LEVELS.radiusPx, -1), 0);
  assert.equal(lerpLevel(LEVELS.radiusPx, 9), 20);
});

void test("use_accent 0.3 で accentHue が null", () => {
  const est = mkEst();
  est.use_accent = { type: "noul", noul: 0.3 };
  assert.equal(make(est).seed.color.accentHue, null);
});

void test("brandColor 指定で brand_hue/chroma 無しでも作れる", () => {
  const req = { prompt: "x", brandColor: "#2a4b8d" };
  const resolved = resolveExplicit(req, brief);
  assert.ok(resolved.skip.includes("brand_hue") && resolved.skip.includes("chroma"));
  const est = mkEst();
  delete est.brand_hue;
  delete est.chroma;
  const r = toSeedResult({ brief, resolved, estimate: est, fontPair: pair, estimateSource: "jev" });
  assert.equal(r.sources["color.brandHue"], "explicit");
  assert.equal(r.sources["shape.radiusPx"], "jev");
  assert.equal(r.seed.color.brandHue, resolved.fixed.brandHue);
});

void test("brand_hue 低確度の別案と、明示指定時は別案なし", () => {
  const est = mkEst();
  est.brand_hue = c("blue", 0.3, { blue: 0.4, indigo: 0.35, cyan: 0.15, teal: 0.05 });
  const r = make(est);
  assert.deepStrictEqual(r.alternatives, [
    { field: "brand_hue", value: "indigo", probability: 0.35 },
    { field: "brand_hue", value: "cyan", probability: 0.15 },
  ]);
  const r2 = make(est, { prompt: "x", brandColor: "#2a4b8d" });
  assert.equal(r2.alternatives.filter((a) => a.field === "brand_hue").length, 0);
});

void test("use_accent 0.6 の別案", () => {
  const est = mkEst();
  est.use_accent = { type: "noul", noul: 0.6 };
  const alt = make(est).alternatives.find((a) => a.field === "use_accent");
  assert.equal(alt?.value, "false");
  assert.ok(Math.abs((alt?.probability ?? 0) - 0.4) < 1e-9);
});

void test("validateEstimate: 不足と不正を全部報告し、type を補う", () => {
  const bad: Record<string, unknown> = mkEst();
  delete bad.chroma;
  bad.brand_hue = { choice: "navy", confidence: 0.9, probabilities: {} };
  assert.throws(
    () => validateEstimate(bad, ESTIMATE_KEYS),
    (e: unknown) => {
      return e instanceof InputError && e.message.includes("chroma") && e.message.includes("brand_hue") && e.message.includes("navy");
    },
  );
  const ok: Record<string, unknown> = mkEst();
  ok.extra = 1;
  ok.shadow = { choice: "soft", confidence: 0.8, probabilities: { soft: 0.8 } };
  const v = validateEstimate(ok, ESTIMATE_KEYS);
  assert.equal(v.shadow?.type, "choice");
  assert.equal(v.extra, 1);
});

void test("applyOverrides は元を変えない", () => {
  const est = mkEst();
  const out = applyOverrides(est, { chroma: 4, brand_hue: "red" });
  assert.equal(scoreAt(out, "chroma"), 4);
  assert.equal(choiceAt(out, "brand_hue"), "red");
  assert.equal(scoreAt(est, "chroma"), 2);
  assert.equal(choiceAt(est, "brand_hue"), "blue");
  assert.throws(() => applyOverrides(est, { nope: 1 }), InputError);
});

void test("lowConfidence に radius が入る", () => {
  const est = mkEst();
  est.radius = sc(1, 0.3);
  assert.deepStrictEqual(make(est).lowConfidence, ["radius"]);
});
