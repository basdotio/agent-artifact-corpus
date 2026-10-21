/**
 * Worker entrypoint.
 *
 * Composes Cloudflare's `OAuthProvider` (which makes us an OAuth 2.1 server
 * for MCP clients) with a Hono app that handles the upstream OAuth dance
 * against vas3k.club, plus the `McpAgent`-backed MCP server itself.
 *
 *   MCP client (Claude)
 *        │  Bearer access_token (issued by us)
 *        ▼
 *   OAuthProvider ─── /mcp ───▶ McpAgent (MyMCP) ──▶ vas3k.club JSON API
 *        │                              ▲
 *        │ tokenExchangeCallback        │ this.props.upstreamAccessToken
 *        ▼                              │
 *   refreshUpstreamTokens() ────────────┘
 */

import { env } from "cloudflare:workers";
import { OAuthProvider } from "@cloudflare/workers-oauth-provider";

import {
  CURRENT_PROPS_VERSION,
  DEFAULT_ACCESS_TOKEN_TTL_SECONDS,
  MAX_ACCESS_TOKEN_TTL_SECONDS,
  UPSTREAM_TIMEOUT_MS,
} from "./constants";
import { MyMCP } from "./mcp";
import { MyMCPFull } from "./mcp-full";
import type { Env, Props } from "./types";
import { Vas3kHandler } from "./vas3k-handler";

/**
 * Exchange an upstream refresh token for a fresh access token at vas3k.club.
 * Exported so unit tests can drive it without instantiating an OAuthProvider.
 *
 * Failures here are the canary for upstream outages: a single user 401 is
 * normal (token revoked), but a sudden burst of failures usually means
 * vas3k.club is down or the OAuth app got revoked. Logged with a stable
 * `[upstream-refresh-fail]` tag so the operator can grep `wrangler tail`
 * or set a Cloudflare Workers Notification rule on it.
 */
