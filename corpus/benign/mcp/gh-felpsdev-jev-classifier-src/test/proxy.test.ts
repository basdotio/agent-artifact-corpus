import assert from "node:assert/strict";
import { createServer as createHttpServer, type Server } from "node:http";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import type { AddressInfo } from "node:net";
import { createServer } from "../server.js";
import type { DecisionRecord } from "../log.js";
import anthropicRequest from "./fixtures/anthropic.request.json" with { type: "json" };

const SSE = [
  'event: content_block_start',
  'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
  '',
  'event: content_block_start',
  'data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_02","name":"Edit","input":{}}}',
  '',
  'event: message_stop',
  'data: {"type":"message_stop"}',
  '',
].join("\n");

interface Seen {
  body: any;
  headers: Record<string, string | string[] | undefined>;
  url?: string;
}

let seen: Seen | undefined;
let mode: "sse" | "json" = "sse";
let upstream: Server;
let proxy: Server;
let dir: string;
let proxyUrl: string;

function listen(server: Server): Promise<number> {
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve((server.address() as AddressInfo).port)));
}

function post(body: unknown): Promise<Response> {
  return fetch(`${proxyUrl}/v1/messages`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": "sk-test-123",
      "anthropic-version": "2023-06-01",
      "anthropic-beta": "prompt-caching-2024-07-31",
    },
    body: JSON.stringify(body),
  });
}

function decisions(): DecisionRecord[] {
  return readFileSync(process.env.JEV_LOG as string, "utf8")
    .split("\n")
    .filter(Boolean)
    .map((l) => JSON.parse(l) as DecisionRecord);
}

before(async () => {
  dir = mkdtempSync(join(tmpdir(), "jev-test-"));
  process.env.JEV_CONFIG_HOME = dir;
  process.env.JEV_STUB = "1";
  process.env.JEV_MODE = "enforce";
  process.env.JEV_LOG = join(dir, "decisions.jsonl");
  delete process.env.TYPESAFE_API_KEY;

  upstream = createHttpServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => {
      seen = { url: req.url, headers: req.headers, body: JSON.parse(Buffer.concat(chunks).toString("utf8")) };
      if (mode === "json") {
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ id: "msg_1", content: [{ type: "tool_use", id: "t1", name: "Bash", input: {} }] }));
        return;
      }
      res.writeHead(200, { "content-type": "text/event-stream" });
      // Write in two pieces so the tap has to stitch a split line back together.
      const half = Math.floor(SSE.length / 2);
      res.write(SSE.slice(0, half));
      res.end(SSE.slice(half));
    });
  });
  const upstreamPort = await listen(upstream);
  process.env.ANTHROPIC_UPSTREAM = `http://127.0.0.1:${upstreamPort}`;

  proxy = createServer();
  proxyUrl = `http://127.0.0.1:${await listen(proxy)}`;
});

after(() => {
  upstream.close();
  proxy.close();
  rmSync(dir, { recursive: true, force: true });
});

test("OpenCode client route forwards to its selected provider and reports its own counters", async () => {
  process.env.JEV_MODE = "shadow";
  const response = await fetch(`${proxyUrl}/clients/opencode/api/claude/v1/messages`, {
    method: "POST", headers: { "content-type": "application/json", "x-api-key": "opencode-key" },
    body: JSON.stringify(anthropicRequest),
  });
  await response.text();
  assert.equal(response.status, 200);
  assert.equal(seen?.url, "/v1/messages");
  assert.equal(seen?.headers["x-api-key"], "opencode-key");
  assert.deepEqual(seen?.body, anthropicRequest);
  const health = await (await fetch(`${proxyUrl}/__jev/health`)).json() as any;
  assert.equal(health.agents.opencode.classified, 1);
  assert.equal(decisions().at(-1)?.agent, "opencode");
  process.env.JEV_MODE = "enforce";
});

