// core 内で使う小さな型ガードと取り出しのヘルパー。実行時の依存は持たない
import type { BaseMode, FontMood, ShadowKind } from "./types.ts";

export const FONT_MOODS: readonly FontMood[] = ["geometric", "humanist", "rounded", "serif", "mincho", "tech"];
const SHADOW_KINDS: readonly ShadowKind[] = ["none", "soft", "hard"];

export function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

export function isBaseMode(x: unknown): x is BaseMode {
  return x === "light" || x === "dark";
}

export function isFontMood(x: unknown): x is FontMood {
  return FONT_MOODS.some((m) => m === x);
}

export function isShadowKind(x: unknown): x is ShadowKind {
  return SHADOW_KINDS.some((s) => s === x);
}

/** 必ずある配列の要素を取り出す。無ければプログラムの誤りなので Error を投げる */
export function at<T>(xs: readonly T[], i: number): T {
  const v = xs[i];
  if (v === undefined) throw new Error(`添字 ${i} の要素がありません (長さ ${xs.length})`);
  return v;
}

/** 必ずあるキーの値を取り出す。無ければプログラムの誤りなので Error を投げる */
export function get<T>(table: Readonly<Record<string, T>>, key: string): T {
  const v = table[key];
  if (v === undefined) throw new Error(`キー ${key} の値がありません`);
  return v;
}

/** 表から値を引く。無いキーは undefined */
export function lookup<T>(table: Readonly<Record<string, T>>, key: string): T | undefined {
  return table[key];
}
