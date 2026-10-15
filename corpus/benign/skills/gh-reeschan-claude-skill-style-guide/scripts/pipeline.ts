// スキル style-guide から使う CLI。ブリーフ (と推定) からテーマ一式を作る
//   node scripts/pipeline.ts questions --request R.json --brief B.json
//   node scripts/pipeline.ts fonts --request R.json --brief B.json --estimate E.json
//   node scripts/pipeline.ts run --request R.json --brief B.json [--estimate E.json] [--estimate-source jev|llm-fallback] [--out DIR] [--dry-run]
//   node scripts/pipeline.ts list
// 標準出力には JSON を 1 つだけ出す。エラーは標準エラーに {"error": ...}
// 終了コード: 0 成功、1 入力エラー、2 推定が必要 (Jev キー無し)、3 Jev の失敗
import { readFileSync } from "node:fs";
import { loadJev as loadJevShared } from "../lib/load-jev.ts";
import { parseArgs } from "node:util";
import type { Brief, Estimate, FontPair, Question, Resolved, ThemeRequest } from "../core/types.ts";
import { InputError, resolveExplicit, validateBrief, validateRequest } from "../core/explicit.ts";
import { JEV_MODEL, estimateQuestions } from "../core/questions.ts";
import { requiredKeys, validateEstimate } from "../core/seed.ts";
import { fontQuestion, loadCatalog, selectCandidates, validateFixedFonts } from "../core/fonts.ts";
import { buildBundle, listThemes, writeBundle } from "../core/bundle.ts";
import type { Bundle } from "../core/bundle.ts";

const EXIT_OK = 0;
const EXIT_INPUT = 1;
const EXIT_NEED_ESTIMATE = 2;
const EXIT_JEV = 3;

// 終了コード付きで CLI を止めるための例外
class CliExit extends Error {
  code: number;
  payload: Record<string, unknown>;
  constructor(code: number, payload: Record<string, unknown>) {
    super(String(payload.error));
    this.code = code;
    this.payload = payload;
  }
}

const usage = (message: string): CliExit => new CliExit(EXIT_INPUT, { error: "usage", message });

// Jev クライアントのうち、ここで使う部分。読み込んだモジュールを実行時に確かめてから包む
type JevModule = {
  callJev: (args: {
    state: unknown;
    questions: Record<string, Question>;
    model: string;
    endpoint?: string;
  }) => Promise<{ answers: Record<string, unknown> }>;
  getApiKey: (env?: NodeJS.ProcessEnv) => string | null;
  isJevError: (e: unknown) => e is Error;
  DEFAULT_ENDPOINT: string;
};

const isRecord = (x: unknown): x is Record<string, unknown> => typeof x === "object" && x !== null && !Array.isArray(x);

// オブジェクトのプロパティを型を決めずに読む
const field = (o: object, key: string): unknown => Reflect.get(o, key);

// 読み込んだモジュールの形を確かめ、型の付いた呼び出し口にする
function toJevModule(mod: unknown): JevModule {
  if (!isRecord(mod)) throw new Error("Jev クライアントがオブジェクトではありません");
  const { callJev, getApiKey, JevError, DEFAULT_ENDPOINT } = mod;
  if (typeof callJev !== "function" || typeof getApiKey !== "function" || typeof JevError !== "function") {
    throw new Error("Jev クライアントに callJev / getApiKey / JevError がありません");
  }
  if (typeof DEFAULT_ENDPOINT !== "string") throw new Error("Jev クライアントに DEFAULT_ENDPOINT がありません");
  return {
    callJev: async (args) => {
      const res: unknown = await Reflect.apply(callJev, mod, [args]);
      const answers = isRecord(res) ? res.answers : undefined;
      if (!isRecord(answers)) throw new Error("Jev の応答に answers がありません");
      return { answers };
    },
    getApiKey: (env) => {
      const key: unknown = Reflect.apply(getApiKey, mod, [env]);
      return typeof key === "string" ? key : null;
    },
    isJevError: (e): e is Error => e instanceof JevError && e instanceof Error,
    DEFAULT_ENDPOINT,
  };
}

async function loadJev(): Promise<JevModule> {
  return toJevModule(await loadJevShared());
}

// 例外の message。Error 以外は文字列にする
const errorMessage = (e: unknown): string => (e instanceof Error ? e.message : String(e));

function readJson(path: string, label: string): unknown {
  let text: string;
  try {
    text = readFileSync(path, "utf8");
  } catch (e) {
    throw new CliExit(EXIT_INPUT, { error: "file", file: label, path, message: errorMessage(e) });
  }
  if (text.charCodeAt(0) === 0xfeff) text = text.slice(1);
  try {
    return JSON.parse(text);
  } catch (e) {
    throw new CliExit(EXIT_INPUT, { error: "file", file: label, path, message: `JSON として読めません: ${errorMessage(e)}` });
  }
}

