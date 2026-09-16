# Testing TypeScript SDK Hooks

TypeScript SDK hooks (`HookCallback` functions) are just async functions — test them like any other async TypeScript function.

## Unit Testing Pattern

### Mock HookInput

```typescript
import { describe, it, expect } from "vitest";
import type { PreToolUseHookInput, PostToolUseHookInput } from "@anthropic-ai/claude-agent-sdk";

// Helper: build mock PreToolUse input
function mockPreToolUse(toolName: string, toolInput: Record<string, unknown>): PreToolUseHookInput {
  return {
    hook_event_name: "PreToolUse",
    tool_name: toolName,
    tool_input: toolInput,
    session_id: "test-session",
    cwd: "/test/project",
    permission_mode: "bypassPermissions",
    transcript_path: "/tmp/transcript.txt",
  } as PreToolUseHookInput;
}

// Helper: build mock PostToolUse input
function mockPostToolUse(toolName: string, toolInput: Record<string, unknown>): PostToolUseHookInput {
  return {
    hook_event_name: "PostToolUse",
    tool_name: toolName,
    tool_input: toolInput,
    tool_result: "",
    session_id: "test-session",
    cwd: "/test/project",
    permission_mode: "bypassPermissions",
    transcript_path: "/tmp/transcript.txt",
  } as PostToolUseHookInput;
}

// Mock AbortSignal
function mockSignal(aborted = false): AbortSignal {
  return { aborted, addEventListener: () => {}, removeEventListener: () => {} } as AbortSignal;
}
```

### Testing an envProtectionHook

```typescript
import { envProtectionHook } from "../hooks/env-protection-hook";

describe("envProtectionHook", () => {
  it("blocks .env reads", async () => {
    const input = mockPreToolUse("Read", { file_path: "/project/.env" });
    const result = await envProtectionHook(input, "tool-1", { signal: mockSignal() });

    expect(result.hookSpecificOutput?.permissionDecision).toBe("deny");
    expect(result.hookSpecificOutput?.permissionDecisionReason).toContain(".env");
  });

  it("blocks .env.local reads", async () => {
    const input = mockPreToolUse("Read", { file_path: "/project/.env.local" });
    const result = await envProtectionHook(input, "tool-1", { signal: mockSignal() });

    expect(result.hookSpecificOutput?.permissionDecision).toBe("deny");
  });

  it("allows non-env file reads", async () => {
    const input = mockPreToolUse("Read", { file_path: "/project/src/index.ts" });
    const result = await envProtectionHook(input, "tool-1", { signal: mockSignal() });

    expect(result).toEqual({});
  });

  it("returns {} when aborted", async () => {
    const input = mockPreToolUse("Read", { file_path: "/project/.env" });
    const result = await envProtectionHook(input, "tool-1", { signal: mockSignal(true) });

    expect(result).toEqual({});
  });

  it("ignores PostToolUse input", async () => {
    const input = mockPostToolUse("Read", { file_path: "/project/.env" });
    const result = await envProtectionHook(input, "tool-1", { signal: mockSignal() });

    expect(result).toEqual({});
  });
});
```

### Testing a factory hook

```typescript
import { createFileRestrictionHook } from "../hooks/file-restriction-hook";

describe("createFileRestrictionHook", () => {
  const hook = createFileRestrictionHook("/project/test/output.test.ts");

  it("allows writes to the target file", async () => {
    const input = mockPreToolUse("Write", { file_path: "/project/test/output.test.ts" });
    const result = await hook(input, "tool-1", { signal: mockSignal() });

    expect(result).toEqual({});
  });

  it("blocks writes to other files", async () => {
    const input = mockPreToolUse("Write", { file_path: "/project/src/main.ts" });
    const result = await hook(input, "tool-1", { signal: mockSignal() });

    expect(result.hookSpecificOutput?.permissionDecision).toBe("deny");
  });

  it("uses path normalization for relative paths", async () => {
    // Resolved to the same absolute path
    const input = mockPreToolUse("Edit", { file_path: "/project/./test/output.test.ts" });
    const result = await hook(input, "tool-1", { signal: mockSignal() });

    expect(result).toEqual({});
  });
});
```

### Testing a PostToolUse hook

```typescript
import { testPruneHook } from "../hooks/test-prune-hook";

describe("testPruneHook", () => {
  it("injects reminder after jest command", async () => {
    const input = mockPostToolUse("Bash", { command: "npx jest src/foo.test.ts" });
    const result = await testPruneHook(input, "tool-1", { signal: mockSignal() });

    expect(result.hookSpecificOutput?.additionalContext).toContain("STOP");
  });

  it("ignores non-test bash commands", async () => {
    const input = mockPostToolUse("Bash", { command: "ls -la" });
    const result = await testPruneHook(input, "tool-1", { signal: mockSignal() });

    expect(result).toEqual({});
  });

  it("ignores PreToolUse input", async () => {
    const input = mockPreToolUse("Bash", { command: "npx jest" });
    const result = await testPruneHook(input, "tool-1", { signal: mockSignal() });

    expect(result).toEqual({});
  });
});
```

