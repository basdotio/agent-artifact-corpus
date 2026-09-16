# PreToolUse Hook Patterns

PreToolUse hooks run **before** a tool executes and can allow, deny, or (future) modify the tool call.

## Output Structure

```typescript
{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "allow" | "deny",
    permissionDecisionReason: string,  // shown in logs when decision is "deny"
  }
}
```

**Empty return `{}`** = implicit allow. Only explicitly return when you need to deny.

## Pattern 1: Path-Based Protection

Deny writes to files outside a specific directory or file:

```typescript
export function createAllowedPathHook(allowedDir: string): HookCallback {
  const normalizedDir = path.resolve(allowedDir);

  return async (input, _, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};
    if (input.tool_name !== "Write" && input.tool_name !== "Edit") return {};

    const filePath = getToolInputFilePath(input);
    if (!filePath) return {};

    const normalized = path.resolve(filePath);
    if (normalized.startsWith(normalizedDir)) return {};

    return {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: `Writes are restricted to ${allowedDir}. Attempted: ${filePath}`,
      },
    };
  };
}
```

## Pattern 2: Filename Pattern Guard

Block reads on files matching a pattern:

```typescript
export const envProtectionHook: HookCallback = async (input, _, { signal }) => {
  if (signal.aborted) return {};
  if (!isPreToolUseInput(input)) return {};

  const filePath = getToolInputFilePath(input);
  if (!filePath) return {};

  if (!path.basename(filePath).startsWith(".env")) return {};

  return {
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Reading .env files is not allowed",
    },
  };
};
```

## Pattern 3: Command Keyword Guard

Block destructive bash commands:

```typescript
const DESTRUCTIVE_PATTERNS = [/\brm\s+-rf\b/, /\bdrop\s+table\b/i, /\bformat\s+[a-z]:/i];

export const safeCommandHook: HookCallback = async (input, _, { signal }) => {
  if (signal.aborted) return {};
  if (!isPreToolUseInput(input)) return {};
  if (input.tool_name !== "Bash") return {};

  const toolInput = input.tool_input as { command?: string };
  const command = toolInput.command ?? "";

  for (const pattern of DESTRUCTIVE_PATTERNS) {
    if (pattern.test(command)) {
      return {
        hookSpecificOutput: {
          hookEventName: "PreToolUse",
          permissionDecision: "deny",
          permissionDecisionReason: `Dangerous command blocked: matches pattern ${pattern}`,
        },
      };
    }
  }

  return {};
};
```

## Pattern 4: Conditional Tool Allow-List

Restrict the agent to only specific files in a directory:

```typescript
export function createExtensionGuardHook(allowedExtensions: string[]): HookCallback {
  return async (input, _, { signal }) => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};

    const filePath = getToolInputFilePath(input);
    if (!filePath) return {};

    const ext = path.extname(filePath).toLowerCase();
    if (allowedExtensions.includes(ext)) return {};

    return {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: `Only ${allowedExtensions.join(", ")} files are allowed. Got: ${ext}`,
      },
    };
  };
}
```

## Multiple PreToolUse Hooks

All hooks for the same matcher run sequentially in registration order. If any denies, the tool is blocked:

```typescript
hooks: {
  PreToolUse: [
    {
      matcher: "Write|Edit",
      hooks: [
        createFileRestrictionHook(targetFile),  // path guard
        createExtensionGuardHook([".ts", ".tsx"]),  // extension guard
      ],
    },
    {
      matcher: "Read",
      hooks: [envProtectionHook],  // env file guard
    },
  ],
}
```
