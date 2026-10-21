// Shapes for the public mobile-app check endpoint (mobile.api.crpt.ru/mobile/check).
//
// ⚠️ The public endpoint is undocumented. These field names are derived from several
// independent open-source clients (li0ard/nechestniy_znak, MarkScanner, HomeMedkit,
// Fridger), NOT from official docs — they have not been verified against a captured
// live response here (the endpoint geo-blocks non-RU IPs). Treat as best-effort and
// keep the parsing defensive: the result flag is `checkResult` (not `isValid`), and
// detail fields (status/producer/owner) frequently live in a nested `<category>Data`
// object rather than at the root.

/** Our normalized output for check / get_product_info / check_batch. */
export interface MarkingCheckResult {
  code: string;
  /** Whether the marking code exists in the system (upstream `codeFounded`). */
  found: boolean;
  /** Whether the check passed (upstream `checkResult`). */
  valid: boolean;
  /** Status enum: EMITTED | APPLIED | INTRODUCED | RETIRED | WRITTEN_OFF | DISAGGREGATION | ... */
  status: string | null;
  productName: string | null;
  category: string | null;
  producerName: string | null;
  ownerName: string | null;
  ownerInn: string | null;
}

/** Raw upstream response from the public /mobile/check endpoint. */
export interface CrptCheckResponse {
  code?: string;
  codeFounded?: boolean;
  checkResult?: boolean;
  productName?: string;
  /** Product group key, e.g. "milk"/"tobacco"/"tires"; detail nested under `<category>Data`. */
  category?: string;
  status?: string;
  producerName?: string;
  ownerName?: string;
  ownerInn?: string;
  // Per-category detail nested under `<category>Data` (e.g. milkData, tobaccoData).
  [key: string]: unknown;
}

// --- Authenticated True API shapes (tolerant; live shapes unverified) ---

export interface CrptCisInfoResponse {
  cis?: string;
  gtin?: string;
  productName?: string;
  producerName?: string;
  producerInn?: string;
  status?: string;
  [key: string]: unknown;
}

export interface CrptProductInfoResponse {
  results?: CrptProductItem[];
  total?: number;
  [key: string]: unknown;
}

export interface CrptProductItem {
  gtin?: string;
  productName?: string;
  producerName?: string;
  brand?: string;
  [key: string]: unknown;
}
