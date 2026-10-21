import type { CslItemData } from "./types.js";
import * as crossref from "./crossref.js";
import * as openalex from "./openalex.js";
import { checkByIssn, type DoajStatus } from "./doaj.js";
import { assessCandidate, classifyCandidate, type CandidateAssessment } from "./match-score.js";

export type CheckVerdict =
  | "verified"
  | "partial_match"
  | "not_found"
  | "suspicious"
  | "check_failed";

export interface CitationCheckResult {
  key: string;
  title: string;
  status: CheckVerdict;
  crossrefMatch: {
    doi?: string;
    title?: string;
    titleSimilarity: number;
    authorOverlap: number;
    yearMatch: boolean;
  } | null;
  openalexMatch: {
    citedByCount?: number;
    isOa?: boolean;
    journalName?: string;
  } | null;
  journalStatus: DoajStatus;
  retracted: boolean;
  warnings: string[];
  /** Set on the document/free-text path: the raw reference string this verdict came from. */
  sourceRef?: string;
}

export interface QuickCheckResult {
  citations: CitationCheckResult[];
  checkedAt: string;
}

export function normalizeTitle(t: string | undefined): string {
  if (!t) return "";
  // NFKD decomposes accented letters into base + combining mark (ü -> u + ̈);
  // the Unicode-aware class then drops the combining marks (they are \p{M}, not
  // \p{L}/\p{N}) — folding diacritics for free while KEEPING non-Latin letters
  // (Cyrillic/Greek/CJK/Arabic). The ASCII-only /[^a-z0-9\s]/ this replaces
  // stripped every non-Latin character, leaving non-English titles with zero
  // tokens and wrongly flagged as fabricated. (Diacritic-DROPPED citation forms
  // like "Muller"/"Korper" now match "Müller"/"Körper"; digraph-EXPANDED forms
  // like "Mueller"/"Koerper" and non-decomposable letters like ß/Ł/Ø are out of
  // scope for this fold.)
  return t
    .normalize("NFKD")
    .toLowerCase()
    // Fold Latin/general diacritics (Combining Diacritical Marks block U+0300–U+036F
    // that NFKD split off) so "Müller" -> "muller". Targeted range, NOT a blanket
    // \p{M} strip, so combining marks that are semantic letters in their script
    // (Devanagari/Thai vowel signs, Arabic harakat) are preserved, not corrupted.
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^\p{L}\p{N}\p{M}\s]/gu, "")  // keep letters, numbers, remaining marks; drop punctuation/symbols
    .replace(/\s+/g, " ")
    .trim();
}

export function jaccardSimilarity(a: string, b: string): number {
  const setA = new Set(a.split(" ").filter(Boolean));
  const setB = new Set(b.split(" ").filter(Boolean));
  if (setA.size === 0 && setB.size === 0) return 1;
  if (setA.size === 0 || setB.size === 0) return 0;
  let intersection = 0;
  for (const w of setA) if (setB.has(w)) intersection++;
  return intersection / (setA.size + setB.size - intersection);
}

function extractFamilyNames(authors: { family?: string; given?: string }[] | undefined): string[] {
  if (!authors) return [];
  return authors.map((a) => (a.family ?? "").toLowerCase()).filter(Boolean);
}

export function authorOverlapScore(
  sourceAuthors: { family?: string; given?: string }[] | undefined,
  crossrefAuthors: crossref.CrossrefAuthor[] | undefined,
): number {
  const src = extractFamilyNames(sourceAuthors);
  const cr = (crossrefAuthors ?? []).map((a) => (a.family ?? "").toLowerCase()).filter(Boolean);
  if (src.length === 0 && cr.length === 0) return 1;
  if (src.length === 0 || cr.length === 0) return 0;
  let matches = 0;
  for (const name of src) if (cr.includes(name)) matches++;
  return matches / Math.max(src.length, cr.length);
}

function getCitationYear(item: CslItemData): number | undefined {
  const parts = item.issued?.["date-parts"]?.[0];
  if (!parts?.[0]) return undefined;
  return typeof parts[0] === "number" ? parts[0] : parseInt(String(parts[0]), 10) || undefined;
}

/** How many candidates to ask Crossref for on the fuzzy path. */
const CANDIDATE_ROWS = 8;
/** Family names beyond the first few add noise to the query, not signal. */
const QUERY_AUTHOR_LIMIT = 3;

