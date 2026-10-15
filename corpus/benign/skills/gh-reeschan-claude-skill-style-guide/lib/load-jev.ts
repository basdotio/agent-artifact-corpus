import { existsSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

// Jev クライアントの場所を決める。
// 環境変数 STYLE_GUIDE_JEV_MODULE → ~/.claude/shared/jev/jev.mjs (あれば) → 同梱の ./jev.mjs
export function jevModulePath(): string {
  const override = process.env.STYLE_GUIDE_JEV_MODULE;
  if (override) return override;
  const shared = join(homedir(), ".claude", "shared", "jev", "jev.mjs");
  if (existsSync(shared)) return shared;
  return join(dirname(fileURLToPath(import.meta.url)), "jev.mjs");
}

// 読み込んだモジュールの形は呼び出し側で確かめる
let cached: Promise<unknown> | null = null;
export async function loadJev(): Promise<unknown> {
  if (!cached) cached = import(pathToFileURL(jevModulePath()).href);
  return cached;
}
