# Smart Hook Dispatching Pattern

Instead of registering many separate hooks, register **one dispatcher** that routes to specialized sub-handlers based on tool name and file type. This keeps your `query()` call clean and makes your hook system easy to extend.

## The Problem It Solves

Without dispatch, as you add hooks, your `query()` options grow cluttered:

```typescript
// Gets unwieldy fast
hooks: {
  PreToolUse: [
    { matcher: "Bash",       hooks: [securityHook] },
    { matcher: "Write|Edit", hooks: [fileRestrictionHook] },
    { matcher: "Write|Edit", hooks: [extensionGuardHook] },
    { matcher: "Read",       hooks: [envProtectionHook] },
    { matcher: "*",          hooks: [velocityGovernorHook] },
  ],
  PostToolUse: [
    { matcher: "Write|Edit", hooks: [typecheckHook] },
    { matcher: "Write|Edit", hooks: [lintFixHook] },
    { matcher: "Write|Edit", hooks: [autoFormatHook] },
    { matcher: "Bash",       hooks: [testPruneHook] },
  ],
}
```

With dispatch, it becomes:

```typescript
hooks: {
  PreToolUse:  [{ matcher: "*", hooks: [preDispatch] }],
  PostToolUse: [{ matcher: "*", hooks: [postDispatch] }],
}
```

Add a new handler by dropping it into the handler map — no touching `query()` options.

## Core Pattern

```typescript
import path from "node:path";
import type { HookCallback, HookJSONOutput, HookInput } from "../types";
import { isPreToolUseInput, isPostToolUseInput } from "../types";

type HookHandler = (input: HookInput, signal: AbortSignal) => Promise<HookJSONOutput>;

// ── Handler maps ───────────────────────────────────────────────────────────────

// Route by file extension (for Write/Edit tools)
const PRE_FILE_HANDLERS: Record<string, HookHandler> = {
  ".ts":  typescriptPreHandler,
  ".tsx": typescriptPreHandler,
};

const POST_FILE_HANDLERS: Record<string, HookHandler> = {
  ".ts":  typescriptPostHandler,
  ".tsx": typescriptPostHandler,
};

// Route by tool name
const PRE_TOOL_HANDLERS: Record<string, HookHandler> = {
  Bash:  bashSecurityHandler,
  Read:  readProtectionHandler,
};

const POST_TOOL_HANDLERS: Record<string, HookHandler> = {
  Bash:  bashPostHandler,
};

// ── Dispatcher factory ─────────────────────────────────────────────────────────

function createDispatcher(
  fileHandlers: Record<string, HookHandler>,
  toolHandlers: Record<string, HookHandler>,
): HookCallback {
  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};

    const toolName = (isPreToolUseInput(input) || isPostToolUseInput(input))
      ? input.tool_name
      : "";

    const toolInput = input.tool_input as Record<string, unknown>;
    const filePath = typeof toolInput.file_path === "string" ? toolInput.file_path : "";

    const handlers: HookHandler[] = [];

    // 1. Route by file extension
    if (filePath) {
      const handler = fileHandlers[path.extname(filePath).toLowerCase()];
      if (handler) handlers.push(handler);
    }

    // 2. Route by tool name
    const toolHandler = toolHandlers[toolName];
    if (toolHandler) handlers.push(toolHandler);

    // 3. Run all applicable handlers sequentially
    for (const handler of handlers) {
      const result = await handler(input, signal);
      if (signal.aborted) return {};

      // First deny wins — return immediately
      if (result.hookSpecificOutput?.permissionDecision === "deny") {
        return result;
      }
    }

    // Return first non-empty additionalContext
    for (const handler of handlers) {
      const result = await handler(input, signal);
      if (result.hookSpecificOutput?.additionalContext) return result;
    }

    return {};
  };
}
```

> **Note**: The loop above runs handlers twice to separate deny detection from context collection. For performance, collect results in the first pass instead — see the optimized version in `examples/smart-dispatch-hook.ts`.

## Merging Results

Two strategies depending on your needs:

### Deny-first (security-critical)
```typescript
// First deny wins — stop immediately
for (const result of results) {
  if (result.hookSpecificOutput?.permissionDecision === "deny") {
    return result;
  }
}
```

### Collect all (audit/feedback)
```typescript
// Accumulate all additionalContext from all handlers
const contexts = results
  .map(r => r.hookSpecificOutput?.additionalContext)
  .filter(Boolean);

if (contexts.length === 0) return {};

return {
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: contexts.join("\n\n"),
  },
};
```

Use deny-first for PreToolUse security gates. Use collect-all for PostToolUse feedback where you want Claude to see all issues at once.

## Registration

```typescript
const preDispatch  = createDispatcher(PRE_FILE_HANDLERS,  PRE_TOOL_HANDLERS);
const postDispatch = createDispatcher(POST_FILE_HANDLERS, POST_TOOL_HANDLERS);

await query({
  prompt,
  options: {
    hooks: {
      PreToolUse:  [{ matcher: "*", hooks: [preDispatch] }],
      PostToolUse: [{ matcher: "*", hooks: [postDispatch] }],
    },
  },
});
```

## Adding a New Handler

To add TypeScript file checking without touching the registration:

```typescript
// 1. Write the handler
const typescriptPreHandler: HookHandler = async (input, signal) => {
  if (signal.aborted) return {};
  // ... your logic
  return {};
};

// 2. Register it in the map — that's it
const PRE_FILE_HANDLERS: Record<string, HookHandler> = {
  ".ts":  typescriptPreHandler,   // ← add here
  ".tsx": typescriptPreHandler,
};
```

No changes to `query()` options. No changes to other handlers. Independently testable.

## Testing Dispatch Handlers

Because handlers are plain `async (input, signal) => HookJSONOutput` functions, test them directly without going through the dispatcher:

```typescript
import { describe, it, expect } from "vitest";

describe("typescriptPreHandler", () => {
  it("blocks writes to .env.ts", async () => {
    const input = makePreToolUse("Write", { file_path: "/project/.env.ts" });
    const result = await typescriptPreHandler(input, liveSignal);
    expect(result.hookSpecificOutput?.permissionDecision).toBe("deny");
  });
});
```

Test the dispatcher integration separately to verify routing:

```typescript
describe("preDispatch routing", () => {
  it("routes .ts files to typescript handler", async () => {
    const input = makePreToolUse("Write", { file_path: "/project/foo.ts" });
    // If typescript handler denies, dispatcher must deny
    const result = await preDispatch(input, "id", { signal: liveSignal });
    expect(result.hookSpecificOutput?.permissionDecision).toBe("deny");
  });
});
```

## When to Use Dispatch

| Use dispatch | Use individual hooks |
|-------------|---------------------|
| 4+ hooks across multiple tools | 1–3 simple hooks |
| Language-aware routing needed | Single file type or tool |
| Growing platform with many rules | Stable, small hook set |
| Want to test handlers in isolation | Hooks are tightly coupled |
