// 入力 → 明示指定の確定 → 推定 → フォントの組 → シード → テーマ を 1 つにまとめ、ストアに保存する
import { mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { Brief, Estimate, FontPair, Resolved, SeedResult, ThemeRequest } from "./types.ts";
import { InputError, resolveExplicit, validateBrief, validateRequest } from "./explicit.ts";
import { FIELDS_BY_KEY, applyOverrides, requiredKeys, toSeedResult, validateEstimate } from "./seed.ts";
import { googleFontsUrl, pickFontPair, selectCandidates, validateFixedFonts } from "./fonts.ts";
import { renderThemeFiles, resolveTheme, themeCss } from "./generate-theme.ts";
import { renderStyleGuideMd } from "./style-guide-md.ts";

const ID_RE = /^[a-z][a-z0-9-]*$/;

export function storeHome(): string {
  const env = process.env.STYLE_GUIDE_HOME;
  return env ? env : join(homedir(), ".claude", "style-guide");
}

export type BundleInput = {
  request: unknown;
  brief: unknown;
  estimate: unknown;
  estimateSource: "jev" | "llm-fallback";
  catalog: FontPair[];
  overrides?: Record<string, string | number>;
};

export type Bundle = {
  request: ThemeRequest;
  brief: Brief;
  estimate: Estimate;
  resolved: Resolved;
  candidates: FontPair[];
  fontPair: FontPair | null;
  seedResult: SeedResult;
  theme: ReturnType<typeof resolveTheme>;
  previewCss: string;
  fontsUrl: string;
  files: Record<string, string>;
};

const json = (x: unknown): string => JSON.stringify(x, null, 2) + "\n";

/** 推定の font_pair (あれば) か候補から、フォントの組を 1 つに決める */
function chooseFontPair(catalog: FontPair[], candidates: FontPair[], estimate: Estimate): FontPair {
  const fp = estimate.font_pair;
  let fontPair: FontPair | null;
  if (fp) {
    if (fp.type !== "choice") throw new InputError("font_pair は choice である必要があります");
    fontPair = catalog.find((p) => p.id === fp.choice) ?? null;
    if (!fontPair) throw new InputError(`font_pair "${fp.choice}" はカタログにありません`);
  } else {
    fontPair = pickFontPair(candidates);
  }
  if (!fontPair) throw new InputError(`font_pair が必要です (候補 ${candidates.length} 件)`);
  return fontPair;
}

/** フォントの候補を選び、組を決める。3 つとも明示指定なら選ばない */
function resolveFontPair(
  catalog: FontPair[],
  brief: Brief,
  resolved: Resolved,
  estimate: Estimate,
): { candidates: FontPair[]; fontPair: FontPair | null } {
  if (resolved.skip.includes("font_pair")) return { candidates: [], fontPair: null };
  const mood = estimate.font_mood;
  const formality = estimate.formality;
  if (!mood || mood.type !== "choice") throw new InputError("font_mood が必要です");
  if (!formality || formality.type !== "score") throw new InputError("formality が必要です");
  const candidates = selectCandidates({
    catalog,
    fontMood: mood,
    needsJapanese: brief.needsJapanese,
    fixed: resolved.fixed.fonts,
    formality: formality.score,
  });
  return { candidates, fontPair: chooseFontPair(catalog, candidates, estimate) };
}

export function buildBundle(input: BundleInput): Bundle {
  const { catalog, estimateSource } = input;

  // 1. 明示指定
  const request = validateRequest(input.request);
  const brief = validateBrief(input.brief);
  const resolved = resolveExplicit(request, brief);

  // 2. 固定フォントがカタログにあるか
  const fontProblems = validateFixedFonts(resolved.fixed.fonts, catalog);
  if (fontProblems.length > 0) throw new InputError(fontProblems.join(" / "));

  // 3. 推定
  let estimate = validateEstimate(input.estimate, requiredKeys(resolved.skip));
  if (input.overrides) estimate = applyOverrides(estimate, input.overrides);

  // 4. フォントの組
  const { candidates, fontPair } = resolveFontPair(catalog, brief, resolved, estimate);

  // 5. シード
  const seedResult = toSeedResult({ brief, resolved, estimate, fontPair, estimateSource });
  for (const key of Object.keys(input.overrides ?? {})) {
    for (const field of FIELDS_BY_KEY[key] ?? []) seedResult.sources[field] = "explicit";
  }

  // 6. テーマ
  const seed = seedResult.seed;
  const theme = resolveTheme(seed);
  const previewCss = themeCss(theme);
  const fontsUrl = googleFontsUrl(seed.font, fontPair);

  // 7. ファイル
  const rendered = renderThemeFiles([seed]);
  const files: Record<string, string> = {
    "request.json": json(request),
    "brief.json": json(brief),
    "estimate.json": json(estimate),
    "seed.json": json(seed),
    "seed-result.json": json(seedResult),
    "theme.css": rendered.css,
    "theme.json": rendered.json + "\n",
    "style-guide.md": renderStyleGuideMd({ seedResult, theme, fontPair, fontsUrl }),
  };

  return { request, brief, estimate, resolved, candidates, fontPair, seedResult, theme, previewCss, fontsUrl, files };
}

export function writeBundle(bundle: Bundle, dir?: string): string {
  const out = dir ?? join(storeHome(), "themes", bundle.brief.id);
  mkdirSync(out, { recursive: true });
  for (const [name, content] of Object.entries(bundle.files)) writeFileSync(join(out, name), content, "utf8");
  return out;
}

type ThemeEntry = { id: string; name: string; tone: string; updated: string; ms: number };

/** themes/<id>/seed.json から一覧の 1 行を作る。壊れた seed.json や無いものは null */
function readThemeEntry(root: string, id: string): ThemeEntry | null {
  const file = join(root, id, "seed.json");
  try {
    const seed: unknown = JSON.parse(readFileSync(file, "utf8"));
    if (!seed || typeof seed !== "object") return null;
    const name = "name" in seed ? seed.name : undefined;
    const tone = "tone" in seed ? seed.tone : undefined;
    const st = statSync(file);
    return {
      id,
      name: typeof name === "string" ? name : id,
      tone: typeof tone === "string" ? tone : "",
      updated: st.mtime.toISOString(),
      ms: st.mtimeMs,
    };
  } catch {
    return null;
  }
}

export function listThemes(): { id: string; name: string; tone: string; updated: string }[] {
  const root = join(storeHome(), "themes");
  let names: string[];
  try {
    names = readdirSync(root);
  } catch {
    return [];
  }
  const out: ThemeEntry[] = [];
  for (const id of names) {
    if (!ID_RE.test(id)) continue;
    const entry = readThemeEntry(root, id);
    if (entry) out.push(entry);
  }
  out.sort((a, b) => b.ms - a.ms || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return out.map(({ id, name, tone, updated }) => ({ id, name, tone, updated }));
}

export function readTheme(id: string): { request: unknown; brief: unknown; estimate: unknown; seedResult: unknown } | null {
  if (typeof id !== "string" || !ID_RE.test(id)) return null;
  const dir = join(storeHome(), "themes", id);
  try {
    const read = (name: string): unknown => JSON.parse(readFileSync(join(dir, name), "utf8"));
    return {
      request: read("request.json"),
      brief: read("brief.json"),
      estimate: read("estimate.json"),
      seedResult: read("seed-result.json"),
    };
  } catch {
    return null;
  }
}
