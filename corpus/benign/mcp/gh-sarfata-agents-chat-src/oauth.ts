import { createHash, randomBytes } from "node:crypto";
import { Hono, type Context } from "hono";
import { nanoid } from "nanoid";
import type { AgentIdentity, Config } from "./config.js";
import { authenticate, digest } from "./config.js";
import type { Db } from "./db.js";
import type { DebugLog } from "./debug-log.js";

const ACCESS_TOKEN_TTL_SECONDS = 60 * 60;
const REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60;
const AUTHORIZATION_TTL_SECONDS = 10 * 60;
const CODE_TTL_SECONDS = 5 * 60;
const DEFAULT_SCOPES = ["chat:read", "chat:write", "events:read", "offline_access"] as const;
const SUPPORTED_SCOPES = new Set<string>(DEFAULT_SCOPES);

type GitHubUser = { id: number; login: string };

export interface GitHubOAuthClient {
  identify(code: string): Promise<GitHubUser>;
}

type TransactionRow = {
  id: string;
  client_id: string;
  redirect_uri: string;
  code_challenge: string;
  resource: string;
  scope: string;
  client_state: string;
  user_id: string | null;
  approval_hash: string | null;
  expires_at: string;
};

type TokenRow = {
  user_id: string;
  client_id: string;
  resource: string;
  scope: string;
  expires_at: string;
  family_id?: string;
  revoked_at?: string | null;
};

export type AuthenticatedAgent = {
  agent: AgentIdentity;
  token: string;
  clientId: string;
  scopes: string[];
};

export class OAuthService {
  readonly app = new Hono();
  private readonly resource: string;
  private readonly github?: GitHubOAuthClient;

  constructor(private readonly db: Db, private readonly config: Config, github?: GitHubOAuthClient, private readonly debug?: DebugLog) {
    this.resource = `${config.publicBaseUrl}/mcp`;
    this.github = github ?? (config.githubOAuth ? new GitHubApiClient(config.githubOAuth) : undefined);
    this.registerRoutes();
  }

  authenticate(authorization: string | undefined): AuthenticatedAgent | null {
    const staticAgent = authenticate(this.config, authorization);
    if (staticAgent && authorization) {
      return {
        agent: staticAgent,
        token: authorization.slice("Bearer ".length),
        clientId: staticAgent.id,
        scopes: [...DEFAULT_SCOPES]
      };
    }
    if (!authorization?.startsWith("Bearer ")) return null;
    const token = authorization.slice("Bearer ".length);
    const now = new Date().toISOString();
    const row = this.db.prepare(`
      select t.user_id, t.client_id, t.resource, t.scope, t.expires_at,
        u.display_name
      from oauth_access_tokens t
      join users u on u.id = t.user_id
      where t.token_hash = ? and t.expires_at > ? and t.resource = ?
    `).get(hash(token), now, this.resource) as (TokenRow & { display_name: string }) | undefined;
    if (!row) return null;
    this.db.prepare(`update oauth_access_tokens set last_used_at = ? where token_hash = ?`).run(now, hash(token));
    return {
      agent: { id: row.user_id, name: row.display_name },
      token,
      clientId: row.client_id,
      scopes: row.scope.split(" ").filter(Boolean)
    };
  }

  challenge(): string {
    return this.config.githubOAuth
      ? `Bearer resource_metadata="${this.config.publicBaseUrl}/.well-known/oauth-protected-resource/mcp"`
      : "Bearer";
  }

  private registerRoutes() {
    this.app.get("/.well-known/oauth-protected-resource", (c) => c.json(this.protectedResourceMetadata()));
    this.app.get("/.well-known/oauth-protected-resource/mcp", (c) => c.json(this.protectedResourceMetadata()));
    this.app.get("/.well-known/oauth-authorization-server", (c) => c.json(this.authorizationServerMetadata()));
    this.app.post("/oauth/register", (c) => this.registerClient(c));
    this.app.get("/oauth/authorize", (c) => this.authorize(c));
    this.app.get("/oauth/github/callback", (c) => this.githubCallback(c));
    this.app.post("/oauth/approve", (c) => this.approve(c));
    this.app.post("/oauth/token", (c) => this.token(c));
  }

