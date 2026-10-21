import { jevStatus } from "./jev.js";
import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync } from "node:fs";
import { createServer as createHttpServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { join } from "node:path";
import { Readable } from "node:stream";
import { type Adapter, type Body } from "./adapters/index.js";
import { appendDecision, type DecisionRecord } from "./log.js";
import { chooseNextTool, minConfidence, RESPOND } from "./router.js";
import { sseTap } from "./sse.js";
import { routeUpstream, type UpstreamRoute } from "./upstream.js";
import { gatewayEvent } from "./terminal.js";

/** Headers that belong to a single hop and must not be forwarded. */
const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
  "accept-encoding",
]);

// Capture protocol metadata only. Session credentials and account identifiers stay in memory.
const CAPTURE_HEADERS = new Set(["content-type", "anthropic-version", "anthropic-beta", "openai-beta", "user-agent"]);

export interface ServeOptions {
  readonly capture?: boolean;
  readonly quiet?: boolean;
  readonly instanceId?: string;
  readonly controlToken?: string;
  readonly onStop?: () => void;
}

interface AgentStatus {
  requests: number;
  classified: number;
  failures: number;
  lastRequest: string;
  lastError?: string;
  shadowReason?: string;
  lastDecision?: { tool: string; mode: string; applied: boolean; at: string };
}

interface ProxyStatus {
  requests: number;
  classified: number;
  classificationFailures: number;
  noTools: number;
  invalidJson: number;
  passthrough: number;
  agents: Record<string, AgentStatus>;
}

function readBody(req: IncomingMessage): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    req.on("data", (c: Buffer) => chunks.push(c));
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}

function forwardHeaders(req: IncomingMessage, route: UpstreamRoute): Headers {
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (HOP_BY_HOP.has(key) || value === undefined) continue;
    headers.set(key, Array.isArray(value) ? value.join(", ") : value);
  }
  // Optional coding-provider API credential override; never used on OAuth routes.
  const key = process.env.UPSTREAM_API_KEY;
  if (key && !route.preserveAuth) {
    for (const name of ["authorization", "x-api-key", "api-key", "cookie", "chatgpt-account-id", "openai-organization", "openai-project"]) {
      headers.delete(name);
    }
    headers.set("authorization", `Bearer ${key}`);
    headers.set("x-api-key", key);
  }
  return headers;
}

function sessionOf(req: IncomingMessage, explicit: string | undefined, userRequest: string): string {
  if (explicit) return explicit;
  const header = req.headers["x-session-id"];
  if (typeof header === "string" && header) return header;
  return createHash("sha1").update(userRequest.slice(0, 2000)).digest("hex").slice(0, 12);
}

function capture(adapter: Adapter, req: IncomingMessage, body: Buffer): void {
  const headers: Record<string, string> = {};
  for (const [key, value] of Object.entries(req.headers)) {
    if (!CAPTURE_HEADERS.has(key)) continue;
    headers[key] = Array.isArray(value) ? value.join(", ") : String(value ?? "");
  }
  const dir = join(".jev-classifier", "captures");
  mkdirSync(dir, { recursive: true });
  let parsed: unknown;
  try {
    parsed = JSON.parse(body.toString("utf8"));
  } catch {
    parsed = body.toString("utf8");
  }
  writeFileSync(join(dir, `${Date.now()}-${adapter.agent}.json`), JSON.stringify({ path: req.url?.split("?")[0], headers, body: parsed }, null, 2));
}

