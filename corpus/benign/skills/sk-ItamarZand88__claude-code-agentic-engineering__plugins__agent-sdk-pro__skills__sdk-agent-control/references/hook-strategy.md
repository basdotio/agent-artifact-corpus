# Hook Strategy Design Guide

## Choosing the Right Hook for Each Goal

| Goal | Hook Type | Event | Matcher |
|------|-----------|-------|---------|
| Restrict file writes | PreToolUse (deny) | PreToolUse | `"Write\|Edit"` |
| Block .env reads | PreToolUse (deny) | PreToolUse | `"Read"` |
| Block dangerous bash | PreToolUse (deny) | PreToolUse | `"Bash"` |
| Auto-fix lint errors | PostToolUse (feedback) | PostToolUse | `"Write\|Edit"` |
| Run typecheck | PostToolUse (feedback) | PostToolUse | `"Write\|Edit"` |
| Remind agent of rules | PostToolUse (feedback) | PostToolUse | `"Bash"` |
| Track test runs | PostToolUse (feedback) | PostToolUse | `"Bash"` |

## Minimum Safe Set for Most Agents

```typescript
hooks: {
  PreToolUse: [
    // 1. Block .env reads (security)
    { matcher: "Read", hooks: [envProtectionHook] },
    // 2. Restrict file writes (control)
    { matcher: "Write|Edit", hooks: [createFileRestrictionHook(targetFile)] },
  ],
  PostToolUse: [
    // 3. Typecheck after edits (quality)
    ...(typecheckHook ? [{ matcher: "Write|Edit", hooks: [typecheckHook] }] : []),
  ],
}
```

## Graduated Hook Strategy

### Level 1: Security (always include)
- `envProtectionHook` — prevents secret leakage

### Level 2: Control (for bounded file tasks)
- `createFileRestrictionHook(targetFile)` — strict file targeting
- `safeCommandHook` — block rm -rf, drop table, etc.

### Level 3: Quality (for code generation tasks)
- `createTypecheckHook(cwd, targetFile)` — catch TS errors early
- `createLintFixHook(cwd, targetFile)` — auto-fix formatting

### Level 4: Guidance (for complex agent decisions)
- Domain-specific reminder hooks — inject decision trees after key events

## Hook Composition Best Practices

### Conditional inclusion (factory returns null)
```typescript
const typecheckHook = createTypecheckHook(workingDirectory, testFilePath);
const lintFixHook = createLintFixHook(workingDirectory, testFilePath);

const postEditHooks: HookCallback[] = [
  ...(typecheckHook ? [typecheckHook] : []),
  ...(lintFixHook ? [lintFixHook] : []),
];

const hooks = {
  PostToolUse: postEditHooks.length > 0
    ? [{ matcher: "Write|Edit", hooks: postEditHooks }]
    : [],
};
```

### Logging hook decisions
```typescript
const fileRestrictionHook = createFileRestrictionHook(targetFile);

// Wrap to add logging:
const loggedHook: HookCallback = async (input, toolUseId, ctx) => {
  const result = await fileRestrictionHook(input, toolUseId, ctx);
  const decision = result.hookSpecificOutput?.permissionDecision;
  if (decision === "deny") {
    sdkLog.warn(`[hook] denied ${input.tool_name} on ${getToolInputFilePath(input as PreToolUseHookInput)}`);
  }
  return result;
};
```

## Anti-Patterns to Avoid

### ❌ Direct tool_input access
```typescript
// BAD: unsafe, no type checking
const filePath = (input.tool_input as any).file_path;

// GOOD: use helper
const filePath = getToolInputFilePath(input as PreToolUseHookInput);
```

### ❌ Missing signal check
```typescript
// BAD: proceeds even if cancelled
export const myHook: HookCallback = async (input, _, ctx) => {
  const filePath = getToolInputFilePath(input as PreToolUseHookInput);
  // ...
};

// GOOD: always first
export const myHook: HookCallback = async (input, _, { signal }) => {
  if (signal.aborted) return {};
  // ...
};
```

### ❌ Wrong permissionDecision value
```typescript
// BAD: not a valid value
return { hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "approve" } };

// GOOD: only "allow" or "deny"
return { hookSpecificOutput: { hookEventName: "PreToolUse", permissionDecision: "deny" } };
```

### ❌ Using systemMessage instead of additionalContext in PostToolUse
```typescript
// BAD: wrong field for PostToolUse
return { systemMessage: "Lint errors found" };

// GOOD: correct field
return { hookSpecificOutput: { hookEventName: "PostToolUse", additionalContext: "Lint errors found" } };
```
