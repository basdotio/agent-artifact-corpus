import assert from "node:assert/strict";
import { after, test } from "node:test";
import {
  buildState,
  chooseNextTool,
  gate,
  limitOptions,
  MAX_OPTIONS,
  RESPOND,
  stubDecision,
  type RouterState,
  type ToolSpec,
} from "../router.js";

const state = (tools: string[]): RouterState => ({
  user_request: "do the thing",
  actions_taken: tools.map((t, i) => ({ step: i + 1, tool: t, input: {}, result: "ok" })),
  assistant_said: [],
});

const ranked: [string, number][] = [
  [RESPOND, 0.6],
  ["Edit", 0.3],
  ["Bash", 0.1],
];

after(() => {
  delete process.env.DONE_THRESHOLD;
  delete process.env.JEV_STUB;
});

test("buildState pairs tool calls with their results", () => {
  const built = buildState([
    { role: "user", text: "fix it" },
    { role: "assistant", text: "reading", calls: [{ id: "a", tool: "Read", input: { file: "x" } }] },
    { role: "tool", id: "a", output: "contents" },
    { role: "user", text: "and test it" },
  ]);
  assert.equal(built.user_request, "fix it\n---\nand test it");
  assert.deepEqual(built.assistant_said, ["reading"]);
  assert.deepEqual(built.actions_taken, [{ step: 1, tool: "Read", input: { file: "x" }, result: "contents" }]);
});

test("buildState clips long results", () => {
  const built = buildState([
    { role: "assistant", calls: [{ id: "a", tool: "Read", input: {} }] },
    { role: "tool", id: "a", output: "x".repeat(1000) },
  ]);
  assert.equal(built.actions_taken[0]?.result.length, 601);
  assert.ok(built.actions_taken[0]?.result.endsWith("…"));
});

test("buildState tolerates a tool result with no matching call", () => {
  const built = buildState([{ role: "tool", id: "orphan", tool: "Bash", output: "hi" }]);
  assert.deepEqual(built.actions_taken, [{ step: 1, tool: "Bash", input: undefined, result: "hi" }]);
});

test("gate overrides a premature respond_to_user", () => {
  process.env.DONE_THRESHOLD = "0.5";
  assert.deepEqual(gate(RESPOND, 0.2, ranked), { tool: "Edit", gated: true });
});

test("gate leaves respond_to_user alone when done agrees", () => {
  process.env.DONE_THRESHOLD = "0.5";
  assert.deepEqual(gate(RESPOND, 0.9, ranked), { tool: RESPOND, gated: false });
});

test("gate never touches a real tool choice", () => {
  process.env.DONE_THRESHOLD = "0.5";
  assert.deepEqual(gate("Edit", 0.0, ranked), { tool: "Edit", gated: false });
});

test("gate honours DONE_THRESHOLD", () => {
  process.env.DONE_THRESHOLD = "0.1";
  assert.deepEqual(gate(RESPOND, 0.2, ranked), { tool: RESPOND, gated: false });
  process.env.DONE_THRESHOLD = "0.5";
});

test("gate keeps respond_to_user when it is the only option", () => {
  process.env.DONE_THRESHOLD = "0.5";
  assert.deepEqual(gate(RESPOND, 0.0, [[RESPOND, 1]]), { tool: RESPOND, gated: false });
});

test("stub picks the first tool that has not run yet", () => {
  const options: ToolSpec[] = [{ name: "Read" }, { name: "Edit" }, { name: "Bash" }];
  assert.equal(stubDecision(state(["Read"]), options, false).tool, "Edit");
  assert.equal(stubDecision(state(["Read", "Edit", "Bash"]), options, false).tool, RESPOND);
  assert.equal(stubDecision(state(["Read", "Edit", "Bash"]), options, false).done, 1);
});

test("limitOptions truncates above 255 labels", () => {
  const many: ToolSpec[] = Array.from({ length: 300 }, (_, i) => ({ name: `t${i}` }));
  const cut = limitOptions(many);
  assert.equal(cut.truncated, true);
  assert.equal(cut.options.length, MAX_OPTIONS - 1);
  assert.equal(cut.options[0]?.name, "t0");
  assert.equal(cut.options.at(-1)?.name, "t253");

  const few = limitOptions(many.slice(0, MAX_OPTIONS - 1));
  assert.equal(few.truncated, false);
  assert.equal(few.options.length, MAX_OPTIONS - 1);
});

test("chooseNextTool in stub mode reports truncation and needs no API key", async () => {
  process.env.JEV_STUB = "1";
  delete process.env.TYPESAFE_API_KEY;
  const many: ToolSpec[] = Array.from({ length: 300 }, (_, i) => ({ name: `t${i}` }));
  const decision = await chooseNextTool(state([]), many);
  assert.equal(decision.truncated, true);
  assert.equal(decision.tool, "t0");
  assert.equal(decision.gated, false);
  assert.equal(decision.latencyMs, 0);
});