async function handle(req: IncomingMessage, res: ServerResponse, options: ServeOptions, status: ProxyStatus): Promise<void> {
  status.requests++;
  let route: UpstreamRoute;
  try {
    route = routeUpstream(req.url ?? "/");
  } catch {
    res.writeHead(400, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: { type: "jev_route_error", message: "Invalid proxy route" } }));
    return;
  }
  const adapter = route.adapter;
  const agentName = route.client || (adapter ? ({ anthropic: "claude", "openai-responses": "codex", "openai-chat": "grok" }[adapter.agent] || adapter.agent) : "gateway");
  const report = (message: string, error = false) => gatewayEvent(agentName, message, error, options.quiet);
  const agent = adapter ? (status.agents[agentName] ??= { requests: 0, classified: 0, failures: 0, lastRequest: "" }) : undefined;
  if (agent) { agent.requests++; agent.lastRequest = new Date().toISOString(); }
  const raw = await readBody(req);

  if (!adapter || req.method !== "POST") {
    status.passthrough++;
    await pipeUpstream(req, res, raw, route, undefined);
    return;
  }

  let body: Body;
  try {
    body = JSON.parse(raw.toString("utf8"));
  } catch {
    status.invalidJson++;
    report(`Skipped: invalid JSON (${req.headers["content-encoding"] ?? "identity"}). Request preserved.`, true);
    await pipeUpstream(req, res, raw, route, undefined);
    return;
  }

  if (options.capture) capture(adapter, req, raw);

  const parsed = adapter.parse(body);

  // No tools in the request: nothing to route.
  if (parsed.options.length === 0) {
    status.noTools++;
    report("Skipped: no supported tools. Request preserved.");
    await pipeUpstream(req, res, raw, route, undefined);
    return;
  }

  let mode: "enforce" | "shadow" = process.env.JEV_MODE === "shadow" ? "shadow" : "enforce";
  if (parsed.shadowReason && mode === "enforce") {
    if (agent?.shadowReason !== parsed.shadowReason) report(`Observe mode: ${parsed.shadowReason}`);
    mode = "shadow";
  }
  if (agent) agent.shadowReason = parsed.shadowReason;

  let outBody = raw;
  let record: DecisionRecord | undefined;

  try {
    report(`Classifying | tools=${parsed.options.length} | mode=${mode === "shadow" ? "observe" : "enforce"}`);
    const decision = await chooseNextTool(parsed.state, parsed.options);
    status.classified++;
    let applied = false;
    if (mode === "enforce") {
      if (decision.confidence >= minConfidence()) {
        adapter.apply(body, decision.tool === RESPOND ? null : decision.tool);
        applied = true;
      } else {
        adapter.apply(body, null);
        const top3 = decision.top.slice(0, 3).map((t) => `${t.name} (${t.p})`).join(", ");
        adapter.hint(body, `Routing hint: the most likely next tools are ${top3}.`);
      }
      outBody = Buffer.from(JSON.stringify(body), "utf8");
    }
    record = {
      ts: new Date().toISOString(),
      agent: route.client || adapter.agent,
      model: parsed.model,
      session: sessionOf(req, parsed.session, parsed.state.user_request),
      mode,
      chosen: decision.tool,
      confidence: decision.confidence,
      done: decision.done,
      gated: decision.gated,
      truncated: decision.truncated,
      top3: decision.top.slice(0, 3).map((t) => ({ ...t })),
      jevMs: decision.latencyMs,
      upstreamMs: 0,
      toolsCount: parsed.options.length,
      applied,
      ...(parsed.shadowReason ? { shadowReason: parsed.shadowReason } : {}),
    };
    if (agent) {
      agent.classified++;
      delete agent.lastError;
      agent.lastDecision = { tool: decision.tool, mode, applied, at: record.ts };
    }
    report(`Decision | chosen=${decision.tool} | confidence=${Math.round(decision.confidence * 100)}% | jev=${decision.latencyMs}ms | result=${applied ? "applied" : mode === "shadow" ? "observed" : "hint"}`);
  } catch (err) {
    status.classificationFailures++;
    if (agent) { agent.failures++; agent.lastError = (err as Error).message; }
    report(`Classification failed: ${(err as Error).message} Request preserved.`, true);
  }

  await pipeUpstream(req, res, outBody, route, record ? { adapter, record, quiet: options.quiet } : undefined);
}

