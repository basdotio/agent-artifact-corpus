import net from "node:net";

export const SERVICE_NAME = "Codex Agent";
export const DEFAULT_HOST = "127.0.0.1";
export const DEFAULT_PORT = 8787;
export const CODEX_PROTOCOL_VERSION = "codex-cli 0.147.0 / app-server v2";

export function parsePort(value: string): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65535) {
    throw new Error(`PORT inválido: ${value}`);
  }
  return parsed;
}

export function isLoopbackHost(host: string): boolean {
  const normalized = host.trim().toLowerCase().replace(/^\[|\]$/g, "");
  if (normalized === "localhost") {
    return true;
  }
  const addressType = net.isIP(normalized);
  return (addressType === 4 && normalized.startsWith("127.")) || normalized === "::1";
}

export function assertSafeHost(host: string, allowNonLoopback = process.env.CODEX_AGENT_ALLOW_NON_LOOPBACK === "1"): void {
  if (isLoopbackHost(host)) {
    return;
  }
  if (!allowNonLoopback) {
    throw new Error(
      `HOST=${host} no es loopback. Define CODEX_AGENT_ALLOW_NON_LOOPBACK=1 sólo cuando un Secure MCP Tunnel o una protección equivalente cubra explícitamente el transporte.`,
    );
  }
}

/**
 * Host headers accepted on /mcp. Anchors DNS rebinding protection to the configured
 * bind address instead of a hardcoded port. A tunnel that rewrites Host must add its
 * own hostname through CODEX_AGENT_ALLOWED_HOSTS.
 */
export function allowedHosts(host: string, port: number, env: NodeJS.ProcessEnv = process.env): string[] {
  const hosts = new Set<string>();
  const add = (name: string): void => {
    const normalized = name.trim().toLowerCase();
    if (normalized.length > 0) hosts.add(normalized);
  };

  const bracket = (name: string): string => (net.isIP(name) === 6 ? `[${name}]` : name);
  add(`${bracket(host)}:${port}`);
  if (isLoopbackHost(host)) {
    add(`127.0.0.1:${port}`);
    add(`localhost:${port}`);
    add(`[::1]:${port}`);
  }
  // El SDK compara la cabecera Host cruda, sin normalizar. Host es
  // case-insensitive, así que se aceptan ambas formas para no rechazar a un
  // túnel que envíe su hostname con mayúsculas.
  for (const extra of (env.CODEX_AGENT_ALLOWED_HOSTS ?? "").split(",")) {
    add(extra);
    const verbatim = extra.trim();
    if (verbatim.length > 0) hosts.add(verbatim);
  }
  return [...hosts];
}

export function runtimeConfig(env: NodeJS.ProcessEnv = process.env): {
  host: string;
  port: number;
  allowedHosts: string[];
  codexCommand: string;
  rpcTimeoutMs: number;
  shutdownTimeoutMs: number;
  stateFile: string | undefined;
} {
  const parseDuration = (name: string, fallback: number): number => {
    const raw = env[name];
    if (raw === undefined || raw.trim() === "") {
      return fallback;
    }
    const value = Number(raw);
    if (!Number.isInteger(value) || value < 1 || value > 10 * 60 * 1000) {
      throw new Error(`${name} inválido: ${raw}`);
    }
    return value;
  };

  const host = env.HOST ?? DEFAULT_HOST;
  assertSafeHost(host, env.CODEX_AGENT_ALLOW_NON_LOOPBACK === "1");
  const port = parsePort(env.PORT ?? String(DEFAULT_PORT));
  return {
    host,
    port,
    allowedHosts: allowedHosts(host, port, env),
    codexCommand: env.CODEX_BIN ?? "codex",
    rpcTimeoutMs: parseDuration("CODEX_RPC_TIMEOUT_MS", 30_000),
    shutdownTimeoutMs: parseDuration("CODEX_SHUTDOWN_TIMEOUT_MS", 2_000),
    stateFile: env.CODEX_AGENT_STATE_FILE,
  };
}
