/**
 * Agent-first output protocol for pdf-brain.
 *
 * Design goals:
 * - stdout is machine-readable (JSON by default)
 * - stderr is diagnostics only (opt-in via log-level)
 * - stable envelope so agents can reliably parse responses and chain next actions
 */

export const PDF_BRAIN_PROTOCOL_VERSION = 1 as const;

export type OutputFormat = "json" | "ndjson" | "text";
export type LogLevel = "silent" | "error" | "info" | "debug";

export interface NextAction {
  kind: "shell";
  argv: string[];
  description?: string;
}

export interface AgentErrorShape {
  code: string;
  message: string;
  details?: unknown;
}

export interface ServerAuthConfig {
  enabled: boolean;
  token?: string;
}

export interface ServerConfigShape {
  host: string;
  port: number;
  auth: ServerAuthConfig;
}

export interface ServerConfigOverrides {
  host?: string;
  port?: number;
  authToken?: string;
}

export const DEFAULT_SERVER_CONFIG: ServerConfigShape = {
  host: "127.0.0.1",
  port: 3838,
  auth: {
    enabled: false,
  },
};

export type AgentEnvelope<T> =
  | {
      ok: true;
      command: string;
      protocolVersion: typeof PDF_BRAIN_PROTOCOL_VERSION;
      result: T;
      nextActions?: NextAction[];
      meta?: Record<string, unknown>;
    }
  | {
      ok: false;
      command: string;
      protocolVersion: typeof PDF_BRAIN_PROTOCOL_VERSION;
      error: AgentErrorShape;
      nextActions?: NextAction[];
      meta?: Record<string, unknown>;
    };

export function toJsonLine(
  value: unknown,
  opts?: { pretty?: boolean }
): string {
  const pretty = opts?.pretty === true;
  return JSON.stringify(value, null, pretty ? 2 : 0) + "\n";
}

export function resolveServerConfig(
  config: Partial<ServerConfigShape> | undefined,
  overrides?: ServerConfigOverrides
): ServerConfigShape {
  const host = overrides?.host ?? config?.host ?? DEFAULT_SERVER_CONFIG.host;
  const port = overrides?.port ?? config?.port ?? DEFAULT_SERVER_CONFIG.port;

  const authEnabled =
    typeof overrides?.authToken === "string"
      ? true
      : config?.auth?.enabled ?? DEFAULT_SERVER_CONFIG.auth.enabled;
  const authToken = overrides?.authToken ?? config?.auth?.token;

  return {
    host,
    port,
    auth: {
      enabled: authEnabled,
      token: authToken,
    },
  };
}

export function isBearerTokenAuthorized(
  headers: Headers,
  auth: ServerAuthConfig
): boolean {
  if (!auth.enabled) return true;
  if (!auth.token) return false;
  const authorization = headers.get("authorization");
  if (!authorization) return false;
  return authorization === `Bearer ${auth.token}`;
}
