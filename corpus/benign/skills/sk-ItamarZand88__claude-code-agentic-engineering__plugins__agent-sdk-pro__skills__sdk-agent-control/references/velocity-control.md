# Velocity Control & Output Validation

Advanced patterns for controlling agent behavior beyond hooks — rate limiting, output quality gates, and checkpoint strategies.

## Pattern: Velocity Governor

Limit how many tool calls the agent makes per time window. Useful for preventing runaway agents that loop excessively.

```typescript
/**
 * Velocity Governor Hook
 *
 * Tracks tool call frequency and denies if rate exceeds threshold.
 * State persisted to temp file across parallel hook calls.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import type { HookCallback, HookJSONOutput } from "../types";
import { isPreToolUseInput } from "../types";

interface VelocityState {
  windowStart: number;
  count: number;
}

export function createVelocityGovernorHook(
  maxCallsPerMinute: number,
  stateFile: string
): HookCallback {
  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};

    const now = Date.now();
    let state: VelocityState = { windowStart: now, count: 0 };

    if (existsSync(stateFile)) {
      try {
        state = JSON.parse(readFileSync(stateFile, "utf8")) as VelocityState;
      } catch { /* corrupt state — reset */ }
    }

    // Reset window if >1 minute has passed
    if (now - state.windowStart > 60_000) {
      state = { windowStart: now, count: 0 };
    }

    state.count++;
    writeFileSync(stateFile, JSON.stringify(state), "utf8");

    if (state.count > maxCallsPerMinute) {
      return {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: `Velocity limit: ${maxCallsPerMinute} tool calls/min exceeded (${state.count} calls). Agent may be in a loop.`,
        },
      };
    }

    return {};
  };
}
```

**Usage**:
```typescript
const velocityHook = createVelocityGovernorHook(
  30,                           // max 30 tool calls per minute
  "/tmp/sdk-velocity-state.json"
);

hooks: {
  PreToolUse: [
    { matcher: "*", hooks: [velocityHook] }
  ],
}
```

## Pattern: Output Validator Hook

After the agent writes code, validate it meets quality gates before the agent considers it done:

```typescript
/**
 * Output Validator Hook (PostToolUse on Write|Edit)
 *
 * Heuristic validation — no LLM call, pure regex patterns.
 * Injects warnings when output contains placeholder or incomplete content.
 */
import { readFileSync, existsSync } from "node:fs";
import type { HookCallback, HookJSONOutput } from "../types";
import { getToolInputFilePath, isPostToolUseInput } from "../types";

const PLACEHOLDER_PATTERNS: RegExp[] = [
  /\/path\/to\//,
  /your-api-key/i,
  /example\.com/i,
  /TODO:/,
  /FIXME:/,
  /NotImplementedError/,
  /throw new Error\(["']Not implemented/,
];

const UNCERTAINTY_MARKERS = [
  "I'm not sure",
  "probably",
  "I think",
  "might work",
];

export const outputValidatorHook: HookCallback = async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
  if (signal.aborted) return {};
  if (!isPostToolUseInput(input)) return {};

  const filePath = getToolInputFilePath(input);
  if (!filePath || !filePath.match(/\.(ts|tsx|js|jsx)$/)) return {};
  if (!existsSync(filePath)) return {};

  const content = readFileSync(filePath, "utf8");
  const warnings: string[] = [];

  for (const pattern of PLACEHOLDER_PATTERNS) {
    if (pattern.test(content)) {
      warnings.push(`Placeholder pattern found: ${pattern.source}`);
    }
  }

  if (warnings.length === 0) return {};

  return {
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: [
        "OUTPUT QUALITY WARNING:",
        ...warnings.map(w => `  - ${w}`),
        "Review before finalizing.",
      ].join("\n"),
    },
  };
};
```

## Pattern: Auto-Checkpoint on Run Exit

Save uncommitted work as a git stash whenever a run completes (success, error, or abort). Implement in your runner's `finally` block:

```typescript
async run(params: RunParams): Promise<RunResult> {
  try {
    const result = await this.executeSDK(params);
    return result;
  } finally {
    // Auto-checkpoint on any exit (success, error, abort)
    await this.checkpoint(params.workingDirectory);
  }
}

private async checkpoint(workingDirectory: string): Promise<void> {
  const { execSync } = await import("node:child_process");
  try {
    const branch = execSync("git rev-parse --abbrev-ref HEAD", { cwd: workingDirectory, encoding: "utf8" }).trim();
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const stashName = `sdk-checkpoint-${branch}-${timestamp}`;
    execSync(`git stash push -u -m "${stashName}"`, { cwd: workingDirectory });
  } catch { /* not a git repo or no changes — silently skip */ }
}
```

## Pattern: maxTurns as Circuit Breaker

Use `maxTurns` as a hard circuit breaker, and detect `error_max_turns` in the result:

```typescript
const messageStream = query({
  prompt,
  options: {
    maxTurns: 50,
    maxBudgetUsd: 2,
    // ...
  },
});

for await (const message of messageStream) {
  if (isResultMessage(message)) {
    if (message.subtype === "error_max_turns") {
      logger.warn("Agent hit turn limit", { maxTurns: 50, numTurns: message.num_turns });
      // Return partial result or throw a retryable error
      const partial = readTestFile(params.testFilePath);
      return { code: partial, timedOut: true };
    }
    // ...
  }
}
```

## Pattern: Budget Guard Hook

Deny expensive operations before they start when budget is nearly exhausted:

```typescript
export function createBudgetGuardHook(
  maxBudgetUsd: number,
  getSpentUsd: () => number
): HookCallback {
  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};

    // Only check expensive tools
    if (!["Bash", "Write"].includes(input.tool_name)) return {};

    const spent = getSpentUsd();
    const remaining = maxBudgetUsd - spent;

    if (remaining < 0.1) {  // < $0.10 remaining
      return {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: `Budget nearly exhausted ($${spent.toFixed(2)} of $${maxBudgetUsd}). Stop and report current progress.`,
        },
      };
    }

    return {};
  };
}
```