  private protectedResourceMetadata() {
    return {
      resource: this.resource,
      authorization_servers: [this.config.publicBaseUrl],
      scopes_supported: [...DEFAULT_SCOPES],
      bearer_methods_supported: ["header"]
    };
  }

  private authorizationServerMetadata() {
    const base = this.config.publicBaseUrl;
    return {
      issuer: base,
      authorization_endpoint: `${base}/oauth/authorize`,
      token_endpoint: `${base}/oauth/token`,
      registration_endpoint: `${base}/oauth/register`,
      response_types_supported: ["code"],
      grant_types_supported: ["authorization_code", "refresh_token"],
      code_challenge_methods_supported: ["S256"],
      token_endpoint_auth_methods_supported: ["none"],
      scopes_supported: [...DEFAULT_SCOPES],
      client_id_metadata_document_supported: false
    };
  }

  private async registerClient(c: Context) {
    if (!this.github) return oauthError(c, 503, "temporarily_unavailable", "GitHub OAuth is not configured");
    let input: Record<string, unknown>;
    try {
      input = await c.req.json<Record<string, unknown>>();
    } catch {
      return oauthError(c, 400, "invalid_client_metadata", "Request body must be JSON");
    }
    const redirectUris = input.redirect_uris;
    if (!Array.isArray(redirectUris) || redirectUris.length < 1 || redirectUris.length > 10 ||
      !redirectUris.every((uri) => typeof uri === "string" && validRedirectUri(uri))) {
      return oauthError(c, 400, "invalid_redirect_uri", "Register 1-10 HTTPS or loopback redirect URIs");
    }
    if (input.token_endpoint_auth_method !== undefined && input.token_endpoint_auth_method !== "none") {
      return oauthError(c, 400, "invalid_client_metadata", "Only public clients are supported");
    }
    const applicationType = input.application_type === "web" ? "web" : "native";
    const clientName = typeof input.client_name === "string" && input.client_name.trim()
      ? input.client_name.trim().slice(0, 128)
      : "MCP client";
    const clientId = `client_${randomToken()}`;
    const now = new Date().toISOString();
    this.db.prepare(`
      insert into oauth_clients(client_id, client_name, redirect_uris_json, application_type, created_at)
      values (?, ?, ?, ?, ?)
    `).run(clientId, clientName, JSON.stringify(redirectUris), applicationType, now);
    return c.json({
      client_id: clientId,
      client_id_issued_at: Math.floor(Date.now() / 1000),
      client_name: clientName,
      redirect_uris: redirectUris,
      application_type: applicationType,
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"],
      token_endpoint_auth_method: "none"
    }, 201);
  }

