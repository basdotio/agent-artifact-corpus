/**
 * Env Protection Hook (PreToolUse on Read)
 *
 * Blocks agent from reading .env files to prevent secret leakage.
 * Pattern: simple filename guard, returns deny with reason.
 */

import path from "node:path";

import type { HookCallback, HookJSONOutput } from "../types";
import { getToolInputFilePath, isPreToolUseInput } from "../types";

export const envProtectionHook: HookCallback = async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
  if (signal.aborted) return {};

  if (!isPreToolUseInput(input)) return {};

  const filePath = getToolInputFilePath(input);
  if (!filePath) return {};

  if (!path.basename(filePath).startsWith(".env")) return {};

  return {
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "Reading .env files is not allowed — they may contain secrets",
    },
  };
};
