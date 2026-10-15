// style-guide/core/generate-theme.ts
// シード(JSON) → セマンティックトークン(ライト/ダーク) → コントラスト検証・自動補正 → theme.json / theme.css
// 依存なし。実行: node generate-theme.ts seeds/a.json seeds/b.json --out dist
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import type { Seed } from "./types.ts";
import { at, get, isBaseMode, isFontMood, isRecord, isShadowKind } from "./guards.ts";

// ---------------------------------------------------------------------------
// OKLCH ユーティリティ
// ---------------------------------------------------------------------------
type Color = { l: number; c: number; h: number };

function toLinearRgb({ l, c, h }: Color): [number, number, number] {
  const rad = (h * Math.PI) / 180;
  const a = c * Math.cos(rad);
  const b = c * Math.sin(rad);
  const l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s_ = (l - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_,
  ];
}

const inGamut = (col: Color) => toLinearRgb(col).every((v) => v >= -0.0005 && v <= 1.0005);

/** sRGBに収まるまで彩度だけを下げる(明度と色相は保つ) */
function fit(col: Color): Color {
  const l = Math.min(1, Math.max(0, col.l));
  if (inGamut({ ...col, l })) return { ...col, l };
  let lo = 0;
  let hi = col.c;
  for (let i = 0; i < 20; i++) {
    const mid = (lo + hi) / 2;
    if (inGamut({ l, c: mid, h: col.h })) lo = mid;
    else hi = mid;
  }
  return { l, c: lo, h: col.h };
}

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

function luminance(col: Color): number {
  const [r, g, b] = toLinearRgb(col);
  return 0.2126 * clamp01(r) + 0.7152 * clamp01(g) + 0.0722 * clamp01(b);
}

export function contrastRatio(a: Color, b: Color): number {
  const la = luminance(a);
  const lb = luminance(b);
  const hi = Math.max(la, lb);
  const lo = Math.min(la, lb);
  return (hi + 0.05) / (lo + 0.05);
}

const css = (c: Color) => `oklch(${c.l.toFixed(3)} ${c.c.toFixed(3)} ${c.h.toFixed(1)})`;

// ---------------------------------------------------------------------------
// セマンティックトークンの組み立て(命名は shadcn/ui 互換)
// ---------------------------------------------------------------------------
type Mode = "light" | "dark";
type Tokens = Record<string, Color>;

/** 明度0.6付近で彩度が最大になり、明暗の両端で落ちるカーブ */
const chromaFactor = (l: number) => Math.max(0.2, 1 - ((l - 0.6) / 0.5) ** 2);

/** モードごとの明度。fg は contrast 1〜5 に対応する文字色の明度 */
const LIGHTNESS = {
  light: {
    fg: [0.32, 0.28, 0.24, 0.2, 0.16],
    mutedFgOffset: 0.28,
    background: 0.985,
    card: 1,
    muted: 0.955,
    border: 0.9,
    secondary: 0.94,
    primary: 0.55,
    accent: 0.95,
    accentFg: 0.35,
    brandAccent: 0.6,
    destructive: 0.55,
    success: 0.5,
  },
  dark: {
    fg: [0.88, 0.91, 0.94, 0.96, 0.98],
    mutedFgOffset: -0.28,
    background: 0.16,
    card: 0.2,
    muted: 0.25,
    border: 0.3,
    secondary: 0.27,
    primary: 0.7,
    accent: 0.28,
    accentFg: 0.85,
    brandAccent: 0.72,
    destructive: 0.62,
    success: 0.65,
  },
};

function buildTokens(seed: Seed, mode: Mode): Tokens {
  const { brandHue, brandChroma, accentHue, neutralHue, neutralChroma, contrast } = seed.color;
  const n = (l: number) => fit({ l, c: neutralChroma, h: neutralHue });
  const hue = (h: number, l: number, c = brandChroma) => fit({ l, c: c * chromaFactor(l), h });
  const brand = (l: number) => hue(brandHue, l);
  const L = LIGHTNESS[mode];

  // contrast が 1〜5 の外 (検証していない上書きなど) だと表に無い。従来どおり NaN のまま進める
  const fgL = L.fg[Math.round(contrast) - 1] ?? Number.NaN;
  const foreground = n(fgL);
  return {
    background: n(L.background),
    foreground,
    card: n(L.card),
    muted: n(L.muted),
    "muted-foreground": n(fgL + L.mutedFgOffset),
    border: n(L.border),
    input: n(L.border),
    secondary: n(L.secondary),
    primary: brand(L.primary),
    ring: brand(0.62),
    accent: fit({ l: L.accent, c: brandChroma * 0.3, h: brandHue }),
    "accent-foreground": brand(L.accentFg),
    "brand-accent": accentHue === null ? brand(L.primary) : hue(accentHue, L.brandAccent, brandChroma * 0.8),
    destructive: hue(25, L.destructive, 0.2),
    success: hue(150, L.success, 0.15),
    warning: hue(75, 0.75, 0.15),
    "card-foreground": foreground,
    "secondary-foreground": foreground,
  };
}

