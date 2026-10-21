/**
 * Candidate scoring and verdict classification for the fuzzy (no-DOI) match path.
 *
 * Split out of `quick-check.ts` so the whole decision is pure and unit-testable
 * without touching the network. The network part (which candidates Crossref
 * returns) lives in `crossref.ts`; the part that decides *which* candidate wins
 * and *what* that means lives here.
 *
 * Why this exists at all: the previous implementation picked the candidate with
 * the highest title Jaccard and ignored authors and year entirely. For
 * `Hiller (2006), "Grundsätze der Humankapitaltheorie"` that returned
 * `Die Grundsätze der Schafzüchtung` (Janke, 1867) as a `partial_match`, because
 * the German function words "grundsätze"/"der" carried the similarity. Title
 * alone is not enough evidence to identify a work.
 */

/**
 * Function words that carry no identifying signal but inflate token overlap
 * between unrelated titles. Multilingual on purpose: the corpus this runs on is
 * German-Swiss theses citing English, German and French literature.
 *
 * Deliberately NOT a full stopword list — content-bearing short words stay in.
 * The list only needs to cover words that appear in titles across unrelated
 * works often enough to fake a match.
 */
export const TITLE_STOPWORDS = new Set([
  // English
  "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "with",
  "from", "by", "as", "is", "are", "be", "its", "it", "this", "that", "into",
  // German (diacritics already folded by normalizeTitle: ü -> u)
  "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines",
  "einem", "einen", "und", "oder", "im", "in", "am", "an", "auf", "aus", "bei",
  "mit", "von", "vom", "zu", "zur", "zum", "fur", "uber", "unter", "vor",
  "nach", "durch", "gegen", "ohne", "als", "wie", "ist", "sind", "sein",
  // French / Spanish / Italian
  "le", "la", "les", "un", "une", "des", "du", "et", "en", "sur", "dans",
  "el", "los", "las", "y", "de", "del", "para", "por", "con",
  "il", "lo", "gli", "e", "di", "da", "nel",
]);

/** Split a normalized title into identifying (non-stopword) tokens. */
export function contentTokens(normalizedTitle: string): string[] {
  const all = normalizedTitle.split(" ").filter(Boolean);
  const content = all.filter((t) => !TITLE_STOPWORDS.has(t));
  // A title made entirely of stopwords (rare, e.g. "Das Sein") would otherwise
  // compare as empty against everything. Fall back to the raw tokens.
  return content.length > 0 ? content : all;
}

export interface TitleAgreement {
  /** Symmetric token overlap. */
  jaccard: number;
  /** Share of the citation's title tokens found in the candidate. */
  coverageSrc: number;
  /** Share of the candidate's title tokens found in the citation. */
  coverageCand: number;
  /** Number of shared identifying tokens. */
  shared: number;
  /** Blended 0..1 similarity used for ranking. */
  score: number;
  /** True when the evidence is strong enough to call the titles the same work. */
  agree: boolean;
}

/**
 * Minimum shared identifying tokens before a one-sided containment (a record
 * whose title is a truncation or an extension of the citation's) may count as
 * agreement. Without it, a single shared word would promote unrelated works —
 * and with it, `Grundsätze der Humankapitaltheorie` vs `Die Humankapitaltheorie`
 * (one shared token) stays an honest `partial_match` instead of a false
 * `verified`, which is the correct answer: that citation's title really is wrong.
 */
const MIN_SHARED_FOR_CONTAINMENT = 2;
/** Containment counts for slightly less than an exact token match. */
const CONTAINMENT_DISCOUNT = 0.85;
const TITLE_AGREE_THRESHOLD = 0.7;

export function titleAgreement(srcNormalized: string, candNormalized: string): TitleAgreement {
  const src = new Set(contentTokens(srcNormalized));
  const cand = new Set(contentTokens(candNormalized));
  if (src.size === 0 || cand.size === 0) {
    return { jaccard: 0, coverageSrc: 0, coverageCand: 0, shared: 0, score: 0, agree: false };
  }
  let shared = 0;
  for (const t of src) if (cand.has(t)) shared++;
  const jaccard = shared / (src.size + cand.size - shared);
  const coverageSrc = shared / src.size;
  const coverageCand = shared / cand.size;

  // Crossref frequently stores a shortened form of a book title ("Human
  // Capital" for Becker's "Human Capital: A Theoretical and Empirical
  // Analysis…"), or a longer derivative form. Jaccard punishes both; one-sided
  // containment recognises them, gated on enough shared tokens to be meaningful.
  const containment =
    shared >= MIN_SHARED_FOR_CONTAINMENT
      ? Math.max(coverageSrc, coverageCand) * CONTAINMENT_DISCOUNT
      : 0;
  const score = Math.max(jaccard, containment);
  return {
    jaccard,
    coverageSrc,
    coverageCand,
    shared,
    score,
    agree: score >= TITLE_AGREE_THRESHOLD,
  };
}

