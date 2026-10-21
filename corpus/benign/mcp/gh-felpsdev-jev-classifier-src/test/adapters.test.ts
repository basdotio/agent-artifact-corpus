import assert from "node:assert/strict";
import { test } from "node:test";
import { adapterFor, type Body } from "../adapters/index.js";
import { anthropic } from "../adapters/anthropic.js";
import { openaiChat } from "../adapters/openai-chat.js";
import { openaiResponses } from "../adapters/openai-responses.js";
import anthropicRequest from "./fixtures/anthropic.request.json" with { type: "json" };
import chatRequest from "./fixtures/openai-chat.request.json" with { type: "json" };
import responsesRequest from "./fixtures/openai-responses.request.json" with { type: "json" };
import codexLiteRequest from "./fixtures/codex-lite.request.json" with { type: "json" };

const USER = "Fix the failing test in src/util.ts and run the suite.";
const SAID = "I'll read the file first.";
const RESULT = "export function add(a: number, b: number) { return a - b; }";

const clone = (o: unknown): Body => JSON.parse(JSON.stringify(o)) as Body;

test("adapterFor routes by path", () => {
  assert.equal(adapterFor("/v1/messages")?.agent, "anthropic");
  assert.equal(adapterFor("/v1/chat/completions?beta=1")?.agent, "openai-chat");
  assert.equal(adapterFor("/v1/responses")?.agent, "openai-responses");
  assert.equal(adapterFor("/v1/models"), undefined);
});

test("anthropic: request -> RouterState", () => {
  const parsed = anthropic.parse(clone(anthropicRequest));
  assert.equal(parsed.model, "claude-sonnet-4-5-20250929");
  assert.equal(parsed.session, "session_abc123");
  assert.deepEqual(
    parsed.options.map((o) => o.name),
    ["Read", "Edit", "Bash"],
  );
  assert.equal(parsed.options[0]?.description, "Reads a file from the local filesystem.");
  assert.deepEqual(parsed.state, {
    user_request: USER,
    assistant_said: [SAID],
    actions_taken: [{ step: 1, tool: "Read", input: { file_path: "src/util.ts" }, result: RESULT }],
  });
});

test("anthropic: tool_choice rewrite", () => {
  const body = clone(anthropicRequest);
  anthropic.apply(body, "Edit");
  assert.deepEqual(body.tool_choice, { type: "tool", name: "Edit" });
  assert.equal(body.tools.length, 3, "tools are never removed");
  anthropic.apply(body, null);
  assert.deepEqual(body.tool_choice, { type: "auto" });
});

test("anthropic: hint appends to a block-array system prompt", () => {
  const body = clone(anthropicRequest);
  anthropic.hint(body, "Routing hint: Edit.");
  assert.equal(body.system.length, 2);
  assert.deepEqual(body.system[1], { type: "text", text: "Routing hint: Edit." });

  const stringSystem: Body = { system: "base" };
  anthropic.hint(stringSystem, "hint");
  assert.equal(stringSystem.system, "base\n\nhint");

  const noSystem: Body = {};
  anthropic.hint(noSystem, "hint");
  assert.equal(noSystem.system, "hint");
});

test("anthropic: actual tool from a non-streaming response", () => {
  const actual = anthropic.actualFrom({
    content: [
      { type: "text", text: "sure" },
      { type: "tool_use", id: "toolu_2", name: "Edit", input: {} },
    ],
  });
  assert.equal(actual, "Edit");
  assert.equal(anthropic.actualFrom({ content: [{ type: "text", text: "no tools" }] }), undefined);
});

test("openai-chat: request -> RouterState", () => {
  const parsed = openaiChat.parse(clone(chatRequest));
  assert.equal(parsed.model, "grok-4");
  assert.deepEqual(
    parsed.options.map((o) => o.name),
    ["read_file", "edit_file", "bash"],
  );
  assert.deepEqual(parsed.state, {
    user_request: USER,
    assistant_said: [SAID],
    actions_taken: [{ step: 1, tool: "read_file", input: '{"path":"src/util.ts"}', result: RESULT }],
  });
});

test("openai-chat: tool_choice rewrite", () => {
  const body = clone(chatRequest);
  openaiChat.apply(body, "edit_file");
  assert.deepEqual(body.tool_choice, { type: "function", function: { name: "edit_file" } });
  assert.equal(body.tools.length, 3, "tools are never removed");
  openaiChat.apply(body, null);
  assert.equal(body.tool_choice, "auto");
});

test("openai-chat: hint goes into the system message", () => {
  const body = clone(chatRequest);
  openaiChat.hint(body, "hint");
  assert.equal(body.messages[0].content, "You are Grok CLI, a coding assistant.\n\nhint");

  const noSystem: Body = { messages: [{ role: "user", content: "hi" }] };
  openaiChat.hint(noSystem, "hint");
  assert.deepEqual(noSystem.messages[0], { role: "system", content: "hint" });
});

