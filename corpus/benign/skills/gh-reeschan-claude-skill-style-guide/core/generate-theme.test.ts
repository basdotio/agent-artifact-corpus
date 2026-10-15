import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { renderThemeFiles, resolveTheme, themeCss, validateSeed } from "./generate-theme.ts";
import { at, isRecord } from "./guards.ts";
import type { Seed } from "./types.ts";

const EXAMPLES = fileURLToPath(new URL("../examples", import.meta.url));
const readSeed = (name: string): Seed => validateSeed(JSON.parse(readFileSync(`${EXAMPLES}/seeds/${name}.json`, "utf8")));

type ExpectedTheme = { seed: Seed; modes: Record<"light" | "dark", { tokens: Record<string, string> }> };

// theme.json のトークン表を検査して取り出す
function toTokens(x: unknown): Record<string, string> {
  if (!isRecord(x)) throw new Error("theme.json の tokens がオブジェクトではない");
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(x)) {
    if (typeof v !== "string") throw new Error(`theme.json の ${k} が文字列ではない`);
    out[k] = v;
  }
  return out;
}

function toExpectedTheme(x: unknown): ExpectedTheme {
  if (!isRecord(x) || !isRecord(x.modes) || !isRecord(x.modes.light) || !isRecord(x.modes.dark)) {
    throw new Error("theme.json のテーマの形が不正");
  }
  return {
    seed: validateSeed(x.seed),
    modes: { light: { tokens: toTokens(x.modes.light.tokens) }, dark: { tokens: toTokens(x.modes.dark.tokens) } },
  };
}

const expectedRaw: unknown = JSON.parse(readFileSync(`${EXAMPLES}/theme.json`, "utf8"));
if (!Array.isArray(expectedRaw)) throw new Error("theme.json が配列ではない");
const expected = expectedRaw.map((t: unknown) => toExpectedTheme(t));
const expectedFor = (id: string) => {
  const hit = expected.find((t) => t.seed.id === id);
  if (!hit) throw new Error(`theme.json に ${id} がない`);
  return hit;
};

const aizome = readSeed("aizome");
const neon = readSeed("neon");
const ACCENT_TOKENS = new Set(["brand-accent", "brand-accent-foreground"]);

void test("aizome / neon: brand-accent 以外のトークンが theme.json と一致する", () => {
  for (const seed of [aizome, neon]) {
    const actual = resolveTheme(seed);
    const exp = expectedFor(seed.id);
    for (const mode of ["light", "dark"] as const) {
      const a = actual.modes[mode].tokens;
      const e = exp.modes[mode].tokens;
      assert.deepEqual(Object.keys(a).sort(), Object.keys(e).sort(), `${seed.id} / ${mode}: トークン名の集合が違う`);
      for (const key of Object.keys(e)) {
        if (ACCENT_TOKENS.has(key)) continue;
        assert.equal(a[key], e[key], `${seed.id} / ${mode} / ${key}`);
      }
    }
  }
});

void test("aizome の brand-accent は元の彩度より低い (約 0.096)", () => {
  const css = themeCss(resolveTheme(aizome));
  const m = css.match(/--brand-accent: oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)/);
  assert.ok(m, "--brand-accent が css に見つからない");
  const chroma = Number(m[2]);
  const originalMatch = expectedFor("aizome").modes.light.tokens["brand-accent"]?.match(/oklch\([\d.]+ ([\d.]+)/);
  assert.ok(originalMatch, "theme.json の brand-accent が読めない");
  const original = Number(originalMatch[1]);
  assert.ok(chroma < original, `彩度 ${chroma} が元の ${original} 以上`);
  assert.ok(Math.abs(chroma - 0.096) < 0.005, `彩度 ${chroma} が 0.096 から離れている`);
});

void test("mood が serif のとき見出しと本文の総称が serif になり、それ以外は sans-serif のまま", () => {
  const serifSeed = { ...aizome, font: { ...aizome.font, mood: "serif" as const } };
  const serifCss = themeCss(resolveTheme(serifSeed));
  assert.ok(serifCss.includes(`--theme-font-heading: "Zen Kaku Gothic New", serif;`));

  const originalCss = themeCss(resolveTheme(aizome));
  assert.ok(originalCss.includes("sans-serif"));
  assert.ok(originalCss.includes(`--theme-font-mono: "JetBrains Mono", monospace;`));
});

void test("renderThemeFiles([aizome, neon]): failed は 0 で、report の 1 行目は aizome / light: で始まる", () => {
  const { failed, report, css, json } = renderThemeFiles([aizome, neon]);
  assert.equal(failed, 0);
  const first = at(report, 0);
  assert.ok(first.startsWith("aizome / light: "), first);
  assert.ok(css.startsWith('@import "tailwindcss";'));
  const parsed: unknown = JSON.parse(json);
  assert.ok(Array.isArray(parsed));
  assert.equal(parsed.length, 2);
});

void test("font.pairId を持つ seed でも例外なく動く", () => {
  const withPair: Seed = { ...aizome, font: { ...aizome.font, pairId: "zen-kaku+noto-sans-jp" } };
  assert.doesNotThrow(() => {
    const { css, failed } = renderThemeFiles([withPair]);
    assert.ok(css.includes("--theme-font-heading"));
    assert.equal(failed, 0);
  });
});