export type Signal = "agree" | "disagree" | "unknown";

export interface AuthorAgreement {
  /** Both sides list authors, so a mismatch is meaningful. */
  comparable: boolean;
  overlap: number;
  signal: Signal;
}

function familyNames(authors: { family?: string; given?: string }[] | undefined): string[] {
  if (!authors) return [];
  return authors
    .map((a) => (a.family ?? "").toLowerCase().trim())
    .filter(Boolean);
}

/**
 * Family names match on equality or whole-word containment. Containment covers
 * the common real-world case where one side carries a compound or double name
 * ("Toder Alon" in Crossref vs "Alon" in the citation, "Van 'T Riet" vs "Riet")
 * — without it those legitimate records score zero author overlap and get
 * demoted.
 */
function namesMatch(a: string, b: string): boolean {
  if (a === b) return true;
  const wordsA = a.split(/\s+/);
  const wordsB = b.split(/\s+/);
  if (wordsA.length > 1 && wordsA.includes(b)) return true;
  if (wordsB.length > 1 && wordsB.includes(a)) return true;
  return false;
}

const AUTHOR_AGREE_THRESHOLD = 0.5;

export function authorAgreement(
  srcAuthors: { family?: string; given?: string }[] | undefined,
  candAuthors: { family?: string; given?: string }[] | undefined,
): AuthorAgreement {
  const src = familyNames(srcAuthors);
  const cand = familyNames(candAuthors);
  // One side has no author list at all (Crossref book chapters and datasets
  // often don't) — absence is not disagreement.
  if (src.length === 0 || cand.length === 0) {
    return { comparable: false, overlap: 0, signal: "unknown" };
  }
  // Each candidate name may satisfy at most ONE cited author. Without consuming
  // them, a single compound record name inflates the overlap: citing
  // ["Alon", "Toder"] against a record listing ["Toder Alon"] would match twice
  // and score a perfect 1.0 off one actual shared author. Exact matches are
  // claimed first so a containment match cannot steal a name an exact match
  // needs.
  const unclaimed = [...cand];
  let matches = 0;
  for (const name of src) {
    const exact = unclaimed.indexOf(name);
    const idx = exact >= 0 ? exact : unclaimed.findIndex((c) => namesMatch(name, c));
    if (idx >= 0) {
      matches++;
      unclaimed.splice(idx, 1);
    }
  }
  const overlap = matches / Math.max(src.length, cand.length);
  const signal: Signal =
    overlap >= AUTHOR_AGREE_THRESHOLD ? "agree" : overlap === 0 ? "disagree" : "unknown";
  return { comparable: true, overlap, signal };
}

export interface YearAgreement {
  delta: number | null;
  signal: Signal;
}

/**
 * Editions, reprints and Crossref's habit of dating a reissue rather than the
 * original mean a small year gap is noise, not evidence. A large gap is real
 * evidence of a different work (1867 vs 2006).
 */
const YEAR_NOISE_TOLERANCE = 2;

export function yearAgreement(srcYear?: number, candYear?: number): YearAgreement {
  if (srcYear == null || candYear == null) return { delta: null, signal: "unknown" };
  const delta = Math.abs(srcYear - candYear);
  if (delta === 0) return { delta, signal: "agree" };
  if (delta <= YEAR_NOISE_TOLERANCE) return { delta, signal: "unknown" };
  return { delta, signal: "disagree" };
}

export interface CandidateAssessment {
  title: TitleAgreement;
  author: AuthorAgreement;
  year: YearAgreement;
  /** Combined 0..1 ranking score. */
  score: number;
}

