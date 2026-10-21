import test from "node:test";
import assert from "node:assert/strict";
import { stripVTControlCharacters } from "node:util";
import { formatLog } from "../log-format.js";

const event = { ts: "2026-09-18T12:00:00Z", agent: "openai-responses", message: "Decision | chosen=read_file | confidence=98% | jev=124ms | result=observed" };

test("live and historical logs fit common terminal sizes without losing fields", () => {
  for (const columns of [40, 60, 80, 120]) {
    for (const date of [false, true]) {
      const output = formatLog(event, { columns, date });
      assert.ok(output.split("\n").every(line => line.length < columns), output);
      assert.match(output, /codex/);
      assert.match(output.replace(/\s+/g, " "), /confidence=98%/);
      assert.doesNotMatch(output, /openai-responses|undefined/);
    }
  }
});

test("colors do not affect wrapping and errors have an explicit level", () => {
  const error = { ...event, level: "error", message: "Provider failed " + "x".repeat(160) };
  const plain = formatLog(error, { columns: 80 });
  assert.equal(stripVTControlCharacters(formatLog(error, { columns: 80, color: true })), plain);
  assert.match(plain, /ERROR/);
  assert.ok(plain.split("\n").every(line => line.length < 80));
});

test("untrusted fields cannot inject terminal controls or new rows", () => {
  const output = formatLog({ ...event, agent: "codex\n\x1b[31m", message: "hello\r\n\x1b[2Jworld" }, { columns: 120 });
  assert.doesNotMatch(output, /[\x1b\r\n]/);
  assert.match(output, /hello\s+world/);
});

test("decision history displays confidence, comparison and durations", () => {
  const output = formatLog({ ts: event.ts, agent: "anthropic", chosen: "Read", actual: "Read", mode: "shadow", confidence: 0.98, match: true, jevMs: 124, upstreamMs: 950 }, { columns: 200 });
  for (const field of ["claude", "chosen=Read", "actual=Read", "confidence=98%", "mode=observe", "match=yes", "jev=124ms", "upstream=950ms"]) assert.ok(output.includes(field));
});
