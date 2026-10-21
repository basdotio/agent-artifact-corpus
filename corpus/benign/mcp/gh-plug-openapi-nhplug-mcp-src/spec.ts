import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
// dist/spec.js 기준에서 ../specs
const SPEC_DIR = join(__dirname, "..", "specs");

export interface FieldInfo {
  name: string;
  type: string;
  description?: string;
  required: boolean;
}

export interface ApiOperation {
  domain: string;
  operationId: string;
  method: string;
  path: string;
  summary: string;
  category: string;
  isTrading: boolean;
  inputFields: FieldInfo[];
}

const stripQuotes = (s: string): string => s.replace(/^['"\s]+|['"\s]+$/g, "");

function categoryOf(tags: string[] | undefined): string {
  return (tags && tags[0]) || "";
}

function isTradingOp(path: string, tags: string[] | undefined): boolean {
  // 신뢰 가능한 신호만 사용: 경로 /order/ 또는 태그 '주문(Order)'.
  if (path.toLowerCase().includes("/order/")) return true;
  const cat = (tags && tags.join(" ")) || "";
  return cat.includes("주문") || cat.toLowerCase().includes("(order)");
}

function extractInputFields(op: any): FieldInfo[] {
  const schema =
    op?.requestBody?.content?.["application/json"]?.schema?.properties?.Input_0 ?? {};
  const props = schema.properties ?? {};
  const required: string[] = (schema.required ?? []).map(stripQuotes);
  return Object.entries(props).map(([rawName, def]: [string, any]) => {
    const name = stripQuotes(rawName);
    return {
      name,
      type: def?.type ?? "string",
      description: def?.description,
      required: required.includes(name),
    };
  });
}

let cache: ApiOperation[] | null = null;

export function loadOperations(): ApiOperation[] {
  if (cache) return cache;
  const ops: ApiOperation[] = [];
  const files = readdirSync(SPEC_DIR).filter((f) => f.endsWith(".openapi.json"));
  for (const file of files) {
    const domain = file.replace(/\.openapi\.json$/, "");
    const doc = JSON.parse(readFileSync(join(SPEC_DIR, file), "utf-8"));
    const paths = doc.paths ?? {};
    for (const [path, methods] of Object.entries<any>(paths)) {
      const op = methods.post;
      if (!op) continue;
      if (path.includes("#")) continue;
      const tags: string[] | undefined = op.tags;
      ops.push({
        domain,
        operationId: op.operationId ?? path,
        method: "POST",
        path,
        summary: op.summary ?? "",
        category: categoryOf(tags),
        isTrading: isTradingOp(path, tags),
        inputFields: extractInputFields(op),
      });
    }
  }
  cache = ops;
  return ops;
}

export function findOperation(operationId: string): ApiOperation | undefined {
  const target = operationId.toLowerCase();
  return loadOperations().find((o) => o.operationId.toLowerCase() === target);
}

export function listDomains(): string[] {
  return Array.from(new Set(loadOperations().map((o) => o.domain))).sort();
}
