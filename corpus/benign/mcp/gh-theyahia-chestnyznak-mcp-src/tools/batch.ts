import { z } from "zod";
import { fetchCheck, codeTypeSchema } from "./check.js";

/** Cap concurrent upstream requests so a 50-code batch doesn't trigger rate limits. */
const CONCURRENCY = 5;

export const checkBatchSchema = z.object({
  codes: z
    .array(z.string().trim().min(1))
    .min(1)
    .max(50)
    .describe("Массив кодов маркировки (до 50 штук) для пакетной проверки"),
  codeType: codeTypeSchema,
});

export interface BatchItem {
  code: string;
  found: boolean;
  valid: boolean;
  status: string | null;
  productName?: string | null;
  error?: string;
}

export interface BatchResult {
  total: number;
  results: BatchItem[];
}

/** Run `fn` over `items` with at most `limit` in flight, preserving input order. */
async function mapLimit<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>,
): Promise<R[]> {
  const results = new Array<R>(items.length);
  let next = 0;
  async function worker(): Promise<void> {
    while (next < items.length) {
      const index = next++;
      results[index] = await fn(items[index], index);
    }
  }
  const workers = Array.from({ length: Math.min(limit, items.length) }, worker);
  await Promise.all(workers);
  return results;
}

export async function handleCheckBatch(
  params: z.infer<typeof checkBatchSchema>,
): Promise<BatchResult> {
  const results = await mapLimit(params.codes, CONCURRENCY, async (code) => {
    try {
      const r = await fetchCheck(code, params.codeType);
      return {
        code,
        found: r.found,
        valid: r.valid,
        status: r.status,
        productName: r.productName,
      } satisfies BatchItem;
    } catch (error) {
      return {
        code,
        found: false,
        valid: false,
        status: "error",
        error: error instanceof Error ? error.message : "Неизвестная ошибка",
      } satisfies BatchItem;
    }
  });

  return { total: results.length, results };
}
