import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { createServer as createHttpServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer } from "../server.js";
import { routeUpstream } from "../upstream.js";
import codexLiteRequest from "./fixtures/codex-lite.request.json" with { type: "json" };

const originalEnv = { ...process.env };
const originalCwd = process.cwd();
let upstream: Server;
let proxy: Server;
let base: string;
let dir: string;
let status = 200;
let seen: { path: string; headers: Record<string, string | string[] | undefined>; body: string }[] = [];

async function listen(server: Server): Promise<string> {
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}

before(async () => {
  dir = mkdtempSync(join(tmpdir(), "jev-oauth-"));
  process.env.JEV_CONFIG_HOME = dir;
  process.chdir(dir);
  process.env.JEV_STUB = "1";
  process.env.JEV_MODE = "enforce";
  process.env.JEV_LOG = join(dir, "decisions.jsonl");
  // These must never replace session routing or credentials.
  process.env.UPSTREAM = "http://127.0.0.1:1";
  process.env.UPSTREAM_API_KEY = "wrong-gateway-key";
  process.env.OPENAI_UPSTREAM = "http://127.0.0.1:1";
  upstream = createHttpServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on("data", (chunk: Buffer) => chunks.push(chunk));
    req.on("end", () => {
      seen.push({ path: req.url!, headers: req.headers, body: Buffer.concat(chunks).toString("utf8") });
      res.writeHead(status, {
        "content-type": "application/json",
        ...(status === 401 ? { "www-authenticate": 'Bearer error="invalid_token"' } : {}),
        ...(status === 307 ? { location: `${base}/must-not-follow` } : {}),
      });
      res.end(status === 200 ? '{"ok":true}' : '{"error":"upstream"}');
    });
  });
  const upstreamBase = await listen(upstream);
  process.env.CLAUDE_OAUTH_UPSTREAM = upstreamBase;
  process.env.CODEX_OAUTH_UPSTREAM = `${upstreamBase}/backend-api/codex`;
  process.env.GROK_OAUTH_UPSTREAM = upstreamBase;
  proxy = createServer({ capture: true });
  base = await listen(proxy);
});

after(async () => {
  await Promise.all([proxy, upstream].map((server) => new Promise<void>((resolve, reject) => {
    server.close((err) => err ? reject(err) : resolve());
    server.closeAllConnections();
  })));
  process.chdir(originalCwd);
  for (const key of Object.keys(process.env)) if (!(key in originalEnv)) delete process.env[key];
  Object.assign(process.env, originalEnv);
  rmSync(dir, { recursive: true, force: true });
});

const cases = [
  { name: "claude", path: "/v1/messages", target: "/v1/messages", body: { messages: [{ role: "user", content: "Read the file" }], tools: [{ name: "Read", input_schema: { type: "object" } }] }, choice: { type: "tool", name: "Read" } },
  { name: "codex", path: "/responses", target: "/backend-api/codex/responses", body: { input: "Read the file", tools: [{ type: "function", name: "Read", parameters: { type: "object" } }] }, choice: { type: "function", name: "Read" } },
  { name: "grok", path: "/v1/chat/completions", target: "/v1/chat/completions", body: { messages: [{ role: "user", content: "Read the file" }], tools: [{ type: "function", function: { name: "Read", parameters: { type: "object" } } }] }, choice: { type: "function", function: { name: "Read" } } },
];

for (const c of cases) {
  test(`${c.name}: session token is preserved, refreshed per request, and routed with classification`, async () => {
    for (const token of ["session-before-refresh", "session-after-refresh"]) {
      const response = await fetch(`${base}/oauth/${c.name}${c.path}?beta=1`, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: `Bearer ${token}`, "chatgpt-account-id": "account-secret", "anthropic-beta": "oauth-2025-04-20", "anthropic-version": "2023-06-01" },
        body: JSON.stringify({ model: "test-model", ...c.body }),
      });
      assert.equal(response.status, 200);
      await response.text();
      const request = seen.at(-1)!;
      assert.equal(request.path, `${c.target}?beta=1`);
      assert.equal(request.headers.authorization, `Bearer ${token}`);
      assert.equal(request.headers["chatgpt-account-id"], "account-secret");
      assert.equal(request.headers["anthropic-beta"], "oauth-2025-04-20");
      assert.equal(request.headers["x-api-key"], undefined);
      const body = JSON.parse(request.body);
      assert.deepEqual(body.tool_choice, c.choice);
      assert.deepEqual(body.tools, c.body.tools);
    }
  });
}

