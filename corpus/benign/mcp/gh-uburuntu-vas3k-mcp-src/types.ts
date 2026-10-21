import type { OAuthHelpers } from "@cloudflare/workers-oauth-provider";

/**
 * Worker-wide bindings (vars + secrets + KV + Durable Object).
 */
export interface Env {
  VAS3K_BASE_URL: string;
  /** Public-facing URL of this worker (e.g. https://vas3k-mcp.rmbk.me). */
  PUBLIC_BASE_URL: string;
  VAS3K_CLIENT_ID: string;
  VAS3K_CLIENT_SECRET: string;
  COOKIE_ENCRYPTION_KEY: string;
  OAUTH_KV: KVNamespace;
  OAUTH_PROVIDER: OAuthHelpers;
  MCP_OBJECT: DurableObjectNamespace;
  MCP_OBJECT_FULL: DurableObjectNamespace;
}

/**
 * Per-session context the OAuth provider hands to McpAgent as `this.props`.
 * Encrypted into the bearer token issued to the MCP client.
 *
 * Only the upstream `access_token` and `refresh_token` go in here — the
 * client_id/secret stay in env vars and never touch token storage.
 */
export interface Props {
  /** Schema version of this Props object. See CURRENT_PROPS_VERSION. */
  propsVersion: number;
  slug: string;
  fullName: string;
  upstreamAccessToken: string;
  upstreamRefreshToken?: string;
  /** vas3k.club-side scopes (e.g. "openid contact"). */
  scope: string;
  /** MCP-side scopes granted by the user (e.g. ["read", "write"]). */
  mcpScopes: string[];
  // OAuthProvider expects Record<string, unknown>; this index signature
  // lets us keep the typed fields above while satisfying that interface.
  [key: string]: unknown;
}