test("enforce: rewrites tool_choice, streams through, logs chosen and actual", async () => {
  mode = "sse";
  const res = await post(anthropicRequest);
  const text = await res.text();

  assert.equal(res.status, 200);
  assert.equal(res.headers.get("content-type"), "text/event-stream");
  assert.equal(text, SSE, "the SSE body is forwarded byte for byte");

  assert.deepEqual(seen?.body.tool_choice, { type: "tool", name: "Edit" });
  assert.equal(seen?.body.tools.length, 3, "tools are never removed");
  assert.equal(seen?.headers["x-api-key"], "sk-test-123", "auth headers are forwarded");
  assert.equal(seen?.headers["anthropic-version"], "2023-06-01");
  assert.equal(seen?.headers["anthropic-beta"], "prompt-caching-2024-07-31");
  assert.equal(
    Number(seen?.headers["content-length"]),
    Buffer.byteLength(JSON.stringify(seen?.body)),
    "content-length matches the rewritten body",
  );

  const record = decisions().at(-1) as DecisionRecord;
  assert.equal(record.agent, "anthropic");
  assert.equal(record.mode, "enforce");
  assert.equal(record.chosen, "Edit");
  assert.equal(record.actual, "Edit");
  assert.equal(record.match, true);
  assert.equal(record.applied, true);
  assert.equal(record.toolsCount, 3);
  assert.equal(record.session, "session_abc123");
  assert.equal(record.model, "claude-sonnet-4-5-20250929");
});

test("non-streaming JSON responses are parsed for the actual tool", async () => {
  mode = "json";
  const res = await post(anthropicRequest);
  const json = (await res.json()) as any;
  assert.equal(json.content[0].name, "Bash");

  const record = decisions().at(-1) as DecisionRecord;
  assert.equal(record.chosen, "Edit");
  assert.equal(record.actual, "Bash");
  assert.equal(record.match, false);
});

test("shadow mode logs without touching the request", async () => {
  mode = "sse";
  process.env.JEV_MODE = "shadow";
  await (await post(anthropicRequest)).text();
  process.env.JEV_MODE = "enforce";

  assert.equal(seen?.body.tool_choice, undefined, "shadow leaves tool_choice alone");
  const record = decisions().at(-1) as DecisionRecord;
  assert.equal(record.mode, "shadow");
  assert.equal(record.applied, false);
  assert.equal(record.chosen, "Edit");
  assert.equal(record.actual, "Edit");
});

test("a request without tools is forwarded untouched and not logged", async () => {
  mode = "sse";
  const before = decisions().length;
  await (
    await post({ model: "claude-sonnet-4-5-20250929", messages: [{ role: "user", content: "hi" }] })
  ).text();
  assert.equal(seen?.body.tool_choice, undefined);
  assert.equal(decisions().length, before);
});

test("UPSTREAM_API_KEY replaces the agent's credentials", async () => {
  mode = "sse";
  process.env.UPSTREAM_API_KEY = "sk-or-proxy";
  await (await post(anthropicRequest)).text();
  delete process.env.UPSTREAM_API_KEY;

  assert.equal(seen?.headers["x-api-key"], "sk-or-proxy");
  assert.equal(seen?.headers["authorization"], "Bearer sk-or-proxy");
});

test("UPSTREAM overrides provider defaults and preserves the provider path prefix", async () => {
  const env = { ...process.env };
  mode = "json";
  try {
    process.env.UPSTREAM = `${process.env.ANTHROPIC_UPSTREAM}/api/`;
    process.env.UPSTREAM_API_KEY = "provider-test-key";
    process.env.ANTHROPIC_UPSTREAM = "http://127.0.0.1:1";
    process.env.OPENAI_UPSTREAM = "http://127.0.0.1:1";
    process.env.XAI_UPSTREAM = "http://127.0.0.1:1";

    for (const path of ["/v1/messages", "/v1/chat/completions", "/v1/responses"]) {
      const body = { model: "provider/model", messages: [], input: "hello" };
      const response = await fetch(`${proxyUrl}${path}?test=1`, {
        method: "POST",
        headers: { "content-type": "application/json", authorization: "Bearer dummy" },
        body: JSON.stringify(body),
      });
      await response.text();
      assert.equal(response.status, 200);
      assert.equal(seen?.url, `/api${path}?test=1`);
      assert.deepEqual(seen?.body, body);
      assert.equal(seen?.headers.authorization, "Bearer provider-test-key");
    }
  } finally {
    for (const key of ["UPSTREAM", "UPSTREAM_API_KEY", "ANTHROPIC_UPSTREAM", "OPENAI_UPSTREAM", "XAI_UPSTREAM"]) {
      if (env[key] === undefined) delete process.env[key];
      else process.env[key] = env[key];
    }
  }
});
