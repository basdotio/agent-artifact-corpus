// テーマ生成ツールの Web アプリ用ローカルサーバー。127.0.0.1 だけで待ち受け、Jev のキーと LLM はサーバー側だけで使う
import http from "node:http";
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { Brief, Estimate, FontPair, Question, ThemeRequest } from "../core/types.ts";
import { ESTIMATE_QUESTIONS, HUES, JEV_MODEL, estimateQuestions } from "../core/questions.ts";
import { InputError, resolveExplicit, validateBrief, validateRequest } from "../core/explicit.ts";
import { familyNames, fontQuestion, loadCatalog, selectCandidates } from "../core/fonts.ts";
import { buildBundle, listThemes, readTheme, storeHome, writeBundle } from "../core/bundle.ts";
import type { Bundle } from "../core/bundle.ts";
import { loadJev as loadJevShared } from "../lib/load-jev.ts";
import { LlmError, estimateWithLlm, generateBrief, llmAvailable } from "./llm.ts";

const MAX_BODY = 1024 * 1024;
const INDEX_PATH = fileURLToPath(new URL("./index.html", import.meta.url));

// 共通 Jev クライアント (SHARED/jev.mjs) を動的 import する
type JevModule = {
  DEFAULT_ENDPOINT: string;
  JevError: new (...args: never[]) => Error & { code: string; status: number };
  getApiKey: (env?: NodeJS.ProcessEnv) => string | null;
  callJev: (args: {
    state: unknown;
    questions: Record<string, Question>;
    model: string;
    endpoint?: string;
  }) => Promise<{ answers: Estimate }>;
};
// JSON.parse の結果などがプレーンなオブジェクトか
function isRecord(x: unknown): x is Record<string, unknown> {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

// 読み込んだモジュールが必要な export を持つか。関数の引数と戻り値の形までは実行時に確かめられないので、共通クライアントの約束を信じる
function isJevModule(x: unknown): x is JevModule {
  return (
    typeof x === "object" &&
    x !== null &&
    "DEFAULT_ENDPOINT" in x &&
    typeof x.DEFAULT_ENDPOINT === "string" &&
    "JevError" in x &&
    typeof x.JevError === "function" &&
    "getApiKey" in x &&
    typeof x.getApiKey === "function" &&
    "callJev" in x &&
    typeof x.callJev === "function"
  );
}

async function loadJev(): Promise<JevModule> {
  const mod: unknown = await loadJevShared();
  if (!isJevModule(mod)) throw new Error("Jev クライアントに必要な export がありません");
  return mod;
}

let catalogCache: FontPair[] | null = null;
function catalog(): FontPair[] {
  if (!catalogCache) catalogCache = loadCatalog();
  return catalogCache;
}

class HttpError extends Error {
  status: number;
  body: Record<string, unknown>;
  constructor(status: number, body: Record<string, unknown>) {
    super(String(body.error));
    this.status = status;
    this.body = body;
  }
}

function sendJson(res: http.ServerResponse, status: number, body: unknown): void {
  const text = JSON.stringify(body);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(text),
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  res.end(text);
}

function readBody(req: http.IncomingMessage): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let total = 0;
    let done = false;
    const onData = (chunk: Buffer) => {
      if (done) return;
      total += chunk.length;
      if (total > MAX_BODY) {
        done = true;
        req.removeListener("data", onData);
        req.pause();
        reject(new HttpError(413, { error: "too-large" }));
        return;
      }
      chunks.push(chunk);
    };
    req.on("data", onData);
    req.on("end", () => {
      if (done) return;
      done = true;
      resolve(Buffer.concat(chunks));
    });
    req.on("error", (e) => {
      if (done) return;
      done = true;
      reject(e);
    });
  });
}

function checkPost(req: http.IncomingMessage): void {
  const port = req.socket.localPort;
  const hosts = [`127.0.0.1:${port}`, `localhost:${port}`];
  if (!hosts.includes(String(req.headers.host ?? ""))) throw new HttpError(403, { error: "forbidden" });
  const origin = req.headers.origin;
  if (origin !== undefined && !hosts.map((h) => `http://${h}`).includes(String(origin))) {
    throw new HttpError(403, { error: "forbidden" });
  }
  const ct = String(req.headers["content-type"] ?? "").toLowerCase();
  if (!ct.startsWith("application/json")) throw new HttpError(415, { error: "unsupported-media-type" });
  const len = Number(req.headers["content-length"]);
  if (Number.isFinite(len) && len > MAX_BODY) throw new HttpError(413, { error: "too-large" });
}

async function readJson(req: http.IncomingMessage): Promise<Record<string, unknown>> {
  const buf = await readBody(req);
  let x: unknown;
  try {
    x = JSON.parse(buf.toString("utf8"));
  } catch {
    throw new HttpError(400, { error: "bad-json" });
  }
  if (!isRecord(x)) throw new HttpError(400, { error: "bad-json" });
  return x;
}

function jevEndpoint(jev: JevModule): string {
  return process.env.JEV_ENDPOINT || jev.DEFAULT_ENDPOINT;
}

