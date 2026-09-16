---
name: sdk-hooks-development
description: Use this skill when implementing TypeScript hook callbacks for the Claude Agent SDK — creating PreToolUse hooks to allow/deny tool calls, PostToolUse hooks to inject additionalContext, building factory functions for parameterized hooks, using HookCallback and HookJSONOutput types, applying isPreToolUseInput and isPostToolUseInput type guards, or designing a hooks strategy for an Agent SDK platform. Hooks in the TypeScript SDK are async functions, NOT JSON config files.
version: 1.0.0
---

# TypeScript SDK Hook Development

**Critical distinction**: Agent SDK hooks (TypeScript `HookCallback` functions) are different from Claude Code plugin hooks (JSON config). This skill covers the TypeScript SDK programmatic API.

## Core Types

```typescript
// From @anthropic-ai/claude-agent-sdk (via your types.ts re-export)
type HookCallback = (
  input: HookInput,
  toolUseId: string,
  context: { signal: AbortSignal }
) => Promise<HookJSONOutput>;

type HookJSONOutput = {
  hookSpecificOutput?: {
    hookEventName: string;
    // PreToolUse:
    permissionDecision?: "allow" | "deny";
    permissionDecisionReason?: string;
    // PostToolUse:
    additionalContext?: string;
  };
};
```

## Pattern: Basic Hook Structure

Every hook follows this exact pattern:

```typescript
import type { HookCallback, HookJSONOutput } from "../types";
import { isPreToolUseInput, getToolInputFilePath } from "../types";

export const myHook: HookCallback = async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
  // 1. Always check abort first
  if (signal.aborted) return {};

  // 2. Guard: only handle the right event type
  if (!isPreToolUseInput(input)) return {};

  // 3. Extract data
  const filePath = getToolInputFilePath(input);
  if (!filePath) return {};

  // 4. Apply logic
  if (filePath.endsWith(".env")) {
    return {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: "Reading .env files is not allowed — they may contain secrets",
      },
    };
  }

  return {};  // empty = allow
};
```

## Pattern: Factory Function (Parameterized Hooks)

Use factory functions when a hook needs runtime parameters:

```typescript
import path from "node:path";
import type { HookCallback, HookJSONOutput } from "../types";
import { getToolInputFilePath, isPreToolUseInput } from "../types";

export function createFileRestrictionHook(allowedFilePath: string): HookCallback {
  const normalized = path.resolve(allowedFilePath);

  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};

    const filePath = getToolInputFilePath(input);
    if (!filePath) return {};

    if (path.resolve(filePath) === normalized) return {};

    return {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: `Only ${allowedFilePath} can be modified`,
      },
    };
  };
}
```

## Pattern: PostToolUse — additionalContext

Inject feedback into tool results to guide the agent:

```typescript
import type { HookCallback, HookJSONOutput } from "../types";
import { getToolInputCommand, isPostToolUseInput } from "../types";

export const testReminderHook: HookCallback = async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
  if (signal.aborted) return {};
  if (!isPostToolUseInput(input)) return {};

  const command = getToolInputCommand(input);

  if (!isTestCommand(command)) return {};

  return {
    hookSpecificOutput: {
      hookEventName: input.hook_event_name,
      additionalContext: "REMINDER: If tests pass, stop. If 10+ pass with failures, prune.",
    },
  };
};
```

## Pattern: PostToolUse — Auto-Fix with Feedback

Run linters/typecheck after edits and inject remaining errors:

```typescript
import { execSync } from "node:child_process";
import type { HookCallback, HookJSONOutput } from "../types";
import { getExecOutput, getToolInputFilePath, isPostToolUseInput } from "../types";

export function createLintFixHook(workingDirectory: string, targetFile: string): HookCallback | null {
  const eslintBin = path.join(workingDirectory, "node_modules", ".bin", "eslint");
  if (!existsSync(eslintBin)) return null;  // graceful disable

  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPostToolUseInput(input)) return {};

    const filePath = getToolInputFilePath(input);
    if (path.resolve(filePath) !== path.resolve(targetFile)) return {};

    try {
      execSync(`${eslintBin} --fix "${targetFile}" 2>&1`, {
        cwd: workingDirectory,
        encoding: "utf8",
        timeout: 30_000,
      });
      return {};
    } catch (error: unknown) {
      const output = getExecOutput(error);
      if (!output) return {};

      return {
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext: `LINT ERRORS after auto-fix:\n${output.slice(0, 2000)}`,
        },
      };
    }
  };
}
```

## Hook Registration

Register hooks in the `query()` call options:

```typescript
const fileRestrictionHook = createFileRestrictionHook(params.testFilePath);
const lintFixHook = createLintFixHook(params.workingDirectory, params.testFilePath);

await query({
  prompt,
  options: {
    // ...
    hooks: {
      PreToolUse: [
        { matcher: "Write|Edit", hooks: [fileRestrictionHook] },
        { matcher: "Read",       hooks: [envProtectionHook] },
      ],
      PostToolUse: [
        { matcher: "Bash",       hooks: [testPruneHook] },
        // Conditionally include lintFixHook if binary exists
        ...(lintFixHook ? [{ matcher: "Write|Edit", hooks: [lintFixHook] }] : []),
      ],
    },
  },
});
```

