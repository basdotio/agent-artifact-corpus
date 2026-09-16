---
name: sdk-typescript-patterns
description: Use this skill when developing TypeScript applications with the Claude Agent SDK (@anthropic-ai/claude-agent-sdk), implementing query() calls, configuring SDK options, handling streaming message iteration, working with SDKMessage and SDKResultMessage types, managing AbortSignal, passing custom env variables, or setting up the single-point-of-contact types file for SDK imports.
version: 1.0.0
---

# TypeScript Agent SDK Patterns

## Core Pattern: Single Point of Contact

Always centralize all SDK imports in one `types.ts` file. This prevents scattered `@anthropic-ai/claude-agent-sdk` imports and provides a single place to add type guards and helpers.

```typescript
// types.ts — single point of contact with the SDK package
export type {
  HookCallback,
  HookInput,
  HookJSONOutput,
  Options,
  PostToolUseHookInput,
  PreToolUseHookInput,
  SDKMessage,
  SDKResultMessage,
} from "@anthropic-ai/claude-agent-sdk";

export { query } from "@anthropic-ai/claude-agent-sdk";

// Type guards
export function isResultMessage(message: SDKMessage): message is SDKResultMessage {
  return message.type === "result";
}
```

## Core Pattern: The query() Call

Use `query()` directly — no wrappers. The SDK returns an `AsyncIterable<SDKMessage>`.

```typescript
import { query, type SDKMessage } from "./types";

const messageStream: AsyncIterable<SDKMessage> = query({
  prompt: userPrompt,
  options: {
    model: "claude-sonnet-4-6",
    systemPrompt: params.systemPrompt,
    allowedTools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    permissionMode: "bypassPermissions",
    maxTurns: 50,
    maxBudgetUsd: 2,
    cwd: params.workingDirectory,
    abortController,
    sessionId: requestId,
    env: { ...process.env, ANTHROPIC_BASE_URL: proxyUrl, ANTHROPIC_AUTH_TOKEN: jwtToken },
    hooks: {
      PreToolUse: [{ matcher: "Write|Edit", hooks: [fileRestrictionHook] }],
      PostToolUse: [{ matcher: "Bash", hooks: [testPruneHook] }],
    },
  },
});
```

## Core Pattern: Message Iteration

Iterate the stream and act only on the result message:

```typescript
for await (const message of messageStream) {
  // log every message for visibility
  messageLogger.logMessage(message);

  if (isResultMessage(message)) {
    // message.duration_ms, message.total_cost_usd, message.modelUsage
    const code = readFileSync(params.testFilePath, "utf8");
    return { code, costUsd: message.total_cost_usd };
  }
}

// Fallback: stream ended without result message
return { code: "" };
```

## Core Pattern: AbortSignal

Always create an `AbortController` internally. Forward external `AbortSignal` to it:

```typescript
const abortController = new AbortController();

if (params.abortSignal) {
  params.abortSignal.addEventListener("abort", () => abortController.abort());
}

// Pass to query() options
{ abortController }
```

Check `signal.aborted` at the start of every hook callback.

## Result Error Handling

Always check `is_error` and handle all subtypes:

```typescript
if (isResultMessage(message)) {
  if (message.is_error) {
    switch (message.subtype) {
      case "error_max_turns":    throw new Error("Agent hit turn limit");
      case "error_max_budget_usd": throw new Error("Agent exceeded budget");
      case "error_during_execution": throw new Error("Agent execution failed");
      case "error_max_structured_output_retries": throw new Error("Output validation failed");
    }
  }
  // Check what was blocked
  if (message.permission_denials?.length) {
    console.warn("Blocked calls:", message.permission_denials.map(d => d.tool_name));
  }
}
```

## Options Reference

See `references/query-options.md` for the full options object documentation including `canUseTool`, `disallowedTools`, `permissionMode` values, and `settingSources`.
See `references/message-types.md` for SDKMessage variant details including `permission_denials` and all error subtypes.

## Key Constants Pattern

Define all SDK tuning constants in a dedicated `*.const.ts` file:

```typescript
export const SDK_MODEL = "claude-sonnet-4-6" as const;
export const SDK_MAX_BUDGET_USD = 2;
export const SDK_MAX_TURNS = 50;
export const SDK_PERMISSION_MODE = "bypassPermissions" as const;
export const SDK_ALLOWED_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"] as const;
```

## Metadata Pattern

Prepend run metadata to output files after SDK completes:

```typescript
function buildMetadataComment(result: SDKResultMessage): string {
  return [
    "/**",
    " * @generated Agent SDK",
    ` * @duration ${(result.duration_ms / 1000).toFixed(1)}s`,
    ` * @cost $${result.total_cost_usd.toFixed(4)}`,
    " */",
  ].join("\n") + "\n";
}
```

## Custom Environment

Pass custom env to the SDK for proxy URLs and auth tokens:

```typescript
env: {
  ...process.env,
  ANTHROPIC_BASE_URL: this.globalConfigService.getAnthropicProxyUrl(),
  ANTHROPIC_AUTH_TOKEN: await this.authStorage.getJWTToken(),
  ANTHROPIC_CUSTOM_HEADERS: `x-request-id: ${requestId}`,
}
```