// 推定に font_pair を足すための候補。skip に font_pair があるか、必要な答えが無ければ空
function fontCandidates(
  brief: Brief,
  est: Estimate,
  skip: string[],
  fixed: { heading?: string; body?: string; mono?: string },
): FontPair[] {
  if (skip.includes("font_pair")) return [];
  const mood = est.font_mood;
  const formality = est.formality;
  if (!mood || mood.type !== "choice" || !formality || formality.type !== "score") return [];
  return selectCandidates({ catalog: catalog(), fontMood: mood, needsJapanese: brief.needsJapanese, fixed, formality: formality.score });
}

type EstimateContext = { brief: Brief; skip: string[]; fixedFonts: { heading?: string; body?: string; mono?: string } };

// Jev で推定する。Jev が失敗したとき (JevError) はフォールバックの理由を文字列で返す
async function estimateByJev(
  jev: JevModule,
  ctx: EstimateContext,
  questions: Record<string, Question>,
): Promise<Record<string, unknown> | string> {
  const { brief, skip } = ctx;
  const endpoint = jevEndpoint(jev);
  try {
    const r1 = await jev.callJev({ state: brief.state, questions, model: JEV_MODEL, endpoint });
    const estimate: Estimate = { ...r1.answers };
    const candidates = fontCandidates(brief, estimate, skip, ctx.fixedFonts);
    if (candidates.length >= 2) {
      const r2 = await jev.callJev({ state: brief.state, questions: fontQuestion(candidates), model: JEV_MODEL, endpoint });
      if (r2.answers.font_pair) estimate.font_pair = r2.answers.font_pair;
    }
    return { estimate, estimateSource: "jev", skip, fallbackReason: null };
  } catch (e) {
    if (!(e instanceof jev.JevError)) throw e;
    return `jev-failed: ${e.code} ${e.status}`;
  }
}

// ローカルの LLM で推定する (Jev が使えないときのフォールバック)
async function estimateByLlm(
  ctx: EstimateContext,
  questions: Record<string, Question>,
  fallbackReason: string,
): Promise<Record<string, unknown>> {
  const { brief, skip } = ctx;
  if (!llmAvailable()) throw new HttpError(503, { error: "estimator-unavailable", questions });
  try {
    const estimate = await estimateWithLlm(brief, questions);
    const candidates = fontCandidates(brief, estimate, skip, ctx.fixedFonts);
    if (candidates.length >= 2) {
      const fp = await estimateWithLlm(brief, fontQuestion(candidates));
      if (fp.font_pair) estimate.font_pair = fp.font_pair;
    }
    return { estimate, estimateSource: "llm-fallback", skip, fallbackReason };
  } catch (e) {
    if (e instanceof LlmError) throw new HttpError(502, { error: "llm-failed", message: e.message });
    throw e;
  }
}

async function handleEstimate(body: Record<string, unknown>): Promise<Record<string, unknown>> {
  const request: ThemeRequest = validateRequest(body.request);
  const brief = validateBrief(body.brief);
  const resolved = resolveExplicit(request, brief);
  const ctx: EstimateContext = { brief, skip: resolved.skip, fixedFonts: resolved.fixed.fonts };
  const questions = estimateQuestions(ctx.skip);

  const jev = await loadJev();
  let fallbackReason = "no-key";
  if (jev.getApiKey() !== null) {
    const r = await estimateByJev(jev, ctx, questions);
    if (typeof r !== "string") return r;
    fallbackReason = r;
  }
  return estimateByLlm(ctx, questions, fallbackReason);
}

// overrides はオブジェクトで、値は文字列か数値だけ受け付ける
function overridesFrom(ov: unknown): Record<string, string | number> | undefined {
  if (ov === undefined || ov === null) return undefined;
  if (!isRecord(ov)) throw new InputError("overrides はオブジェクトで指定してください");
  const out: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(ov)) {
    if (typeof v !== "string" && typeof v !== "number") throw new InputError(`overrides.${k} は文字列か数値で指定してください`);
    out[k] = v;
  }
  return out;
}

function bundleFrom(body: Record<string, unknown>): Bundle {
  const src = body.estimateSource;
  if (src !== "jev" && src !== "llm-fallback") throw new InputError("estimateSource は jev か llm-fallback で指定してください");
  const overrides = overridesFrom(body.overrides);
  return buildBundle({
    request: body.request,
    brief: body.brief,
    estimate: body.estimate,
    estimateSource: src,
    catalog: catalog(),
    overrides,
  });
}

function serveIndex(res: http.ServerResponse): void {
  let html: Buffer;
  try {
    html = readFileSync(INDEX_PATH);
  } catch {
    sendJson(res, 404, { error: "not-found" });
    return;
  }
  res.writeHead(200, { "Content-Type": "text/html; charset=utf-8", "Content-Length": html.length, "Cache-Control": "no-store" });
  res.end(html);
}