test("openai-chat: actual tool from a non-streaming response", () => {
  const actual = openaiChat.actualFrom({
    choices: [{ message: { tool_calls: [{ function: { name: "edit_file" } }] } }],
  });
  assert.equal(actual, "edit_file");
  assert.equal(openaiChat.actualFrom({ choices: [{ message: { content: "hi" } }] }), undefined);
});

test("openai-responses: request -> RouterState", () => {
  const parsed = openaiResponses.parse(clone(responsesRequest));
  assert.equal(parsed.model, "gpt-5-codex");
  assert.equal(parsed.shadowReason, undefined);
  assert.deepEqual(
    parsed.options.map((o) => o.name),
    ["shell", "apply_patch", "update_plan"],
  );
  assert.deepEqual(parsed.state, {
    user_request: USER,
    assistant_said: [SAID],
    actions_taken: [{ step: 1, tool: "shell", input: '{"command":["cat","src/util.ts"]}', result: RESULT }],
  });
});

test("openai-responses: previous_response_id forces shadow", () => {
  const body = clone(responsesRequest);
  body.previous_response_id = "resp_123";
  const parsed = openaiResponses.parse(body);
  assert.match(parsed.shadowReason ?? "", /previous_response_id/);
  assert.equal(parsed.session, "resp_123");
});

test("openai-responses: tool_choice rewrite", () => {
  const body = clone(responsesRequest);
  openaiResponses.apply(body, "apply_patch");
  assert.deepEqual(body.tool_choice, { type: "function", name: "apply_patch" });
  assert.equal(body.tools.length, 3, "tools are never removed");
  openaiResponses.apply(body, null);
  assert.equal(body.tool_choice, "auto");
});

test("openai-responses: hint appends to instructions", () => {
  const body = clone(responsesRequest);
  openaiResponses.hint(body, "hint");
  assert.equal(body.instructions, "You are Codex, a coding agent running in a terminal.\n\nhint");
});

test("openai-responses: actual tool from a non-streaming response", () => {
  const actual = openaiResponses.actualFrom({
    output: [
      { type: "reasoning", summary: [] },
      { type: "function_call", name: "apply_patch", arguments: "{}" },
    ],
  });
  assert.equal(actual, "apply_patch");
  assert.equal(openaiResponses.actualFrom({ output: [{ type: "message" }] }), undefined);
});

test("a request with no tools yields no options", () => {
  assert.equal(anthropic.parse({ messages: [] }).options.length, 0);
  assert.equal(openaiChat.parse({ messages: [] }).options.length, 0);
  assert.equal(openaiResponses.parse({ input: "hello" }).options.length, 0);
});

test("openai-responses accepts a plain string input", () => {
  assert.equal(openaiResponses.parse({ input: "hello" }).state.user_request, "hello");
});

test("openai-responses preserves custom tools used by Codex", () => {
  const call = { type: "custom_tool_call", call_id: "patch1", name: "apply_patch", input: "*** Begin Patch" };
  const body: Body = {
    tools: [{ type: "custom", name: "apply_patch", format: { type: "text" } }],
    input: [call, { type: "custom_tool_call_output", call_id: "patch1", output: "patched" }],
  };
  const parsed = openaiResponses.parse(body);
  assert.equal(parsed.options[0]?.name, "apply_patch");
  assert.deepEqual(parsed.state.actions_taken, [{ step: 1, tool: "apply_patch", input: "*** Begin Patch", result: "patched" }]);
  openaiResponses.apply(body, "apply_patch");
  assert.deepEqual(body.tool_choice, { type: "custom", name: "apply_patch" });
  assert.equal(openaiResponses.actualFrom({ output: [call] }), "apply_patch");
  assert.equal(openaiResponses.actualFromEvent({ type: "response.output_item.added", item: call }), "apply_patch");
});

test("Codex 0.154 Responses Lite discovers additional_tools inside namespaces", () => {
  const body = clone(codexLiteRequest);
  const input = structuredClone(body.input);
  const parsed = openaiResponses.parse(body);
  assert.deepEqual(parsed.options.map((tool) => tool.name), ["exec", "wait"]);
  assert.equal(parsed.state.user_request, "List the files in the current directory.");
  assert.match(parsed.shadowReason ?? "", /Responses Lite/);
  openaiResponses.apply(body, "exec");
  assert.deepEqual(body.tool_choice, { type: "custom", name: "exec" });
  assert.deepEqual(body.input, input, "embedded tool declarations remain unchanged");
  assert.equal(body.tools, undefined, "do not relocate tools and invalidate the cache");
  openaiResponses.apply(body, "wait");
  assert.deepEqual(body.tool_choice, { type: "function", name: "wait" });
});

test("duplicate names in namespaces fall back to shadow instead of forcing the wrong tool", () => {
  const body = clone(codexLiteRequest);
  body.input[0].tools.push({ type: "namespace", name: "other", tools: [{ type: "function", name: "exec" }] });
  assert.match(openaiResponses.parse(body).shadowReason ?? "", /duplicate tool names/);
});