  private authorize(c: Context) {
    if (!this.github || !this.config.githubOAuth) {
      return oauthError(c, 503, "temporarily_unavailable", "GitHub OAuth is not configured");
    }
    this.cleanup();
    const query = c.req.query();
    if (query.response_type !== "code") return oauthError(c, 400, "unsupported_response_type", "Use response_type=code");
    if (!query.client_id || !query.redirect_uri || !query.state) {
      return oauthError(c, 400, "invalid_request", "client_id, redirect_uri, and state are required");
    }
    const client = this.db.prepare(`select redirect_uris_json from oauth_clients where client_id = ?`)
      .get(query.client_id) as { redirect_uris_json: string } | undefined;
    if (!client) return oauthError(c, 400, "unauthorized_client", "Unknown client_id");
    const redirectUris = JSON.parse(client.redirect_uris_json) as string[];
    if (!redirectUris.includes(query.redirect_uri)) return oauthError(c, 400, "invalid_request", "redirect_uri is not registered");
    if (query.code_challenge_method !== "S256" || !query.code_challenge || !validCodeChallenge(query.code_challenge)) {
      return oauthRedirectError(c, query.redirect_uri, query.state, this.config.publicBaseUrl, "invalid_request", "S256 PKCE is required");
    }
    const resource = query.resource ?? this.resource;
    if (resource !== this.resource) {
      return oauthRedirectError(c, query.redirect_uri, query.state, this.config.publicBaseUrl, "invalid_target", "Invalid resource");
    }
    const scope = normalizeScope(query.scope);
    if (!scope) return oauthRedirectError(c, query.redirect_uri, query.state, this.config.publicBaseUrl, "invalid_scope", "Unsupported scope");
    const transactionId = `txn_${randomToken()}`;
    const now = new Date();
    this.db.prepare(`
      insert into oauth_transactions(
        id, client_id, redirect_uri, code_challenge, resource, scope, client_state, expires_at, created_at
      ) values (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      transactionId,
      query.client_id,
      query.redirect_uri,
      query.code_challenge,
      resource,
      scope,
      query.state,
      new Date(now.getTime() + AUTHORIZATION_TTL_SECONDS * 1000).toISOString(),
      now.toISOString()
    );
    const githubUrl = new URL("https://github.com/login/oauth/authorize");
    githubUrl.searchParams.set("client_id", this.config.githubOAuth.clientId);
    githubUrl.searchParams.set("redirect_uri", this.config.githubOAuth.callbackUrl);
    githubUrl.searchParams.set("state", transactionId);
    return c.redirect(githubUrl.toString(), 302);
  }

  private async githubCallback(c: Context) {
    if (!this.github) return c.text("GitHub OAuth is not configured", 503);
    const transactionId = c.req.query("state");
    if (!transactionId) return c.text("Missing OAuth state", 400);
    const transaction = this.transaction(transactionId);
    if (!transaction) return c.text("This authorization request expired or is invalid", 400);
    const githubError = c.req.query("error");
    if (githubError) {
      this.deleteTransaction(transactionId);
      return oauthRedirectError(c, transaction.redirect_uri, transaction.client_state, this.config.publicBaseUrl, "access_denied", "GitHub sign-in was denied");
    }
    const code = c.req.query("code");
    if (!code) return c.text("Missing GitHub authorization code", 400);
    let githubUser: GitHubUser;
    try {
      githubUser = await this.github.identify(code);
    } catch (error) {
      console.error("GitHub identity lookup failed", error);
      return c.text("GitHub sign-in could not be completed", 502);
    }
    const userId = this.upsertUser(githubUser);
    const approvalToken = randomToken();
    const updated = this.db.prepare(`
      update oauth_transactions set user_id = ?, approval_hash = ?
      where id = ? and expires_at > ?
    `).run(userId, hash(approvalToken), transactionId, new Date().toISOString());
    if (updated.changes !== 1) return c.text("This authorization request expired or is invalid", 400);
    const client = this.db.prepare(`select client_name from oauth_clients where client_id = ?`)
      .get(transaction.client_id) as { client_name: string };
    c.header("Cache-Control", "no-store");
    // Chromium applies form-action to redirects after the consent POST too.
    // The exact registered callback origin must be allowed, including its port.
    const callbackOrigin = new URL(transaction.redirect_uri).origin;
    c.header("Content-Security-Policy", `default-src 'none'; style-src 'unsafe-inline'; form-action 'self' ${callbackOrigin}; frame-ancestors 'none'; base-uri 'none'`);
    c.header("X-Frame-Options", "DENY");
    return c.html(consentPage({
      transactionId,
      approvalToken,
      clientName: client.client_name,
      redirectUri: transaction.redirect_uri,
      githubLogin: githubUser.login,
      scope: transaction.scope
    }));
  }

  private async approve(c: Context) {
    const body = await c.req.parseBody();
    const transactionId = stringField(body.transaction_id);
    const approvalToken = stringField(body.approval_token);
    const decision = stringField(body.decision);
    if (!transactionId || !approvalToken || !decision || !["allow", "deny"].includes(decision)) {
      return c.text("Invalid authorization submission", 400);
    }
    const outcome = this.db.transaction(() => {
      const transaction = this.transaction(transactionId);
      if (!transaction || !transaction.user_id || !transaction.approval_hash ||
        transaction.approval_hash !== hash(approvalToken)) return null;
      const deleted = this.db.prepare(`delete from oauth_transactions where id = ?`).run(transactionId);
      if (deleted.changes !== 1) return null;
      if (decision !== "allow") return { transaction };
      const authorizationCode = `code_${randomToken()}`;
      this.db.prepare(`
        insert into oauth_codes(
          code_hash, user_id, client_id, redirect_uri, code_challenge, resource, scope, expires_at, used_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, null)
      `).run(
        hash(authorizationCode), transaction.user_id, transaction.client_id, transaction.redirect_uri,
        transaction.code_challenge, transaction.resource, transaction.scope,
        new Date(Date.now() + CODE_TTL_SECONDS * 1000).toISOString()
      );
      return { transaction, authorizationCode };
    })();
    if (!outcome) {
      return c.text("This authorization request expired or is invalid", 400);
    }
    const { transaction } = outcome;
    if (decision !== "allow") {
      return oauthRedirectError(c, transaction.redirect_uri, transaction.client_state, this.config.publicBaseUrl, "access_denied", "The user denied access");
    }
    const redirect = new URL(transaction.redirect_uri);
    redirect.searchParams.set("code", outcome.authorizationCode!);
    redirect.searchParams.set("state", transaction.client_state);
    redirect.searchParams.set("iss", this.config.publicBaseUrl);
    return c.redirect(redirect.toString(), 302);
  }

  private async token(c: Context) {
    const body = await c.req.parseBody();
    const grantType = stringField(body.grant_type);
    if (grantType === "authorization_code") return this.exchangeAuthorizationCode(c, body);
    if (grantType === "refresh_token") return this.exchangeRefreshToken(c, body);
    return oauthError(c, 400, "unsupported_grant_type", "Supported grants: authorization_code, refresh_token");
  }

  private exchangeAuthorizationCode(c: Context, body: Record<string, string | File>) {
    const code = stringField(body.code);
    const clientId = stringField(body.client_id);
    const redirectUri = stringField(body.redirect_uri);
    const verifier = stringField(body.code_verifier);
    const resource = stringField(body.resource) ?? this.resource;
    if (!code || !clientId || !redirectUri || !verifier || !validCodeVerifier(verifier)) {
      return oauthError(c, 400, "invalid_request", "code, client_id, redirect_uri, and code_verifier are required");
    }
    const response = this.db.transaction(() => {
      const now = new Date().toISOString();
      const row = this.db.prepare(`
        select user_id, client_id, redirect_uri, code_challenge, resource, scope, expires_at, used_at
        from oauth_codes where code_hash = ?
      `).get(hash(code)) as (TokenRow & {
        redirect_uri: string;
        code_challenge: string;
        used_at: string | null;
      }) | undefined;
      if (!row || row.used_at || row.expires_at <= now || row.client_id !== clientId ||
        row.redirect_uri !== redirectUri || row.resource !== resource || pkceChallenge(verifier) !== row.code_challenge) return null;
      const consumed = this.db.prepare(`update oauth_codes set used_at = ? where code_hash = ? and used_at is null`)
        .run(now, hash(code));
      if (consumed.changes !== 1) return null;
      return this.issueTokens(row, `family_${nanoid(20)}`);
    })();
    if (!response) return oauthError(c, 400, "invalid_grant", "The authorization code is invalid or expired");
    return tokenResponse(c, response);
  }

  private exchangeRefreshToken(c: Context, body: Record<string, string | File>) {
    const refreshToken = stringField(body.refresh_token);
    const clientId = stringField(body.client_id);
    const resource = stringField(body.resource) ?? this.resource;
    if (!refreshToken || !clientId) return oauthError(c, 400, "invalid_request", "refresh_token and client_id are required");
    const outcome = this.db.transaction(() => {
      const now = new Date().toISOString();
      const row = this.db.prepare(`
        select user_id, client_id, resource, scope, expires_at, family_id, revoked_at
        from oauth_refresh_tokens where token_hash = ?
      `).get(hash(refreshToken)) as TokenRow | undefined;
      if (!row || row.client_id !== clientId || row.resource !== resource || row.expires_at <= now) return { kind: "invalid" } as const;
      if (row.revoked_at) {
        this.db.prepare(`update oauth_refresh_tokens set revoked_at = ? where family_id = ? and revoked_at is null`)
          .run(now, row.family_id);
        return { kind: "reused" } as const;
      }
      const consumed = this.db.prepare(`update oauth_refresh_tokens set revoked_at = ? where token_hash = ? and revoked_at is null`)
        .run(now, hash(refreshToken));
      if (consumed.changes !== 1) return { kind: "invalid" } as const;
      return { kind: "issued", response: this.issueTokens(row, row.family_id!) } as const;
    })();
    if (outcome.kind === "reused") return oauthError(c, 400, "invalid_grant", "Refresh token reuse detected");
    if (outcome.kind === "invalid") return oauthError(c, 400, "invalid_grant", "The refresh token is invalid or expired");
    return tokenResponse(c, outcome.response);
  }

  private issueTokens(row: Pick<TokenRow, "user_id" | "client_id" | "resource" | "scope">, familyId: string) {
    const accessToken = `ac_${randomToken()}`;
    const refreshToken = `rf_${randomToken()}`;
    const now = new Date();
    this.db.prepare(`
      insert into oauth_access_tokens(token_hash, user_id, client_id, resource, scope, expires_at, created_at)
      values (?, ?, ?, ?, ?, ?, ?)
    `).run(
      hash(accessToken), row.user_id, row.client_id, row.resource, row.scope,
      new Date(now.getTime() + ACCESS_TOKEN_TTL_SECONDS * 1000).toISOString(), now.toISOString()
    );
    this.db.prepare(`
      insert into oauth_refresh_tokens(
        token_hash, family_id, user_id, client_id, resource, scope, expires_at, created_at, revoked_at
      ) values (?, ?, ?, ?, ?, ?, ?, ?, null)
    `).run(
      hash(refreshToken), familyId, row.user_id, row.client_id, row.resource, row.scope,
      new Date(now.getTime() + REFRESH_TOKEN_TTL_SECONDS * 1000).toISOString(), now.toISOString()
    );
    return {
      access_token: accessToken,
      token_type: "Bearer",
      expires_in: ACCESS_TOKEN_TTL_SECONDS,
      refresh_token: refreshToken,
      scope: row.scope
    };
  }

  private transaction(id: string): TransactionRow | undefined {
    return this.db.prepare(`
      select id, client_id, redirect_uri, code_challenge, resource, scope, client_state,
        user_id, approval_hash, expires_at
      from oauth_transactions where id = ? and expires_at > ?
    `).get(id, new Date().toISOString()) as TransactionRow | undefined;
  }

  private deleteTransaction(id: string) {
    this.db.prepare(`delete from oauth_transactions where id = ?`).run(id);
  }

  private upsertUser(user: GitHubUser): string {
    const now = new Date().toISOString();
    const existing = this.db.prepare(`select id from users where provider = 'github' and provider_subject = ?`)
      .get(String(user.id)) as { id: string } | undefined;
    const id = existing?.id ?? `user_${nanoid(20)}`;
    this.db.prepare(`
      insert into users(id, provider, provider_subject, display_name, created_at, updated_at)
      values (?, 'github', ?, ?, ?, ?)
      on conflict(provider, provider_subject) do update set
        display_name = excluded.display_name,
        updated_at = excluded.updated_at
    `).run(id, String(user.id), user.login, now, now);
    this.debug?.record(existing ? "agent.authenticated" : "agent.registered", { actor: { id, name: user.login } });
    return id;
  }

  private cleanup() {
    const now = new Date().toISOString();
    this.db.prepare(`delete from oauth_transactions where expires_at <= ?`).run(now);
    this.db.prepare(`delete from oauth_codes where expires_at <= ?`).run(now);
    this.db.prepare(`delete from oauth_access_tokens where expires_at <= ?`).run(now);
  }
}

class GitHubApiClient implements GitHubOAuthClient {
  constructor(private readonly config: NonNullable<Config["githubOAuth"]>) {}

  async identify(code: string): Promise<GitHubUser> {
    const tokenResponse = await fetch("https://github.com/login/oauth/access_token", {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json", "User-Agent": "agents-chat" },
      body: JSON.stringify({
        client_id: this.config.clientId,
        client_secret: this.config.clientSecret,
        code,
        redirect_uri: this.config.callbackUrl
      })
    });
    const tokenBody = await tokenResponse.json() as { access_token?: string; error?: string };
    if (!tokenResponse.ok || !tokenBody.access_token) throw new Error(tokenBody.error ?? "GitHub token exchange failed");
    const userResponse = await fetch("https://api.github.com/user", {
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${tokenBody.access_token}`,
        "User-Agent": "agents-chat",
        "X-GitHub-Api-Version": "2022-11-28"
      }
    });
    const user = await userResponse.json() as Partial<GitHubUser> & { message?: string };
    if (!userResponse.ok || typeof user.id !== "number" || typeof user.login !== "string") {
      throw new Error(user.message ?? "GitHub identity lookup failed");
    }
    return { id: user.id, login: user.login };
  }
}

