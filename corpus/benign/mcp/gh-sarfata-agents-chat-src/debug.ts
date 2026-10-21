import { randomBytes } from "node:crypto";
import { readFileSync } from "node:fs";
import { Hono } from "hono";
import { getCookie, setCookie, deleteCookie } from "hono/cookie";
import { digest, type Config } from "./config.js";
import type { Db } from "./db.js";
import type { DebugLog } from "./debug-log.js";
import type { OAuthService } from "./oauth.js";

const assets = new Map(["index.html", "debug.css", "debug.js"].map((name) =>
  [name, readFileSync(new URL(`../public/debug/${name}`, import.meta.url), "utf8")]));
const CLIENT_ID = "agents-chat-debug-ui";
const LOGIN_TTL_MS = 10 * 60_000;

export function createDebugApp(config: Config, db: Db, oauth: OAuthService, log: DebugLog) {
  const app = new Hono();
  const enabled = Boolean(config.githubOAuth && config.debugGithubIds?.length);
  const secure = new URL(config.publicBaseUrl).protocol === "https:";
  const cookieName = `${secure ? "__Secure-" : ""}agents_chat_debug`;
  const loginCookie = `${cookieName}_login`;
  const cookieOptions = { path: "/debug", httpOnly: true, secure, sameSite: "Lax" as const };
  const redirectUri = `${config.publicBaseUrl}/debug/callback`;
  const pending = new Map<string, { verifier: string; expires: number }>();
  if (enabled) {
    db.prepare(`insert into oauth_clients(client_id, client_name, redirect_uris_json, application_type, created_at)
      values (?, ?, ?, 'web', ?) on conflict(client_id) do update set redirect_uris_json = excluded.redirect_uris_json`)
      .run(CLIENT_ID, "Agents Chat Debug (administrator only)", JSON.stringify([redirectUri]), new Date().toISOString());
  }
  const allowed = (agentId: string) => {
    const user = db.prepare(`select provider_subject from users where id = ? and provider = 'github'`).get(agentId) as
      { provider_subject: string } | undefined;
    return Boolean(user && config.debugGithubIds?.includes(user.provider_subject));
  };
  const revoke = (token: string | undefined) => {
    if (token) db.prepare(`delete from oauth_access_tokens where token_hash = ? and client_id = ?`)
      .run(digest(token).toString("hex"), CLIENT_ID);
  };

  app.use("*", async (c, next) => {
    c.header("Cache-Control", "no-store");
    c.header("Referrer-Policy", "no-referrer");
    c.header("X-Content-Type-Options", "nosniff");
    c.header("X-Robots-Tag", "noindex, nofollow");
    c.header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'");
    if (!enabled) return c.notFound();
    await next();
  });
  app.get("/", (c) => c.html(assets.get("index.html")!));
  app.get("/debug.css", (c) => { c.header("Content-Type", "text/css; charset=utf-8"); return c.body(assets.get("debug.css")!); });
  app.get("/debug.js", (c) => { c.header("Content-Type", "text/javascript; charset=utf-8"); return c.body(assets.get("debug.js")!); });

  app.get("/login", (c) => {
    for (const [key, login] of pending) if (login.expires <= Date.now()) pending.delete(key);
    const prior = getCookie(c, loginCookie);
    if (prior) pending.delete(prior);
    if (pending.size >= 200) return c.text("Too many sign-in attempts. Please try again later.", 429);
    const state = randomBytes(32).toString("base64url");
    const verifier = randomBytes(32).toString("base64url");
    pending.set(state, { verifier, expires: Date.now() + LOGIN_TTL_MS });
    setCookie(c, loginCookie, state, { ...cookieOptions, maxAge: LOGIN_TTL_MS / 1000 });
    const url = new URL(`${config.publicBaseUrl}/oauth/authorize`);
    url.search = new URLSearchParams({ response_type: "code", client_id: CLIENT_ID, redirect_uri: redirectUri,
      state, code_challenge: digest(verifier).toString("base64url"), code_challenge_method: "S256",
      resource: `${config.publicBaseUrl}/mcp`, scope: "chat:read events:read" }).toString();
    return c.redirect(url.toString());
  });
  app.get("/callback", async (c) => {
    const state = c.req.query("state");
    const login = state ? pending.get(state) : undefined;
    if (!state || getCookie(c, loginCookie) !== state || !login || login.expires <= Date.now()) {
      return c.text("This sign-in has expired or is invalid. Start again at /debug.", 400);
    }
    pending.delete(state);
    deleteCookie(c, loginCookie, cookieOptions);
    if (c.req.query("error")) return c.redirect("/debug");
    if (c.req.query("iss") !== config.publicBaseUrl || !c.req.query("code")) return c.text("Invalid sign-in response.", 400);
    const response = await oauth.app.request("/oauth/token", { method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ grant_type: "authorization_code", code: c.req.query("code")!, client_id: CLIENT_ID,
        redirect_uri: redirectUri, code_verifier: login.verifier, resource: `${config.publicBaseUrl}/mcp` }).toString()
    });
    if (!response.ok) return c.text("Sign-in failed. Start again at /debug.", 400);
    const tokens = await response.json() as { access_token: string; refresh_token?: string; expires_in: number };
    // This UI has one-hour sessions, not background/offline access.
    if (tokens.refresh_token) db.prepare(`delete from oauth_refresh_tokens where token_hash = ? and client_id = ?`)
      .run(digest(tokens.refresh_token).toString("hex"), CLIENT_ID);
    const auth = oauth.authenticate(`Bearer ${tokens.access_token}`);
    if (!auth || auth.clientId !== CLIENT_ID || !allowed(auth.agent.id)) {
      revoke(tokens.access_token);
      return c.text("This debug view is restricted to the server administrator.", 403);
    }
    revoke(getCookie(c, cookieName));
    setCookie(c, cookieName, tokens.access_token, { ...cookieOptions, maxAge: Math.min(tokens.expires_in, 3600) });
    return c.redirect("/debug");
  });
  app.post("/logout", (c) => {
    const origin = c.req.header("Origin");
    // With no-referrer, Chromium sends Origin: null on a form navigation.
    // Fetch Metadata is browser-controlled and still distinguishes same-origin
    // forms from cross-site/same-site CSRF attempts; never trust a null origin alone.
    const sameOriginForm = (!origin || origin === "null") && c.req.header("Sec-Fetch-Site") === "same-origin";
    if (origin !== new URL(config.publicBaseUrl).origin && !sameOriginForm) return c.text("Invalid origin.", 403);
    revoke(getCookie(c, cookieName));
    deleteCookie(c, cookieName, cookieOptions);
    return c.redirect("/debug", 303);
  });
  app.get("/api/events", (c) => {
    const token = getCookie(c, cookieName);
    const auth = token ? oauth.authenticate(`Bearer ${token}`) : null;
    if (!auth || auth.clientId !== CLIENT_ID) return c.json({ error: "sign_in_required" }, 401);
    if (!allowed(auth.agent.id)) return c.json({ error: "administrator_only" }, 403);
    const after = c.req.query("after");
    const limit = c.req.query("limit") ?? "200";
    if ((after !== undefined && !/^\d{1,16}$/.test(after)) || !/^\d{1,3}$/.test(limit) ||
      !Number.isSafeInteger(Number(after ?? 0)) || Number(limit) < 1 || Number(limit) > 500) {
      return c.json({ error: "invalid_cursor_or_limit" }, 400);
    }
    return c.json({ ...log.read(after === undefined ? undefined : Number(after), Number(limit)), viewer: auth.agent.name });
  });
  return app;
}
