import { z } from "zod";
import { crptAuthPost } from "../client.js";
import type { CrptProductInfoResponse, CrptProductItem } from "../types.js";

// ⚠️ The True API has no free-text "search by name/brand" endpoint — that belongs to
// the National Catalog (nk.crpt.ru), a separate API. Product lookup in the True API is
// by GTIN via POST /api/v4/true-api/product/info. This tool therefore looks products up
// by GTIN. The exact request/response shape is research-derived and UNVERIFIED against a
// live token (the True API gates everything behind cert-challenge auth); parsing is kept
// tolerant. See README "Авторизация".

export const searchProductsSchema = z.object({
  query: z
    .string()
    .trim()
    .min(1)
    .describe("GTIN товара (14 цифр). Поиск по названию/бренду требует Нацкаталог — вне API."),
});

export interface ProductSearchResult {
  query: string;
  total: number;
  results: Array<{
    gtin: string | null;
    productName: string | null;
    producerName: string | null;
    brand: string | null;
  }>;
}

export async function handleSearchProducts(
  params: z.infer<typeof searchProductsSchema>,
): Promise<ProductSearchResult> {
  const result = (await crptAuthPost("/api/v4/true-api/product/info", {
    gtins: [params.query],
  })) as CrptProductInfoResponse;

  const items = (result.results ?? []).map((item: CrptProductItem) => ({
    gtin: item.gtin ?? null,
    productName: item.productName ?? null,
    producerName: item.producerName ?? null,
    brand: item.brand ?? null,
  }));

  return { query: params.query, total: result.total ?? items.length, results: items };
}