function validRedirectUri(value: string): boolean {
  try {
    const url = new URL(value);
    if (url.hash || url.username || url.password) return false;
    // This origin is also a CSP source. Reject URL-valid host characters that
    // could inject a directive or widen it with a wildcard.
    if (!/^https?:\/\/(?:[a-z0-9._-]+|\[[a-f0-9:]+\])(?::\d+)?$/i.test(url.origin)) return false;
    if (url.protocol === "https:") return true;
    return url.protocol === "http:" && ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  } catch {
    return false;
  }
}

function validCodeChallenge(value: string): boolean {
  return /^[A-Za-z0-9_-]{43}$/.test(value);
}

function validCodeVerifier(value: string): boolean {
  return /^[A-Za-z0-9._~-]{43,128}$/.test(value);
}

function normalizeScope(input: string | undefined): string | null {
  const scopes = input ? [...new Set(input.split(/\s+/).filter(Boolean))] : [...DEFAULT_SCOPES];
  if (scopes.some((scope) => !SUPPORTED_SCOPES.has(scope))) return null;
  return scopes.join(" ");
}

function pkceChallenge(verifier: string): string {
  return createHash("sha256").update(verifier).digest("base64url");
}

function randomToken(): string {
  return randomBytes(32).toString("base64url");
}

