# Hook Events Reference — TypeScript Agent SDK

## Supported Events

| Event | When it fires | TypeScript-only | Primary use |
|-------|---------------|-----------------|-------------|
| `PreToolUse` | Before a tool executes | No | Security, file restriction, input modification |
| `PostToolUse` | After a tool completes | No | Linting, typecheck, feedback injection, audit |
| `PostToolUseFailure` | When a tool execution fails | **Yes** | Error handling, failure logging, retry logic |
| `UserPromptSubmit` | When user sends a prompt | No | Inject context, pre-process prompt |
| `Stop` | Agent execution stops | No | Save state, cleanup, checkpoint |
| `SubagentStart` | Subagent initialized | **Yes** | Track parallel tasks, inject permissions |
| `SubagentStop` | Subagent completes | No | Aggregate results, monitor completion |
| `PreCompact` | Before conversation compaction | No | Archive transcript before summarizing |
| `PermissionRequest` | Permission dialog would show | **Yes** | Custom permission handling |
| `SessionStart` | Session initialized | **Yes** | Telemetry, logging, env setup |
| `SessionEnd` | Session terminated | **Yes** | Cleanup, release resources |
| `Notification` | Agent sends status message | **Yes** | Slack/PagerDuty forwarding, monitoring |

> For lifecycle hooks (`Stop`, `SessionStart`, `SessionEnd`, `Notification`, `SubagentStart`, `SubagentStop`): matchers are **ignored** — the hook fires for all events of that type regardless of matcher.

---

## Registering Hooks

```typescript
await query({
  prompt,
  options: {
    hooks: {
      PreToolUse: [
        { matcher: "Write|Edit", hooks: [fileRestrictionHook] },
        { matcher: "Read",       hooks: [envProtectionHook] },
        { matcher: "^mcp__",    hooks: [mcpAuditHook] },   // all MCP tools
        { hooks: [globalLogger] },                          // no matcher = all tools
      ],
      PostToolUse: [
        { matcher: "Bash",       hooks: [testPruneHook] },
        { matcher: "Write|Edit", hooks: [typecheckHook, lintFixHook] },
      ],
      PostToolUseFailure: [
        { hooks: [failureLoggerHook] },
      ],
    },
  },
});
```

**Matcher syntax**: regex matched against tool name. Use `|` for multiple tools, `^mcp__` for all MCP tools.

**Built-in tool names**: `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`, `LS`, `WebFetch`, `Task`. MCP tools: `mcp__<server>__<action>` (e.g., `mcp__playwright__browser_click`).

**Hook chaining**: Hooks execute **sequentially** in registration order. Each hook runs even if a previous one denied the operation.

---

## Callback Outputs — Complete Reference

### `HookJSONOutput` union

A hook can return either a synchronous or async output:

```typescript
type HookJSONOutput = SyncHookJSONOutput | AsyncHookJSONOutput;
```

### AsyncHookJSONOutput

Return this to signal that the hook needs more time (e.g., waiting on an external approval API):

```typescript
return {
  async: true,
  asyncTimeout: 30000,  // ms — how long to wait before timing out
};
```

The SDK will wait until the hook resolves or `asyncTimeout` expires.

### SyncHookJSONOutput — top-level fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `continue` | `boolean` | `true` | Set to `false` to stop the agent session entirely |
| `stopReason` | `string` | — | Message shown when `continue` is `false` |
| `suppressOutput` | `boolean` | `false` | Hide hook stdout from the transcript |
| `systemMessage` | `string` | — | Message injected directly into Claude's conversation |
| `decision` | `"approve" \| "block"` | — | Legacy permission field (prefer `hookSpecificOutput.permissionDecision`) |
| `reason` | `string` | — | Paired with `decision` (legacy) |

```typescript
// Stop the agent entirely
return {
  continue: false,
  stopReason: "Budget exhausted — stopping before incurring more cost.",
};

// Inject guidance without blocking
return {
  systemMessage: "Remember: only edit files inside the /output directory.",
};
```

### hookSpecificOutput fields

`hookSpecificOutput` is a **discriminated union** keyed on `hookEventName`. Only certain fields are valid per event — the TypeScript type enforces this:

| `hookEventName` | Supported fields |
|-----------------|-----------------|
| `"PreToolUse"` | `permissionDecision`, `permissionDecisionReason`, `updatedInput` |
| `"PostToolUse"` | `additionalContext` |
| `"UserPromptSubmit"` | `additionalContext` |
| `"SessionStart"` | `additionalContext` |

