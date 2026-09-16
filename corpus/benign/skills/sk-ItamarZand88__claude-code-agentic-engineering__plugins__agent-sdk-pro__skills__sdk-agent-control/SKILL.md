---
name: sdk-agent-control
description: Use this skill when controlling agent behavior in TypeScript Agent SDK platforms — restricting allowed tools, setting budget and turn limits, crafting system prompts that guide agents to specific behaviors, implementing the file pre-creation pattern, augmenting prompts with runtime context, building message loggers, or tracking agent run metadata (cost, duration, iterations).
version: 1.0.0
---

# Agent Control Patterns for SDK Platforms

## Core Control Levers

Control agents through five primary mechanisms:

1. **`allowedTools`** — what tools the agent can call
2. **`permissionMode`** — whether to bypass permission prompts
3. **`maxTurns`** — hard iteration cap
4. **`maxBudgetUsd`** — hard spend cap
5. **`hooks`** — programmatic allow/deny on every tool call

## Pattern: Minimal Tool Allow-List

Give the agent only the tools it needs. Fewer tools = more predictable behavior:

```typescript
// For a code-writing agent: read and edit only
allowedTools: ["Read", "Write", "Edit", "Glob", "Grep"]

// For a test runner: also needs Bash
allowedTools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

// For a read-only analysis agent
allowedTools: ["Read", "Glob", "Grep"]
```

## Pattern: File Pre-Creation

Pre-create the output file before running the agent. Instruct the agent to use `Edit` instead of `Write`:

```typescript
// 1. Scaffold the file before SDK run
writeFileSync(testFilePath, "// Scaffolded by platform\n", "utf8");

// 2. Augment the prompt with file path instruction
function buildPromptWithFilePath(userPrompt: string, testFilePath: string): string {
  return [
    userPrompt,
    "",
    "---",
    `IMPORTANT: A file has been pre-created at: ${testFilePath}`,
    "Use the Edit tool to modify this file. Do NOT create a new file with Write.",
  ].join("\n");
}

// 3. Read the file back after SDK completes
const code = readFileSync(testFilePath, "utf8");
```

**Why**: Combining `createFileRestrictionHook(testFilePath)` with pre-creation gives you full control over what the agent writes and where.

## Pattern: Constants File

Never hardcode SDK config inline. Use a dedicated `*.const.ts`:

```typescript
// agent-sdk.const.ts
export const SDK_MODEL = "claude-sonnet-4-5-20250929" as const;
export const SDK_MAX_BUDGET_USD = 2;       // $2 hard cap
export const SDK_MAX_TURNS = 50;           // 50 iterations max
export const SDK_PERMISSION_MODE = "bypassPermissions" as const;
export const SDK_ALLOWED_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"] as const;

// Per-tool timeouts (used in hooks)
export const ESLINT_TIMEOUT_MS = 30_000;
export const TSC_TIMEOUT_MS = 60_000;
export const LINT_OUTPUT_TRUNCATION_LIMIT = 2_000;
export const TSC_OUTPUT_TRUNCATION_LIMIT = 3_000;
```

## Pattern: System Prompt Engineering

System prompts control agent strategy. Structure them with explicit phases:

```typescript
const systemPrompt = `
You are a test generation agent. Follow these phases strictly:

## Phase 1: Analyze
Read the source file. Identify all exported functions/classes.

## Phase 2: Generate
Write comprehensive tests to the pre-created test file using Edit.
Cover: happy path, edge cases, error cases.

## Phase 3: Verify
Run the tests with Bash. Do NOT run more than 3 times.

## Constraints
- ONLY edit the pre-created test file
- Do NOT install packages
- Do NOT modify source files
`.trim();
```

## Pattern: Conditional Hook Composition

Build the hook list dynamically — some hooks may not be available:

```typescript
const fileRestrictionHook = createFileRestrictionHook(params.testFilePath);
const lintFixHook = createLintFixHook(params.workingDirectory, params.testFilePath);
const typecheckHook = createTypecheckHook(params.workingDirectory, params.testFilePath);

const postEditHooks = [
  ...(lintFixHook ? [lintFixHook] : []),
  ...(typecheckHook ? [typecheckHook] : []),
];

const hooks = {
  PreToolUse: [
    { matcher: "Write|Edit", hooks: [fileRestrictionHook] },
    { matcher: "Read", hooks: [envProtectionHook] },
  ],
  PostToolUse: [
    { matcher: "Bash", hooks: [testPruneHook] },
    ...(postEditHooks.length > 0 ? [{ matcher: "Write|Edit", hooks: postEditHooks }] : []),
  ],
};
```

## Pattern: Run Metadata

Always track and persist run metadata for observability:

```typescript
if (isResultMessage(message)) {
  const metadata = {
    durationMs: message.duration_ms,
    costUsd: message.total_cost_usd,
    numTurns: message.num_turns,
    modelUsage: message.modelUsage,
    subtype: message.subtype,  // "success" | "error_max_turns" | "error_during_execution"
  };

  logger.info("SDK run complete", metadata);

  // Prepend to output file as a JSDoc comment
  const comment = [
    "/**",
    ` * @generated Agent SDK`,
    ` * @duration ${(message.duration_ms / 1000).toFixed(1)}s`,
    ` * @cost $${message.total_cost_usd.toFixed(4)}`,
    " */",
    "",
  ].join("\n");

  const existing = readFileSync(outputPath, "utf8");
  writeFileSync(outputPath, comment + existing, "utf8");
}
```

## Pattern: AbortSignal with Cleanup

Forward cancellation from external sources to the SDK:

```typescript
async run(params: { abortSignal?: AbortSignal }): Promise<Result> {
  const abortController = new AbortController();

  if (params.abortSignal) {
    params.abortSignal.addEventListener("abort", () => abortController.abort());
  }

  try {
    for await (const message of query({ ..., options: { ..., abortController } })) {
      if (abortController.signal.aborted) break;
      // ...
    }
  } finally {
    // cleanup if needed
  }
}
```

## Pattern: Verbose Logging Toggle

Use an env-controlled verbose flag to switch between minimal and debug logging:

```typescript
export const isSdkVerboseLogging = process.env.SDK_VERBOSE === "true";

// In your MessageLogger
logMessage(message: SDKMessage): void {
  if (!this.verbose) return;  // skip in production
  console.log("[SDK]", message.type, ...);
}
```

## Advanced Control Patterns

For more patterns from these references:

- **`references/hook-strategy.md`** — hook strategy matrix, minimum safe set, graduated levels (security→control→quality→guidance), composition best practices, anti-patterns to avoid
- **`references/velocity-control.md`** — velocity governor (rate-limit tool calls per minute), output validator (heuristic placeholder detection), `maxTurns` as circuit breaker, budget guard hook, auto-checkpoint in `finally` block

Example:

- **`examples/complete-runner.ts`** — production-ready runner with Inversify DI, conditional hook composition, null-filtering, augmented prompt, full message iteration, metadata prepend