function need(values: Record<string, unknown>, name: string): string {
  const v = values[name];
  if (typeof v !== "string" || v === "") throw usage(`--${name} が必要です`);
  return v;
}

function loadInputs(values: Record<string, unknown>): { request: ThemeRequest; brief: Brief; resolved: Resolved } {
  const request = validateRequest(readJson(need(values, "request"), "request"));
  const brief = validateBrief(readJson(need(values, "brief"), "brief"));
  return { request, brief, resolved: resolveExplicit(request, brief) };
}

function candidatesFor(catalog: FontPair[], brief: Brief, resolved: Resolved, estimate: Estimate): FontPair[] {
  const problems = validateFixedFonts(resolved.fixed.fonts, catalog);
  if (problems.length > 0) throw new InputError(problems.join(" / "));
  const mood = estimate.font_mood;
  const formality = estimate.formality;
  if (!mood || mood.type !== "choice") throw new InputError("font_mood が必要です");
  if (!formality || formality.type !== "score") throw new InputError("formality が必要です");
  return selectCandidates({
    catalog,
    fontMood: mood,
    needsJapanese: brief.needsJapanese,
    fixed: resolved.fixed.fonts,
    formality: formality.score,
  });
}

const candidateView = (p: FontPair) => ({
  id: p.id,
  heading: p.heading,
  body: p.body,
  mono: p.mono,
  mood: p.mood,
  description: p.description,
});

function endpointOf(jev: JevModule): string {
  return process.env.JEV_ENDPOINT || jev.DEFAULT_ENDPOINT;
}

function jevFailure(jev: JevModule, e: unknown, stage: string, extra: Record<string, unknown>): never {
  if (jev.isJevError(e)) {
    throw new CliExit(EXIT_JEV, {
      error: "jev-failed",
      stage,
      code: field(e, "code"),
      status: field(e, "status"),
      message: e.message,
      ...extra,
    });
  }
  throw e;
}

// ---------------------------------------------------------------------------
// サブコマンド
// ---------------------------------------------------------------------------
function cmdQuestions(values: Record<string, unknown>): unknown {
  const { resolved } = loadInputs(values);
  return { skip: resolved.skip, questions: estimateQuestions(resolved.skip) };
}

function cmdFonts(values: Record<string, unknown>): unknown {
  const { brief, resolved } = loadInputs(values);
  const raw = readJson(need(values, "estimate"), "estimate");
  if (resolved.skip.includes("font_pair")) return { candidates: [], question: null };
  const estimate = validateEstimate(raw, ["font_mood", "formality"]);
  const candidates = candidatesFor(loadCatalog(), brief, resolved, estimate);
  return {
    candidates: candidates.map(candidateView),
    question: candidates.length > 1 ? fontQuestion(candidates) : null,
  };
}

type EstimateSource = "jev" | "llm-fallback";

function estimateSourceArg(values: Record<string, unknown>): EstimateSource | undefined {
  const sourceArg = values["estimate-source"];
  if (sourceArg === undefined || sourceArg === "jev" || sourceArg === "llm-fallback") return sourceArg;
  throw usage("--estimate-source は jev か llm-fallback です");
}

// 推定の生データを得る。--estimate があれば読み、無ければ Jev に聞く
async function obtainEstimate(
  values: Record<string, unknown>,
  ctx: { jev: JevModule; hasKey: boolean; brief: Brief; skip: string[]; sourceArg: EstimateSource | undefined },
): Promise<{ raw: unknown; estimateSource: EstimateSource }> {
  if (typeof values.estimate === "string") {
    return { raw: readJson(values.estimate, "estimate"), estimateSource: ctx.sourceArg ?? "llm-fallback" };
  }
  const questions = estimateQuestions(ctx.skip);
  if (!ctx.hasKey) throw new CliExit(EXIT_NEED_ESTIMATE, { error: "estimate-required", questions });
  try {
    const res = await ctx.jev.callJev({ state: ctx.brief.state, questions, model: JEV_MODEL, endpoint: endpointOf(ctx.jev) });
    return { raw: res.answers, estimateSource: "jev" };
  } catch (e) {
    return jevFailure(ctx.jev, e, "estimate", { questions });
  }
}

// Jev にフォントの組を選ばせる
async function askFontPair(jev: JevModule, brief: Brief, question: Record<string, Question>): Promise<unknown> {
  let answer: unknown;
  try {
    const res = await jev.callJev({ state: brief.state, questions: question, model: JEV_MODEL, endpoint: endpointOf(jev) });
    answer = res.answers.font_pair;
  } catch (e) {
    jevFailure(jev, e, "fonts", { question });
  }
  if (answer === undefined) {
    throw new CliExit(EXIT_JEV, {
      error: "jev-failed",
      stage: "fonts",
      code: "bad-response",
      status: 0,
      message: "応答に font_pair がありません",
      question,
    });
  }
  return answer;
}

