import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync, copyFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { configDirectory } from "./settings.js";

export const AGENTS = ["codex", "claude", "grok", "opencode", "cursor", "antigravity"] as const;
export const isEditor = (agent: string) => agent === "cursor" || agent === "antigravity";

export function mcpConfig(agent: string) {
  if (!isEditor(agent)) throw new Error("MCP integration must be cursor or antigravity.");
  return { mcpServers: { "jev-classifier": {
    ...(agent === "cursor" ? { type: "stdio" } : {}),
    command: process.execPath,
    args: [fileURLToPath(new URL("./cli.js", import.meta.url)), "mcp", "--global", "--client", agent],
    env: { JEV_CONFIG_HOME: configDirectory() },
  } } };
}

export function integrationPath(agent: string, home = homedir()): string {
  if (agent === "cursor") return join(home, ".cursor", "mcp.json");
  if (agent === "antigravity") {
    // Older IDE releases still use this path. Prefer the file already in use.
    const current = join(home, ".gemini", "config", "mcp_config.json");
    const legacy = join(home, ".gemini", "antigravity", "mcp_config.json");
    return existsSync(current) || !existsSync(legacy) ? current : legacy;
  }
  throw new Error("Use connect cursor or connect antigravity. For OpenCode, use run opencode.");
}

/** Merge only our entry; refuse malformed configurations instead of losing user settings. */
export function connectEditor(agent: string, file = integrationPath(agent)): { file: string; backup?: string } {
  let config: Record<string, any> = {};
  if (existsSync(file)) {
    try { config = JSON.parse(readFileSync(file, "utf8")); }
    catch { throw new Error(`Cannot parse ${file}. Use config ${agent} and merge its MCP entry manually.`); }
    if (!config || typeof config !== "object" || Array.isArray(config) ||
      (config.mcpServers !== undefined && (!config.mcpServers || typeof config.mcpServers !== "object" || Array.isArray(config.mcpServers)))) {
      throw new Error(`Invalid MCP configuration at ${file}; no changes made.`);
    }
  }
  const entry = mcpConfig(agent).mcpServers["jev-classifier"];
  if (JSON.stringify(config.mcpServers?.["jev-classifier"]) === JSON.stringify(entry)) return { file };
  mkdirSync(dirname(file), { recursive: true, mode: 0o700 });
  const backup = existsSync(file) ? `${file}.jev-backup-${Date.now()}` : undefined;
  if (backup) copyFileSync(file, backup);
  config.mcpServers = { ...config.mcpServers, "jev-classifier": entry };
  const temporary = `${file}.${process.pid}.tmp`;
  writeFileSync(temporary, JSON.stringify(config, null, 2) + "\n", { mode: 0o600, flag: "wx" });
  renameSync(temporary, file);
  return { file, backup };
}

/** OpenCode v1 API-key providers. Subscription plugins may bypass baseURL, so are not advertised here. */
export function openCodeConfig(port: number): { provider: Record<string, { options: { baseURL: string } }> } {
  return { provider: Object.fromEntries([
    ["openai", "codex"], ["anthropic", "claude"], ["xai", "grok"],
  ].map(([provider, destination]) => [provider, { options: {
    baseURL: `http://127.0.0.1:${port}/clients/opencode/api/${destination}/v1`,
  } }])) };
}

export function openCodeRuntime(port: number, original?: string): string {
  let config: Record<string, any> = {};
  if (original) {
    try { config = JSON.parse(original); } catch { throw new Error("OPENCODE_CONFIG_CONTENT must contain valid JSON."); }
    if (!config || typeof config !== "object" || Array.isArray(config)) throw new Error("OpenCode inline configuration must be an object.");
  }
  config.provider = { ...config.provider };
  for (const [name, provider] of Object.entries(openCodeConfig(port).provider)) {
    const previous = config.provider[name] || {};
    config.provider[name] = { ...previous, options: { ...previous.options, ...provider.options } };
  }
  return JSON.stringify(config);
}
