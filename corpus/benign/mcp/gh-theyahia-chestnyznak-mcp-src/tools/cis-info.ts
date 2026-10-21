import { z } from "zod";
import { crptAuthPost } from "../client.js";
import type { CrptCisInfoResponse } from "../types.js";

// Real True API CIS lookup: POST /api/v3/true-api/cises/info with a JSON array of CIS
// strings (plural "cises", max 100). ⚠️ Method/version are research-derived and
// UNVERIFIED against a live token (True API requires cert-challenge auth). Parsing is
// tolerant. See README "Авторизация".

export const getCisInfoSchema = z.object({
  cis: z
    .string()
    .trim()
    .min(1)
    .describe("CIS (код идентификации) для получения информации из True API"),
});

export interface CisInfoResult {
  cis: string;
  gtin: string | null;
  productName: string | null;
  producerName: string | null;
  producerInn: string | null;
  status: string | null;
}

export async function handleGetCisInfo(
  params: z.infer<typeof getCisInfoSchema>,
): Promise<CisInfoResult> {
  const result = await crptAuthPost("/api/v3/true-api/cises/info", [params.cis]);

  // The endpoint returns either a single object or an array (one entry per CIS).
  const entry = (Array.isArray(result) ? result[0] : result) as
    | CrptCisInfoResponse
    | undefined;

  return {
    cis: entry?.cis ?? params.cis,
    gtin: entry?.gtin ?? null,
    productName: entry?.productName ?? null,
    producerName: entry?.producerName ?? null,
    producerInn: entry?.producerInn ?? null,
    status: entry?.status ?? null,
  };
}
