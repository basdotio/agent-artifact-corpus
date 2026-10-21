/**
 * Handles the upstream OAuth handshake with vas3k.club.
 *
 * Routes:
 *   GET  /authorize  → render approval dialog, then redirect to vas3k.club/auth/openid/authorize
 *   POST /authorize  → user clicked "approve", do the redirect
 *   GET  /callback   → exchange `code` for an access_token, hand a token back to the MCP client
 */

import type { AuthRequest } from "@cloudflare/workers-oauth-provider";
import { Hono } from "hono";
import {
  CURRENT_PROPS_VERSION,
  UPSTREAM_SCOPE as SCOPE,
  STATE_TTL_SECONDS,
  UPSTREAM_TIMEOUT_MS,
} from "./constants";
import { installMd } from "./install-md";
import { landingHtml } from "./landing";
import type { Env, Props } from "./types";

// ---------- HMAC-signed state ------------------------------------------------
// Replaces KV-stored state — eliminates the regional-eventual-consistency
// race where /callback would arrive at a colo that hadn't yet seen
// /authorize's KV write. We sign `{oauthReqInfo, exp}` with the
// COOKIE_ENCRYPTION_KEY secret using HMAC-SHA-256 and put the whole thing
// in the URL state param. /callback verifies and decodes — no shared
// storage required.

interface SignedState {
  oauthReqInfo: AuthRequest;
  exp: number; // unix epoch seconds
}

function b64urlEncode(bytes: Uint8Array): string {
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
function b64urlDecode(s: string): Uint8Array {
  s = s.replace(/-/g, "+").replace(/_/g, "/");
  while (s.length % 4) s += "=";
  const str = atob(s);
  const bytes = new Uint8Array(str.length);
  for (let i = 0; i < str.length; i++) bytes[i] = str.charCodeAt(i);
  return bytes;
}

async function hmacKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

async function signState(state: SignedState, secret: string): Promise<string> {
  const payload = new TextEncoder().encode(JSON.stringify(state));
  const key = await hmacKey(secret);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, payload));
  return `${b64urlEncode(payload)}.${b64urlEncode(sig)}`;
}