test("session auxiliary endpoints and malformed JSON keep the selected upstream", async () => {
  for (const [path, method, body, expected] of [
    ["/oauth/codex/models?client_version=1", "GET", undefined, "/backend-api/codex/models?client_version=1"],
    ["/oauth/codex/responses/compact", "POST", "{}", "/backend-api/codex/responses/compact"],
    ["/oauth/grok/v1/models", "GET", undefined, "/v1/models"],
    ["/oauth/claude/v1/messages/count_tokens", "POST", "{}", "/v1/messages/count_tokens"],
    ["/oauth/codex/responses", "POST", "malformed", "/backend-api/codex/responses"],
  ] as const) {
    const res = await fetch(`${base}${path}`, { method, body, headers: { authorization: "Bearer auxiliary-token" } });
    assert.equal(res.status, 200);
    await res.text();
    assert.equal(seen.at(-1)!.path, expected);
    assert.equal(seen.at(-1)!.headers.authorization, "Bearer auxiliary-token");
    assert.equal(seen.at(-1)!.body, body ?? "");
  }
});

test("401 and authentication challenge reach the agent for token refresh", async () => {
  status = 401;
  try {
    const response = await fetch(`${base}/oauth/codex/models`, { headers: { authorization: "Bearer expired" } });
    assert.equal(response.status, 401);
    assert.equal(response.headers.get("www-authenticate"), 'Bearer error="invalid_token"');
    assert.deepEqual(await response.json(), { error: "upstream" });
  } finally { status = 200; }
});

test("upstream redirects are returned without replaying credentials", async () => {
  status = 307;
  const count = seen.length;
  try {
    const response = await fetch(`${base}/oauth/grok/v1/models`, { redirect: "manual" });
    assert.equal(response.status, 307);
    await response.text();
    assert.equal(seen.length, count + 1);
  } finally { status = 200; }
});

test("capture and decision logs omit session credentials and query secrets", async () => {
  const response = await fetch(`${base}/oauth/claude/v1/messages?access_token=query-secret`, {
    method: "POST",
    headers: { authorization: "Bearer capture-secret", cookie: "session=cookie-secret", "x-custom-token": "custom-secret", "chatgpt-account-id": "account-secret" },
    body: JSON.stringify({ model: "test", ...cases[0]!.body }),
  });
  await response.text();
  const files = readdirSync(join(dir, ".jev-classifier", "captures")).map((file) => join(dir, ".jev-classifier", "captures", file));
  files.push(process.env.JEV_LOG!);
  for (const file of files) {
    assert.doesNotMatch(readFileSync(file, "utf8"), /capture-secret|cookie-secret|custom-secret|account-secret|query-secret|session-before-refresh|session-after-refresh/);
  }
});

test("unknown session routes fail locally without forwarding", async () => {
  const count = seen.length;
  const response = await fetch(`${base}/oauth/unknown/responses`);
  assert.equal(response.status, 400);
  await response.text();
  assert.equal(seen.length, count);
  assert.throws(() => routeUpstream("/oauth/codex/%2e%2e/models"));
});

test("session shadow mode preserves request bytes", async () => {
  process.env.JEV_MODE = "shadow";
  try {
    const body = JSON.stringify(cases[1]!.body, null, 2);
    const response = await fetch(`${base}/oauth/codex/responses`, { method: "POST", body });
    await response.text();
    assert.equal(seen.at(-1)!.body, body);
  } finally { process.env.JEV_MODE = "enforce"; }
});

