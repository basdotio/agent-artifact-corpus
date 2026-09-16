/**
 * Input Redirect Hook (PreToolUse on Write)
 *
 * Demonstrates the updatedInput pattern — modifying the tool's input
 * before it executes, rather than blocking or allowing unchanged.
 *
 * Use cases:
 * - Redirect all writes to a sandboxed directory
 * - Inject credentials into tool inputs
 * - Normalize file paths
 * - Strip dangerous flags from Bash commands
 *
 * Rules:
 * - updatedInput MUST be inside hookSpecificOutput
 * - permissionDecision: "allow" is REQUIRED alongside updatedInput
 * - Always return a NEW object — never mutate tool_input directly
 * - Use input.hook_event_name (not hardcoded string) for hookEventName
 */

import path from "node:path";
import type { HookCallback, HookJSONOutput } from "../types";
import { isPreToolUseInput, getToolInputFilePath } from "../types";

// ── Pattern 1: Redirect writes to a sandbox directory ────────────────────────

export function createSandboxRedirectHook(sandboxRoot: string): HookCallback {
  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};
    if (input.tool_name !== "Write" && input.tool_name !== "Edit") return {};

    const filePath = getToolInputFilePath(input);
    if (!filePath) return {};

    // Already inside sandbox — allow unchanged
    if (filePath.startsWith(sandboxRoot)) return {};

    const sandboxedPath = path.join(sandboxRoot, path.basename(filePath));

    return {
      hookSpecificOutput: {
        hookEventName: input.hook_event_name,
        permissionDecision: "allow",
        updatedInput: {
          ...(input.tool_input as Record<string, unknown>),
          file_path: sandboxedPath,
        },
      },
    };
  };
}

// ── Pattern 2: Strip dangerous flags from Bash commands ──────────────────────

const DANGEROUS_FLAGS = ["--no-preserve-root", "--force", "-rf /", "-rf ~"];

export const stripDangerousFlagsHook: HookCallback = async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
  if (signal.aborted) return {};
  if (!isPreToolUseInput(input)) return {};
  if (input.tool_name !== "Bash") return {};

  const toolInput = input.tool_input as Record<string, unknown>;
  let command = typeof toolInput.command === "string" ? toolInput.command : "";

  let modified = false;
  for (const flag of DANGEROUS_FLAGS) {
    if (command.includes(flag)) {
      command = command.replaceAll(flag, "");
      modified = true;
    }
  }

  if (!modified) return {};

  return {
    hookSpecificOutput: {
      hookEventName: input.hook_event_name,
      permissionDecision: "allow",
      updatedInput: {
        ...toolInput,
        command: command.trim(),
      },
    },
  };
};

// ── Pattern 3: Inject env variables into Bash commands ───────────────────────

export function createEnvInjectorHook(envVars: Record<string, string>): HookCallback {
  const envPrefix = Object.entries(envVars)
    .map(([k, v]) => `${k}="${v}"`)
    .join(" ");

  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};
    if (input.tool_name !== "Bash") return {};

    const toolInput = input.tool_input as Record<string, unknown>;
    const command = typeof toolInput.command === "string" ? toolInput.command : "";
    if (!command) return {};

    return {
      hookSpecificOutput: {
        hookEventName: input.hook_event_name,
        permissionDecision: "allow",
        updatedInput: {
          ...toolInput,
          command: `${envPrefix} ${command}`,
        },
      },
    };
  };
}

// ── Usage ─────────────────────────────────────────────────────────────────────
//
// const sandboxHook = createSandboxRedirectHook("/tmp/agent-sandbox");
// const envHook = createEnvInjectorHook({ NODE_ENV: "test", CI: "true" });
//
// hooks: {
//   PreToolUse: [
//     { matcher: "Write|Edit", hooks: [sandboxHook] },
//     { matcher: "Bash",       hooks: [stripDangerousFlagsHook, envHook] },
//   ],
// }
