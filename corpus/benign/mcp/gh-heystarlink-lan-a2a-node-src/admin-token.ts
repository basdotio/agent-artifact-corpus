import { randomBytes, timingSafeEqual } from "node:crypto";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { RuntimeConfig } from "./types.js";
import { writePrivateText } from "./files.js";

export async function loadAdminToken(config: RuntimeConfig): Promise<string> {
  const path = join(config.dataDir, "admin-token");
  try {
    const token = (await readFile(path, "utf8")).trim();
    if (token.length < 32) throw new Error("本机管理 Token 文件无效");
    return token;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== "ENOENT") throw error;
    const token = randomBytes(32).toString("hex");
    await writePrivateText(path, `${token}\n`);
    return token;
  }
}

export function matchesToken(expected: string, authorization: string | undefined): boolean {
  const supplied = authorization?.startsWith("Bearer ") ? authorization.slice(7) : "";
  const left = Buffer.from(expected);
  const right = Buffer.from(supplied);
  return left.length === right.length && timingSafeEqual(left, right);
}
