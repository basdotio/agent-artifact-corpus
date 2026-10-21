// Which files are indexed, their language, and why others are skipped (shared rules: shared/semantic/languages.json).
import { sharedJson } from "../shared.js";

export const MAX_LINE_CHARS = 5000; // a line longer than this marks a minified/generated file
export const MINIFIED_AVG_LINE = 300; // average line length above this marks a minified/generated file
const BINARY_SNIFF_BYTES = 8192;

export interface Rules {
  extensions: Record<string, string>;
  filenames: Record<string, string>;
  structural: string[];
  comment_prefixes: Record<string, string[]>;
  unit_kinds: string[];
  skip_extensions: string[];
  skip_filenames: string[];
  skip_suffixes: string[];
}

export function rules(): Rules {
  return sharedJson<Rules>("semantic/languages.json");
}

function basename(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1);
}

function ext(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot > 0 ? name.slice(dot).toLowerCase() : "";
}

/** Length in code points (matches Python len()); fast path for ASCII. */
export function cpLength(s: string): number {
  // eslint-disable-next-line no-control-regex
  if (/^[\x00-\x7f]*$/.test(s)) return s.length;
  let n = 0;
  for (const _ of s) n++;
  return n;
}

export function languageOf(path: string): string {
  const r = rules();
  const name = basename(path);
  if (name in r.filenames) return r.filenames[name];
  return r.extensions[ext(name)] ?? "text";
}

export function isStructural(language: string): boolean {
  return rules().structural.includes(language);
}

/** Skip decision from the name and size alone (no file read). */
export function preSkipReason(path: string, size: number, maxKb: number): string {
  const r = rules();
  const name = basename(path);
  const low = name.toLowerCase();
  if (r.skip_filenames.includes(name)) return "generated";
  if (r.skip_suffixes.some((s) => low.endsWith(s))) return "generated";
  if (r.skip_extensions.includes(ext(name))) return "binary";
  if (size > maxKb * 1024) return "too-large";
  if (size === 0) return "empty";
  return "";
}

/** Skip decision from the content: binary (NUL bytes without a UTF-16 BOM) or minified/generated. */
export function contentSkipReason(data: Uint8Array, text: string): string {
  const head = data.subarray(0, BINARY_SNIFF_BYTES);
  const utf16 = head.length >= 2 && ((head[0] === 0xff && head[1] === 0xfe) || (head[0] === 0xfe && head[1] === 0xff));
  if (!utf16 && head.includes(0)) return "binary";
  const lines = text.split("\n");
  if (!lines.some((ln) => ln.trim())) return "empty";
  let longest = 0;
  for (const ln of lines) longest = Math.max(longest, cpLength(ln));
  const avg = cpLength(text) / Math.max(lines.length, 1);
  if (longest > MAX_LINE_CHARS || avg > MINIFIED_AVG_LINE) return "minified";
  return "";
}

export interface FileStat {
  path: string;
  size: number;
  mtimeNs: string;
}
