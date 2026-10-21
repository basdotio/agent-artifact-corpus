import { existsSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { dirname, isAbsolute, resolve } from "node:path";
import { z } from "zod";
import type { Permission, RuntimeConfig } from "./types.js";

const permissionSchema = z.enum(["read-only", "workspace-write"]);
const webSearchModeSchema = z.enum(["disabled", "cached", "live"]);
const fileSchema = z.object({
  nodeName: z.string().trim().min(1).max(100),
  host: z.string().trim().min(1).default("0.0.0.0"),
  port: z.number().int().min(0).max(65535).default(4545),
  dataDir: z.string().min(1).default("./data"),
  logFile: z.string().min(1).default("./logs/lan-a2a.jsonl"),
  maxConcurrentTasks: z.number().int().min(1).max(8).default(2),
  discovery: z.object({ enabled: z.boolean().default(true) }).default({ enabled: true }),
  workspaces: z.record(z.string().min(1).max(100), z.object({
    path: z.string().min(1),
    maxPermission: permissionSchema.default("read-only"),
    skipGitRepoCheck: z.boolean().default(false),
    networkAccessEnabled: z.boolean().default(false),
    webSearchMode: webSearchModeSchema.default("disabled"),
  })).default({}),
});

export async function loadConfig(path = process.env.LAN_A2A_CONFIG ?? "config.json"): Promise<RuntimeConfig> {
  const configPath = resolve(path);
  if (!existsSync(configPath)) throw new Error(`配置文件不存在：${configPath}，请先执行 init`);
  const parsed = fileSchema.parse(JSON.parse(await readFile(configPath, "utf8")));
  const base = dirname(configPath);
  const absolute = (value: string) => isAbsolute(value) ? value : resolve(base, value);
  return {
    configPath,
    nodeName: parsed.nodeName,
    host: parsed.host,
    port: parsed.port,
    dataDir: absolute(parsed.dataDir),
    logFile: absolute(parsed.logFile),
    maxConcurrentTasks: parsed.maxConcurrentTasks,
    discoveryEnabled: parsed.discovery.enabled,
    workspaces: Object.fromEntries(Object.entries(parsed.workspaces).map(([name, workspace]) => [
      name,
      { ...workspace, path: absolute(workspace.path) },
    ])),
  };
}

export function permissionAllowed(requested: Permission, maximum: Permission): boolean {
  return requested === "read-only" || maximum === "workspace-write";
}
