import type { Brief, Fixed, Resolved, Source, ThemeRequest } from "./types.ts";
import { isBaseMode, isRecord } from "./guards.ts";

export class InputError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InputError";
  }
}

const HEX_RE = /^#[0-9a-fA-F]{6}$/;
const ID_RE = /^[a-z][a-z0-9-]*$/;

export function hexToOklch(hex: string): { l: number; c: number; h: number } {
  if (!HEX_RE.test(hex)) throw new InputError(`hex は #RRGGBB 形式で指定してください: ${hex}`);
  const lin = (v: number) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  const r = lin(parseInt(hex.slice(1, 3), 16) / 255);
  const g = lin(parseInt(hex.slice(3, 5), 16) / 255);
  const b = lin(parseInt(hex.slice(5, 7), 16) / 255);
  const l_ = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m_ = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s_ = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  const L = 0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_;
  const A = 1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_;
  const B = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_;
  const c = Math.sqrt(A * A + B * B);
  let h = 0;
  if (c >= 0.0001) {
    h = (Math.atan2(B, A) * 180) / Math.PI;
    if (h < 0) h += 360;
    if (h >= 360) h -= 360;
  }
  return { l: L, c, h };
}

const isHex = (v: unknown): v is string => typeof v === "string" && HEX_RE.test(v);
const isStringArray = (v: unknown): v is string[] => Array.isArray(v) && v.every((m) => typeof m === "string");

function validatePrompt(v: unknown): string {
  if (typeof v !== "string") throw new InputError("prompt は文字列で指定してください");
  const prompt = v.trim();
  if (prompt.length < 1 || prompt.length > 2000) throw new InputError("prompt は trim 後 1〜2000 文字で指定してください");
  return prompt;
}

function validateRequestFonts(v: unknown): { heading?: string; body?: string; mono?: string } {
  if (!isRecord(v)) throw new InputError("fonts はオブジェクトで指定してください");
  const fonts: { heading?: string; body?: string; mono?: string } = {};
  for (const k of ["heading", "body", "mono"] as const) {
    const f = v[k];
    if (f === undefined) continue;
    if (typeof f !== "string") throw new InputError(`fonts.${k} は文字列で指定してください`);
    fonts[k] = f;
  }
  return fonts;
}

export function validateRequest(x: unknown): ThemeRequest {
  if (!isRecord(x)) throw new InputError("リクエストはオブジェクトで指定してください");
  const out: ThemeRequest = { prompt: validatePrompt(x.prompt) };
  if (x.brandColor !== undefined) {
    if (!isHex(x.brandColor)) throw new InputError("brandColor は #RRGGBB 形式で指定してください");
    out.brandColor = x.brandColor;
  }
  if (x.baseMode !== undefined) {
    if (!isBaseMode(x.baseMode)) throw new InputError("baseMode は light か dark で指定してください");
    out.baseMode = x.baseMode;
  }
  if (x.fonts !== undefined) out.fonts = validateRequestFonts(x.fonts);
  return out;
}

function validateBriefState(s: unknown): Brief["state"] {
  if (!isRecord(s)) throw new InputError("brief.state はオブジェクトで指定してください");
  const str = (k: "product" | "audience" | "references" | "avoid"): string => {
    const v = s[k];
    if (typeof v !== "string") throw new InputError(`brief.state.${k} は文字列で指定してください`);
    return v;
  };
  const product = str("product");
  const audience = str("audience");
  const references = str("references");
  const avoid = str("avoid");
  const mood = s.mood;
  if (!isStringArray(mood) || mood.length < 1 || mood.length > 6) {
    throw new InputError("brief.state.mood は 1〜6 個の文字列の配列で指定してください");
  }
  return { product, audience, mood, references, avoid };
}

function validateBriefExplicit(e: unknown): Brief["explicit"] {
  if (!isRecord(e)) throw new InputError("brief.explicit はオブジェクトで指定してください");
  const { brandColor, baseMode } = e;
  if (brandColor !== null && !isHex(brandColor)) {
    throw new InputError("brief.explicit.brandColor は null か #RRGGBB 形式で指定してください");
  }
  if (baseMode !== null && !isBaseMode(baseMode)) {
    throw new InputError("brief.explicit.baseMode は null か light/dark で指定してください");
  }
  return { brandColor, baseMode };
}

const isBriefId = (v: unknown): v is string => typeof v === "string" && ID_RE.test(v) && v.length <= 20;

export function validateBrief(x: unknown): Brief {
  if (!isRecord(x)) throw new InputError("brief はオブジェクトで指定してください");
  if (!isBriefId(x.id)) throw new InputError("brief.id は /^[a-z][a-z0-9-]*$/ に合う 20 文字以内の文字列で指定してください");
  if (typeof x.name !== "string") throw new InputError("brief.name は文字列で指定してください");
  if (typeof x.tone !== "string") throw new InputError("brief.tone は文字列で指定してください");
  if (typeof x.needsJapanese !== "boolean") throw new InputError("brief.needsJapanese は真偽値で指定してください");
  const state = validateBriefState(x.state);
  const explicit = validateBriefExplicit(x.explicit);
  return { id: x.id, name: x.name, tone: x.tone, needsJapanese: x.needsJapanese, state, explicit };
}

/** ブランド色を確定する。彩度が低い色は色相を決めず、彩度だけ固定する */
function resolveColor(color: string | null, fixed: Fixed, skipSet: Set<string>, sources: Record<string, Source>): void {
  if (!color) return;
  const { c, h } = hexToOklch(color);
  if (c >= 0.02) {
    fixed.brandHue = Math.round(h * 10) / 10;
    fixed.brandChroma = Math.round(Math.min(0.25, Math.max(0.02, c)) * 1000) / 1000;
    skipSet.add("brand_hue");
    skipSet.add("chroma");
    sources["color.brandHue"] = "explicit";
    sources["color.brandChroma"] = "explicit";
  } else {
    fixed.brandChroma = 0.04;
    skipSet.add("chroma");
    sources["color.brandChroma"] = "explicit";
  }
}

/** 指定されたフォントを固定する。3 つとも揃えば font_pair の質問を省く */
function resolveFonts(request: ThemeRequest, fixed: Fixed, skipSet: Set<string>, sources: Record<string, Source>): void {
  const rf = request.fonts ?? {};
  for (const k of ["heading", "body", "mono"] as const) {
    const v = rf[k];
    if (typeof v === "string" && v !== "") {
      fixed.fonts[k] = v;
      sources[`font.${k}`] = "explicit";
    }
  }
  if (fixed.fonts.heading && fixed.fonts.body && fixed.fonts.mono) skipSet.add("font_pair");
}

export function resolveExplicit(request: ThemeRequest, brief: Brief | null): Resolved {
  const fixed: Fixed = { fonts: {} };
  const sources: Record<string, Source> = {};
  const skipSet = new Set<string>();

  resolveColor(request.brandColor ?? brief?.explicit.brandColor ?? null, fixed, skipSet, sources);

  const baseMode = request.baseMode ?? brief?.explicit.baseMode ?? null;
  if (baseMode) {
    fixed.baseMode = baseMode;
    skipSet.add("base_mode");
    sources["baseMode"] = "explicit";
  }

  resolveFonts(request, fixed, skipSet, sources);

  const skip = ["brand_hue", "chroma", "base_mode", "font_pair"].filter((k) => skipSet.has(k));
  return { fixed, skip, sources };
}
