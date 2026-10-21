import assert from "node:assert/strict";
import { test } from "node:test";
import { anthropic } from "../adapters/anthropic.js";
import { openaiChat } from "../adapters/openai-chat.js";
import { openaiResponses } from "../adapters/openai-responses.js";
import { actualFromStream, sseTap } from "../sse.js";

const ANTHROPIC_SSE = [
  'event: message_start',
  'data: {"type":"message_start","message":{"id":"msg_01","type":"message","role":"assistant","model":"claude-sonnet-4-5-20250929","content":[],"stop_reason":null,"usage":{"input_tokens":1200,"output_tokens":1}}}',
  '',
  'event: content_block_start',
  'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
  '',
  'event: content_block_delta',
  'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Let me fix the bug."}}',
  '',
  'event: content_block_stop',
  'data: {"type":"content_block_stop","index":0}',
  '',
  'event: content_block_start',
  'data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_02","name":"Edit","input":{}}}',
  '',
  'event: content_block_delta',
  'data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\\"file_path\\":\\"src/util.ts\\"}"}}',
  '',
  'event: message_delta',
  'data: {"type":"message_delta","delta":{"stop_reason":"tool_use"},"usage":{"output_tokens":42}}',
  '',
  'event: message_stop',
  'data: {"type":"message_stop"}',
  '',
].join("\n");

const CHAT_SSE = [
  'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","model":"grok-4","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
  '',
  'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","model":"grok-4","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_2","type":"function","function":{"name":"edit_file","arguments":""}}]},"finish_reason":null}]}',
  '',
  'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","model":"grok-4","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"path\\":\\"src/util.ts\\"}"}}]},"finish_reason":null}]}',
  '',
  'data: {"id":"chatcmpl-1","object":"chat.completion.chunk","model":"grok-4","choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}',
  '',
  'data: [DONE]',
  '',
].join("\n");

const RESPONSES_SSE = [
  'event: response.created',
  'data: {"type":"response.created","response":{"id":"resp_1","status":"in_progress"}}',
  '',
  'event: response.output_item.added',
  'data: {"type":"response.output_item.added","output_index":0,"item":{"type":"reasoning","id":"rs_1","summary":[]}}',
  '',
  'event: response.output_item.added',
  'data: {"type":"response.output_item.added","output_index":1,"item":{"type":"function_call","id":"fc_1","call_id":"call_2","name":"apply_patch","arguments":""}}',
  '',
  'event: response.function_call_arguments.delta',
  'data: {"type":"response.function_call_arguments.delta","item_id":"fc_1","delta":"{\\"input\\":"}',
  '',
  'event: response.completed',
  'data: {"type":"response.completed","response":{"id":"resp_1","status":"completed"}}',
  '',
].join("\n");

test("anthropic stream: tool name from content_block_start", () => {
  assert.equal(actualFromStream(ANTHROPIC_SSE, anthropic.actualFromEvent), "Edit");
});

test("openai chat stream: tool name from delta.tool_calls", () => {
  assert.equal(actualFromStream(CHAT_SSE, openaiChat.actualFromEvent), "edit_file");
});

test("responses stream: tool name from response.output_item.added", () => {
  assert.equal(actualFromStream(RESPONSES_SSE, openaiResponses.actualFromEvent), "apply_patch");
});

test("a text-only stream reports no tool", () => {
  const textOnly = ANTHROPIC_SSE.split("\n\nevent: content_block_start\ndata: {\"type\":\"content_block_start\",\"index\":1")[0] ?? "";
  assert.equal(actualFromStream(textOnly, anthropic.actualFromEvent), undefined);
});

test("the tap survives chunks split mid-line", () => {
  let found: string | undefined;
  const feed = sseTap((d) => {
    found ??= anthropic.actualFromEvent(d);
  });
  for (let i = 0; i < ANTHROPIC_SSE.length; i += 7) feed(ANTHROPIC_SSE.slice(i, i + 7));
  assert.equal(found, "Edit");
});

test("the tap handles CRLF line endings and ignores junk", () => {
  const seen: unknown[] = [];
  const feed = sseTap((d) => seen.push(d));
  feed('data: {"a":1}\r\n: comment\r\ndata: not json\r\ndata: [DONE]\r\n');
  assert.deepEqual(seen, [{ a: 1 }]);
});
