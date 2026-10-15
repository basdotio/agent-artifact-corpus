// style-guide の型。docs/INPUT_SPEC.md (V1) に対応する。実行時の検証は explicit.ts / seed.ts / fonts.ts の validate* で行う
export type BaseMode = "light" | "dark";
export type FontMood = "geometric" | "humanist" | "rounded" | "serif" | "mincho" | "tech";
export type ShadowKind = "none" | "soft" | "hard";
export type Source = "explicit" | "jev" | "llm-fallback";

export type ThemeRequest = {
  prompt: string; // 1〜2000 文字
  brandColor?: string; // "#RRGGBB"
  baseMode?: BaseMode;
  fonts?: { heading?: string; body?: string; mono?: string }; // fonts.json に載っている family 名
};

export type Brief = {
  id: string; // /^[a-z][a-z0-9-]*$/、20 文字以内
  name: string;
  tone: string;
  needsJapanese: boolean;
  state: { product: string; audience: string; mood: string[]; references: string; avoid: string };
  explicit: { brandColor: string | null; baseMode: BaseMode | null };
};

// Jev の質問。choice の criteria は 選択肢→説明、noul は {"1": 真のとき, "0": 偽のとき}、score は水準 0〜4 の説明の配列
export type Question =
  | { type: "choice"; instructions: string; criteria: Record<string, string> }
  | { type: "noul"; instructions: string; criteria: { "1": string; "0": string } }
  | { type: "score"; instructions: string; criteria: string[] };

export type ChoiceAnswer = { type: "choice"; choice: string; confidence: number; probabilities: Record<string, number> };
export type NoulAnswer = { type: "noul"; noul: number };
export type ScoreAnswer = { type: "score"; score: number; confidence: number; probabilities?: Record<string, number> };
export type Answer = ChoiceAnswer | NoulAnswer | ScoreAnswer;

// Jev 応答の answers と同じ形。キーは ESTIMATE_KEYS と "font_pair"。①で省いた質問のキーは無い
export type Estimate = Record<string, Answer>;

export type FontPair = {
  id: string;
  heading: string; // Google Fonts の family 名
  body: string;
  mono: string;
  mood: FontMood;
  japanese: boolean; // 本文が日本語に対応しているか
  formality: number; // 0〜4
  description: string; // Jev に見せる英語の説明
  weights: { heading: number[]; body: number[] }; // 日本語フォントは 2 つまで
};

export type Seed = {
  id: string;
  name: string;
  tone: string;
  baseMode: BaseMode;
  color: {
    brandHue: number;
    brandChroma: number;
    accentHue: number | null;
    neutralHue: number;
    neutralChroma: number;
    contrast: number; // 1〜5
  };
  shape: { radiusPx: number; spacingScale: number; shadow: ShadowKind };
  font: { mood: FontMood; heading: string; body: string; mono: string; pairId?: string };
};

export type Alternative = { field: string; value: string; probability: number };

export type SeedResult = {
  seed: Seed;
  alternatives: Alternative[];
  sources: Record<string, Source>; // キーは "baseMode", "color.brandHue" のようなシードの項目のパス
  lowConfidence: string[]; // 確度が低かった score のキー (Web アプリのスライダーに印を付ける)
};

// ① の結果
export type Fixed = {
  brandHue?: number;
  brandChroma?: number;
  baseMode?: BaseMode;
  fonts: { heading?: string; body?: string; mono?: string };
};
export type Resolved = { fixed: Fixed; skip: string[]; sources: Record<string, Source> };