async function pipeUpstream(
  req: IncomingMessage,
  res: ServerResponse,
  body: Buffer,
  route: UpstreamRoute,
  tap: { adapter: Adapter; record: DecisionRecord; quiet?: boolean } | undefined,
): Promise<void> {
  if (res.destroyed) return;
  const abort = new AbortController();
  res.once("close", () => { if (!res.writableFinished) abort.abort(); });
  const headers = forwardHeaders(req, route);
  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  if (hasBody) headers.set("content-length", String(body.byteLength));

  const started = performance.now();
  let upstream: Response;
  try {
    upstream = await fetch(route.target, { method: req.method, headers, body: hasBody ? new Uint8Array(body) : undefined, redirect: "manual", signal: abort.signal });
  } catch (err) {
    res.writeHead(502, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: { type: "jev_upstream_error", message: (err as Error).message } }));
    if (tap) finish(tap, undefined, performance.now() - started);
    return;
  }

  const outHeaders: Record<string, string> = {};
  if (!upstream.ok) gatewayEvent("upstream", `Provider returned HTTP ${upstream.status}. ${upstream.status === 401 ? "Check the agent's login; classifier credentials are separate." : "The response is being passed back to the agent."}`, true, tap?.quiet);
  upstream.headers.forEach((value, key) => {
    // fetch already decoded the body, so the upstream length/encoding no longer apply.
    if (key === "content-encoding" || key === "content-length" || HOP_BY_HOP.has(key)) return;
    outHeaders[key] = value;
  });
  res.writeHead(upstream.status, outHeaders);

  if (!upstream.body) {
    res.end();
    if (tap) finish(tap, undefined, performance.now() - started);
    return;
  }

  const isSse = (upstream.headers.get("content-type") ?? "").includes("text/event-stream");
  let actual: string | undefined;
  const jsonChunks: Buffer[] = [];
  const feed =
    tap && isSse
      ? sseTap((data) => {
          if (actual === undefined) actual = tap.adapter.actualFromEvent(data);
        })
      : undefined;

  const stream = Readable.fromWeb(upstream.body as never);
  stream.on("data", (chunk: Buffer) => {
    if (feed) feed(chunk);
    else if (tap) jsonChunks.push(chunk);
  });
  stream.on("end", () => {
    if (!tap) return;
    if (!isSse && jsonChunks.length) {
      try {
        actual = tap.adapter.actualFrom(JSON.parse(Buffer.concat(jsonChunks).toString("utf8")));
      } catch {
        // non-JSON body (error page, etc.)
      }
    }
    finish(tap, actual, performance.now() - started);
  });
  stream.on("error", () => {
    if (tap) finish(tap, actual, performance.now() - started);
    res.destroy();
  });
  stream.pipe(res);
}

function finish(tap: { record: DecisionRecord; quiet?: boolean }, actual: string | undefined, ms: number): void {
  const record: DecisionRecord = {
    ...tap.record,
    upstreamMs: Math.round(ms),
    actual,
    match: actual ? actual === tap.record.chosen : undefined,
  };
  appendDecision(record);
  gatewayEvent(record.agent, `Completed | actual=${actual ?? "none"} | match=${record.match === undefined ? "n/a" : record.match ? "yes" : "no"} | upstream=${record.upstreamMs}ms`, false, tap.quiet);
}

export function createServer(options: ServeOptions = {}): Server {
  const status: ProxyStatus = { requests: 0, classified: 0, classificationFailures: 0, noTools: 0, invalidJson: 0, passthrough: 0, agents: {} };
  return createHttpServer((req, res) => {
    if (req.url === "/__jev/stop") {
      if (req.method !== "POST" || !options.controlToken || req.headers.authorization !== `Bearer ${options.controlToken}` || !options.onStop) {
        res.writeHead(403); res.end("Forbidden"); return;
      }
      res.writeHead(200, { "content-type": "application/json" });
      res.end('{"stopping":true}', () => options.onStop?.());
      return;
    }
    if (req.method === "GET" && req.url === "/__jev/health") {
      res.writeHead(200, { "content-type": "application/json", "cache-control": "no-store" });
      res.end(JSON.stringify({ service: "jev-classifier", pid: process.pid, instanceId: options.instanceId, stub: process.env.JEV_STUB === "1", ...jevStatus(), ...status }));
      return;
    }
    handle(req, res, options, status).catch((err) => {
      gatewayEvent("gateway", `Request failed: ${(err as Error).message}`, true, options.quiet);
      if (!res.headersSent) res.writeHead(500, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: { type: "jev_error", message: String(err) } }));
    });
  });
}
