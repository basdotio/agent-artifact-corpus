/**
 * Shared constants — single source of truth for values that would otherwise
 * be duplicated across modules. Keep additions terse: numbers with units in
 * the name, strings with what-they-are explained inline.
 */

/** Hard request timeout for any single upstream HTTP call. */
export const UPSTREAM_TIMEOUT_MS = 15_000;

/** OAuth scopes we request from vas3k.club. `contact` unlocks email + tg. */
export const UPSTREAM_SCOPE = "openid contact";

/** TTL for the HMAC-signed state ferried through the upstream OAuth dance. */
export const STATE_TTL_SECONDS = 600;

/** Default MCP-side access-token lifetime when upstream omits expires_in. */
export const DEFAULT_ACCESS_TOKEN_TTL_SECONDS = 3600;
/** Hard cap on accepted upstream expires_in to avoid surprise huge values. */
export const MAX_ACCESS_TOKEN_TTL_SECONDS = 24 * 3600;

/** McpServer identity. Bump version when registered tools change shape. */
export const MCP_SERVER_NAME = "vas3k-club";
export const MCP_SERVER_VERSION = "1.1.3";

/** User-Agent on outbound requests to vas3k.club. Track project version. */
export const USER_AGENT = `vas3k-mcp/${MCP_SERVER_VERSION}`;

/** Bump when `Props` shape changes; old tokens then refuse refresh. */
export const CURRENT_PROPS_VERSION = 1;
