import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { LlmError, estimateWithLlm, generateBrief, llmAvailable, resetLlmCache, runStructured } from "./llm.ts";
import { estimateQuestions } from "../core/questions.ts";

const MOCK = join(dirname(fileURLToPath(import.meta.url)), "mock-llm.mjs");

// echo-args モードの出力 ({ args, stdin }) を検査して取り出す
function echoed(x: unknown): { args: string[]; stdin: unknown } {
  if (typeof x !== "object" || x === null || !("args" in x)) throw new Error("echo-args の出力ではありません");
  const args = x.args;
  if (!Array.isArray(args) || !args.every((a) => typeof a === "string")) throw new Error("args が文字列の配列ではありません");
  return { args, stdin: "stdin" in x ? x.stdin : undefined };
}

beforeEach(() => {
  process.env.STYLE_GUIDE_LLM_CMD = JSON.stringify([process.execPath, MOCK]);
  delete process.env.STYLE_GUIDE_LLM_MODEL;
  delete process.env.MOCK_LLM_MODE;
  delete process.env.MOCK_LLM_COUNTER;
  resetLlmCache();
});

void test("llmAvailable は true", () => {
  assert.equal(llmAvailable(), true);
});

void test("echo-args: 引数と標準入力", async () => {
  process.env.MOCK_LLM_MODE = "echo-args";
  const r = echoed(await runStructured("SECRET PROMPT", { type: "object" }));
  for (const a of [
    "-p",
    "--setting-sources",
    "project",
    "--no-session-persistence",
    "--output-format",
    "json",
    "--model",
    "sonnet",
    "--json-schema",
  ]) {
    assert.ok(r.args.includes(a), a);
  }
  assert.equal(r.args[r.args.indexOf("--tools") + 1], "");
  assert.ok(!r.args.some((a) => a.includes("SECRET PROMPT")));
  assert.equal(r.stdin, "SECRET PROMPT");
  process.env.STYLE_GUIDE_LLM_MODEL = "haiku";
  const r2 = echoed(await runStructured("x", {}));
  assert.equal(r2.args[r2.args.indexOf("--model") + 1], "haiku");
});

void test("generateBrief が Brief を返す", async () => {
  process.env.MOCK_LLM_MODE = "brief";
  const b = await generateBrief({ prompt: "落ち着いた請求書アプリ" });
  assert.equal(b.id, "calm-blue");
});

void test("bad-then-good は再試行で成功、always-bad は LlmError", async () => {
  process.env.MOCK_LLM_MODE = "bad-then-good";
  const counter = join(fs.mkdtempSync(join(os.tmpdir(), "sg-cnt-")), "n");
  process.env.MOCK_LLM_COUNTER = counter;
  const b = await generateBrief({ prompt: "x" });
  assert.equal(b.id, "calm-blue");
  assert.equal(fs.readFileSync(counter, "utf8"), "2");
  process.env.MOCK_LLM_MODE = "always-bad";
  await assert.rejects(generateBrief({ prompt: "x" }), LlmError);
});

void test("error モードは LlmError (boom)", async () => {
  process.env.MOCK_LLM_MODE = "error";
  await assert.rejects(runStructured("x", {}), (e: Error) => e instanceof LlmError && e.name === "LlmError" && e.message.includes("boom"));
});

void test("estimateWithLlm は 12 キーで type 付き", async () => {
  process.env.MOCK_LLM_MODE = "brief";
  const brief = await generateBrief({ prompt: "x" });
  process.env.MOCK_LLM_MODE = "estimate";
  const qs = estimateQuestions([]);
  const est = await estimateWithLlm(brief, qs);
  assert.equal(Object.keys(est).length, 12);
  for (const [k, a] of Object.entries(est)) assert.equal(a.type, qs[k]?.type);
});

void test("存在しないコマンドなら llmAvailable は false", () => {
  process.env.STYLE_GUIDE_LLM_CMD = JSON.stringify(["definitely-not-a-command-xyz"]);
  resetLlmCache();
  assert.equal(llmAvailable(), false);
});