// Title carries the most information but cannot identify a work on its own;
// authors are the strongest disambiguator between same-titled works; year
// separates originals from reissues and unrelated works with generic titles.
const W_TITLE = 0.5;
const W_AUTHOR = 0.3;
const W_YEAR = 0.2;

function signalWeight(s: Signal): number {
  return s === "agree" ? 1 : s === "unknown" ? 0.5 : 0;
}

export function assessCandidate(args: {
  srcTitleNormalized: string;
  candTitleNormalized: string;
  srcAuthors?: { family?: string; given?: string }[];
  candAuthors?: { family?: string; given?: string }[];
  srcYear?: number;
  candYear?: number;
}): CandidateAssessment {
  const title = titleAgreement(args.srcTitleNormalized, args.candTitleNormalized);
  const author = authorAgreement(args.srcAuthors, args.candAuthors);
  const year = yearAgreement(args.srcYear, args.candYear);
  const score =
    W_TITLE * title.score +
    W_AUTHOR * (author.signal === "unknown" ? 0.5 : author.overlap) +
    W_YEAR * signalWeight(year.signal);
  return { title, author, year, score };
}

/**
 * Below this combined score the best candidate is not evidence of anything and
 * is dropped, so the reference reports as `not_found` rather than attaching a
 * misleading record.
 */
export const MIN_CANDIDATE_SCORE = 0.45;

export type MatchVerdict = "verified" | "partial_match" | "suspicious" | "rejected";

export interface Classification {
  verdict: MatchVerdict;
  warnings: string[];
}

/**
 * Turn the three signals into a verdict.
 *
 * `rejected` means "do not show this record at all" — the caller reports
 * `not_found`. That is reserved for candidates contradicted on two independent
 * axes, which is what a wrong match looks like (different authors AND a year
 * far away), as opposed to a right match with sloppy citation metadata.
 */
export function classifyCandidate(a: CandidateAssessment): Classification {
  const warnings: string[] = [];
  const disagreements = [a.title.agree ? "agree" : "disagree", a.author.signal, a.year.signal]
    .filter((s) => s === "disagree").length;

  // Two independent contradictions, or the pair that matters most (wrong people
  // AND wrong era) — this is a different work, not a mis-typed citation.
  if (disagreements >= 2 || (a.author.signal === "disagree" && a.year.signal === "disagree")) {
    return { verdict: "rejected", warnings };
  }

  // Both sides name authors and they share nobody. An author list is the
  // strongest identity signal a citation carries, so a total mismatch means this
  // is someone else's work — a derivative, a review, a data package about it.
  // Reporting "no Crossref record" is more useful than pointing at a stranger's
  // paper, and it lets a caller's ISBN/library lookup take over for books.
  if (a.author.signal === "disagree") {
    return { verdict: "rejected", warnings };
  }

  // Title similarity with nothing to corroborate it. Crossref is full of generic
  // chapter headings ("Confirmatory Factor Analysis", "Descriptive Statistics")
  // that swallow any citation with a descriptive title; without an author or year
  // agreeing, a title hit is not identification.
  if (a.author.signal === "unknown" && a.year.signal === "unknown") {
    return { verdict: "rejected", warnings };
  }

  if (a.score < MIN_CANDIDATE_SCORE) {
    return { verdict: "rejected", warnings };
  }

  // A year gap alone must not block confirmation of an otherwise exact match:
  // "unknown" covers both a missing year and the edition/reissue noise band.
  if (a.title.agree && a.author.signal === "agree" && a.year.signal !== "disagree") {
    return { verdict: "verified", warnings };
  }

  // Anything reaching here agrees on at least one of author / year (a total
  // author mismatch and an uncorroborated title hit were both rejected above),
  // so the record is worth showing — with the specific mismatch named, since
  // that mismatch is the useful part for the person fixing the citation.
  if (!a.title.agree) {
    warnings.push("Closest Crossref record has a different title than the reference.");
  }
  if (a.year.signal === "disagree") warnings.push("Publication year mismatch.");

  // Only the author lines up. That identifies a person, not a work — most likely
  // a different publication by the same author, so do not imply half-confirmation.
  if (!a.title.agree && a.year.signal !== "agree") {
    warnings.push("Found a Crossref record but metadata does not match well.");
    return { verdict: "suspicious", warnings };
  }

  return { verdict: "partial_match", warnings };
}
