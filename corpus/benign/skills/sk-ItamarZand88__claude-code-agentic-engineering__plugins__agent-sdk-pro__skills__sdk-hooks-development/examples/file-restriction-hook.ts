/**
 * File Restriction Hook (PreToolUse on Write|Edit)
 *
 * Factory function: restricts Write/Edit to a single allowed file.
 * Pattern: factory with closure over normalized path.
 */

import path from "node:path";

import type { HookCallback, HookJSONOutput } from "../types";
import { getToolInputFilePath, isPreToolUseInput } from "../types";

export function createFileRestrictionHook(allowedFilePath: string): HookCallback {
  const normalizedAllowed = path.resolve(allowedFilePath);

  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};

    if (!isPreToolUseInput(input)) return {};

    const filePath = getToolInputFilePath(input);
    if (!filePath) return {};

    if (path.resolve(filePath) === normalizedAllowed) return {};

    return {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "deny",
        permissionDecisionReason: `Only the allowed file can be modified: ${allowedFilePath}. Attempted: ${filePath}`,
      },
    };
  };
}
