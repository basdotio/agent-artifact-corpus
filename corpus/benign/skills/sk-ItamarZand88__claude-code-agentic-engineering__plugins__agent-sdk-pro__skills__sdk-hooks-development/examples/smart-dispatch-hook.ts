/**
 * Smart Dispatch Hook Pattern
 *
 * Instead of registering many separate hooks, register ONE dispatcher that
 * routes to specialized sub-handlers based on tool name and file type.
 *
 *
 * Benefits:
 * - Single registration in query() options
 * - Easy to extend: add a handler, no registration change
 * - Language-aware: different validation per file type
 * - Both file-type and tool-type routing supported
 */

import path from "node:path";

import type { HookCallback, HookJSONOutput, HookInput } from "../types";
import { isPreToolUseInput, isPostToolUseInput } from "../types";

type HookHandler = (input: HookInput, signal: AbortSignal) => Promise<HookJSONOutput>;

// ── Sub-handlers (register your own here) ────────────────────────────────────

const TYPESCRIPT_HANDLER: HookHandler = async (input, signal) => {
  // Runs for .ts / .tsx files — add typecheck, lint-fix, etc.
  return {};
};

const BASH_HANDLER: HookHandler = async (input, signal) => {
  // Runs for all Bash commands — add security checks here
  return {};
};

const NEW_FILE_HANDLER: HookHandler = async (input, signal) => {
  // Runs when Write creates a new file — check naming conventions
  return {};
};

// ── File extension → handler map ─────────────────────────────────────────────

const FILE_TYPE_HANDLERS: Record<string, HookHandler> = {
  ".ts": TYPESCRIPT_HANDLER,
  ".tsx": TYPESCRIPT_HANDLER,
  ".js": TYPESCRIPT_HANDLER,   // Reuse same handler
  ".jsx": TYPESCRIPT_HANDLER,
};

// ── Tool → handler map ────────────────────────────────────────────────────────

const TOOL_HANDLERS: Record<string, HookHandler> = {
  Bash: BASH_HANDLER,
  Write: NEW_FILE_HANDLER,
};

// ── Dispatcher (single registration entry point) ──────────────────────────────

export const createDispatchHook = (): HookCallback => {
  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};

    const toolInput = input.tool_input as Record<string, unknown>;
    const toolName = isPreToolUseInput(input) || isPostToolUseInput(input)
      ? input.tool_name
      : "";

    const handlers: HookHandler[] = [];

    // 1. Route by file type (if tool has file_path)
    const filePath = typeof toolInput.file_path === "string" ? toolInput.file_path : "";
    if (filePath) {
      const ext = path.extname(filePath).toLowerCase();
      const fileHandler = FILE_TYPE_HANDLERS[ext];
      if (fileHandler) handlers.push(fileHandler);
    }

    // 2. Route by tool name
    const toolHandler = TOOL_HANDLERS[toolName];
    if (toolHandler) handlers.push(toolHandler);

    // 3. Run all applicable handlers and merge results
    const results = await Promise.all(handlers.map(h => h(input, signal)));

    // Merge: if any handler denies, deny overall
    for (const result of results) {
      const decision = result.hookSpecificOutput?.permissionDecision;
      if (decision === "deny") return result;
    }

    // Return first non-empty additionalContext (or {})
    for (const result of results) {
      const ctx = result.hookSpecificOutput?.additionalContext;
      if (ctx) return result;
    }

    return {};
  };
};

// ── Usage ─────────────────────────────────────────────────────────────────────
// Register once for all events:
//
// hooks: {
//   PreToolUse: [
//     { matcher: "*", hooks: [createDispatchHook()] }
//   ],
//   PostToolUse: [
//     { matcher: "*", hooks: [createDispatchHook()] }
//   ],
// }
//
// Then add handlers to FILE_TYPE_HANDLERS or TOOL_HANDLERS as needed.
