// Locate files from the repo-level `shared/` folder (or the copy placed next to the compiled server).
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const jsonCache = new Map<string, unknown>();

export function sharedFile(name: string): string | null {
  for (const cand of [join(here, "_shared", name), join(here, "..", "..", "shared", name), join(here, "..", "shared", name)]) {
    if (existsSync(cand)) return cand;
  }
  return null;
}

export function sharedJson<T = any>(name: string): T {
  if (!jsonCache.has(name)) {
    const p = sharedFile(name);
    if (!p) throw new Error(`shared/${name} not found (run npm run build)`);
    jsonCache.set(name, JSON.parse(readFileSync(p, "utf8")));
  }
  return jsonCache.get(name) as T;
}

export function sharedText(name: string): string {
  const p = sharedFile(name);
  if (!p) throw new Error(`shared/${name} not found (run npm run build)`);
  return readFileSync(p, "utf8");
}
