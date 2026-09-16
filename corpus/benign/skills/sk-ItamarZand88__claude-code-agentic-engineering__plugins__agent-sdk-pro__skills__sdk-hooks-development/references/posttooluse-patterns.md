# PostToolUse Hook Patterns

PostToolUse hooks run **after** a tool completes. They inject `additionalContext` into the tool result — the agent sees this as part of the tool output and can react to it.

## Output Structure

```typescript
{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",  // use input.hook_event_name for accuracy
    additionalContext: string,  // injected into the tool result the agent reads
  }
}
```

**Empty return `{}`** = no additional context injected.

## Pattern 1: Test Command Reminder

After test runs, inject phase decision logic to guide agent behavior:

```typescript
const TEST_PATTERNS = [/\bjest\b/, /\bvitest\b/, /\bnpm\s+test\b/, /\bnpx\s+jest\b/];

function isTestCommand(cmd: string): boolean {
  return TEST_PATTERNS.some(p => p.test(cmd));
}

export const testPruneHook: HookCallback = async (input, _, { signal }) => {
  if (signal.aborted) return {};
  if (!isPostToolUseInput(input)) return {};

  const command = getToolInputCommand(input);
  if (!isTestCommand(command)) return {};

  return {
    hookSpecificOutput: {
      hookEventName: input.hook_event_name,
      additionalContext: [
        "DECISION TREE:",
        "- ALL tests pass → STOP immediately",
        "- 10+ pass, some fail → PRUNE failing tests, then STOP",
        "- <10 pass → REPAIR failing tests",
      ].join("\n"),
    },
  };
};
```

## Pattern 2: TypeScript Auto-Fix with Error Feedback

Run `tsc --noEmit` after edits, inject filtered errors for the agent to fix:

```typescript
export function createTypecheckHook(workingDirectory: string, targetFile: string): HookCallback | null {
  const tsconfigPath = path.join(workingDirectory, "tsconfig.json");
  if (!existsSync(tsconfigPath)) return null;  // graceful disable

  const tscBin = path.join(workingDirectory, "node_modules", ".bin", "tsc");
  const normalizedTarget = path.resolve(targetFile);

  return async (input, _, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPostToolUseInput(input)) return {};

    const filePath = getToolInputFilePath(input);
    if (path.resolve(filePath) !== normalizedTarget) return {};

    try {
      execSync(`${tscBin} --noEmit 2>&1`, { cwd: workingDirectory, timeout: 60_000 });
      return {};  // all good
    } catch (error: unknown) {
      const rawOutput = getExecOutput(error);
      if (!rawOutput) return {};

      // Filter to only errors from the target file
      const filtered = rawOutput
        .split("\n")
        .filter(line => line.includes(targetFile) || line.includes(normalizedTarget))
        .join("\n");

      if (!filtered) return {};

      const errorCount = (filtered.match(/error TS\d+/g) ?? []).length;

      return {
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext: [
            `TYPECHECK ERRORS (${errorCount}) in ${filePath}`,
            "Fix these before running tests:",
            "",
            filtered.slice(0, 3000),
          ].join("\n"),
        },
      };
    }
  };
}
```

## Pattern 3: ESLint Auto-Fix with Remaining Errors

```typescript
export function createLintFixHook(workingDirectory: string, targetFile: string): HookCallback | null {
  const eslintBin = path.join(workingDirectory, "node_modules", ".bin", "eslint");
  if (!existsSync(eslintBin)) return null;

  return async (input, _, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPostToolUseInput(input)) return {};

    const filePath = getToolInputFilePath(input);
    if (path.resolve(filePath) !== path.resolve(targetFile)) return {};

    try {
      execSync(`${eslintBin} --fix "${targetFile}" 2>&1`, {
        cwd: workingDirectory,
        timeout: 30_000,
      });
      return {};
    } catch (error: unknown) {
      const output = getExecOutput(error);
      if (!output) return {};

      const errorCount = (output.match(/\d+ error/g) ?? []).length;
      if (errorCount === 0) return {};

      return {
        hookSpecificOutput: {
          hookEventName: "PostToolUse",
          additionalContext: `LINT ERRORS (${errorCount}) after auto-fix on ${filePath}:\n${output.slice(0, 2000)}`,
        },
      };
    }
  };
}
```

## Pattern 4: Build Verification

After Bash commands that look like builds, verify they succeeded:

```typescript
const BUILD_PATTERNS = [/\bnpm\s+run\s+build\b/, /\btsc\b/, /\bvite\s+build\b/];

export const buildVerifyHook: HookCallback = async (input, _, { signal }) => {
  if (signal.aborted) return {};
  if (!isPostToolUseInput(input)) return {};

  const command = getToolInputCommand(input);
  const isBuildCommand = BUILD_PATTERNS.some(p => p.test(command));
  if (!isBuildCommand) return {};

  // tool_result is the output of the bash command
  const toolResult = (input as { tool_result?: unknown }).tool_result;
  const output = typeof toolResult === "string" ? toolResult : "";

  if (output.includes("error TS") || output.toLowerCase().includes("build failed")) {
    return {
      hookSpecificOutput: {
        hookEventName: "PostToolUse",
        additionalContext: "BUILD FAILED. Fix TypeScript errors before proceeding.",
      },
    };
  }

  return {};
};
```

## Key Differences: PreToolUse vs PostToolUse

| Aspect | PreToolUse | PostToolUse |
|--------|-----------|-------------|
| Timing | Before tool runs | After tool completes |
| Can block | Yes (`permissionDecision: "deny"`) | No |
| Injects feedback | Yes (`additionalContext`, without `permissionDecision`) | Yes (`additionalContext`) |
| Common use | Security guards, file restrictions | Linting, typechecking, reminders |
| Input type guard | `isPreToolUseInput()` | `isPostToolUseInput()` |
