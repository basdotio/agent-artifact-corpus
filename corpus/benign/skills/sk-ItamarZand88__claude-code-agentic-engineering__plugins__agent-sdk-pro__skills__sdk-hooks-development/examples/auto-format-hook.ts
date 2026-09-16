/**
 * Auto-Format Hook (PostToolUse on Write|Edit)
 *
 * Runs Prettier on TypeScript/JavaScript files after the agent edits them.
 * Non-blocking: runs in the background and does NOT inject additionalContext,
 * since formatting is cosmetic and shouldn't consume Claude's attention.
 *
 * Factory pattern: returns null if Prettier binary is not installed.
 */

import path from "node:path";
import { existsSync } from "node:fs";
import { execSync } from "node:child_process";

import type { HookCallback, HookJSONOutput } from "../types";
import { getToolInputFilePath, isPostToolUseInput } from "../types";

const FORMATTABLE_EXTENSIONS = new Set([".ts", ".tsx", ".js", ".jsx", ".json", ".md"]);

export function createAutoFormatHook(workingDirectory: string): HookCallback | null {
  // Prefer local Prettier for version consistency
  const localPrettier = path.join(workingDirectory, "node_modules", ".bin", "prettier");
  const prettierBin = existsSync(localPrettier) ? localPrettier : null;

  if (!prettierBin) return null;  // graceful disable if Prettier not installed

  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPostToolUseInput(input)) return {};

    const filePath = getToolInputFilePath(input);
    if (!filePath) return {};

    const ext = path.extname(filePath).toLowerCase();
    if (!FORMATTABLE_EXTENSIONS.has(ext)) return {};
    if (!existsSync(filePath)) return {};

    try {
      // Run synchronously but swallow all output — formatting is cosmetic.
      // We do NOT inject additionalContext: no point telling Claude about formatting.
      execSync(`"${prettierBin}" --write "${filePath}"`, {
        cwd: workingDirectory,
        stdio: "ignore",
        timeout: 10_000,
      });
    } catch {
      // Prettier failed (parse error, binary issue) — silently skip.
      // Do not block Claude over a formatter failure.
    }

    return {};  // never inject context — formatting is invisible to Claude
  };
}

// ── Usage ─────────────────────────────────────────────────────────────────────
//
// const autoFormatHook = createAutoFormatHook(params.workingDirectory);
//
// hooks: {
//   PostToolUse: [
//     { matcher: "Write|Edit", hooks: [
//         typecheckHook,         // inject errors (Claude sees these)
//         lintFixHook,           // inject remaining lint errors (Claude sees these)
//         ...(autoFormatHook ? [autoFormatHook] : []),  // silent cosmetic formatting
//       ]
//     },
//   ],
// }
//
// Register AFTER typecheck/lint hooks so formatting runs last (no point
// formatting a file that still has errors Claude needs to fix).
