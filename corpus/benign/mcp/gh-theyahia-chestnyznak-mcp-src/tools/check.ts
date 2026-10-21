import { z } from "zod";
import { crptPublicGet } from "../client.js";
import type { CrptCheckResponse, MarkingCheckResult } from "../types.js";

/** DataMatrix is the default; the public endpoint requires a codeType. */
export const codeTypeSchema = z
  .enum(["datamatrix", "qr", "ean13"])
  .default("datamatrix")
  .describe("Тип кода: datamatrix (по умолчанию), qr или ean13");

export const checkMarkingCodeSchema = z.object({
  code: z
    .string()
    .trim()
    .min(1)
    .describe("Код маркировки товара (DataMatrix, QR, штрихкод EAN-13)"),
  codeType: codeTypeSchema,
});

export const getProductInfoSchema = checkMarkingCodeSchema;

/** Nested detail wins over root, mirroring the real OSS clients (e.g. MarkScanner). */
function pick(raw: CrptCheckResponse, key: string): string | null {
  const nested =
    typeof raw.category === "string"
      ? (raw[`${raw.category}Data`] as Record<string, unknown> | undefined)
      : undefined;
  const value = nested?.[key] ?? raw[key];
  if (value == null) return null;
  return typeof value === "string" ? value : String(value);
}

/** Call the public check endpoint and normalize the (defensively parsed) response. */
export async function fetchCheck(
  code: string,
  codeType: string,
): Promise<MarkingCheckResult> {
  const path = `/check?code=${encodeURIComponent(code)}&codeType=${encodeURIComponent(codeType)}`;
  const raw = (await crptPublicGet(path)) as CrptCheckResponse;

  return {
    code,
    found: raw.codeFounded ?? false,
    valid: raw.checkResult ?? false,
    status: pick(raw, "status"),
    productName: pick(raw, "productName"),
    category: raw.category ?? null,
    producerName: pick(raw, "producerName"),
    ownerName: pick(raw, "ownerName"),
    ownerInn: pick(raw, "ownerInn"),
  };
}

/** Minimal authenticity check. */
export async function handleCheckMarkingCode(
  params: z.infer<typeof checkMarkingCodeSchema>,
): Promise<Pick<MarkingCheckResult, "code" | "found" | "valid" | "status">> {
  const { code, found, valid, status } = await fetchCheck(params.code, params.codeType);
  return { code, found, valid, status };
}

/** Full product detail. */
export async function handleGetProductInfo(
  params: z.infer<typeof getProductInfoSchema>,
): Promise<MarkingCheckResult> {
  return fetchCheck(params.code, params.codeType);
}
