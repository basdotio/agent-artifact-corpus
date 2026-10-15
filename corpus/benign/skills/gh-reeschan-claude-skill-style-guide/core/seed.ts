import type { Alternative, Answer, Brief, Estimate, Fixed, FontPair, Question, Resolved, Seed, SeedResult, Source } from "./types.ts";
import { ESTIMATE_KEYS, ESTIMATE_QUESTIONS, HUES, THRESHOLDS } from "./questions.ts";
import { InputError } from "./explicit.ts";
import { at, isBaseMode, isFontMood, isRecord, isShadowKind, lookup } from "./guards.ts";

export const LEVELS = {
  brandChroma: [0.04, 0.08, 0.12, 0.16, 0.2],
  radiusPx: [0, 4, 8, 12, 20],
  spacingScale: [0.85, 0.92, 1.0, 1.1, 1.2],
};
export const ACCENT_OFFSET = { analogous: 30, complementary: 180, triadic: 120 };

// 質問のキー → その答えで決まるシードの項目 (sources のキー)
export const FIELDS_BY_KEY: Record<string, string[]> = {
  brand_hue: ["color.brandHue"],
  chroma: ["color.brandChroma"],
  neutral_tint: ["color.neutralHue", "color.neutralChroma"],
  accent_scheme: ["color.accentHue"],
  use_accent: ["color.accentHue"],
  contrast: ["color.contrast"],
  radius: ["shape.radiusPx"],
  density: ["shape.spacingScale"],
  shadow: ["shape.shadow"],
  base_mode: ["baseMode"],
  font_mood: ["font.mood"],
  font_pair: ["font.heading", "font.body", "font.mono"],
};

const round3 = (x: number): number => Math.round(x * 1000) / 1000;
const round2 = (x: number): number => Math.round(x * 100) / 100;

export function lerpLevel(table: number[], score: number): number {
  const s = Math.min(4, Math.max(0, score));
  const i = Math.min(3, Math.floor(s));
  const t = s - i;
  const lo = table[i];
  const hi = table[i + 1];
  // score が NaN (数でない上書きなど) や表が短いときは添字が外れる。従来どおり NaN を返す
  if (lo === undefined || hi === undefined) return Number.NaN;
  return lo + (hi - lo) * t;
}

export function requiredKeys(skip: string[]): string[] {
  return ESTIMATE_KEYS.filter((k) => !skip.includes(k));
}

const isNum = (x: unknown, lo: number, hi: number): boolean => typeof x === "number" && Number.isFinite(x) && x >= lo && x <= hi;

/** エラーメッセージ用に値を文字列にする。オブジェクトは [object Object] にならないよう JSON で表す */
const show = (v: unknown): string => (typeof v === "object" && v !== null ? JSON.stringify(v) : String(v));

const questionOf = (key: string): Question | undefined => (key === "font_pair" ? undefined : ESTIMATE_QUESTIONS[key]);

function checkChoice(key: string, a: Record<string, unknown>, q: Question | undefined): string | null {
  if (typeof a.choice !== "string" || a.choice === "") return `${key}: choice が文字列ではありません`;
  if (q && q.type === "choice" && !Object.prototype.hasOwnProperty.call(q.criteria, a.choice)) {
    return `${key}: choice "${a.choice}" は選択肢 (${Object.keys(q.criteria).join(", ")}) にありません`;
  }
  if (!isNum(a.confidence, 0, 1)) return `${key}: confidence は 0〜1 の数値である必要があります`;
  if (!isRecord(a.probabilities)) return `${key}: probabilities がオブジェクトではありません`;
  return null;
}

function checkScore(key: string, a: Record<string, unknown>): string | null {
  if (!isNum(a.score, 0, 4)) return `${key}: score は 0〜4 の数値である必要があります`;
  if (!isNum(a.confidence, 0, 1)) return `${key}: confidence は 0〜1 の数値である必要があります`;
  return null;
}

function checkAnswer(key: string, a: Record<string, unknown>): string | null {
  const q = questionOf(key);
  const type = q ? q.type : "choice";
  if (a.type !== undefined && a.type !== type) return `${key}: type は ${type} である必要があります (${show(a.type)})`;
  if (type === "choice") return checkChoice(key, a, q);
  if (type === "noul") return isNum(a.noul, 0, 1) ? null : `${key}: noul は 0〜1 の数値である必要があります`;
  return checkScore(key, a);
}

/** 1 つの答えを検査し、type を補った答えか、問題の説明を返す */
function checkKey(x: Record<string, unknown>, key: string): Record<string, unknown> | string {
  const v = x[key];
  if (!(key in x) || v === undefined) return `${key}: 答えがありません`;
  if (!isRecord(v)) return `${key}: オブジェクトではありません`;
  const msg = checkAnswer(key, v);
  if (msg) return msg;
  const q = questionOf(key);
  return { type: q ? q.type : "choice", ...v };
}

