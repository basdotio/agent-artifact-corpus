import { Rng } from "./rng.js";
import * as C from "./corpus.js";

/** Uppercase the first character of a sentence. */
function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Sentence templates. Each returns a finished sentence (capitalized, terminally
 * punctuated). Weighted so the signature "I <verb> the <adj> '<jargon>' <noun>
 * (<tag>)" shape shows up most, matching the reference screenshot.
 */
type Template = (r: Rng) => string;

const verifyClause: Template = (r) => {
  let s = `${r.pick(C.OPENERS).toLowerCase()}, I ${r.pick(C.VERBS)} the ${r.pick(
    C.ADJECTIVES,
  )} '${r.pick(C.QUOTED_JARGON)}' ${r.pick(C.NOUNS)} (${r.pick(C.STATUS_TAGS)})`;
  if (r.chance(0.7)) {
    s += `, ${r.pick(C.CONNECTORS)} the ${r.pick(C.ADJECTIVES)} ${r.pick(
      C.PLURAL_NOUNS,
    )} (${r.pick(C.STATUS_TAGS)}) are ${r.pick(C.PREDICATE_ADJECTIVES)}`;
  }
  if (r.chance(0.5)) s += `—and ${r.pick(C.DEFERRALS)}`;
  return cap(s) + ".";
};

const hedgeClause: Template = (r) =>
  cap(
    `${r.pick(C.OPENERS)}: the ${r.pick(C.ADJECTIVES)} ${r.pick(
      C.NOUNS,
    )} is ${r.pick(C.PREDICATE_ADJECTIVES)}, ${r.pick(C.CONNECTORS)} ${r.pick(
      C.DEFERRALS,
    )}`,
  ) + ".";

const reassureClause: Template = (r) =>
  cap(
    `${r.pick(C.REASSURANCES)}, ${r.pick(C.CONNECTORS)} ${r.pick(C.DEFERRALS)}`,
  ) + ".";

const contrastClause: Template = (r) =>
  cap(
    `the ${r.pick(C.ADJECTIVES)} ${r.pick(C.NOUNS)} is ${r.pick(
      C.STATUS_TAGS,
    )}—the ${r.pick(C.PLURAL_NOUNS)} (${r.pick(
      C.STATUS_TAGS,
    )}) are ${r.pick(C.PREDICATE_ADJECTIVES)}`,
  ) + ".";

// "Yes. The current implementation is pathologically scalar." — joined with an
// em-dash so the whole verdict stays one sentence and sentence counts hold.
const verdictClause: Template = (r) => {
  const subject = r.chance(0.4) ? "implementation" : r.pick(C.NOUNS);
  let s = `${r.pick(C.AFFIRMATIONS)}—the current ${subject} is ${r.pick(
    C.DIAGNOSTIC_ADVERBS,
  )} ${r.pick(C.DIAGNOSTIC_ADJECTIVES)}`;
  if (r.chance(0.3)) s += ` (${r.pick(C.STATUS_TAGS)})`;
  return cap(s) + ".";
};

const TEMPLATES: readonly { weight: number; fn: Template }[] = [
  { weight: 5, fn: verifyClause },
  { weight: 2, fn: hedgeClause },
  { weight: 2, fn: contrastClause },
  { weight: 2, fn: verdictClause },
  { weight: 1, fn: reassureClause },
];

const TOTAL_WEIGHT = TEMPLATES.reduce((n, t) => n + t.weight, 0);

/** Generate one sentence via weighted template choice. */
export function sentence(r: Rng): string {
  let roll = r.float() * TOTAL_WEIGHT;
  for (const t of TEMPLATES) {
    roll -= t.weight;
    if (roll < 0) return t.fn(r);
  }
  return verifyClause(r);
}

/** Count whitespace-delimited words. */
export function countWords(text: string): number {
  const t = text.trim();
  return t === "" ? 0 : t.split(/\s+/).length;
}

/** Closer word-lengths available, largest first. */
const CLOSER_LENGTHS = Object.keys(C.CLOSERS)
  .map(Number)
  .sort((a, b) => b - a);

/**
 * Compose complete closer sentences summing to exactly `remaining` words.
 * Greedy largest-first; the length-1 bank guarantees termination.
 */
function fillExact(remaining: number, r: Rng): string[] {
  const out: string[] = [];
  while (remaining > 0) {
    const len = CLOSER_LENGTHS.find((l) => l <= remaining)!;
    out.push(cap(r.pick(C.CLOSERS[len]!)) + ".");
    remaining -= len;
  }
  return out;
}

/** Exactly `count` sentences joined with single spaces. */
export function sentences(count: number, r: Rng): string {
  if (count <= 0) return "";
  const out: string[] = [];
  for (let i = 0; i < count; i++) out.push(sentence(r));
  return out.join(" ");
}

/** Exactly `count` paragraphs, each 3–6 sentences, joined by blank lines. */
export function paragraphs(count: number, r: Rng): string {
  if (count <= 0) return "";
  const out: string[] = [];
  for (let i = 0; i < count; i++) out.push(sentences(r.int(3, 6), r));
  return out.join("\n\n");
}

/**
 * Exactly `count` words. Packs whole sentences up to the budget, then fills the
 * remainder with complete short closers so output never ends mid-clause.
 */
export function words(count: number, r: Rng): string {
  if (count <= 0) return "";
  const parts: string[] = [];
  let used = 0;
  while (used < count) {
    let placed = false;
    for (let attempt = 0; attempt < 12; attempt++) {
      const s = sentence(r);
      const w = countWords(s);
      if (used + w <= count) {
        parts.push(s);
        used += w;
        placed = true;
        break;
      }
    }
    if (!placed) break; // no full sentence fits the remaining budget
  }
  if (used < count) parts.push(...fillExact(count - used, r));
  return parts.join(" ");
}