## Integration Testing Pattern

Test the full hook registration in a query() call using a dry run:

```typescript
import { describe, it, expect, vi } from "vitest";
import { createFileRestrictionHook, envProtectionHook } from "./hooks";

describe("hook integration", () => {
  it("all hooks are callable without errors", async () => {
    const fileHook = createFileRestrictionHook("/project/output.ts");
    const hooks = [fileHook, envProtectionHook];

    const testInput = mockPreToolUse("Write", { file_path: "/project/other.ts" });
    const signal = mockSignal();

    for (const hook of hooks) {
      // Should not throw
      const result = await hook(testInput, "test-id", { signal });
      expect(result).toBeDefined();
    }
  });
});
```

## Testing Command Hooks (with execSync)

For hooks that run processes (eslint, tsc), mock the child_process module:

```typescript
import { vi } from "vitest";
import { existsSync } from "node:fs";
import { createTypecheckHook } from "../hooks/typecheck-hook";

vi.mock("node:child_process", () => ({
  execSync: vi.fn(),
}));

vi.mock("node:fs", () => ({
  existsSync: vi.fn(() => true),  // tsconfig.json exists
}));

describe("createTypecheckHook", () => {
  it("returns {} when typecheck passes", async () => {
    const { execSync } = await import("node:child_process");
    vi.mocked(execSync).mockReturnValue("");  // no output = success

    const hook = createTypecheckHook("/project", "/project/test.ts")!;
    const input = mockPostToolUse("Edit", { file_path: "/project/test.ts" });
    const result = await hook(input, "tool-1", { signal: mockSignal() });

    expect(result).toEqual({});
  });

  it("injects errors when typecheck fails", async () => {
    const { execSync } = await import("node:child_process");
    vi.mocked(execSync).mockImplementation(() => {
      const err = new Error("typecheck failed");
      (err as any).stdout = "/project/test.ts(5,3): error TS2345: Argument of type 'string' not assignable";
      (err as any).stderr = "";
      throw err;
    });

    const hook = createTypecheckHook("/project", "/project/test.ts")!;
    const input = mockPostToolUse("Edit", { file_path: "/project/test.ts" });
    const result = await hook(input, "tool-1", { signal: mockSignal() });

    expect(result.hookSpecificOutput?.additionalContext).toContain("TYPECHECK ERRORS");
    expect(result.hookSpecificOutput?.additionalContext).toContain("TS2345");
  });

  it("returns null when tsconfig.json missing", () => {
    // existsSync is already mocked via vi.mock("node:fs") above
    vi.mocked(existsSync).mockReturnValue(false);

    const hook = createTypecheckHook("/project", "/project/test.ts");
    expect(hook).toBeNull();
  });
});
```

## Hook Test Utilities (test-scaffold.ts pattern)

Create a shared test utilities file for all hook tests:

```typescript
// src/services/agent-sdk/hooks/test-utils.ts
import type { HookInput, PreToolUseHookInput, PostToolUseHookInput } from "../types";

export function makePreToolUse(toolName: string, toolInput: Record<string, unknown>): PreToolUseHookInput {
  return { hook_event_name: "PreToolUse", tool_name: toolName, tool_input: toolInput, session_id: "test", cwd: "/test", permission_mode: "bypassPermissions", transcript_path: "" } as PreToolUseHookInput;
}

export function makePostToolUse(toolName: string, toolInput: Record<string, unknown>, toolResult = ""): PostToolUseHookInput {
  return { hook_event_name: "PostToolUse", tool_name: toolName, tool_input: toolInput, tool_result: toolResult, session_id: "test", cwd: "/test", permission_mode: "bypassPermissions", transcript_path: "" } as PostToolUseHookInput;
}

export const liveSignal = new AbortController().signal;
export const abortedSignal = (() => { const c = new AbortController(); c.abort(); return c.signal; })();
```

## Shell Hook Testing (JSON plugin hooks)

Use the utility scripts from the hook-development skill to test shell-based hooks:

```bash
# Test a command hook directly
echo '{"tool_name": "Write", "tool_input": {"file_path": "/project/.env"}}' | \
  bash ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/detect-sdk-project.sh

# Test with dangerous command input
echo '{"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}' | \
  bash your-security-hook.sh
echo "Exit code: $?"  # Should be 2 for blocked

# Validate JSON output
output=$(echo '{"tool_name": "Read", "tool_input": {"file_path": "test.ts"}}' | bash your-hook.sh)
echo "$output" | jq .  # Validate valid JSON
```