export function validateEstimate(x: unknown, required: string[]): Estimate {
  if (!isRecord(x)) throw new InputError("推定結果がオブジェクトではありません");
  const problems: string[] = [];
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(x)) out[k] = v;
  const keys = [...required];
  if (x.font_pair !== undefined && !keys.includes("font_pair")) keys.push("font_pair");
  for (const key of keys) {
    const r = checkKey(x, key);
    if (typeof r === "string") problems.push(r);
    else out[key] = r;
  }
  if (problems.length) throw new InputError(`推定結果が不正です: ${problems.join(" / ")}`);
  // 検査したキーは Answer の形になっている。検査の対象外のキーは従来どおりそのまま残すため、型は宣言で合わせる
  return out as Estimate;
}

export function applyOverrides(est: Estimate, overrides: Record<string, string | number>): Estimate {
  const out: Estimate = structuredClone(est);
  for (const [key, v] of Object.entries(overrides)) {
    const q = key === "font_pair" ? null : ESTIMATE_QUESTIONS[key];
    if (key !== "font_pair" && !q) throw new InputError(`未知の質問キーです: ${key}`);
    const type = q ? q.type : "choice";
    let a: Answer;
    if (type === "choice") a = { type: "choice", choice: String(v), confidence: 1, probabilities: { [String(v)]: 1 } };
    else if (type === "noul") a = { type: "noul", noul: Number(v) };
    else a = { type: "score", score: Number(v), confidence: 1 };
    out[key] = a;
  }
  return out;
}

const NEUTRAL: Record<string, [number | null, number]> = { pure: [null, 0], brand: [null, 0.01], warm: [70, 0.01], cool: [250, 0.01] };

function need(est: Estimate, key: string): Answer {
  const a = est[key];
  if (!a) throw new InputError(`推定結果に ${key} がありません`);
  return a;
}
const choiceOf = (est: Estimate, key: string): string => {
  const a = need(est, key);
  if (a.type !== "choice") throw new InputError(`${key} は choice である必要があります`);
  return a.choice;
};
const scoreOf = (est: Estimate, key: string): number => {
  const a = need(est, key);
  if (a.type !== "score") throw new InputError(`${key} は score である必要があります`);
  return a.score;
};
const noulOf = (est: Estimate, key: string): number => {
  const a = need(est, key);
  if (a.type !== "noul") throw new InputError(`${key} は noul である必要があります`);
  return a.noul;
};
/** choice の答えを取り出し、シードの項目の型に合うか確かめる (検証していない上書きの値を弾く) */
function choiceAs<T extends string>(est: Estimate, key: string, guard: (x: unknown) => x is T): T {
  const v = choiceOf(est, key);
  if (!guard(v)) throw new InputError(`${key} が不正です: ${v}`);
  return v;
}

function resolveBrand(fixed: Fixed, estimate: Estimate): { brandHue: number; brandChroma: number } {
  const brandHue = fixed.brandHue ?? lookup(HUES, choiceOf(estimate, "brand_hue"));
  if (brandHue === undefined) throw new InputError("brand_hue の色相を決められません");
  const brandChroma = fixed.brandChroma ?? round3(lerpLevel(LEVELS.brandChroma, scoreOf(estimate, "chroma")));
  return { brandHue, brandChroma };
}

function resolveAccentHue(estimate: Estimate, brandHue: number): number | null {
  if (!(noulOf(estimate, "use_accent") >= 0.5)) return null;
  const scheme = choiceOf(estimate, "accent_scheme");
  const off = lookup(ACCENT_OFFSET, scheme);
  if (off === undefined) throw new InputError(`accent_scheme が不正です: ${scheme}`);
  return (brandHue + off) % 360;
}

function resolveNeutral(estimate: Estimate, brandHue: number): { neutralHue: number; neutralChroma: number } {
  const tint = NEUTRAL[choiceOf(estimate, "neutral_tint")];
  if (!tint) throw new InputError("neutral_tint が不正です");
  return { neutralHue: tint[0] ?? brandHue, neutralChroma: tint[1] };
}

/** 役割ごとのフォント。明示指定を優先し、無ければフォントの組から取る */
const familyOf = (fixed: Fixed, fontPair: FontPair | null, role: "heading" | "body" | "mono"): string | undefined =>
  fixed.fonts[role] ?? fontPair?.[role];