/** 塗りの上に載せる文字色。明るい色と暗い色のうちコントラストが高いほうを選ぶ */
function onColor(bg: Color, seed: Seed): Color {
  const lightText = fit({ l: 0.985, c: seed.color.neutralChroma, h: seed.color.neutralHue });
  const darkText = fit({ l: 0.18, c: seed.color.neutralChroma, h: seed.color.neutralHue });
  return contrastRatio(lightText, bg) >= contrastRatio(darkText, bg) ? lightText : darkText;
}

// ---------------------------------------------------------------------------
// コントラスト検証と自動補正(WCAG 2.x)
// ---------------------------------------------------------------------------
type Check = { fg: string; bg: string; min: number; ratio: number; adjusted: boolean; pass: boolean };

/** fg の明度を bg から遠ざけて、基準を満たすまで動かす */
function ensure(fg: Color, bg: Color, min: number): { color: Color; adjusted: boolean } {
  if (contrastRatio(fg, bg) >= min) return { color: fg, adjusted: false };
  const dir = luminance(bg) > 0.18 ? -0.01 : 0.01;
  let cur = fg;
  for (let i = 0; i < 100 && contrastRatio(cur, bg) < min; i++) {
    const l = cur.l + dir;
    if (l < 0 || l > 1) break;
    cur = fit({ ...fg, l });
  }
  return { color: cur, adjusted: true };
}

function validate(t: Tokens, seed: Seed): Check[] {
  const textMin = seed.color.contrast >= 4 ? 7 : 4.5; // コントラスト指定が高いテーマはAAA相当
  const checks: Check[] = [];
  const run = (fg: string, bg: string, min: number) => {
    const bgColor = get(t, bg);
    const r = ensure(get(t, fg), bgColor, min);
    t[fg] = r.color;
    const ratio = contrastRatio(r.color, bgColor);
    checks.push({ fg, bg, min, ratio: Math.round(ratio * 100) / 100, adjusted: r.adjusted, pass: ratio >= min });
  };

  // 塗りの色は背景に対して3:1以上(UI部品の基準)。先に確定させてから文字色を選ぶ
  for (const fill of ["primary", "destructive", "ring"]) run(fill, "background", 3);
  for (const fill of ["primary", "destructive", "success", "warning", "brand-accent"]) {
    t[`${fill}-foreground`] = onColor(get(t, fill), seed);
    run(`${fill}-foreground`, fill, 4.5);
  }
  run("foreground", "background", textMin);
  t["card-foreground"] = get(t, "foreground");
  t["secondary-foreground"] = get(t, "foreground");
  run("card-foreground", "card", textMin);
  run("secondary-foreground", "secondary", 4.5);
  run("muted-foreground", "background", 4.5);
  run("muted-foreground", "card", 4.5);
  run("muted-foreground", "muted", 4.5);
  run("accent-foreground", "accent", 4.5);
  return checks;
}

// ---------------------------------------------------------------------------
// 書き出し
// ---------------------------------------------------------------------------
const SHADOW = {
  none: "0 0 #0000",
  soft: "0 4px 16px -4px oklch(0 0 0 / 0.14)",
  hard: "3px 3px 0 0 var(--foreground)",
};

const MODES: readonly Mode[] = ["light", "dark"];

function resolveMode(seed: Seed, mode: Mode): { tokens: Record<string, string>; checks: Check[] } {
  const t = buildTokens(seed, mode);
  const checks = validate(t, seed);
  return { tokens: Object.fromEntries(Object.entries(t).map(([k, v]) => [k, css(v)])), checks };
}

export function resolveTheme(seed: Seed) {
  const modes: Record<Mode, { tokens: Record<string, string>; checks: Check[] }> = {
    light: resolveMode(seed, "light"),
    dark: resolveMode(seed, "dark"),
  };
  return { seed, modes };
}
type Resolved = ReturnType<typeof resolveTheme>;

/** 全テーマ共通。Tailwind v4 のユーティリティ名とCSS変数を結びつける(テーマを増やしても増えない) */
export function baseCss(tokenNames: string[]): string {
  return [
    `@import "tailwindcss";`,
    ``,
    `@theme inline {`,
    ...tokenNames.map((n) => `  --color-${n}: var(--${n});`),
    `  --radius-sm: calc(var(--theme-radius) * 0.5);`,
    `  --radius-md: var(--theme-radius);`,
    `  --radius-lg: calc(var(--theme-radius) * 1.5);`,
    `  --spacing: calc(0.25rem * var(--theme-spacing-scale));`,
    `  --shadow-md: var(--theme-shadow);`,
    `  --font-sans: var(--theme-font-body);`,
    `  --font-heading: var(--theme-font-heading);`,
    `  --font-mono: var(--theme-font-mono);`,
    `}`,
  ].join("\n");
}