// 推定に font_pair が無く候補が 2 つ以上なら、Jev に選ばせて推定に足す
async function withFontPair(
  estimate: Estimate,
  ctx: { catalog: FontPair[]; brief: Brief; resolved: Resolved; jev: JevModule; hasKey: boolean },
): Promise<Estimate> {
  const skip = ctx.resolved.skip;
  if (skip.includes("font_pair") || estimate.font_pair !== undefined) return estimate;
  const candidates = candidatesFor(ctx.catalog, ctx.brief, ctx.resolved, estimate);
  if (candidates.length < 2) return estimate;
  const question = fontQuestion(candidates);
  if (!ctx.hasKey) {
    throw new CliExit(EXIT_NEED_ESTIMATE, { error: "font-pair-required", candidates: candidates.map(candidateView), question });
  }
  const answer = await askFontPair(ctx.jev, ctx.brief, question);
  return validateEstimate({ ...estimate, font_pair: answer }, requiredKeys(skip));
}

type CheckSummary = { pass: number; total: number; adjusted: number };

// コントラスト検査の件数をモードごとにまとめる
function summarizeChecks(bundle: Bundle): Record<string, CheckSummary> {
  const checks: Record<string, CheckSummary> = {};
  for (const mode of ["light", "dark"] as const) {
    const cs = bundle.theme.modes[mode].checks;
    checks[mode] = { pass: cs.filter((c) => c.pass).length, total: cs.length, adjusted: cs.filter((c) => c.adjusted).length };
  }
  return checks;
}

async function cmdRun(values: Record<string, unknown>): Promise<unknown> {
  const { request, brief, resolved } = loadInputs(values);
  const skip = resolved.skip;
  const sourceArg = estimateSourceArg(values);

  // 推定
  const jev = await loadJev();
  const hasKey = jev.getApiKey(process.env) !== null;
  const { raw, estimateSource } = await obtainEstimate(values, { jev, hasKey, brief, skip, sourceArg });
  let estimate = validateEstimate(raw, requiredKeys(skip));

  // フォントの組
  const catalog = loadCatalog();
  estimate = await withFontPair(estimate, { catalog, brief, resolved, jev, hasKey });

  // 組み立てと保存
  const bundle = buildBundle({ request, brief, estimate, estimateSource, catalog });
  const dir = values["dry-run"] ? null : writeBundle(bundle, typeof values.out === "string" ? values.out : undefined);
  const sr = bundle.seedResult;
  return {
    dir,
    seed: sr.seed,
    alternatives: sr.alternatives,
    sources: sr.sources,
    lowConfidence: sr.lowConfidence,
    checks: summarizeChecks(bundle),
    fontsUrl: bundle.fontsUrl,
  };
}

// ---------------------------------------------------------------------------
// 入口
// ---------------------------------------------------------------------------
function parseCli(argv: string[]): { command: string; values: Record<string, unknown> } {
  let parsed;
  try {
    parsed = parseArgs({
      args: argv,
      allowPositionals: true,
      strict: true,
      options: {
        request: { type: "string" },
        brief: { type: "string" },
        estimate: { type: "string" },
        "estimate-source": { type: "string" },
        out: { type: "string" },
        "dry-run": { type: "boolean" },
      },
    });
  } catch (e) {
    throw usage(errorMessage(e));
  }
  const { values, positionals } = parsed;
  const [command] = positionals;
  if (positionals.length !== 1 || command === undefined)
    throw usage("サブコマンドを 1 つ指定してください (questions / fonts / run / list)");
  return { command, values };
}

async function runCommand(command: string, values: Record<string, unknown>): Promise<unknown> {
  switch (command) {
    case "questions":
      return cmdQuestions(values);
    case "fonts":
      return cmdFonts(values);
    case "run":
      return await cmdRun(values);
    case "list":
      return listThemes();
    default:
      throw usage(`不明なサブコマンド: ${command}`);
  }
}

// 例外の message。無ければ文字列にする
function messageOf(e: unknown): unknown {
  const message = typeof e === "object" && e !== null && "message" in e ? e.message : undefined;
  return message ?? String(e);
}

// 例外を標準エラーに書き、終了コードを返す
function reportError(e: unknown): number {
  if (e instanceof CliExit) {
    process.stderr.write(JSON.stringify(e.payload) + "\n");
    return e.code;
  }
  if (e instanceof InputError) {
    process.stderr.write(JSON.stringify({ error: "input", message: e.message }) + "\n");
    return EXIT_INPUT;
  }
  process.stderr.write(JSON.stringify({ error: "internal", message: messageOf(e) }) + "\n");
  return EXIT_INPUT;
}

async function main(argv: string[]): Promise<number> {
  try {
    const { command, values } = parseCli(argv);
    const result = await runCommand(command, values);
    process.stdout.write(JSON.stringify(result, null, 2) + "\n");
    return EXIT_OK;
  } catch (e) {
    return reportError(e);
  }
}

process.exitCode = await main(process.argv.slice(2));