function resolveFont(fixed: Fixed, estimate: Estimate, fontPair: FontPair | null): Seed["font"] {
  const heading = familyOf(fixed, fontPair, "heading");
  const body = familyOf(fixed, fontPair, "body");
  const mono = familyOf(fixed, fontPair, "mono");
  if (!heading || !body || !mono) throw new InputError("フォントの組が決まっていません");
  const font: Seed["font"] = { mood: choiceAs(estimate, "font_mood", isFontMood), heading, body, mono };
  if (fontPair) font.pairId = fontPair.id;
  return font;
}

const SEED_PATHS = [
  "baseMode",
  "color.brandHue",
  "color.brandChroma",
  "color.accentHue",
  "color.neutralHue",
  "color.neutralChroma",
  "color.contrast",
  "shape.radiusPx",
  "shape.spacingScale",
  "shape.shadow",
  "font.mood",
  "font.heading",
  "font.body",
  "font.mono",
];

function collectSources(resolved: Resolved, estimateSource: Source): Record<string, Source> {
  const sources: Record<string, Source> = {};
  for (const p of SEED_PATHS) sources[p] = resolved.sources[p] ?? estimateSource;
  return sources;
}

/** use_accent が 0.5 付近で迷っているとき、逆の答えを別案にする */
function useAccentAlternative(a: Answer): Alternative[] {
  if (a.type !== "noul") return [];
  const range = THRESHOLDS.noulUncertain.use_accent;
  const lo = at(range, 0);
  const hi = at(range, 1);
  if (!(a.noul >= lo && a.noul <= hi)) return [];
  return [{ field: "use_accent", value: a.noul < 0.5 ? "true" : "false", probability: a.noul < 0.5 ? a.noul : 1 - a.noul }];
}

/** choice の確度が低いとき、次に確率の高い選択肢 (2 つまでのうち 0.1 以上) を別案にする */
function choiceAlternatives(key: string, a: Answer, skip: string[]): Alternative[] {
  if (a.type !== "choice" || skip.includes(key)) return [];
  const th = lookup(THRESHOLDS.choice, key);
  if (th === undefined || !(a.confidence < th)) return [];
  return Object.entries(a.probabilities)
    .filter(([v]) => v !== a.choice)
    .sort((p, q) => q[1] - p[1])
    .slice(0, 2)
    .filter(([, probability]) => probability >= 0.1)
    .map(([value, probability]) => ({ field: key, value, probability }));
}

function collectAlternatives(estimate: Estimate, skip: string[]): Alternative[] {
  const alternatives: Alternative[] = [];
  const choiceKeys = ["brand_hue", "neutral_tint", "accent_scheme", "base_mode", "font_mood", "shadow", "use_accent", "font_pair"];
  for (const key of choiceKeys) {
    const a = estimate[key];
    if (!a) continue;
    alternatives.push(...(key === "use_accent" ? useAccentAlternative(a) : choiceAlternatives(key, a, skip)));
  }
  return alternatives;
}

function collectLowConfidence(estimate: Estimate): string[] {
  const lowConfidence: string[] = [];
  for (const key of ["chroma", "contrast", "radius", "density", "formality"]) {
    const a = estimate[key];
    const th = lookup(THRESHOLDS.scoreLow, key);
    if (a && a.type === "score" && th !== undefined && a.confidence < th) lowConfidence.push(key);
  }
  return lowConfidence;
}

export function toSeedResult(args: {
  brief: Brief;
  resolved: Resolved;
  estimate: Estimate;
  fontPair: FontPair | null;
  estimateSource: "jev" | "llm-fallback";
}): SeedResult {
  const { brief, resolved, estimate, fontPair, estimateSource } = args;
  const fixed = resolved.fixed;

  // 項目を決める順 (足りない答えを報告する順) は従来どおり
  const { brandHue, brandChroma } = resolveBrand(fixed, estimate);
  const baseMode = fixed.baseMode ?? choiceAs(estimate, "base_mode", isBaseMode);
  const accentHue = resolveAccentHue(estimate, brandHue);
  const { neutralHue, neutralChroma } = resolveNeutral(estimate, brandHue);
  const font = resolveFont(fixed, estimate, fontPair);

  const seed: Seed = {
    id: brief.id,
    name: brief.name,
    tone: brief.tone,
    baseMode,
    color: { brandHue, brandChroma, accentHue, neutralHue, neutralChroma, contrast: round2(scoreOf(estimate, "contrast") + 1) },
    shape: {
      radiusPx: Math.round(lerpLevel(LEVELS.radiusPx, scoreOf(estimate, "radius"))),
      spacingScale: round3(lerpLevel(LEVELS.spacingScale, scoreOf(estimate, "density"))),
      shadow: choiceAs(estimate, "shadow", isShadowKind),
    },
    font,
  };

  return {
    seed,
    alternatives: collectAlternatives(estimate, resolved.skip),
    sources: collectSources(resolved, estimateSource),
    lowConfidence: collectLowConfidence(estimate),
  };
}
