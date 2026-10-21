import { Rng } from "./rng.js";
import * as gen from "./generator.js";

export type Unit = "words" | "sentences" | "paragraphs";

export interface GenerateOptions {
  /** How many units to produce. Values <= 0 yield "". */
  count: number;
  /** What `count` measures. Default: "words". */
  unit?: Unit;
  /** Seed for reproducible output. Omit for fresh random text. */
  seed?: string | number;
}

export interface GenerateResult {
  /** The generated claudem-ipsum. */
  text: string;
  /** Exact counts of the produced text — handy for an API response body. */
  stats: { words: number; sentences: number; paragraphs: number };
}

function statsFor(text: string): GenerateResult["stats"] {
  const trimmed = text.trim();
  return {
    words: gen.countWords(trimmed),
    sentences: trimmed === "" ? 0 : (trimmed.match(/[.!?](?=\s|$)/g) ?? []).length,
    paragraphs: trimmed === "" ? 0 : trimmed.split(/\n{2,}/).length,
  };
}

/**
 * Core entry point. Generate filler text in Claude's voice, measured in words,
 * sentences, or paragraphs, and get exact counts back alongside it.
 *
 * @example
 * generate({ count: 40, unit: "words", seed: "demo" });
 */
export function generate(opts: GenerateOptions): GenerateResult {
  const { count, unit = "words", seed } = opts;
  const r = new Rng(seed);
  let text: string;
  switch (unit) {
    case "sentences":
      text = gen.sentences(Math.max(0, count), r);
      break;
    case "paragraphs":
      text = gen.paragraphs(Math.max(0, count), r);
      break;
    case "words":
    default:
      text = gen.words(Math.max(0, count), r);
      break;
  }
  return { text, stats: statsFor(text) };
}

/** Convenience: N words as a string. */
export function words(count: number, seed?: string | number): string {
  return gen.words(Math.max(0, count), new Rng(seed));
}

/** Convenience: N sentences as a string. */
export function sentences(count: number, seed?: string | number): string {
  return gen.sentences(Math.max(0, count), new Rng(seed));
}

/** Convenience: N paragraphs as a string. */
export function paragraphs(count: number, seed?: string | number): string {
  return gen.paragraphs(Math.max(0, count), new Rng(seed));
}
