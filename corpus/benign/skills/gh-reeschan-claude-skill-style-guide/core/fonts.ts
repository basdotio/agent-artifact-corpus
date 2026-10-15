import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { ChoiceAnswer, FontPair, Question } from "./types.ts";
import { THRESHOLDS } from "./questions.ts";
import { InputError } from "./explicit.ts";
import { at, isFontMood, isRecord } from "./guards.ts";

export const CATALOG_PATH: string = fileURLToPath(new URL("../data/fonts.json", import.meta.url));

const ID_RE = /^[a-z0-9-]+\+[a-z0-9-]+$/;

function validWeights(w: unknown): w is number[] {
  return Array.isArray(w) && w.length >= 1 && w.every((n) => Number.isInteger(n) && n >= 100 && n <= 900);
}

function checkId(p: Record<string, unknown>, label: string, seen: Set<string>, errors: string[]): void {
  if (typeof p.id !== "string" || !ID_RE.test(p.id)) errors.push(`${label} id が不正です: ${String(p.id)}`);
  else if (seen.has(p.id)) errors.push(`${label} id が重複しています: ${p.id}`);
  else seen.add(p.id);
}

function checkAttributes(p: Record<string, unknown>, label: string, errors: string[]): void {
  for (const k of ["heading", "body", "mono", "description"]) {
    if (typeof p[k] !== "string" || p[k] === "") errors.push(`${label} ${k} が不正です`);
  }
  if (!isFontMood(p.mood)) errors.push(`${label} mood が不正です: ${String(p.mood)}`);
  if (typeof p.japanese !== "boolean") errors.push(`${label} japanese が真偽値ではありません`);
  if (typeof p.formality !== "number" || !(p.formality >= 0 && p.formality <= 4))
    errors.push(`${label} formality が 0〜4 の数ではありません`);
}

function checkWeights(w: unknown, label: string, errors: string[]): void {
  if (!w || typeof w !== "object") {
    errors.push(`${label} weights がありません`);
    return;
  }
  if (!validWeights("heading" in w ? w.heading : undefined)) errors.push(`${label} weights.heading が不正です`);
  if (!validWeights("body" in w ? w.body : undefined)) errors.push(`${label} weights.body が不正です`);
}

/** 1 件を検査して問題を errors に足す。この件に問題が無ければ FontPair とみなせる */
function checkPair(raw: unknown, label: string, seen: Set<string>, errors: string[]): raw is FontPair {
  if (!isRecord(raw)) {
    errors.push(`${label} はオブジェクトではありません`);
    return false;
  }
  const before = errors.length;
  checkId(raw, label, seen, errors);
  checkAttributes(raw, label, errors);
  checkWeights(raw.weights, label, errors);
  return errors.length === before;
}

export function validateCatalog(x: unknown): FontPair[] {
  if (!Array.isArray(x)) throw new InputError("フォントカタログは配列である必要があります");
  const errors: string[] = [];
  const seen = new Set<string>();
  const pairs: FontPair[] = [];
  x.forEach((raw: unknown, i) => {
    if (checkPair(raw, `[${i}]`, seen, errors)) pairs.push(raw);
  });
  if (errors.length > 0) throw new InputError(`フォントカタログが不正です:\n${errors.join("\n")}`);
  return pairs;
}

export function loadCatalog(path: string = CATALOG_PATH): FontPair[] {
  return validateCatalog(JSON.parse(readFileSync(path, "utf8")));
}

export function familyNames(catalog: FontPair[]): { heading: string[]; body: string[]; mono: string[] } {
  const uniq = (f: (p: FontPair) => string) => [...new Set(catalog.map(f))].sort();
  return { heading: uniq((p) => p.heading), body: uniq((p) => p.body), mono: uniq((p) => p.mono) };
}

export function validateFixedFonts(fonts: { heading?: string; body?: string; mono?: string }, catalog: FontPair[]): string[] {
  const out: string[] = [];
  for (const role of ["heading", "body", "mono"] as const) {
    const name = fonts[role];
    if (name === undefined) continue;
    if (!catalog.some((p) => p[role] === name)) out.push(`${role} のフォント ${name} はカタログにありません`);
  }
  return out;
}

export function selectCandidates(args: {
  catalog: FontPair[];
  fontMood: ChoiceAnswer;
  needsJapanese: boolean;
  fixed: { heading?: string; body?: string; mono?: string };
  formality: number;
  maxCount?: number;
}): FontPair[] {
  const { catalog, fontMood, needsJapanese, fixed, formality } = args;
  const maxCount = args.maxCount ?? 8;
  const moods = [fontMood.choice];
  if (fontMood.confidence < THRESHOLDS.choice.font_mood) {
    const second = Object.entries(fontMood.probabilities ?? {})
      .filter(([k]) => k !== fontMood.choice)
      .sort((a, b) => b[1] - a[1])[0];
    if (second) moods.push(second[0]);
  }
  const base = (p: FontPair) =>
    (!needsJapanese || p.japanese) &&
    (fixed.heading === undefined || p.heading === fixed.heading) &&
    (fixed.body === undefined || p.body === fixed.body);
  let found = catalog.filter((p) => moods.includes(p.mood) && base(p));
  if (found.length === 0) found = catalog.filter(base);
  return found
    .map((p, i) => ({ p, i }))
    .sort((a, b) => Math.abs(a.p.formality - formality) - Math.abs(b.p.formality - formality) || a.i - b.i)
    .slice(0, maxCount)
    .map((e) => e.p);
}

export function fontQuestion(candidates: FontPair[]): Record<string, Question> {
  const criteria: Record<string, string> = {};
  for (const p of candidates) criteria[p.id] = p.description;
  return {
    font_pair: { type: "choice", instructions: "Which font pairing best fits this product?", criteria },
  };
}

export function pickFontPair(candidates: FontPair[], answer?: ChoiceAnswer): FontPair | null {
  if (candidates.length === 1) return at(candidates, 0);
  if (answer) return candidates.find((p) => p.id === answer.choice) ?? null;
  return null;
}

export function googleFontsUrl(fonts: { heading: string; body: string; mono: string }, pair?: FontPair | null): string {
  const families = new Map<string, Set<number>>();
  const add = (name: string, ws: number[]) => {
    const s = families.get(name) ?? new Set<number>();
    ws.forEach((w) => s.add(w));
    families.set(name, s);
  };
  add(fonts.heading, pair?.weights.heading ?? [400, 700]);
  add(fonts.body, pair?.weights.body ?? [400, 700]);
  add(fonts.mono, [400]);
  const parts = [...families].map(([name, ws]) => `family=${name.replace(/ /g, "+")}:wght@${[...ws].sort((a, b) => a - b).join(";")}`);
  return `https://fonts.googleapis.com/css2?${parts.join("&")}&display=swap`;
}