async function verifyState(token: string, secret: string): Promise<SignedState | null> {
  const [payloadB64, sigB64] = token.split(".");
  if (!payloadB64 || !sigB64) return null;
  const payload = b64urlDecode(payloadB64);
  const sig = b64urlDecode(sigB64);
  const key = await hmacKey(secret);
  const ok = await crypto.subtle.verify("HMAC", key, sig, payload);
  if (!ok) return null;
  let parsed: SignedState;
  try {
    parsed = JSON.parse(new TextDecoder().decode(payload)) as SignedState;
  } catch {
    return null;
  }
  if (parsed.exp < Math.floor(Date.now() / 1000)) return null;
  return parsed;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

const app = new Hono<{ Bindings: Env }>();

app.get("/", (c) => {
  c.header("Cache-Control", "public, max-age=300, s-maxage=3600");
  return c.html(landingHtml);
});

// Markdown install guide for AI agents — same content at /install.md
// (intuitive) and /llms.txt (the llmstxt.org convention). Point an agent
// at either URL and it has every URL + snippet it needs.
app.get("/install.md", (c) => {
  c.header("Content-Type", "text/markdown; charset=utf-8");
  c.header("Cache-Control", "public, max-age=300, s-maxage=3600");
  return c.body(installMd);
});
app.get("/llms.txt", (c) => {
  c.header("Content-Type", "text/plain; charset=utf-8");
  c.header("Cache-Control", "public, max-age=300, s-maxage=3600");
  return c.body(installMd);
});

app.get("/authorize", async (c) => {
  // OAuthProvider throws on bad PKCE / unsupported response_type / etc.
  // Hono would render those as 500; OAuth spec wants 400 on malformed
  // authorize requests, so wrap and surface as text/plain.
  let oauthReqInfo: AuthRequest;
  try {
    oauthReqInfo = await c.env.OAUTH_PROVIDER.parseAuthRequest(c.req.raw);
  } catch (err) {
    return c.text(`OAuth authorize request rejected: ${(err as Error).message}`, 400);
  }
  if (!oauthReqInfo.clientId) {
    return c.text("Invalid request", 400);
  }

  // PKCE is mandated by MCP 2025-06-18 §2.1.1 and OAuth 2.1. The library
  // verifies code_challenge against code_verifier only when one was sent —
  // reject outright if the client omitted it (defends against legacy
  // PKCE-bypass downgrade where omission silently disables the check).
  if (!oauthReqInfo.codeChallenge) {
    return c.text("PKCE required (code_challenge with method=S256)", 400);
  }

  const client = await c.env.OAUTH_PROVIDER.lookupClient(oauthReqInfo.clientId);
  const clientName = client?.clientName ?? oauthReqInfo.clientId;
  // The `client_id` is either an opaque registered id, or — with CIMD — a
  // stable HTTPS URL the user can verify. Surface it alongside the name so
  // a user being phished sees the mismatch.
  const clientIdentifier = oauthReqInfo.clientId;
  const redirectUri = oauthReqInfo.redirectUri ?? "(none)";

  // HMAC-sign the MCP-side OAuth request and ship it as the upstream `state`
  // param — no shared KV needed, no regional consistency race.
  const state = await signState(
    {
      oauthReqInfo,
      exp: Math.floor(Date.now() / 1000) + STATE_TTL_SECONDS,
    },
    c.env.COOKIE_ENCRYPTION_KEY,
  );

  // Consent screen — same design system as the landing page (Ubuntu, the
  // .block + .button tokens, warm-amber accent). The `client_name` is
  // attacker-controlled, so every dynamic field goes through escapeHtml.
  return c.html(`<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Подключить «${escapeHtml(clientName)}» к Клубу?</title>
<meta name="robots" content="noindex" />
<link rel="icon" type="image/x-icon" href="/favicon.ico" sizes="32x32" />
<link rel="icon" type="image/png" href="/favicon-96x96.png" sizes="96x96" />
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Ubuntu:wght@400;500;700&family=Ubuntu+Mono:wght@400;700&display=swap" />
<style>
:root {
  --sans-font: "Ubuntu", Helvetica, Verdana, sans-serif;
  --mono-font: "Ubuntu Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  --block-border-radius: 15px;
  --button-border-radius: 15px;
  --accent: rgba(255, 196, 85, 0.91);
  --accent-strong: #f7b733;
  --accent-soft: rgba(255, 196, 85, 0.18);
  --bg-color: #FCFDFF;
  --text-color: #333;
  --brighter-text-color: #000;
  --block-bg-color: #FFF;
  --block-shadow: 10px 15px 40px rgba(83, 91, 110, 0.11);
  --block-border: none;
  --link-color: #333;
  --link-hover-color: #000;
  --button-color: #FFF;
  --button-bg-color: #333;
  --button-border: solid 2px #333;
  --button-hover-color: #333;
  --button-hover-bg-color: #FFF;
  --button-hover-border: solid 2px #333;
  --muted: #6b7180;
  --hairline: rgba(0, 0, 0, 0.08);
  --kv-bg: rgba(0, 0, 0, 0.045);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg-color: #282c35;
    --text-color: #DDD;
    --brighter-text-color: #FFF;
    --block-bg-color: #1B1B1C;
    --block-shadow: 0 0 0 #000;
    --block-border: solid 1px #FCFDFF;
    --link-color: #DDD;
    --link-hover-color: #FFF;
    --button-color: #333;
    --button-bg-color: #FFF;
    --button-border: solid 2px #FFF;
    --button-hover-color: #FFF;
    --button-hover-bg-color: #333;
    --button-hover-border: solid 2px #FFF;
    --muted: #9aa0ad;
    --hairline: rgba(255, 255, 255, 0.12);
    --kv-bg: rgba(255, 255, 255, 0.05);
  }
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: var(--sans-font);
  font-size: 17px;
  line-height: 1.55;
  color: var(--text-color);
  background: var(--bg-color);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
@media (max-width: 800px) { body { font-size: 15px; } }

main {
  max-width: 36rem;
  margin: 0 auto;
  padding: 36px 20px 40px;
}
@media (max-width: 570px) { main { padding: 22px 14px 28px; } }

a {
  color: var(--link-color);
  font-weight: 500;
  transition: color 0.1s linear;
}
a:hover { color: var(--link-hover-color); }

.brand {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  margin: 0 0 22px;
}
.brand-tag {
  display: inline-block;
  background: var(--accent);
  color: #333;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 500;
  transition: transform 0.15s ease;
}
.brand:hover .brand-tag { transform: translateY(-1px); }

.card {
  padding: 36px;
  background: var(--block-bg-color);
  border: var(--block-border);
  border-radius: var(--block-border-radius);
  box-shadow: var(--block-shadow);
}
@media (max-width: 570px) { .card { padding: 24px 20px; } }

h1 {
  margin: 0 0 14px;
  font-size: 28px;
  line-height: 1.2;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--brighter-text-color);
  word-wrap: break-word;
}
@media (max-width: 570px) { h1 { font-size: 22px; } }

p { margin: 0 0 14px; }
p:last-of-type { margin-bottom: 0; }

.warn {
  margin: 18px 0 22px;
  padding: 14px 18px;
  background: var(--accent-soft);
  border: 1px solid var(--accent-strong);
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
}
.warn strong { color: var(--brighter-text-color); }

.kv {
  margin: 8px 0;
  padding: 12px 16px;
  background: var(--kv-bg);
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.4;
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 12px;
  align-items: baseline;
}
@media (max-width: 480px) {
  .kv { grid-template-columns: 1fr; gap: 6px; }
}
.kv-label {
  font-family: var(--sans-font);
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}
.kv code {
  font-family: var(--mono-font);
  font-size: 13px;
  color: var(--brighter-text-color);
  background: transparent;
  padding: 0;
  word-break: break-all;
}

ul { margin: 8px 0 18px; padding-left: 1.3rem; }
ul li { margin: 5px 0; }

code.inline {
  font-family: var(--mono-font);
  font-size: 0.92em;
  padding: 2px 6px;
  border-radius: 5px;
  background: var(--accent-soft);
  color: var(--brighter-text-color);
}

.fineprint {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid var(--hairline);
  font-size: 14px;
  color: var(--muted);
}
.fineprint p { margin: 0 0 8px; }
.fineprint p:last-child { margin-bottom: 0; }
.fineprint a { color: var(--text-color); }
.fineprint a:hover { color: var(--brighter-text-color); }

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin: 26px 0 0;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none !important;
  padding: 14px 22px;
  border-radius: var(--button-border-radius);
  background: var(--button-bg-color);
  border: var(--button-border);
  color: var(--button-color);
  cursor: pointer;
  line-height: 1em;
  font-family: var(--sans-font);
  font-weight: 500;
  font-size: 16px;
  transition: 0.2s ease-out;
}
.button:hover {
  color: var(--button-hover-color);
  background: var(--button-hover-bg-color);
  border: var(--button-hover-border);
}
.button:focus-visible {
  outline: 2px solid var(--accent-strong);
  outline-offset: 2px;
}
.button-ghost {
  background: transparent;
  color: var(--text-color);
  border: solid 2px var(--hairline);
}
.button-ghost:hover {
  background: transparent;
  color: var(--brighter-text-color);
  border: solid 2px var(--text-color);
}
@media (max-width: 480px) {
  .button { width: 100%; }
}

.warn details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--accent-strong);
}
.warn summary {
  cursor: pointer;
  font-weight: 500;
  color: var(--brighter-text-color);
  list-style: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.warn summary::-webkit-details-marker { display: none; }
.warn summary::before {
  content: "▸";
  display: inline-block;
  font-size: 11px;
  transition: transform 0.15s ease;
}
.warn details[open] summary::before { transform: rotate(90deg); }
.warn details > p { margin: 10px 0 0; }

.ethics-check {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin: 22px 0 0;
  padding-top: 18px;
  border-top: 1px solid var(--hairline);
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-color);
  cursor: pointer;
}
.ethics-check input[type="checkbox"] {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  margin: 2px 0 0;
  accent-color: var(--accent-strong);
  cursor: pointer;
}
.ethics-check span { user-select: none; }
</style>
</head>
<body>
<main>
  <a class="brand" href="/" aria-label="vas3k-mcp">
    <span class="brand-tag">✖️ Вастрик.Клуб MCP</span>
  </a>

  <section class="card">
    <h1>Подключить «${escapeHtml(clientName)}» к Клубу?</h1>
    <p>Приложение запрашивает доступ к твоему профилю на <a href="https://vas3k.club">vas3k.club</a> через OAuth.</p>

    <div class="warn">⚠️ <strong>Имя «${escapeHtml(clientName)}» приложение указало само — никто его не проверял.</strong> Если это приложение подключал не ты — закрой вкладку. Проверь идентификатор и redirect URL ниже.</div>

    <div class="warn">🧠 <strong>Подумай о приватности участников Клуба.</strong> Контент, который AI-приложение прочитает через MCP — это посты и комментарии других людей, иногда из закрытых разделов. Если твой AI обучается на твоих сообщениях, всё это может попасть в обучение модели и теоретически попасть в чужие руки.
      <details>
        <summary>Где это проверить</summary>
        <p>Открой настройки приватности своего AI-приложения и поищи раздел про обучение модели на твоих данных. В каждом приложении называется по-разному — но если такая опция вообще есть, лучше её отключить перед подключением. Если опции нет и ты не платишь за услуги — это, скорее всего, признак, что данные используются для обучения по умолчанию.</p>
      </details>
    </div>

    <div class="kv"><span class="kv-label">Client ID</span><code>${escapeHtml(clientIdentifier)}</code></div>
    <div class="kv"><span class="kv-label">Redirect URL</span><code>${escapeHtml(redirectUri)}</code></div>

    <p style="margin-top: 18px;">Что приложение сможет:</p>
    <ul>
      <li>доступ к твоему профилю и контактам</li>
      <li>посты, комментарии и ленту, которые видишь ты</li>
      <li>поиск людей и тегов</li>
      <li>если приложение использует <code class="inline">/mcp-full</code> — ставить лайки и закладки, подписки и запросы в друзья от твоего имени</li>
    </ul>

    <p>На следующем экране Клуб формально скажет «приложение не сможет писать посты и комментарии» — это правда: создавать посты или писать комментарии через MCP нельзя. Действия выше (лайки, закладки и подписки) идут через API и в это ограничение не попадают.</p>

    <form method="POST" action="/authorize">
      <input type="hidden" name="state" value="${state}" />
      <label class="ethics-check">
        <input type="checkbox" name="ai_consent" required />
        <span>Я понимаю риск и проверил(а) настройки приватности своего AI-приложения.</span>
      </label>
      <div class="actions">
        <button type="submit" class="button">Подключить и перейти к vas3k.club</button>
        <a href="https://vas3k.club" class="button button-ghost">Отмена</a>
      </div>
    </form>

    <div class="fineprint">
      <p>Отозвать доступ можно в любой момент на <a href="https://vas3k.club/apps/">vas3k.club/apps/</a>.</p>
    </div>
  </section>
</main>
</body>
</html>`);
});

app.post("/authorize", async (c) => {
  const form = await c.req.formData();
  const state = form.get("state");
  if (typeof state !== "string") return c.text("Missing state", 400);

  // Verify the state we minted at GET-time is intact (rejects tampered
  // / expired tokens). We don't need its contents here — the upstream
  // will round-trip it back to /callback, which re-verifies.
  const verified = await verifyState(state, c.env.COOKIE_ENCRYPTION_KEY);
  if (!verified) return c.text("State expired or invalid", 400);

  const redirectUri = new URL("/callback", c.env.PUBLIC_BASE_URL).href;
  const upstream = new URL("/auth/openid/authorize", c.env.VAS3K_BASE_URL);
  upstream.searchParams.set("response_type", "code");
  upstream.searchParams.set("client_id", c.env.VAS3K_CLIENT_ID);
  upstream.searchParams.set("redirect_uri", redirectUri);
  upstream.searchParams.set("scope", SCOPE);
  upstream.searchParams.set("state", state);

  return c.redirect(upstream.href, 302);
});

app.get("/callback", async (c) => {
  const code = c.req.query("code");
  const state = c.req.query("state");
  const error = c.req.query("error");
  if (error) return c.text(`vas3k.club returned: ${error}`, 400);
  if (!code || !state) return c.text("Missing code/state", 400);

  const verified = await verifyState(state, c.env.COOKIE_ENCRYPTION_KEY);
  if (!verified) return c.text("State expired or invalid", 400);

  const oauthReqInfo = verified.oauthReqInfo;
  const redirectUri = new URL("/callback", c.env.PUBLIC_BASE_URL).href;

  // exchange code -> tokens at vas3k.club
  const tokenResp = await fetch(new URL("/auth/openid/token", c.env.VAS3K_BASE_URL).href, {
    method: "POST",
    headers: {
      Authorization: `Basic ${btoa(`${c.env.VAS3K_CLIENT_ID}:${c.env.VAS3K_CLIENT_SECRET}`)}`,
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri,
      client_id: c.env.VAS3K_CLIENT_ID,
    }).toString(),
    signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
  });
  if (!tokenResp.ok) {
    const body = await tokenResp.text();
    console.error("[upstream-token-exchange-fail]", {
      status: tokenResp.status,
      body: body.slice(0, 200),
    });
    return c.text("Token exchange failed", 502);
  }
  const tokens = (await tokenResp.json()) as {
    access_token: string;
    refresh_token?: string;
    token_type?: string;
    expires_in?: number;
    scope?: string;
  };

  // fetch user info to get a stable user id (slug)
  const meResp = await fetch(new URL("/user/me.json", c.env.VAS3K_BASE_URL).href, {
    headers: { Authorization: `Bearer ${tokens.access_token}` },
    signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
  });
  if (!meResp.ok) {
    const body = await meResp.text();
    console.error("[upstream-userinfo-fail]", {
      status: meResp.status,
      body: body.slice(0, 200),
    });
    return c.text("Failed to fetch userinfo", 502);
  }
  const me = (await meResp.json()) as { user?: { slug?: string; full_name?: string } };
  const slug = me.user?.slug ?? "unknown";
  const fullName = me.user?.full_name ?? slug;

  const props: Props = {
    propsVersion: CURRENT_PROPS_VERSION,
    slug,
    fullName,
    upstreamAccessToken: tokens.access_token,
    upstreamRefreshToken: tokens.refresh_token,
    scope: tokens.scope ?? SCOPE,
    // The MCP-side scopes the original `oauthReqInfo` requested. Echo back
    // exactly what the client asked for so /mcp-full's write tools can
    // gate on `props.mcpScopes.includes("write")`.
    // `parseAuthRequest` returns [] when the client omitted `scope=`. Default
    // to the full set so write tools work; clients that explicitly want
    // read-only can pass `scope=read` and the /mcp-full guard will hold.
    mcpScopes: oauthReqInfo.scope.length ? oauthReqInfo.scope : ["read", "write"],
  };

  const { redirectTo } = await c.env.OAUTH_PROVIDER.completeAuthorization({
    request: oauthReqInfo,
    userId: slug,
    metadata: { label: fullName },
    scope: oauthReqInfo.scope,
    props: props as unknown as Record<string, unknown>,
  });

  return c.redirect(redirectTo, 302);
});

export { app as Vas3kHandler };