> **Note on PreToolUse `additionalContext`**: The hooks documentation mentions it, but the official TypeScript type definition for PreToolUse `hookSpecificOutput` does **not** include `additionalContext`. To inject context alongside a PreToolUse event, use the top-level `systemMessage` field instead.

---

## Permission Decision Evaluation Order

When multiple hooks and rules apply to the same tool call, the SDK evaluates them in this priority order:

1. **Deny** — any hook returning `deny` blocks the call immediately
2. **Ask** — prompt for human confirmation
3. **Allow** — explicit allow
4. **Default** — ask (if nothing matched)

**Important**: If any hook returns `deny`, it wins — `allow` from other hooks cannot override it.

---

## PreToolUse — All Patterns

### Block (deny)
```typescript
return {
  hookSpecificOutput: {
    hookEventName: input.hook_event_name,
    permissionDecision: "deny",
    permissionDecisionReason: "Only the pre-created test file can be modified",
  },
};
```

### Allow explicitly
```typescript
return {
  hookSpecificOutput: {
    hookEventName: input.hook_event_name,
    permissionDecision: "allow",
    permissionDecisionReason: "Read-only tool auto-approved",
  },
};
```

### Modify tool input (updatedInput)
Redirect or sanitize the tool call before it executes. **Must include `permissionDecision: 'allow'`**. Always return a new object — never mutate `tool_input`.

```typescript
const redirectToSandbox: HookCallback = async (input, toolUseID, { signal }) => {
  if (signal.aborted) return {};
  if (!isPreToolUseInput(input)) return {};

  const filePath = getToolInputFilePath(input);
  if (!filePath) return {};

  return {
    hookSpecificOutput: {
      hookEventName: input.hook_event_name,
      permissionDecision: "allow",
      updatedInput: {
        ...(input.tool_input as Record<string, unknown>),
        file_path: `/sandbox${filePath}`,  // redirect all writes to sandbox
      },
    },
  };
};
```

Use cases: redirect file paths to a sandbox directory, inject credentials into tool inputs, normalize paths, strip dangerous flags from commands.

### Inject context (allow + additionalContext)
```typescript
return {
  hookSpecificOutput: {
    hookEventName: input.hook_event_name,
    additionalContext: "Current git branch: feature/auth. Last 3 test failures: ...",
    // No permissionDecision — tool is allowed to run
  },
};
```

---

## PostToolUse — Patterns

### Inject feedback
```typescript
return {
  hookSpecificOutput: {
    hookEventName: input.hook_event_name,
    additionalContext: "TYPECHECK ERRORS:\n  src/index.ts(5,3): error TS2345",
  },
};
```

### Access tool result
```typescript
const postInput = input as PostToolUseHookInput;
const toolResult = postInput.tool_response;  // what the tool returned
```

---

## PostToolUseFailure (TypeScript-only)

Fires when a tool execution fails. Useful for logging, alerting, or deciding whether to retry.

> **Important**: `PostToolUseFailure` does **not** support `hookSpecificOutput.additionalContext` — it is not in the TypeScript type union. Use the top-level `systemMessage` field to inject guidance when a tool fails.

```typescript
import type { PostToolUseFailureHookInput } from "../types";

const failureLogger: HookCallback = async (input, toolUseID, { signal }) => {
  if (signal.aborted) return {};
  if (input.hook_event_name !== "PostToolUseFailure") return {};

  const failure = input as PostToolUseFailureHookInput;
  console.error("[TOOL FAILURE]", {
    tool: failure.tool_name,
    error: failure.error,
    isInterrupt: failure.is_interrupt,
    toolUseID,
  });

  // Use systemMessage (top-level), NOT hookSpecificOutput — PostToolUseFailure doesn't support it
  return {
    systemMessage: `Tool "${failure.tool_name}" failed: ${failure.error}. Consider an alternative approach.`,
  };
};
```

Input fields specific to this event:
- `tool_name`: which tool failed
- `error`: the error message string
- `is_interrupt?`: optional boolean — whether failure was caused by an interrupt

---

## toolUseID — Correlating Pre and PostToolUse

The second argument to every `HookCallback` is `toolUseID`. It is the same value for the `PreToolUse` and `PostToolUse` events of the **same tool call**. Use it to build audit trails or measure tool execution duration:

