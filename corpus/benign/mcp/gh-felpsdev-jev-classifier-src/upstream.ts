import { adapterFor, upstreamFor, type Adapter } from "./adapters/index.js";

/** Session routes are explicit: never guess a token's issuer or send it to a gateway. */
export const SESSION_PROVIDERS = {
  claude: { base: "https://api.anthropic.com", env: "CLAUDE_OAUTH_UPSTREAM" },
  codex: { base: "https://chatgpt.com/backend-api/codex", env: "CODEX_OAUTH_UPSTREAM" },
  grok: { base: "https://cli-chat-proxy.grok.com", env: "GROK_OAUTH_UPSTREAM" },
} as const;

export const API_PROVIDERS = {
  claude: { base: "https://api.anthropic.com", env: "ANTHROPIC_UPSTREAM" },
  codex: { base: "https://api.openai.com", env: "OPENAI_UPSTREAM" },
  grok: { base: "https://api.x.ai", env: "XAI_UPSTREAM" },
} as const;

export interface UpstreamRoute {
  readonly client?: string;
  readonly target: string;
  readonly adapter?: Adapter;
  readonly preserveAuth: boolean;
}

export function routeUpstream(path: string): UpstreamRoute {
  if (!path.startsWith("/") || path.startsWith("//")) throw new Error("Expected an origin-relative request path");
  if (path.startsWith("/clients/")) {
    const match = /^\/clients\/(opencode)(\/api\/(?:claude|codex|grok)\/.*)$/.exec(path);
    if (!match) throw new Error("Unknown client route");
    return { ...routeUpstream(match[2]!), client: match[1] };
  }
  if (path.startsWith("/api/")) {
    const match = /^\/api\/(claude|codex|grok)(\/[^?]*)?(\?.*)?$/.exec(path);
    if (!match) throw new Error("Unknown API provider route");
    const config = API_PROVIDERS[match[1] as keyof typeof API_PROVIDERS];
    const suffix = `${match[2] || "/"}${match[3] || ""}`;
    const base = (process.env.UPSTREAM || process.env[config.env] || config.base).replace(/\/+$/, "");
    return { target: `${base}${suffix}`, adapter: adapterFor(suffix), preserveAuth: false };
  }
  if (path.startsWith("/oauth/") || path === "/oauth") {
    const match = /^\/oauth\/(claude|codex|grok)(\/[^?]*)?(\?.*)?$/.exec(path);
    if (!match) throw new Error("Unknown OAuth route; use /oauth/claude, /oauth/codex or /oauth/grok");
    const provider = match[1] as keyof typeof SESSION_PROVIDERS;
    const config = SESSION_PROVIDERS[provider];
    const suffix = match[2] || "/";
    // Keep the URL under the selected provider's base, including encoded dot segments.
    const decoded = decodeURIComponent(suffix);
    if (decoded.includes("\\") || decoded.split("/").some((part) => part === "." || part === "..")) {
      throw new Error("Invalid OAuth request path");
    }
    const base = (process.env[config.env] || config.base).replace(/\/+$/, "");
    const adapterPath = provider === "codex" && suffix === "/responses" ? "/v1/responses" : suffix;
    return {
      target: `${base}${suffix}${match[3] || ""}`,
      adapter: adapterFor(adapterPath),
      preserveAuth: true,
    };
  }
  const adapter = adapterFor(path);
  const base = adapter
    ? upstreamFor(adapter)
    : (process.env.UPSTREAM || process.env.ANTHROPIC_UPSTREAM || "https://api.anthropic.com").replace(/\/+$/, "");
  return { target: `${base}${path}`, adapter, preserveAuth: false };
}