## Utility Functions

Keep these in your `types.ts` — they centralize unsafe casts:

```typescript
// Safe extraction of file_path from PreToolUse or PostToolUse input
export function getToolInputFilePath(input: PreToolUseHookInput | PostToolUseHookInput): string {
  const toolInput = input.tool_input as Record<string, unknown> | undefined;
  const filePath = toolInput?.file_path;
  return typeof filePath === "string" ? filePath : "";
}

// Safe extraction of command from PostToolUse Bash input
export function getToolInputCommand(input: PostToolUseHookInput): string {
  const toolInput = input.tool_input as Record<string, unknown> | undefined;
  const command = toolInput?.command;
  return typeof command === "string" ? command : "";
}

// Safe extraction of execSync error output
export function getExecOutput(error: unknown): string {
  const execError = error as { stdout?: string; stderr?: string };
  return ((execError.stdout ?? "") + (execError.stderr ?? "")).trim();
}
```

## Type Guards

```typescript
export function isPreToolUseInput(input: HookInput): input is PreToolUseHookInput {
  return input.hook_event_name === "PreToolUse";
}

export function isPostToolUseInput(input: HookInput): input is PostToolUseHookInput {
  return input.hook_event_name === "PostToolUse";
}
```

## Pattern: Modify Tool Input (updatedInput)

Redirect or sanitize tool inputs before execution. Requires `permissionDecision: "allow"`. Never mutate `tool_input` — always return a new object:

```typescript
return {
  hookSpecificOutput: {
    hookEventName: input.hook_event_name,   // always use input.hook_event_name, not hardcoded string
    permissionDecision: "allow",            // required when using updatedInput
    updatedInput: {
      ...(input.tool_input as Record<string, unknown>),
      file_path: `/sandbox${filePath}`,     // redirect writes to sandbox
    },
  },
};
```

## Pattern: Stop the Agent

Return `continue: false` to halt the agent entirely (different from denying a single tool):

```typescript
return {
  continue: false,
  stopReason: "Budget exhausted — stopping before incurring more cost.",
};
```

Top-level output fields (outside `hookSpecificOutput`):
- `continue: boolean` — whether the agent continues (default `true`)
- `stopReason: string` — message shown when `continue` is `false`
- `suppressOutput: boolean` — hide hook stdout from transcript
- `systemMessage: string` — inject a message directly into Claude's conversation

## Pattern: PostToolUseFailure

Handle tool execution failures. TypeScript-only event. Use top-level `systemMessage` — `hookSpecificOutput` is **not** supported for this event type:

```typescript
const failureLogger: HookCallback = async (input, toolUseID, { signal }) => {
  if (signal.aborted) return {};
  if (input.hook_event_name !== "PostToolUseFailure") return {};

  const failure = input as PostToolUseFailureHookInput;
  console.error("[TOOL FAILURE]", failure.tool_name, failure.error, { isInterrupt: failure.is_interrupt });

  // systemMessage (top-level) — NOT hookSpecificOutput, which isn't supported here
  return {
    systemMessage: `Tool "${failure.tool_name}" failed: ${failure.error}. Consider an alternative approach.`,
  };
};
```

## Design Rules

1. **Always check `signal.aborted` first** — prevents work on cancelled operations
2. **Always type-guard the input** — hooks receive `HookInput`, guard to the specific type
3. **Return `{}` for non-applicable cases** — empty output = allow/no-op
4. **Graceful disable** — factory hooks that depend on binaries (eslint, tsc) should return `null` when unavailable
5. **Never trust `tool_input` types** — always cast safely via helpers
6. **Keep hooks independent** — hooks for the same matcher run sequentially; all are evaluated even if an earlier one denies
7. **Never throw from a hook** — swallow errors; throwing can crash the agent
8. **Pass `signal` to `fetch()`** — so HTTP requests cancel properly on hook timeout
9. **Use `input.hook_event_name`** — not hardcoded strings in `hookEventName` field

## Advanced Patterns

For more patterns from these references:

- **`references/pretooluse-patterns.md`** — path guards, filename guards, command keyword guards, extension guards
- **`references/posttooluse-patterns.md`** — test reminders, TypeScript auto-fix, ESLint auto-fix, build verification
- **`references/hook-events-reference.md`** — PreToolUse and PostToolUse deep dive, execution model, tool name reference
- **`references/smart-dispatch-pattern.md`** — single dispatcher routing to sub-handlers by file type and tool; merge strategies; testing handlers in isolation
- **`references/testing-hooks.md`** — unit test patterns with vitest, mock helpers, integration testing, mocking `execSync`

Examples:

- **`examples/env-protection-hook.ts`** — `.env` file read blocker (PreToolUse)
- **`examples/file-restriction-hook.ts`** — single-file write restriction factory (PreToolUse)
- **`examples/security-blocker-hook.ts`** — comprehensive security: dangerous commands + protected files + out-of-project writes
- **`examples/smart-dispatch-hook.ts`** — single dispatcher routing to sub-handlers by file type and tool name
- **`examples/auto-format-hook.ts`** — silent Prettier formatting after edits (PostToolUse, no additionalContext)
- **`examples/input-redirect-hook.ts`** — `updatedInput` patterns: sandbox redirect, strip dangerous flags, inject env vars
