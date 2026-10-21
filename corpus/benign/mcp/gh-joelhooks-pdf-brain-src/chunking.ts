import type { Document, LibraryConfig } from "./types.js";

export type ChunkerMetadata = {
  /** Stable identifier for the chunking algorithm implementation */
  id: string;
  /** Monotonic version for breaking chunker changes */
  version: number;
  /** Unit used for chunk sizing and overlap */
  unit: "chars";
  chunkSize: number;
  chunkOverlap: number;
};

export const CURRENT_CHUNKER: Record<
  "pdf" | "markdown",
  { id: string; version: number }
> = {
  // v2: paragraph-preserving normalization + hyphenation fix
  pdf: { id: "pdf-extractor:paragraphs-v2", version: 2 },
  // v1: section-aware markdown parsing + placeholder-preserving chunking
  markdown: { id: "markdown-extractor:sections+placeholders-v1", version: 1 },
};

export function inferFileTypeFromPath(path: string): "pdf" | "markdown" {
  const lower = path.toLowerCase();
  if (lower.endsWith(".md") || lower.endsWith(".markdown")) return "markdown";
  return "pdf";
}

export function buildChunkerMetadata(
  fileType: "pdf" | "markdown",
  config: Pick<LibraryConfig, "chunkSize" | "chunkOverlap">,
): ChunkerMetadata {
  const base = CURRENT_CHUNKER[fileType];
  return {
    id: base.id,
    version: base.version,
    unit: "chars",
    chunkSize: config.chunkSize,
    chunkOverlap: config.chunkOverlap,
  };
}

export function parseChunkerMetadata(value: unknown): ChunkerMetadata | null {
  if (!value || typeof value !== "object") return null;
  const v: any = value;

  const id = typeof v.id === "string" ? v.id : null;
  const version = typeof v.version === "number" ? v.version : null;
  const unit = v.unit === "chars" ? ("chars" as const) : null;
  const chunkSize = typeof v.chunkSize === "number" ? v.chunkSize : null;
  const chunkOverlap = typeof v.chunkOverlap === "number" ? v.chunkOverlap : null;

  if (!id || version === null || !unit || chunkSize === null || chunkOverlap === null) {
    return null;
  }

  return { id, version, unit, chunkSize, chunkOverlap };
}

export function getDocChunkerMetadata(doc: Document): ChunkerMetadata | null {
  const meta = doc.metadata;
  if (!meta || typeof meta !== "object") return null;
  const chunker = (meta as any).chunker;
  return parseChunkerMetadata(chunker);
}

export function assessDocChunker(
  doc: Document,
  config: Pick<LibraryConfig, "chunkSize" | "chunkOverlap">,
): {
  needsRechunk: boolean;
  code:
    | "ok"
    | "missing_metadata"
    | "id_version_mismatch"
    | "config_mismatch"
    | "unit_mismatch";
  reason: string;
  expected: ChunkerMetadata;
  actual: ChunkerMetadata | null;
} {
  const fileType =
    doc.fileType ??
    (doc.path ? inferFileTypeFromPath(doc.path) : ("pdf" as const));
  const expected = buildChunkerMetadata(fileType, config);
  const actual = getDocChunkerMetadata(doc);

  if (!actual) {
    return {
      needsRechunk: true,
      code: "missing_metadata",
      reason: "missing chunker metadata",
      expected,
      actual: null,
    };
  }

  if (actual.id !== expected.id || actual.version !== expected.version) {
    return {
      needsRechunk: true,
      code: "id_version_mismatch",
      reason: `chunker id/version mismatch (${actual.id}@${actual.version} != ${expected.id}@${expected.version})`,
      expected,
      actual,
    };
  }

  if (actual.chunkSize !== expected.chunkSize || actual.chunkOverlap !== expected.chunkOverlap) {
    return {
      needsRechunk: true,
      code: "config_mismatch",
      reason: `chunkSize/chunkOverlap mismatch (${actual.chunkSize}/${actual.chunkOverlap} != ${expected.chunkSize}/${expected.chunkOverlap})`,
      expected,
      actual,
    };
  }

  if (actual.unit !== expected.unit) {
    return {
      needsRechunk: true,
      code: "unit_mismatch",
      reason: `chunk unit mismatch (${actual.unit} != ${expected.unit})`,
      expected,
      actual,
    };
  }

  return { needsRechunk: false, code: "ok", reason: "ok", expected, actual };
}