/**
 * Build the query for Crossref's fuzzy bibliographic search out of everything
 * the citation knows — not just its title.
 *
 * This is the single highest-impact part of the match: a title-only query for
 * `"Grundsätze der Humankapitaltheorie"` does not return Hiller's actual 2006
 * WiSt article anywhere in its top results, while the same query plus the author
 * name and year returns it at rank 1. Crossref's own relevance ranking is good;
 * it just needs to be given the metadata.
 */
export function buildBibliographicQuery(item: CslItemData): string {
  const authors = (item.author ?? [])
    .map((a) => a.family?.trim())
    .filter((n): n is string => Boolean(n))
    .slice(0, QUERY_AUTHOR_LIMIT);
  const year = getCitationYear(item);
  const container = Array.isArray(item["container-title"])
    ? item["container-title"][0]
    : item["container-title"];
  return [item.title, ...authors, year, container]
    .filter(Boolean)
    .join(" ")
    .replace(/\s+/g, " ")
    .trim();
}

interface ScoredCandidate {
  work: crossref.CrossrefWork;
  assessment: CandidateAssessment;
}

/**
 * Rank candidates on title, authors and year together and return the best one.
 *
 * The previous implementation maximised title Jaccard alone, which is why a
 * 1867 book on sheep breeding beat a 2006 economics article: both start with
 * "Grundsätze der". Ranking on the combination means a candidate has to agree
 * with the citation on more than one axis to win.
 */
export function pickBestCandidate(
  item: CslItemData,
  srcTitleNormalized: string,
  srcYear: number | undefined,
  candidates: crossref.CrossrefWork[],
): ScoredCandidate | null {
  // Viability first, score second. Ranking on raw score alone lets a candidate
  // that will be rejected anyway (an exact-title derivative with different
  // authors, say) outrank a lower-scoring candidate that would have verified —
  // and since only the winner is classified, the reference would come back
  // `not_found` while a usable record sat one position below it.
  let bestViable: ScoredCandidate | null = null;
  let bestRejected: ScoredCandidate | null = null;
  for (const work of candidates) {
    const assessment = assessCandidate({
      srcTitleNormalized,
      candTitleNormalized: normalizeTitle(work.title?.[0]),
      srcAuthors: item.author,
      candAuthors: work.author,
      srcYear,
      candYear: crossref.extractYear(work),
    });
    const scored: ScoredCandidate = { work, assessment };
    if (classifyCandidate(assessment).verdict === "rejected") {
      if (!bestRejected || assessment.score > bestRejected.assessment.score) bestRejected = scored;
      continue;
    }
    if (!bestViable || assessment.score > bestViable.assessment.score) bestViable = scored;
  }
  // No viable candidate: hand back the best rejected one so the caller still
  // reports `not_found` through the same path (and can log what it saw).
  return bestViable ?? bestRejected;
}

