# SDK Message Types Reference

The `query()` stream emits `SDKMessage` variants. Use `isResultMessage()` to detect completion.

## Message Variants

### `system` (first message)
```typescript
{
  type: "system";
  subtype: "init";
  model: string;
  tools: string[];
  session_id: string;
}
```
Use for logging: confirm model, tools, session ID at start of run.

### `assistant` (agent outputs)
```typescript
{
  type: "assistant";
  message: {
    content: Array<ContentBlock>;  // text blocks, tool_use blocks
  };
}
```
Content blocks:
- `{ type: "text", text: string }` — agent's reasoning/output
- `{ type: "tool_use", id: string, name: string, input: Record<string, unknown> }` — tool calls

### `user` (tool results fed back)
```typescript
{
  type: "user";
  message: {
    content: Array<{
      type: "tool_result";
      tool_use_id: string;
      content: string | unknown[];
      is_error?: boolean;
    }>;
  };
}
```

### `result` (terminal — stream ends after this)
```typescript
{
  type: "result";
  subtype:
    | "success"
    | "error_max_turns"
    | "error_during_execution"
    | "error_max_budget_usd"               // maxBudgetUsd exceeded
    | "error_max_structured_output_retries"; // model failed to produce valid output
  duration_ms: number;
  total_cost_usd: number;
  is_error: boolean;
  num_turns: number;
  result?: string;                          // final text output from agent (success only)
  permission_denials?: SDKPermissionDenial[]; // tool calls blocked by hooks or canUseTool
  modelUsage: {
    input_tokens: number;
    output_tokens: number;
    cache_read_input_tokens?: number;
    cache_creation_input_tokens?: number;
  };
}
```

### Result subtype meanings

| Subtype | `is_error` | Cause |
|---------|-----------|-------|
| `"success"` | `false` | Agent finished normally |
| `"error_max_turns"` | `true` | Hit `maxTurns` limit |
| `"error_during_execution"` | `true` | Unhandled error during run |
| `"error_max_budget_usd"` | `true` | Hit `maxBudgetUsd` limit |
| `"error_max_structured_output_retries"` | `true` | Structured output failed repeatedly |

### SDKPermissionDenial

Appears in `result.permission_denials[]` — records every tool call that was blocked:

```typescript
{
  tool_name: string;          // which tool was denied
  tool_use_id: string;        // correlates with PreToolUse hook toolUseID
  reason?: string;            // permissionDecisionReason from the denying hook
}
```

Use `permission_denials` for:
- Audit logging of what the agent tried to do
- Debugging hooks that are too aggressive
- Showing users which operations were blocked and why

## Utility Functions

Extract content blocks safely (the message shape uses `unknown` internally):

```typescript
export function getMessageContentBlocks(message: SDKMessage): ContentBlock[] | undefined {
  const typed = message as { message?: { content?: unknown[] } };
  return Array.isArray(typed.message?.content)
    ? (typed.message.content as ContentBlock[])
    : undefined;
}

export function getSystemInitData(message: SDKMessage): {
  subtype?: string;
  model?: string;
  tools?: string[];
  session_id?: string;
} {
  return message as { subtype?: string; model?: string; tools?: string[]; session_id?: string };
}

export function getPermissionDenials(message: SDKMessage): SDKPermissionDenial[] {
  const typed = message as { permission_denials?: SDKPermissionDenial[] };
  return typed.permission_denials ?? [];
}
```

## Logging Pattern

```typescript
for await (const message of messageStream) {
  switch (message.type) {
    case "system": {
      const { model, tools, session_id } = getSystemInitData(message);
      console.log(`Session ${session_id}: model=${model}, tools=${tools?.join(", ")}`);
      break;
    }
    case "assistant": {
      const blocks = getMessageContentBlocks(message);
      for (const block of blocks ?? []) {
        if (block.type === "tool_use") {
          console.log(`→ ${block.name}`, block.input);
        }
      }
      break;
    }
    case "result": {
      const denials = getPermissionDenials(message);
      console.log(`Done in ${message.duration_ms}ms, cost $${message.total_cost_usd.toFixed(4)}`);
      if (message.is_error) {
        console.error(`Error: ${message.subtype}`);
      }
      if (denials.length > 0) {
        console.warn(`Blocked ${denials.length} tool call(s):`, denials.map(d => d.tool_name).join(", "));
      }
      break;
    }
  }
}
```

## Handling All Error Subtypes

```typescript
const result = await run(); // your wrapper that extracts the result message

switch (result.subtype) {
  case "success":
    return { output: result.result, cost: result.total_cost_usd };

  case "error_max_turns":
    throw new Error(`Agent exceeded maxTurns (${result.num_turns} turns used)`);

  case "error_max_budget_usd":
    throw new Error(`Agent exceeded budget: $${result.total_cost_usd.toFixed(4)} spent`);

  case "error_max_structured_output_retries":
    throw new Error("Agent failed to produce valid structured output after retries");

  case "error_during_execution":
    throw new Error("Agent encountered an unhandled error during execution");
}
```