export function themeCss({ seed, modes }: Resolved): string {
  const other: Mode = seed.baseMode === "light" ? "dark" : "light";
  const vars = (m: Mode) => Object.entries(modes[m].tokens).map(([k, v]) => `  --${k}: ${v};`);
  const sel = `[data-theme="${seed.id}"]`;
  const generic = seed.font.mood === "serif" || seed.font.mood === "mincho" ? "serif" : "sans-serif";
  return [
    `/* ${seed.name} — ${seed.tone} */`,
    `${sel} {`,
    `  color-scheme: ${seed.baseMode};`,
    ...vars(seed.baseMode),
    `  --theme-radius: ${seed.shape.radiusPx}px;`,
    `  --theme-spacing-scale: ${seed.shape.spacingScale};`,
    `  --theme-shadow: ${SHADOW[seed.shape.shadow]};`,
    `  --theme-font-heading: "${seed.font.heading}", ${generic};`,
    `  --theme-font-body: "${seed.font.body}", ${generic};`,
    `  --theme-font-mono: "${seed.font.mono}", monospace;`,
    `}`,
    `${sel}[data-mode="${other}"] {`,
    `  color-scheme: ${other};`,
    ...vars(other),
    `}`,
  ].join("\n");
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------
/** シード列からテーマ一式を作る。ファイルへの書き出しと表示は呼び出し側が行う */
export function renderThemeFiles(seeds: Seed[]): { css: string; json: string; failed: number; report: string[] } {
  const themes = seeds.map((seed) => resolveTheme(seed));
  const tokenNames = Object.keys(at(themes, 0).modes.light.tokens);

  let failed = 0;
  const report: string[] = [];
  for (const { seed, modes } of themes) {
    for (const mode of MODES) {
      const { checks } = modes[mode];
      const adjusted = checks.filter((c) => c.adjusted);
      const fails = checks.filter((c) => !c.pass);
      failed += fails.length;
      report.push(`${seed.id} / ${mode}: ${checks.length - fails.length}/${checks.length} pass, ${adjusted.length} adjusted`);
      for (const c of adjusted) report.push(`  adjusted  ${c.fg} on ${c.bg} -> ${c.ratio} (min ${c.min})`);
      for (const c of fails) report.push(`  FAIL      ${c.fg} on ${c.bg} = ${c.ratio} (min ${c.min})`);
    }
  }

  return {
    css: [baseCss(tokenNames), ...themes.map(themeCss)].join("\n\n") + "\n",
    json: JSON.stringify(themes, null, 2),
    failed,
    report,
  };
}

const isNumber = (x: unknown): x is number => typeof x === "number";

function isSeedColor(x: unknown): x is Seed["color"] {
  if (!isRecord(x)) return false;
  const { brandHue, brandChroma, accentHue, neutralHue, neutralChroma, contrast } = x;
  return [brandHue, brandChroma, neutralHue, neutralChroma, contrast].every(isNumber) && (accentHue === null || isNumber(accentHue));
}

function isSeedShape(x: unknown): x is Seed["shape"] {
  return isRecord(x) && isNumber(x.radiusPx) && isNumber(x.spacingScale) && isShadowKind(x.shadow);
}

function isSeedFont(x: unknown): x is Seed["font"] {
  if (!isRecord(x) || !isFontMood(x.mood)) return false;
  const names = [x.heading, x.body, x.mono].every((v) => typeof v === "string");
  return names && (x.pairId === undefined || typeof x.pairId === "string");
}

function isSeed(x: unknown): x is Seed {
  return (
    isRecord(x) &&
    [x.id, x.name, x.tone].every((v) => typeof v === "string") &&
    isBaseMode(x.baseMode) &&
    isSeedColor(x.color) &&
    isSeedShape(x.shape) &&
    isSeedFont(x.font)
  );
}

/** JSON から読んだシードを検査する。CLI やテストの入力用 */
export function validateSeed(x: unknown): Seed {
  if (!isSeed(x)) throw new Error("シードの形が不正です");
  return x;
}

function main() {
  const args = process.argv.slice(2);
  const outIdx = args.indexOf("--out");
  const outDir = outIdx >= 0 ? args[outIdx + 1] : "dist";
  const files = args.filter((_, i) => outIdx < 0 || (i !== outIdx && i !== outIdx + 1));
  if (files.length === 0 || outDir === undefined) {
    console.error("usage: node generate-theme.ts <seed.json>... [--out dir]");
    process.exit(1);
  }

  const seeds = files.map((f) => validateSeed(JSON.parse(readFileSync(f, "utf8"))));
  const { css, json, failed, report } = renderThemeFiles(seeds);

  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "theme.json"), json);
  writeFileSync(join(outDir, "theme.css"), css);

  for (const line of report) console.log(line);
  process.exit(failed > 0 ? 1 : 0);
}

if (process.argv[1]?.endsWith("generate-theme.ts")) main();
