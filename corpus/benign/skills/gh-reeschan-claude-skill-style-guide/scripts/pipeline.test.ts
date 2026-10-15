import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";
import type { IncomingMessage, ServerResponse } from "node:http";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const SKILL = dirname(dirname(fileURLToPath(import.meta.url)));
const CLI = "scripts/pipeline.ts";
const NO_CREDS = join(tmpdir(), "sg-pipeline-nonexistent", "credentials.json");

const c = (choice: string, confidence = 0.9) => ({ type: "choice", choice, confidence, probabilities: { [choice]: confidence } });
const sc = (score: number, confidence = 0.9) => ({ type: "score", score, confidence });
const mkEst = (withPair = true): Record<string, unknown> => {
  const e: Record<string, unknown> = {
    brand_hue: c("indigo"),
    neutral_tint: c("warm"),
    accent_scheme: c("complementary"),
    base_mode: c("light"),
    font_mood: c("humanist"),
    shadow: c("soft"),
    use_accent: { type: "noul", noul: 0.8 },
    chroma: sc(2),
    contrast: sc(2),
    radius: sc(1),
    density: sc(2),
    formality: sc(3),
  };
  if (withPair) e.font_pair = c("zen-kaku-gothic-new+noto-sans-jp");
  return e;
};
const brief = {
  id: "aizome",
  name: "藍染",
  tone: "落ち着いた和の藍色。",
  needsJapanese: true,
  state: { product: "p", audience: "a", mood: ["calm"], references: "", avoid: "" },
  explicit: { brandColor: null, baseMode: null },
};

let tmp = "";
let files: { req: string; reqColor: string; brief: string; est: string; estNoPair: string };

// テストごとに別のストアを使う
const newHome = (name: string) => join(tmp, `home-${name}`);

function baseEnv(home: string, extra: Record<string, string> = {}): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, STYLE_GUIDE_HOME: home, TYPESAFE_CREDENTIALS_FILE: NO_CREDS, ...extra };
  delete env.JEV_ENDPOINT;
  if (!("TYPESAFE_API_KEY" in extra)) delete env.TYPESAFE_API_KEY;
  if (extra.JEV_ENDPOINT) env.JEV_ENDPOINT = extra.JEV_ENDPOINT;
  return env;
}

type Out = { status: number | null; stdout: string; stderr: string };

// JSON の外部入力を検査して絞る
const isRecord = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);

function asRecord(x: unknown): Record<string, unknown> {
  assert.ok(isRecord(x), `オブジェクトではありません: ${JSON.stringify(x)}`);
  return x;
}

function asArray(x: unknown): unknown[] {
  assert.ok(Array.isArray(x), `配列ではありません: ${JSON.stringify(x)}`);
  return x;
}

function asString(x: unknown): string {
  assert.ok(typeof x === "string", `文字列ではありません: ${JSON.stringify(x)}`);
  return x;
}

const parseRecord = (text: string): Record<string, unknown> => asRecord(JSON.parse(text));

function runSync(args: string[], env: NodeJS.ProcessEnv): Out {
  const r = spawnSync(process.execPath, [CLI, ...args], { cwd: SKILL, env, encoding: "utf8" });
  return { status: r.status, stdout: r.stdout, stderr: r.stderr };
}

function runAsync(args: string[], env: NodeJS.ProcessEnv): Promise<Out> {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [CLI, ...args], { cwd: SKILL, env });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8").on("data", (d) => (stdout += d));
    child.stderr.setEncoding("utf8").on("data", (d) => (stderr += d));
    child.on("error", reject);
    child.on("close", (status) => resolve({ status, stdout, stderr }));
  });
}

type Mock = { url: string; bodies: Record<string, unknown>[]; close: () => Promise<void> };

function startMock(handler: (n: number, body: Record<string, unknown>, res: ServerResponse) => void): Promise<Mock> {
  const bodies: Record<string, unknown>[] = [];
  const server = createServer((req: IncomingMessage, res: ServerResponse) => {
    let text = "";
    req.setEncoding("utf8");
    req.on("data", (d) => (text += d));
    req.on("end", () => {
      const body = asRecord(JSON.parse(text));
      bodies.push(body);
      handler(bodies.length, body, res);
    });
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const addr = server.address();
      const port = typeof addr === "object" && addr ? addr.port : 0;
      resolve({
        url: `http://127.0.0.1:${port}/v1/systemone`,
        bodies,
        close: () => new Promise<void>((r) => server.close(() => r())),
      });
    });
  });
}

const sendJson = (res: ServerResponse, status: number, x: unknown) => {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(x));
};

before(() => {
  tmp = mkdtempSync(join(tmpdir(), "sg-pipeline-test-"));
  const w = (name: string, x: unknown) => {
    const p = join(tmp, name);
    writeFileSync(p, JSON.stringify(x), "utf8");
    return p;
  };
  files = {
    req: w("req.json", { prompt: "和風のSaaS" }),
    reqColor: w("req-color.json", { prompt: "和風のSaaS", brandColor: "#1e3a8a" }),
    brief: w("brief.json", brief),
    est: w("est.json", mkEst(true)),
    estNoPair: w("est-nopair.json", mkEst(false)),
  };
});
after(() => {
  rmSync(tmp, { recursive: true, force: true });
});

void test("1. questions: brandColor 指定で skip と 10 問", () => {
  const r = runSync(["questions", "--request", files.reqColor, "--brief", files.brief], baseEnv(newHome("q")));
  assert.equal(r.status, 0, r.stderr);
  const out = parseRecord(r.stdout);
  assert.deepStrictEqual(out.skip, ["brand_hue", "chroma"]);
  assert.equal(Object.keys(asRecord(out.questions)).length, 10);
});

