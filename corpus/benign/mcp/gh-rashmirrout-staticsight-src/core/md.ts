// Markdown helpers shared by all tools. Lengths are counted in code points to match the Python implementation.
export const LINE_CLIP = 160;

export function cpLen(s: string): number {
  let n = 0;
  for (const _ of s) n++;
  return n;
}

export function cpSlice(s: string, start: number, end?: number): string {
  return Array.from(s).slice(start, end).join("");
}

/** Python str.rstrip() (whitespace only). */
export function rstrip(s: string): string {
  return s.replace(/\s+$/u, "");
}

export function clip(text: string, limit = LINE_CLIP): string {
  const t = rstrip(text.replace(/\t/g, "    "));
  if (cpLen(t) <= limit) return t;
  return cpSlice(t, 0, limit - 1) + "…";
}

export function codeSpan(text: string): string {
  const t = clip(text.trim());
  if (t.includes("`")) return `\`\` ${t} \`\``;
  return `\`${t}\``;
}

export function errorCard(title: string, message: string, hint?: string): string {
  let out = `### ❌ ${title}\n${message}`;
  if (hint) out += `\n\n💡 ${hint}`;
  return out;
}

export function truncateList(items: string[], limit: number, noun = "results", hint = ""): string[] {
  if (items.length <= limit) return [...items];
  const extra = items.length - limit;
  let note = `_…and ${extra} more ${noun}`;
  note += hint ? `. ${hint}_` : "._";
  return [...items.slice(0, limit), note];
}

export function numberedCode(lines: string[], startLine: number, mark: Iterable<number> = [], width?: number): string[] {
  const marks = new Set(mark);
  const last = startLine + lines.length - 1;
  const w = width ?? String(Math.max(last, 1)).length;
  return lines.map((text, i) => {
    const n = startLine + i;
    const prefix = marks.has(n) ? ">" : " ";
    return `${prefix}${String(n).padStart(w)} | ${clip(text, 200)}`;
  });
}

export function compressRanges(numbers: Iterable<number>, maxParts = 0): string {
  const nums = [...new Set(numbers)].sort((a, b) => a - b);
  if (!nums.length) return "";
  const parts: string[] = [];
  let start = nums[0];
  let prev = nums[0];
  for (const n of nums.slice(1)) {
    if (n === prev + 1) {
      prev = n;
      continue;
    }
    parts.push(start === prev ? `L${start}` : `L${start}-${prev}`);
    start = prev = n;
  }
  parts.push(start === prev ? `L${start}` : `L${start}-${prev}`);
  if (maxParts && parts.length > maxParts) return parts.slice(0, maxParts).join(", ") + `, … (+${parts.length - maxParts} more ranges)`;
  return parts.join(", ");
}

export function enforceBudget(text: string, maxChars: number): string {
  const cps = Array.from(text);
  if (cps.length <= maxChars) return text;
  let cut = cps.slice(0, maxChars).lastIndexOf("\n");
  if (cut <= 0) cut = maxChars;
  let kept = cps.slice(0, cut).join("");
  if ((kept.split("```").length - 1) % 2 === 1) kept += "\n```";
  return kept + `\n\n_…output truncated at ${maxChars} characters to protect the context budget. Narrow the query for more._`;
}

export function plural(n: number, word: string, suffix = "s"): string {
  return `${n} ${word}${n === 1 ? "" : suffix}`;
}

/** Python-compatible `round(x, digits)` / `f"{x:.{digits}f}"`: correctly rounded, exact binary ties go to even,
 * and negative values (including -0) keep their sign, e.g. -0.0001 -> "-0.00". */
export function formatFixed(x: number, digits: number): string {
  const neg = x < 0 || Object.is(x, -0);
  const ax = Math.abs(x);
  const exact = ax.toFixed(20);
  const tail = exact.slice(exact.indexOf(".") + 1 + digits);
  let body: string;
  if (/^50*$/.test(tail)) {
    const scaled = Math.trunc(ax * 10 ** digits);
    body = ((scaled % 2 === 0 ? scaled : scaled + 1) / 10 ** digits).toFixed(digits);
  } else {
    body = ax.toFixed(digits);
  }
  return neg ? "-" + body : body;
}

export function roundTo(x: number, digits: number): number {
  return Number(formatFixed(x, digits));
}

/** Python-compatible round-half-even formatting for `{x:.0f}`. */
export function formatFixed0(x: number): string {
  const f = Math.floor(x);
  const diff = x - f;
  let r: number;
  if (Math.abs(diff - 0.5) < 1e-12) r = f % 2 === 0 ? f : f + 1;
  else r = Math.round(x);
  return String(r);
}

export function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