export async function refreshUpstreamTokens(
  refreshToken: string,
  baseUrl: string,
  clientId: string,
  clientSecret: string,
) {
  const response = await fetch(new URL("/auth/openid/token", baseUrl).href, {
    method: "POST",
    headers: {
      Authorization: `Basic ${btoa(`${clientId}:${clientSecret}`)}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: refreshToken,
    }).toString(),
    signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
  });
  if (!response.ok) {
    const body = await response.text();
    console.error("[upstream-refresh-fail]", { status: response.status, body: body.slice(0, 200) });
    throw new Error(`vas3k.club refresh failed: ${response.status} ${body}`);
  }
  return (await response.json()) as {
    access_token: string;
    refresh_token?: string;
    token_type?: string;
    expires_in?: number;
    scope?: string;
  };
}

/**
 * Hardening flags (security review P1-1, P1-2):
 *
 * - `clientIdMetadataDocumentEnabled: true` — let MCP clients use a stable
 *   HTTPS URL as their `client_id` (RFC draft-ietf-oauth-client-id-metadata-document).
 *   Requires the `global_fetch_strictly_public` compatibility flag in
 *   wrangler.jsonc for SSRF protection during metadata fetches.
 * - `allowPlainPKCE: false` — require S256 code challenges; reject `plain`.
 * - `allowImplicitFlow: false` — only authorization-code flow is allowed;
 *   the implicit flow is deprecated and unsafe for confidential props.
 *
 * Note: `disallowPublicClientRegistration` is intentionally NOT set. The MCP
 * spec mandates DCR support, and disabling it locks out MCP Inspector,
 * Claude Desktop, Cursor — basically every MCP client that registers
 * dynamically. The phishing concern from the security review is mitigated
 * by the consent-screen warning in `vas3k-handler.ts` that the client name
 * is self-declared, plus by tracking the `redirect_uri` the user actually
 * sees in the upstream vas3k.club approval flow.
 */
export default new OAuthProvider({
  // Two MCP endpoints sharing one OAuth registration:
  //   /mcp       — read-only. Safe default for hosted use.
  //   /mcp-full  — read + write tools (votes, bookmarks, friends,
  //                room subscriptions, profile-tag toggles, etc).
  // Sibling paths (not nested) so OAuthProvider's prefix match can't
  // accidentally route /mcp-full requests through the /mcp handler.
  // McpAgent.serve(path) defaults `binding` to "MCP_OBJECT", so without an
  // explicit binding both classes would route through the same Durable Object
  // and the second class's tools would never run. Pass each its own binding.
  // `transport: "auto"` makes the same route serve both Streamable HTTP
  // (the current default) AND legacy SSE for the handful of pre-mid-2025
  // clients that probe SSE first. Single mount, no extra route to manage.
  // `as never` coerces McpAgent.serve()'s handler to OAuthProvider's opaque
  // apiHandlers value type — runtime shape is correct, the two libraries
  // just don't share a type for it.
  apiHandlers: {
    "/mcp-full": MyMCPFull.serve("/mcp-full", {
      binding: "MCP_OBJECT_FULL",
      transport: "auto",
    }) as never,
    "/mcp": MyMCP.serve("/mcp", {
      binding: "MCP_OBJECT",
      transport: "auto",
    }) as never,
  },
  defaultHandler: Vas3kHandler as never,
  authorizeEndpoint: "/authorize",
  tokenEndpoint: "/token",
  clientRegistrationEndpoint: "/register",
  // `scopesSupported` advertises what an MCP client may request. `read` is
  // necessary for any tool, `write` is required for /mcp-full's mutating
  // tools (we check at tool-call time via `props.mcpScopes`). Honest
  // limitation: today most clients request the full set by default; the
  // boundary is real only when a client explicitly drops `write`.
  scopesSupported: ["read", "write"],
  clientIdMetadataDocumentEnabled: true,
  allowPlainPKCE: false,
  allowImplicitFlow: false,
  // Surfaced at /.well-known/oauth-protected-resource — helps MCP-aware
  // clients pick a sensible display name when they list connected servers.
  resourceMetadata: { resource_name: "vas3k-mcp" },

  /**
   * When the MCP client refreshes its token, transparently refresh the
   * upstream vas3k.club token too and rotate it inside `props`.
   */
  tokenExchangeCallback: async (options) => {
    if (options.grantType !== "refresh_token") return;
    const props = options.props as unknown as Props;
    if (!props?.upstreamRefreshToken) return;
    // propsVersion guard: if a future deploy bumps the schema, this lets us
    // force everyone to re-auth cleanly instead of silently undefined-ing
    // fields the new code expects.
    if (props.propsVersion !== CURRENT_PROPS_VERSION) {
      console.error("[props-version-mismatch]", {
        got: props.propsVersion,
        expected: CURRENT_PROPS_VERSION,
      });
      throw new Error("propsVersion mismatch — please re-authorize");
    }

    const e = env as unknown as Env;
    const refreshed = await refreshUpstreamTokens(
      props.upstreamRefreshToken,
      e.VAS3K_BASE_URL,
      e.VAS3K_CLIENT_ID,
      e.VAS3K_CLIENT_SECRET,
    );
    const nextProps: Props = {
      ...props,
      upstreamAccessToken: refreshed.access_token,
      upstreamRefreshToken: refreshed.refresh_token ?? props.upstreamRefreshToken,
    };

    // Always set accessTokenTTL so the MCP-issued token never outlives the
    // upstream one. Bound the upstream value to avoid surprise huge values
    // (code review P1-6).
    const accessTokenTTL = Math.min(
      refreshed.expires_in ?? DEFAULT_ACCESS_TOKEN_TTL_SECONDS,
      MAX_ACCESS_TOKEN_TTL_SECONDS,
    );

    return {
      accessTokenProps: nextProps as unknown as Record<string, unknown>,
      newProps: nextProps as unknown as Record<string, unknown>,
      accessTokenTTL,
    };
  },
});

// Durable Object classes need to be re-exported so the runtime can find them.
export { MyMCP, MyMCPFull };
