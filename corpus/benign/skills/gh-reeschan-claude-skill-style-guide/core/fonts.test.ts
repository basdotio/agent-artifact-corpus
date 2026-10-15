import { test } from "node:test";
import assert from "node:assert/strict";
import type { ChoiceAnswer, FontPair } from "./types.ts";
import { InputError } from "./explicit.ts";
import { at, get } from "./guards.ts";
import { loadCatalog, validateCatalog, selectCandidates, fontQuestion, pickFontPair, googleFontsUrl, validateFixedFonts } from "./fonts.ts";

function fp(id: string, mood: FontPair["mood"], japanese: boolean, formality: number, heading = "H " + id, body = "B " + id): FontPair {
  return {
    id,
    heading,
    body,
    mono: "JetBrains Mono",
    mood,
    japanese,
    formality,
    description: "d " + id,
    weights: { heading: [400, 700], body: [400, 700] },
  };
}
const cat: FontPair[] = [
  fp("a+a", "serif", false, 1),
  fp("b+b", "serif", false, 4),
  fp("c+c", "mincho", true, 3),
  fp("d+d", "geometric", true, 2),
  fp("e+e", "geometric", false, 0, "Shared Head"),
  fp("f+f", "tech", false, 2),
];
const ans = (choice: string, confidence: number, probabilities: Record<string, number> = { [choice]: confidence }): ChoiceAnswer => ({
  type: "choice",
  choice,
  confidence,
  probabilities,
});
const sel = (o: Partial<Parameters<typeof selectCandidates>[0]>) =>
  selectCandidates({ catalog: cat, fontMood: ans("serif", 0.9), needsJapanese: false, fixed: {}, formality: 2, ...o });

void test("1 loadCatalog reads real catalog", () => {
  assert.ok(loadCatalog().length >= 40);
});
void test("2 validateCatalog reports duplicate id and bad mood", () => {
  const bad = [fp("a+a", "serif", false, 1), fp("a+a", "serif", false, 1), { ...fp("z+z", "serif", false, 1), mood: "weird" }];
  assert.throws(
    () => validateCatalog(bad),
    (e: Error) => e instanceof InputError && /重複/.test(e.message) && /mood/.test(e.message),
  );
});
void test("3 mood selection and second mood on low confidence", () => {
  assert.deepEqual(
    sel({})
      .map((p) => p.id)
      .sort(),
    ["a+a", "b+b"],
  );
  const r = sel({ fontMood: ans("serif", 0.4, { serif: 0.4, mincho: 0.3, tech: 0.1 }) });
  assert.deepEqual(r.map((p) => p.id).sort(), ["a+a", "b+b", "c+c"]);
});
void test("4 needsJapanese", () => {
  const r = sel({ needsJapanese: true, fontMood: ans("geometric", 0.9) });
  assert.deepEqual(
    r.map((p) => p.id),
    ["d+d"],
  );
});
void test("5 formality ordering and maxCount", () => {
  const r = sel({ formality: 4, maxCount: 2 });
  assert.equal(r.length, 2);
  assert.equal(at(r, 0).id, "b+b");
});
void test("6 fixed heading narrows, falls back without mood", () => {
  assert.deepEqual(
    sel({ fixed: { heading: "H b+b" } }).map((p) => p.id),
    ["b+b"],
  );
  assert.deepEqual(
    sel({ fixed: { heading: "Shared Head" } }).map((p) => p.id),
    ["e+e"],
  );
});
void test("7 fontQuestion keys follow candidate order", () => {
  const q = fontQuestion([at(cat, 2), at(cat, 0), at(cat, 1)]);
  const fq = get(q, "font_pair");
  assert.deepEqual(Object.keys(fq.criteria), ["c+c", "a+a", "b+b"]);
  assert.equal(fq.type, "choice");
});
void test("8 pickFontPair", () => {
  assert.equal(pickFontPair([at(cat, 0)]), at(cat, 0));
  assert.equal(pickFontPair([at(cat, 0), at(cat, 1)], ans("b+b", 0.9)), at(cat, 1));
  assert.equal(pickFontPair([at(cat, 0), at(cat, 1)], ans("zzz", 0.9)), null);
  assert.equal(pickFontPair([at(cat, 0), at(cat, 1)]), null);
});
void test("9 googleFontsUrl", () => {
  const pair = { ...at(cat, 0), weights: { heading: [500, 700], body: [400, 700] } };
  assert.equal(
    googleFontsUrl({ heading: "Zen Kaku Gothic New", body: "Noto Sans JP", mono: "JetBrains Mono" }, pair),
    "https://fonts.googleapis.com/css2?family=Zen+Kaku+Gothic+New:wght@500;700&family=Noto+Sans+JP:wght@400;700&family=JetBrains+Mono:wght@400&display=swap",
  );
  assert.equal(
    googleFontsUrl({ heading: "Inter", body: "Inter", mono: "JetBrains Mono" }),
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono:wght@400&display=swap",
  );
});
void test("10 validateFixedFonts", () => {
  const r = validateFixedFonts({ heading: "Comic Sans MS" }, cat);
  assert.equal(r.length, 1);
  assert.equal(at(r, 0), "heading のフォント Comic Sans MS はカタログにありません");
  assert.deepEqual(validateFixedFonts({ heading: "H a+a" }, cat), []);
});