async function serveMeta(res: http.ServerResponse): Promise<void> {
  const jev = await loadJev();
  const cat = catalog();
  sendJson(res, 200, {
    llm: llmAvailable(),
    jev: jev.getApiKey() !== null,
    hues: HUES,
    questions: ESTIMATE_QUESTIONS,
    catalog: cat,
    families: familyNames(cat),
    storeHome: storeHome(),
  });
}

function serveTheme(res: http.ServerResponse, path: string): void {
  let id: string;
  try {
    id = decodeURIComponent(path.slice("/api/themes/".length));
  } catch {
    id = "";
  }
  const t = readTheme(id);
  if (!t) sendJson(res, 404, { error: "not-found" });
  else sendJson(res, 200, t);
}

async function routeGet(res: http.ServerResponse, path: string): Promise<void> {
  if (path === "/" || path === "/index.html") serveIndex(res);
  else if (path === "/api/meta") await serveMeta(res);
  else if (path === "/api/themes") sendJson(res, 200, listThemes());
  else if (path.startsWith("/api/themes/")) serveTheme(res, path);
  else sendJson(res, 404, { error: "not-found" });
}

async function handleBrief(res: http.ServerResponse, body: Record<string, unknown>): Promise<void> {
  const request = validateRequest(body.request);
  if (!llmAvailable()) throw new HttpError(503, { error: "llm-unavailable" });
  try {
    sendJson(res, 200, { brief: await generateBrief(request) });
  } catch (e) {
    if (e instanceof LlmError) throw new HttpError(502, { error: "llm-failed", message: e.message });
    throw e;
  }
}

// /api/render と /api/save。どちらも本文からバンドルを組み立てる
function handleBundle(res: http.ServerResponse, path: string, body: Record<string, unknown>): void {
  const bundle = bundleFrom(body);
  if (path === "/api/render") {
    sendJson(res, 200, {
      seedResult: bundle.seedResult,
      theme: bundle.theme,
      previewCss: bundle.previewCss,
      fontsUrl: bundle.fontsUrl,
      candidates: bundle.candidates,
      styleGuideMd: bundle.files["style-guide.md"],
    });
    return;
  }
  sendJson(res, 201, { dir: writeBundle(bundle) });
}

async function routePost(req: http.IncomingMessage, res: http.ServerResponse, path: string): Promise<void> {
  checkPost(req);
  const body = await readJson(req);
  if (path === "/api/brief") await handleBrief(res, body);
  else if (path === "/api/estimate") sendJson(res, 200, await handleEstimate(body));
  else handleBundle(res, path, body);
}

async function route(req: http.IncomingMessage, res: http.ServerResponse): Promise<void> {
  const method = req.method ?? "GET";
  const path = new URL(req.url ?? "/", "http://127.0.0.1").pathname;

  if (method === "GET") {
    await routeGet(res, path);
    return;
  }
  if (method === "POST" && ["/api/brief", "/api/estimate", "/api/render", "/api/save"].includes(path)) {
    await routePost(req, res, path);
    return;
  }
  sendJson(res, 404, { error: "not-found" });
}

export function createAppServer(): http.Server {
  return http.createServer((req, res) => {
    route(req, res).catch((e: unknown) => {
      if (res.headersSent) {
        res.destroy();
        return;
      }
      if (e instanceof HttpError) {
        if (e.status === 413) res.setHeader("Connection", "close");
        sendJson(res, e.status, e.body);
        return;
      }
      if (e instanceof InputError) {
        sendJson(res, 400, { error: "input", message: e.message });
        return;
      }
      console.error(e instanceof Error ? (e.stack ?? e.message) : e);
      sendJson(res, 500, { error: "internal" });
    });
  });
}

function openBrowser(url: string): void {
  try {
    const child =
      process.platform === "win32"
        ? spawn("cmd", ["/c", "start", "", url], { stdio: "ignore", detached: true, windowsHide: true })
        : spawn(process.platform === "darwin" ? "open" : "xdg-open", [url], { stdio: "ignore", detached: true });
    child.on("error", () => {});
    child.unref();
  } catch {
    // ブラウザが開けなくてもサーバーは動かし続ける
  }
}

function main(argv: string[]): void {
  let port = 0;
  let browser = true;
  let openId: string | null = null;
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--port") {
      const n = Number(argv[++i]);
      if (!Number.isInteger(n) || n < 0 || n > 65535) {
        console.error("--port は 0〜65535 の整数で指定してください");
        process.exit(1);
      }
      port = n;
    } else if (a === "--no-browser") {
      browser = false;
    } else if (a === "--open") {
      openId = argv[++i] ?? null;
    } else {
      console.error(`未知の引数です: ${a}`);
      process.exit(1);
    }
  }
  const server = createAppServer();
  server.listen(port, "127.0.0.1", () => {
    const addr = server.address();
    const actual = typeof addr === "object" && addr ? addr.port : port;
    const url = `http://127.0.0.1:${actual}/`;
    console.log(`style-guide app: ${url}`);
    if (browser) openBrowser(openId ? `${url}#theme=${encodeURIComponent(openId)}` : url);
  });
}

if (process.argv[1] && process.argv[1].endsWith("server.ts")) main(process.argv.slice(2));
