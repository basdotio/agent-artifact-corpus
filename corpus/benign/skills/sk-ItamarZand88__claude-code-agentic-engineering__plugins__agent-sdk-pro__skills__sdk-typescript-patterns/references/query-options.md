# query() Options Reference

Full reference for the `Options` object passed to `query()`.

## Required

| Field | Type | Description |
|-------|------|-------------|
| `model` | `string` | Claude model ID. Use constant: `SDK_MODEL = "claude-sonnet-4-6"` |

## Agent Behavior

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `systemPrompt` | `string` | — | System prompt for the agent. Be specific about role, constraints, and file paths. |
| `allowedTools` | `string[]` | all tools | Restrict which Claude tools are available. Prefer explicit allow-lists. |
| `disallowedTools` | `string[]` | `[]` | Block specific tools by name. Complement to `allowedTools` — use when you want most tools available but need to exclude a few. |
| `permissionMode` | `"default" \| "acceptEdits" \| "bypassPermissions" \| "plan"` | `"default"` | Controls how permissions are handled. Use `"bypassPermissions"` for automated pipelines. Use `"acceptEdits"` to auto-approve file edits. Use `"plan"` for read-only planning passes. |
| `maxTurns` | `number` | unlimited | Hard cap on agent iterations. Safety rail against infinite loops. Recommended: 30–80. |
| `maxBudgetUsd` | `number` | unlimited | Hard cap on spend. Safety rail. Recommended: $1–$5 for bounded tasks. |

## Runtime

| Field | Type | Description |
|-------|------|-------------|
| `cwd` | `string` | Working directory for the agent's Bash/file tools. Should be the project root. |
| `abortController` | `AbortController` | Forward external abort signals here. The SDK respects `abort()` calls. |
| `sessionId` | `string` | Correlates SDK session with your request ID for tracing/logging. |
| `env` | `Record<string, string>` | Environment variables injected into the agent's shell context. Use for API keys, proxy URLs, custom headers. |
| `settingSources` | `("user" \| "project" \| "local")[]` | Controls which filesystem settings files load. Defaults to `[]` (no filesystem settings). Pass `["user", "project", "local"]` to load all. |

## Hooks

```typescript
hooks: {
  PreToolUse?: Array<{
    matcher: string;  // e.g. "Write|Edit", "Bash", "mcp__.*__delete.*", "*"
    hooks: HookCallback[];
  }>;
  PostToolUse?: Array<{
    matcher: string;
    hooks: HookCallback[];
  }>;
  PostToolUseFailure?: Array<{
    hooks: HookCallback[];  // matcher ignored for failure events
  }>;
}
```

Matchers are regex-matched against tool names. Multiple matchers can target the same tool — all matching hooks run sequentially in registration order.

## canUseTool — Custom Permission Function

An alternative to PreToolUse hooks for permission control. Called before each tool use:

```typescript
canUseTool: async (
  toolName: string,
  input: Record<string, unknown>,
  options: { signal: AbortSignal }
) => Promise<PermissionResult>
```

Where `PermissionResult` is `"allow" | "deny" | "ask"`.

Use `canUseTool` when:
- Permission logic is simple and synchronous-looking
- You want a single function rather than multiple hook registrations
- You don't need to inject `additionalContext` or modify `updatedInput`

Use PreToolUse hooks when:
- You need to modify tool inputs (`updatedInput`)
- You need to inject context (`systemMessage`)
- You have multiple independent checks per tool

```typescript
await query({
  prompt,
  options: {
    model: SDK_MODEL,
    canUseTool: async (toolName, input, { signal }) => {
      if (signal.aborted) return "allow";

      // Block writes to protected files
      if (toolName === "Write" || toolName === "Edit") {
        const filePath = (input as { file_path?: string }).file_path ?? "";
        if (filePath.includes(".env")) return "deny";
      }

      return "allow";
    },
  },
});
```

## Matcher Patterns

```typescript
"Write"              // exact match
"Write|Edit"         // multiple tools
"Bash"               // bash commands only
"mcp__.*"            // all MCP tools
"mcp__asana__.*"     // specific MCP server
"Read|Glob|Grep"     // all read tools
"*"                  // wildcard — matches everything (not recommended for PreToolUse)
```