function hash(value: string): string {
  return digest(value).toString("hex");
}

function stringField(value: string | File | undefined): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function tokenResponse(c: Context, value: Record<string, unknown>) {
  c.header("Cache-Control", "no-store");
  c.header("Pragma", "no-cache");
  return c.json(value);
}

function oauthError(c: Context, status: 400 | 503, error: string, description: string) {
  c.header("Cache-Control", "no-store");
  return c.json({ error, error_description: description }, status);
}

function oauthRedirectError(
  c: Context,
  redirectUri: string,
  state: string,
  issuer: string,
  error: string,
  description: string
) {
  const url = new URL(redirectUri);
  url.searchParams.set("error", error);
  url.searchParams.set("error_description", description);
  url.searchParams.set("state", state);
  url.searchParams.set("iss", issuer);
  return c.redirect(url.toString(), 302);
}

function consentPage(input: {
  transactionId: string;
  approvalToken: string;
  clientName: string;
  redirectUri: string;
  githubLogin: string;
  scope: string;
}): string {
  const redirectHost = new URL(input.redirectUri).host;
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Authorize Agents Chat</title><style>
body{font:16px/1.5 system-ui,sans-serif;background:#f6f8fa;color:#1f2328;margin:0;padding:32px}.card{max-width:520px;margin:8vh auto;background:white;border:1px solid #d0d7de;border-radius:12px;padding:28px;box-shadow:0 8px 24px #8c959f33}h1{font-size:24px;margin-top:0}.muted{color:#59636e}.scope{background:#f6f8fa;border-radius:8px;padding:12px}.actions{display:flex;gap:12px;margin-top:24px}button{font:inherit;padding:9px 16px;border-radius:7px;border:1px solid #8c959f;background:white;cursor:pointer}.allow{background:#1f883d;color:white;border-color:#1f883d}</style></head>
<body><main class="card"><h1>Authorize ${escapeHtml(input.clientName)}</h1>
<p>Signed in to Agents Chat as <strong>${escapeHtml(input.githubLogin)}</strong>.</p>
<p>This MCP client will return to <strong>${escapeHtml(redirectHost)}</strong> and may:</p>
<p class="scope">${escapeHtml(input.scope.split(" ").filter((scope) => scope !== "offline_access").join(", "))}</p>
<p class="muted">Agents Chat receives only your stable GitHub account ID and login. It does not retain a GitHub token or receive repository access.</p>
<form method="post" action="/oauth/approve"><input type="hidden" name="transaction_id" value="${escapeHtml(input.transactionId)}"><input type="hidden" name="approval_token" value="${escapeHtml(input.approvalToken)}"><div class="actions"><button class="allow" name="decision" value="allow">Authorize</button><button name="decision" value="deny">Cancel</button></div></form>
</main></body></html>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[character]!);
}
