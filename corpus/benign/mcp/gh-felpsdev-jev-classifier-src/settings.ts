import { existsSync, mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";
import { parseEnv } from "node:util";
import * as tls from "node:tls";

export const SETTING_KEYS = ["JEV_PROVIDER", "JEV_API_KEY", "TYPESAFE_API_KEY", "OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY",
  "JEV_MODEL", "JEV_MODE", "JEV_PROXY", "JEV_STUB", "PORT", "DONE_THRESHOLD", "MIN_CONFIDENCE", "JEV_LOG",
  "JEV_DEFAULT_AGENT", "JEV_AUTH", "JEV_SYSTEM_CA", "UPSTREAM", "UPSTREAM_API_KEY", "ANTHROPIC_UPSTREAM",
  "OPENAI_UPSTREAM", "XAI_UPSTREAM", "CLAUDE_OAUTH_UPSTREAM", "CODEX_OAUTH_UPSTREAM", "GROK_OAUTH_UPSTREAM",
  "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"] as const;
export type Settings = Partial<Record<typeof SETTING_KEYS[number], string>>;
export const isSecret = (key: string) => key.endsWith("API_KEY");
export const SETTING_LABELS: Record<keyof Settings, string> = {
  JEV_PROXY: "Use Jev proxy for agent launches",
  JEV_PROVIDER: "Jev provider", JEV_API_KEY: "Classifier key override", TYPESAFE_API_KEY: "TypeSafe key", OPENROUTER_API_KEY: "OpenRouter key", AI_GATEWAY_API_KEY: "Vercel Gateway key",
  JEV_MODEL: "Jev model", JEV_MODE: "Routing mode", JEV_STUB: "Offline test", PORT: "Gateway port", DONE_THRESHOLD: "Completion threshold", MIN_CONFIDENCE: "Minimum confidence",
  JEV_LOG: "Decision log file", JEV_DEFAULT_AGENT: "Default agent", JEV_AUTH: "Agent authentication", JEV_SYSTEM_CA: "Trust system certificates",
  UPSTREAM: "Agent API destination override", UPSTREAM_API_KEY: "Agent API credential override", ANTHROPIC_UPSTREAM: "Claude API destination", OPENAI_UPSTREAM: "Codex API destination", XAI_UPSTREAM: "Grok API destination",
  CLAUDE_OAUTH_UPSTREAM: "Claude login destination", CODEX_OAUTH_UPSTREAM: "Codex login destination", GROK_OAUTH_UPSTREAM: "Grok login destination",
  OPENAI_API_KEY: "Codex API key", ANTHROPIC_API_KEY: "Claude API key", XAI_API_KEY: "Grok API key",
};

export function configDirectory(env: NodeJS.ProcessEnv = process.env): string {
  if (env.JEV_CONFIG_HOME) return resolve(env.JEV_CONFIG_HOME);
  return join(process.platform === "win32" ? (env.APPDATA || join(homedir(), "AppData", "Roaming"))
    : (env.XDG_CONFIG_HOME || join(homedir(), ".config")), "jev-classifier");
}
export const configFile = () => join(configDirectory(), "config.json");

export function validateSettings(value: unknown): Settings {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Settings must be a JSON object.");
  const settings: Settings = {};
  for (const key of SETTING_KEYS) {
    const v = (value as Record<string, unknown>)[key];
    if (v === undefined || v === "") continue;
    if (typeof v !== "string" || /[\r\n\0]/.test(v)) throw new Error(`Invalid value for ${key}.`);
    settings[key] = v;
  }
  for (const [key, allowed] of Object.entries({ JEV_PROVIDER: ["typesafe", "openrouter", "vercel"], JEV_MODE: ["shadow", "enforce"],
    JEV_DEFAULT_AGENT: ["codex", "claude", "grok", "opencode", "cursor", "antigravity"], JEV_AUTH: ["oauth", "api-key"], JEV_PROXY: ["0", "1"], JEV_STUB: ["0", "1"], JEV_SYSTEM_CA: ["0", "1"] })) {
    const v = settings[key as keyof Settings];
    if (v && !allowed.includes(v)) throw new Error(`${key} must be ${allowed.join(" or ")}.`);
  }
  if (settings.PORT && (!/^\d+$/.test(settings.PORT) || +settings.PORT < 1 || +settings.PORT > 65535)) throw new Error("PORT must be between 1 and 65535.");
  for (const key of ["DONE_THRESHOLD", "MIN_CONFIDENCE"] as const) {
    if (settings[key] && (!Number.isFinite(+settings[key]) || +settings[key] < 0 || +settings[key] > 1)) throw new Error(`${key} must be between 0 and 1.`);
  }
  for (const key of SETTING_KEYS.filter(k => k === "UPSTREAM" || k.endsWith("_UPSTREAM"))) {
    if (!settings[key]) continue;
    try { const url = new URL(settings[key]); if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw Error(); }
    catch { throw new Error(`${key} must be an HTTP(S) URL without embedded credentials.`); }
  }
  return settings;
}

export function readSettings(file = configFile()): Settings {
  if (!existsSync(file)) return {};
  try { return validateSettings(JSON.parse(readFileSync(file, "utf8"))); }
  catch { throw new Error(`Cannot read settings at ${file}. Fix the JSON or move the file aside and run setup.`); }
}

export function saveSettings(settings: Settings, directory = configDirectory()): void {
  const validated = validateSettings(settings);
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const temporary = join(directory, `config.${process.pid}.${Date.now()}.tmp`);
  try {
    writeFileSync(temporary, JSON.stringify(validated, null, 2) + "\n", { mode: 0o600, flag: "wx" });
    renameSync(temporary, join(directory, "config.json"));
  } finally { rmSync(temporary, { force: true }); }
}

export function loadSettings(globalOnly = false, envFile?: string): { file: string; localKeys: string[] } {
  if (globalOnly && envFile) throw new Error("Choose either --global or --env-file, not both.");
  const global = readSettings();
  // Once setup is saved, it is authoritative. Legacy .env is automatic only before first setup.
  const localFile = globalOnly ? undefined : envFile || (!existsSync(configFile()) && existsSync(".env") ? ".env" : undefined);
  const local = localFile ? validateSettings(parseEnv(readFileSync(localFile, "utf8"))) : {};
  for (const [key, value] of Object.entries({ ...global, ...local })) if (process.env[key] === undefined) process.env[key] = value;
  process.env.JEV_LOG ??= join(configDirectory(), "decisions.jsonl");
  // Keep certificate verification enabled while supporting managed OS trust stores.
  if (process.env.JEV_SYSTEM_CA !== "0" && typeof tls.setDefaultCACertificates === "function") {
    tls.setDefaultCACertificates([...new Set([...tls.getCACertificates("default"), ...tls.getCACertificates("system")])]);
  }
  return { file: configFile(), localKeys: Object.keys(local) };
}

export function publicSettings(settings: Settings): Settings {
  return Object.fromEntries(Object.entries(settings).map(([k, v]) => [k, isSecret(k) ? "[saved]" : v]));
}