test("API provider routes support auxiliary endpoints and replace only API credentials", async () => {
  const previous = process.env.UPSTREAM;
  process.env.UPSTREAM = `${process.env.CLAUDE_OAUTH_UPSTREAM}/gateway`;
  try {
    for (const provider of ["claude", "codex", "grok"]) {
      const response = await fetch(`${base}/api/${provider}/v1/models`, {
        headers: { authorization: "Bearer old-session", cookie: "session=old", "chatgpt-account-id": "old-account", "api-key": "old-key" },
      });
      assert.equal(response.status, 200);
      await response.text();
      assert.equal(seen.at(-1)!.path, "/gateway/v1/models");
      const headers = seen.at(-1)!.headers;
      assert.equal(headers.authorization, "Bearer wrong-gateway-key");
      assert.equal(headers["x-api-key"], "wrong-gateway-key");
      for (const key of ["cookie", "chatgpt-account-id", "api-key"]) assert.equal(headers[key], undefined);
    }
  } finally { process.env.UPSTREAM = previous; }
});

test("session defaults select subscription services, not public API destinations", () => {
  for (const [provider, env, suffix, expected] of [
    ["claude", "CLAUDE_OAUTH_UPSTREAM", "/v1/messages", "https://api.anthropic.com/v1/messages"],
    ["codex", "CODEX_OAUTH_UPSTREAM", "/responses", "https://chatgpt.com/backend-api/codex/responses"],
    ["grok", "GROK_OAUTH_UPSTREAM", "/v1/chat/completions", "https://cli-chat-proxy.grok.com/v1/chat/completions"],
  ]) {
    const previous = process.env[env!];
    delete process.env[env!];
    try { assert.equal(routeUpstream(`/oauth/${provider}${suffix}`).target, expected); }
    finally { process.env[env!] = previous; }
  }
});

test("Codex Lite requests produce decisions and health distinguishes classification from bypass", async () => {
  const response = await fetch(`${base}/oauth/codex/responses`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-openai-internal-codex-responses-lite": "true", authorization: "Bearer lite-token" },
    body: JSON.stringify(codexLiteRequest, null, 2),
  });
  assert.equal(response.status, 200);
  await response.text();
  const forwarded = JSON.parse(seen.at(-1)!.body);
  assert.equal(seen.at(-1)!.body, JSON.stringify(codexLiteRequest, null, 2), "Lite requests pass through byte for byte");
  assert.equal(forwarded.tool_choice, "auto");
  assert.deepEqual(forwarded.input, codexLiteRequest.input);
  const records = readFileSync(process.env.JEV_LOG!, "utf8").trim().split("\n").map((line) => JSON.parse(line));
  assert.equal(records.at(-1).chosen, "exec");
  assert.equal(records.at(-1).toolsCount, 2);
  assert.equal(records.at(-1).mode, "shadow");
  assert.equal(records.at(-1).applied, false);
  assert.match(records.at(-1).shadowReason, /Responses Lite/);
  const count = seen.length;
  const health = await (await fetch(`${base}/__jev/health`)).json() as any;
  assert.equal(health.service, "jev-classifier");
  assert.ok(health.classified > 0);
  assert.ok(health.agents.codex.classified > 0);
  assert.equal(health.agents.codex.lastDecision.mode, "shadow");
  assert.equal(health.agents.codex.lastDecision.applied, false);
  assert.ok(health.invalidJson > 0);
  assert.equal(seen.length, count, "health is local and never reaches a provider");
  assert.doesNotMatch(JSON.stringify(health), /lite-token|wrong-gateway-key/);
});

test("gateways are not coding-agent destinations", () => {
  for (const provider of ["openrouter", "vercel"]) {
    assert.throws(() => routeUpstream(`/api/${provider}/v1/responses`));
    assert.throws(() => routeUpstream(`/oauth/${provider}/responses`));
  }
});