async function checkSingle(item: CslItemData): Promise<CitationCheckResult> {
  const result: CitationCheckResult = {
    key: (item.id as string) ?? "",
    title: item.title ?? "",
    status: "not_found",
    crossrefMatch: null,
    openalexMatch: null,
    journalStatus: "unknown",
    retracted: false,
    warnings: [],
  };

  const srcTitle = normalizeTitle(item.title);
  const srcYear = getCitationYear(item);
  let crWork: crossref.CrossrefWork | null = null;
  let crossrefUnreachable = false;

  if (item.DOI) {
    try {
      crWork = await crossref.checkDoi(item.DOI);
    } catch {
      crossrefUnreachable = true;
    }
  }

  // Assessment of the candidate we settled on, carried down to the verdict so
  // the classification sees the same signals the ranking did.
  let best: ScoredCandidate | null = null;

  if (!crWork && !crossrefUnreachable && item.title) {
    try {
      const candidates = await crossref.searchByBibliographic(
        buildBibliographicQuery(item),
        CANDIDATE_ROWS,
      );
      best = pickBestCandidate(item, srcTitle, srcYear, candidates);
      if (best) crWork = best.work;
    } catch {
      crossrefUnreachable = true;
    }
  }

  // Couldn't reach Crossref at all — say so instead of mislabelling a real
  // reference as "not found".
  if (!crWork && crossrefUnreachable) {
    result.status = "check_failed";
    result.warnings.push("Could not reach Crossref — re-run to check this reference.");
    return result;
  }

  if (crWork) {
    // A DOI lookup is an identity match, not a guess — there is no candidate to
    // reject, so it keeps the legacy scoring path and is always attached.
    const assessment =
      best?.assessment ??
      assessCandidate({
        srcTitleNormalized: srcTitle,
        candTitleNormalized: normalizeTitle(crWork.title?.[0]),
        srcAuthors: item.author,
        candAuthors: crWork.author,
        srcYear,
        candYear: crossref.extractYear(crWork),
      });
    const classification = best ? classifyCandidate(assessment) : null;

    // The best candidate contradicts the citation on two axes — showing it would
    // be worse than showing nothing, which is exactly the failure this fixes.
    if (classification?.verdict === "rejected") {
      result.status = "not_found";
      result.warnings.push("No matching record in Crossref — this reference may be fabricated.");
      return withOpenAlex(result, item, null);
    }

    result.crossrefMatch = {
      doi: crWork.DOI,
      title: crWork.title?.[0],
      titleSimilarity: Math.round(assessment.title.score * 100) / 100,
      authorOverlap: Math.round(assessment.author.overlap * 100) / 100,
      yearMatch: assessment.year.signal !== "disagree",
    };

    if (crossref.isRetracted(crWork)) {
      result.retracted = true;
      result.warnings.push("This work has been retracted.");
    }

    if (classification) {
      result.status = classification.verdict as CheckVerdict;
      result.warnings.push(...classification.warnings);
    } else {
      // DOI path: the record is authoritative. Still surface metadata drift so a
      // copy-pasted DOI that points somewhere else is visible.
      result.status = "verified";
      if (!assessment.title.agree && assessment.title.score < 0.4) {
        result.warnings.push("Title differs from Crossref record.");
      }
      if (assessment.year.signal === "disagree") {
        result.warnings.push("Publication year mismatch.");
      }
    }

    const issns = crWork.ISSN ?? [];
    if (issns.length > 0) {
      result.journalStatus = await checkByIssn(issns[0]!);
    }
  }

  return withOpenAlex(result, item, crWork);
}

/**
 * Enrich a result with OpenAlex (citation count, open-access + DOAJ signal).
 *
 * Extracted so the "candidate rejected" early return still gets enrichment for a
 * citation that carried its own DOI, instead of silently skipping it.
 */
async function withOpenAlex(
  result: CitationCheckResult,
  item: CslItemData,
  crWork: crossref.CrossrefWork | null,
): Promise<CitationCheckResult> {
  let oaWork: openalex.OpenAlexWork | null = null;
  if (item.DOI) {
    oaWork = await openalex.lookupByDoi(item.DOI);
  } else if (crWork?.DOI) {
    oaWork = await openalex.lookupByDoi(crWork.DOI);
  }

  if (oaWork) {
    result.openalexMatch = {
      citedByCount: oaWork.cited_by_count,
      isOa: oaWork.open_access?.is_oa ?? oaWork.is_oa,
      journalName: oaWork.primary_location?.source?.display_name,
    };
    if (oaWork.primary_location?.source?.is_in_doaj === true) {
      result.journalStatus = "doaj_listed";
    }
  }

  return result;
}

/**
 * Give refs that died on transient network failures (check_failed) ONE more
 * chance after the parallel burst has drained. Sequential (concurrency 1) so it
 * cannot re-create the burst that killed them, and bounded by a wall-clock
 * budget so a hard API outage cannot stall a scan for minutes. Mutates
 * `results` in place.
 */
export async function salvageCheckFailed<T>(
  results: CitationCheckResult[],
  inputs: T[],
  recheck: (input: T) => Promise<CitationCheckResult>,
): Promise<void> {
  const failed = results
    .map((r, i) => (r.status === "check_failed" ? i : -1))
    .filter((i) => i >= 0);
  if (failed.length === 0) return;
  // Let any active rate-limit window pass before the first re-attempt.
  await new Promise((r) => setTimeout(r, 1000));
  const deadline = Date.now() + 60_000;
  for (const i of failed) {
    if (Date.now() > deadline) return;
    const retry = await recheck(inputs[i]!);
    if (retry.status !== "check_failed") results[i] = retry;
  }
}

/** Check every reference against Crossref, OpenAlex and DOAJ. No API key needed. */
export async function quickCheck(items: CslItemData[]): Promise<QuickCheckResult> {
  const batchSize = 10;
  const results: CitationCheckResult[] = [];

  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize);
    const batchResults = await Promise.all(batch.map(checkSingle));
    results.push(...batchResults);
  }

  await salvageCheckFailed(results, items, checkSingle);

  return { citations: results, checkedAt: new Date().toISOString() };
}