void test("2. run + --estimate (font_pair 入り)", () => {
  const home = newHome("est");
  const r = runSync(["run", "--request", files.req, "--brief", files.brief, "--estimate", files.est], baseEnv(home));
  assert.equal(r.status, 0, r.stderr);
  const out = parseRecord(r.stdout);
  assert.equal(out.dir, join(home, "themes", "aizome"));
  assert.equal(readdirSync(asString(out.dir)).length, 8);
  assert.equal(asRecord(out.sources)["shape.radiusPx"], "llm-fallback");
  const checks = asRecord(out.checks);
  assert.equal(typeof asRecord(checks.light).pass, "number");
  assert.equal(typeof asRecord(checks.dark).total, "number");
  assert.ok(asString(out.fontsUrl).startsWith("https://fonts.googleapis.com/"));
});

void test("3. run キーなし・推定なしで estimate-required", () => {
  const r = runSync(["run", "--request", files.req, "--brief", files.brief], baseEnv(newHome("noest")));
  assert.equal(r.status, 2);
  const err = parseRecord(r.stderr);
  assert.equal(err.error, "estimate-required");
  assert.ok("font_mood" in asRecord(err.questions));
  assert.equal(r.stdout, "");
});

void test("4. run + モック Jev (推定とフォントの 2 回)", async () => {
  const answers = mkEst(false);
  const mock = await startMock((n, _body, res) => {
    if (n === 1) sendJson(res, 200, { model: "jev-1.13.0", answers });
    else sendJson(res, 200, { model: "jev-1.13.0", answers: { font_pair: c("zen-kaku-gothic-new+noto-sans-jp") } });
  });
  try {
    const home = newHome("jev");
    const r = await runAsync(
      ["run", "--request", files.req, "--brief", files.brief],
      baseEnv(home, { TYPESAFE_API_KEY: "dummy", JEV_ENDPOINT: mock.url }),
    );
    assert.equal(r.status, 0, r.stderr);
    assert.equal(mock.bodies.length, 2);
    const [first, second] = mock.bodies;
    assert.ok(first && second);
    assert.equal(first.model, "jev-1.13.0");
    assert.ok("font_mood" in asRecord(first.questions));
    assert.deepStrictEqual(first.state, brief.state);
    assert.deepStrictEqual(Object.keys(asRecord(second.questions)), ["font_pair"]);
    assert.deepStrictEqual(second.state, brief.state);
    const out = parseRecord(r.stdout);
    assert.equal(asRecord(out.sources)["color.brandHue"], "jev");
    assert.equal(asRecord(asRecord(out.seed).font).pairId, "zen-kaku-gothic-new+noto-sans-jp");
  } finally {
    await mock.close();
  }
});

void test("5. run + モック Jev が 401 で jev-failed", async () => {
  const mock = await startMock((_n, _body, res) => sendJson(res, 401, { error: "unauthorized" }));
  try {
    const r = await runAsync(
      ["run", "--request", files.req, "--brief", files.brief],
      baseEnv(newHome("401"), { TYPESAFE_API_KEY: "dummy", JEV_ENDPOINT: mock.url }),
    );
    assert.equal(r.status, 3);
    const err = parseRecord(r.stderr);
    assert.equal(err.error, "jev-failed");
    assert.equal(err.stage, "estimate");
    assert.equal(err.status, 401);
    assert.ok("font_mood" in asRecord(err.questions));
    assert.ok(!r.stderr.includes("dummy"));
  } finally {
    await mock.close();
  }
});

void test("6. run キーなし・font_pair 無しで font-pair-required", () => {
  const r = runSync(["run", "--request", files.req, "--brief", files.brief, "--estimate", files.estNoPair], baseEnv(newHome("nopair")));
  assert.equal(r.status, 2);
  const err = parseRecord(r.stderr);
  assert.equal(err.error, "font-pair-required");
  assert.ok(asArray(err.candidates).length >= 2);
  assert.deepStrictEqual(Object.keys(asRecord(err.question)), ["font_pair"]);
});

void test("7. --dry-run で dir が null、ストアに書かない", () => {
  const home = newHome("dry");
  const r = runSync(["run", "--request", files.req, "--brief", files.brief, "--estimate", files.est, "--dry-run"], baseEnv(home));
  assert.equal(r.status, 0, r.stderr);
  assert.equal(parseRecord(r.stdout).dir, null);
  assert.ok(!existsSync(home));
});

void test("8. list が保存済みの id を返す", () => {
  const home = newHome("list");
  const env = baseEnv(home);
  assert.equal(runSync(["run", "--request", files.req, "--brief", files.brief, "--estimate", files.est], env).status, 0);
  const r = runSync(["list"], env);
  assert.equal(r.status, 0, r.stderr);
  const out = asArray(JSON.parse(r.stdout));
  assert.ok(out.some((t) => isRecord(t) && t.id === "aizome"));
});

void test("fonts: 候補と質問を返す / 入力エラーは終了コード 1", () => {
  const env = baseEnv(newHome("fonts"));
  const r = runSync(["fonts", "--request", files.req, "--brief", files.brief, "--estimate", files.estNoPair], env);
  assert.equal(r.status, 0, r.stderr);
  const out = parseRecord(r.stdout);
  const candidates = asArray(out.candidates);
  assert.ok(candidates.length >= 2);
  assert.deepStrictEqual(Object.keys(asRecord(candidates[0])).sort(), ["body", "description", "heading", "id", "mono", "mood"]);
  assert.deepStrictEqual(Object.keys(asRecord(out.question)), ["font_pair"]);
  const bad = runSync(["run", "--request", join(tmp, "missing.json"), "--brief", files.brief], env);
  assert.equal(bad.status, 1);
  assert.equal(parseRecord(bad.stderr).error, "file");
});
