import { readFileSync } from "fs";
import { extname } from "path";

export interface Token {
  name: string;
  value: string;
  type: string;
  group?: string;
  resolvedValue?: string;
}

interface DTCGNode {
  $value?: string;
  $type?: string;
  [key: string]: unknown;
}

export function parseTokens(filePath: string): Token[] {
  const ext = extname(filePath);

  if (ext !== ".json" && ext !== ".css") {
    throw new Error(`Unsupported token file format: ${ext}. Use .json (DTCG) or .css`);
  }

  const content = readFileSync(filePath, "utf-8");

  if (ext === ".json") {
    const parsed = JSON.parse(content);
    const tokens = isDTCG(parsed) ? parseDTCG(parsed) : parsePlainJSON(parsed);
    resolveAliases(tokens);
    return tokens;
  }

  if (ext === ".css") {
    return parseCSS(content);
  }

  return [];
}

function parseDTCG(obj: Record<string, unknown>, prefix = "", group = ""): Token[] {
  const tokens: Token[] = [];

  for (const [key, value] of Object.entries(obj)) {
    if (key.startsWith("$")) continue;

    const path = prefix ? `${prefix}.${key}` : key;
    const node = value as DTCGNode;

    if (node.$value !== undefined) {
      tokens.push({
        name: path,
        value: String(node.$value),
        type: String(node.$type || "unknown"),
        group: group || key,
      });
    } else if (typeof node === "object" && node !== null) {
      tokens.push(...parseDTCG(node as Record<string, unknown>, path, group || key));
    }
  }

  return tokens;
}

function resolveAliases(tokens: Token[]): void {
  const tokenMap = new Map(tokens.map((t) => [t.name, t]));

  for (const token of tokens) {
    const aliasMatch = token.value.match(/^\{(.+)\}$/);
    if (!aliasMatch) continue;

    const referencedName = aliasMatch[1];
    const referenced = tokenMap.get(referencedName);
    if (referenced) {
      token.resolvedValue = referenced.value;
    }
  }
}

function isDTCG(obj: Record<string, unknown>): boolean {
  for (const value of Object.values(obj)) {
    if (typeof value !== "object" || value === null) continue;
    const node = value as Record<string, unknown>;
    if ("$value" in node) return true;
    if (isDTCG(node)) return true;
  }
  return false;
}

function parsePlainJSON(obj: Record<string, unknown>, prefix = "", group = ""): Token[] {
  const tokens: Token[] = [];

  for (const [key, value] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${key}` : key;

    if (typeof value === "object" && value !== null) {
      tokens.push(...parsePlainJSON(value as Record<string, unknown>, path, group || key));
    } else if (typeof value === "string" || typeof value === "number") {
      const strValue = String(value);
      tokens.push({
        name: path,
        value: strValue,
        type: inferType(strValue),
        group: group || key,
      });
    }
  }

  return tokens;
}

function inferType(value: string): string {
  if (value.startsWith("#") || value.startsWith("rgb") || value.startsWith("hsl")) {
    return "color";
  }
  if (value.endsWith("px") || value.endsWith("rem") || value.endsWith("em")) {
    return "dimension";
  }
  if (/^[\d.]+$/.test(value)) {
    return "number";
  }
  return "string";
}

function parseCSS(content: string): Token[] {
  const tokens: Token[] = [];
  const stripped = content.replace(/\/\*[\s\S]*?\*\//g, "");
  const regex = /--([\w-]+)\s*:\s*([^;]+);/g;
  let match;

  while ((match = regex.exec(stripped)) !== null) {
    const rawName = match[1];
    const value = match[2].trim();
    const name = rawName.replace(/-/g, ".");

    tokens.push({ name, value, type: inferType(value) });
  }

  return tokens;
}
