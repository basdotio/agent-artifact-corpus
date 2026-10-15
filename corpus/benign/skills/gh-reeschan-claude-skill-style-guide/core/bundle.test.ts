import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { buildBundle, listThemes, readTheme, storeHome, writeBundle } from "./bundle.ts";
import type { BundleInput } from "./bundle.ts";
import { InputError } from "./explicit.ts";
import { loadCatalog } from "./fonts.ts";

const catalog = loadCatalog();
const c = (choice: string, confidence = 0.9) => ({ type: "choice", choice, confidence, probabilities: { [choice]: confidence } });
const sc = (score: number, confidence = 0.9) => ({ type: "score", score, confidence });
const mkEst = (withPair = true): Record<string, unknown> => {
  const e: Record<string, unknown> = {
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
  };
  if (withPair) e.font_pair = c("zen-kaku-gothic-new+noto-sans-jp");
  return e;
};
const brief = {
  id: "aizome",
  name: "藍染",
  tone: "落ち着いた和の藍色。",
  needsJapanese: true,
  state: { product: "p", audience: "a", mood: ["calm"], references: "", avoid: "" },
  explicit: { brandColor: null, baseMode: null },
};
const input = (over: Partial<BundleInput> = {}): BundleInput => ({
  request: { prompt: "和風のSaaS" },
  brief,
  estimate: mkEst(),
  estimateSource: "jev",
  catalog,
  ...over,
});

let tmp = "";
let prevHome: string | undefined;
before(() => {
  prevHome = process.env.STYLE_GUIDE_HOME;
  tmp = mkdtempSync(join(tmpdir(), "sg-bundle-test-"));
  process.env.STYLE_GUIDE_HOME = tmp;
});
after(() => {
  if (prevHome === undefined) delete process.env.STYLE_GUIDE_HOME;
  else process.env.STYLE_GUIDE_HOME = prevHome;
  rmSync(tmp, { recursive: true, force: true });
});

void test("aizome 相当で buildBundle が通る", () => {
  const b = buildBundle(input());
  assert.equal(b.seedResult.seed.font.body, "Noto Sans JP");
  assert.equal(b.fontPair?.id, "zen-kaku-gothic-new+noto-sans-jp");
  assert.equal(Object.keys(b.files).length, 8);
  assert.ok(!b.previewCss.includes("@import"));
});

void test("writeBundle / listThemes / readTheme", () => {
  assert.equal(storeHome(), tmp);
  const b = buildBundle(input());
  const dir = writeBundle(b);
  assert.equal(dir, join(tmp, "themes", "aizome"));
  for (const name of Object.keys(b.files)) assert.ok(existsSync(join(dir, name)), name);
  assert.ok(listThemes().some((t) => t.id === "aizome"));
  assert.deepStrictEqual(readTheme("aizome")?.seedResult, b.seedResult);
  assert.equal(readTheme("../x"), null);
});

void test("font_pair が無く候補が 2 件以上なら InputError", () => {
  assert.throws(
    () => buildBundle(input({ estimate: mkEst(false) })),
    (e: unknown) => e instanceof InputError && /font_pair/.test(e.message),
  );
});

void test("fonts を 3 つ指定すると候補が空で font_pair 無しでも通る", () => {
  const req = { prompt: "x", fonts: { heading: "Zen Kaku Gothic New", body: "Noto Sans JP", mono: "JetBrains Mono" } };
  const b = buildBundle(input({ request: req, estimate: mkEst(false) }));
  assert.deepStrictEqual(b.candidates, []);
  assert.equal(b.fontPair, null);
  assert.equal(b.seedResult.sources["font.heading"], "explicit");
});

void test("カタログに無いフォント名で InputError", () => {
  assert.throws(() => buildBundle(input({ request: { prompt: "x", fonts: { heading: "No Such Font" } } })), InputError);
});

void test("overrides radius=4 で radiusPx 20 かつ explicit", () => {
  const b = buildBundle(input({ overrides: { radius: 4 } }));
  assert.equal(b.seedResult.seed.shape.radiusPx, 20);
  assert.equal(b.seedResult.sources["shape.radiusPx"], "explicit");
});

void test("style-guide.md の中身と決定性", () => {
  const md = buildBundle(input()).files["style-guide.md"];
  assert.ok(md !== undefined, "style-guide.md が無い");
  assert.ok(md.startsWith("# 藍染 スタイルガイド"));
  assert.ok(md.includes("## 色トークン"));
  assert.ok(md.includes("| primary |"));
  assert.equal(buildBundle(input()).files["style-guide.md"], md);
});