```typescript
const auditMap = new Map<string, { tool: string; startMs: number }>();

const preAuditHook: HookCallback = async (input, toolUseID, { signal }) => {
  if (!isPreToolUseInput(input) || !toolUseID) return {};
  auditMap.set(toolUseID, { tool: input.tool_name, startMs: Date.now() });
  return {};
};

const postAuditHook: HookCallback = async (input, toolUseID, { signal }) => {
  if (!isPostToolUseInput(input) || !toolUseID) return {};
  const entry = auditMap.get(toolUseID);
  if (entry) {
    console.log(`[AUDIT] ${entry.tool} took ${Date.now() - entry.startMs}ms`);
    auditMap.delete(toolUseID);
  }
  return {};
};
```

---

## Async Hooks with fetch()

For hooks that call external APIs (webhooks, Slack, monitoring), pass the `signal` to `fetch()` so the request cancels properly if the hook times out:

```typescript
const webhookNotifier: HookCallback = async (input, toolUseID, { signal }) => {
  if (signal.aborted) return {};
  if (!isPostToolUseInput(input)) return {};

  try {
    await fetch("https://hooks.example.com/agent-events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        tool: input.tool_name,
        sessionId: input.session_id,
        timestamp: new Date().toISOString(),
      }),
      signal,  // ← propagate cancellation to the HTTP request
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") return {};
    console.error("Webhook failed:", error);
    // Never throw from a hook — swallow errors to avoid blocking the agent
  }

  return {};
};
```

---

## Subagent Hooks

### SubagentStart (TypeScript-only)

Fires when a subagent initializes. Use to inject permissions so subagents don't trigger repeated permission prompts:

```typescript
const subagentPermissioner: HookCallback = async (input, toolUseID, { signal }) => {
  if (signal.aborted) return {};
  if (input.hook_event_name !== "SubagentStart") return {};

  // Auto-approve read-only tools for subagents
  return {
    hookSpecificOutput: {
      hookEventName: input.hook_event_name,
      additionalContext: "Subagent started. Read-only tools are pre-approved.",
    },
  };
};
```

Input fields: `agent_id` (unique ID), `agent_type` (role/type of the subagent).

### SubagentStop

Input fields: `stop_hook_active: boolean` only. Does **not** have `agent_id` or `agent_type` — those are SubagentStart only.

```typescript
const subagentTracker: HookCallback = async (input, toolUseID, { signal }) => {
  if (signal.aborted) return {};
  if (input.hook_event_name !== "SubagentStop") return {};

  const subStop = input as SubagentStopHookInput;
  console.log("[SUBAGENT DONE]", { toolUseID, stopHookActive: subStop.stop_hook_active });
  return {};
};
```

> **Subagents don't inherit parent permissions.** Each subagent starts fresh. Use `PreToolUse` hooks with `permissionDecision: 'allow'` to auto-approve tools for subagents, or they will trigger permission prompts independently.

---

## Recursive Hook Loop Warning

`UserPromptSubmit` hooks that spawn subagents can create infinite loops if those subagents trigger the same hook. To prevent this, check whether you're already in a subagent context before spawning:

```typescript
const safeSpawner: HookCallback = async (input, toolUseID, { signal }) => {
  if (signal.aborted) return {};
  if (input.hook_event_name !== "UserPromptSubmit") return {};

  // Check if this is already a subagent session to avoid infinite loops
  const parentToolUseId = (input as any).parent_tool_use_id;
  if (parentToolUseId) return {};  // already in a subagent — don't spawn again

  // Safe to spawn subagent here
  return {};
};
```

---

## MCP Tool Naming

MCP tools always follow the pattern `mcp__<server>__<action>`. Match them with regex:

```typescript
hooks: {
  PreToolUse: [
    { matcher: "^mcp__",              hooks: [mcpAuditHook] },      // all MCP tools
    { matcher: "mcp__playwright__",   hooks: [browserSecurityHook] }, // one server
    { matcher: "mcp__filesystem__write", hooks: [fsWriteGuard] },   // one action
  ],
}
```

The server name comes from the key you use in `mcpServers` configuration.

---

## Hook Execution Model

```
Claude decides to call a tool
  → PreToolUse hooks run sequentially (in registration order)
  → Permission evaluation: deny wins over ask wins over allow
  → If denied: Claude receives permissionDecisionReason, tool does not execute
  → Tool executes
  → PostToolUse hooks run sequentially
  → additionalContext appended to tool result
  → Claude reads combined result + context

If tool fails:
  → PostToolUseFailure hooks run instead of PostToolUse
```

TypeScript SDK hooks are **always synchronous from the agent's perspective** — `query()` awaits each hook before continuing.
