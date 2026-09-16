/**
 * Security Blocker Hook (PreToolUse on Bash + Write|Edit)
 *
 * Comprehensive security hook that:
 * - Blocks dangerous Bash commands (rm -rf /, dd, fork bombs, force pushes)
 * - Blocks writes to sensitive files (.env, credentials, SSH keys)
 * - Blocks writes outside the project directory
 * - Detects secret patterns in commands
 *
 * Pattern: large PreToolUse hook with fast-path exits
 */

import path from "node:path";

import type { HookCallback, HookJSONOutput } from "../types";
import { isPreToolUseInput } from "../types";

// ── Bash: Dangerous command patterns ─────────────────────────────────────────

const DANGEROUS_BASH_PATTERNS: ReadonlyArray<string | RegExp> = [
  "rm -rf /",
  "rm -rf ~",
  "rm -rf $HOME",
  "> /dev/sda",
  "dd if=",
  "mkfs",
  ":(){:|:&};:",           // Fork bomb
  "--no-preserve-root",
  "chmod -R 777 /",
  "DROP DATABASE",
  "DROP TABLE",
  /git push.+(-f|--force).+(main|master)/,
  /npm publish|pnpm publish|yarn publish/,
];

// ── Bash: Secret patterns ─────────────────────────────────────────────────────

const SECRET_PATTERNS: ReadonlyArray<RegExp> = [
  /password=/i,
  /secret=/i,
  /api_key=/i,
  /apikey=/i,
  /token=/i,
  /aws_access_key/i,
  /aws_secret/i,
  /private_key/i,
  /sk-[a-zA-Z0-9]{20,}/,  // OpenAI/Anthropic key patterns
];

// ── Write|Edit: Protected file names ─────────────────────────────────────────

const PROTECTED_FILES: ReadonlySet<string> = new Set([
  ".env",
  ".env.local",
  ".env.production",
  ".env.development",
  ".env.staging",
  "credentials.json",
  "serviceAccountKey.json",
  "id_rsa",
  "id_ed25519",
  "id_ecdsa",
  ".npmrc",
  ".pypirc",
  "secrets.yml",
  "secrets.yaml",
]);

function isDangerousCommand(command: string): { blocked: boolean; reason?: string } {
  for (const pattern of DANGEROUS_BASH_PATTERNS) {
    if (typeof pattern === "string") {
      if (command.includes(pattern)) {
        return { blocked: true, reason: `Dangerous pattern: ${pattern}` };
      }
    } else if (pattern.test(command)) {
      return { blocked: true, reason: `Dangerous pattern: ${pattern.source}` };
    }
  }

  for (const secretPattern of SECRET_PATTERNS) {
    if (secretPattern.test(command)) {
      return { blocked: true, reason: `Potential secret in command: ${secretPattern.source}` };
    }
  }

  return { blocked: false };
}

function isProtectedFile(filePath: string): boolean {
  return PROTECTED_FILES.has(path.basename(filePath));
}

function isOutsideProject(filePath: string, projectDir: string): boolean {
  const normalizedFile = path.resolve(filePath);
  const normalizedProject = path.resolve(projectDir);
  const tmpDir = path.resolve("/tmp");

  return (
    !normalizedFile.startsWith(normalizedProject) &&
    !normalizedFile.startsWith(tmpDir)
  );
}

export function createSecurityBlockerHook(projectDir: string): HookCallback {
  return async (input, _toolUseId, { signal }): Promise<HookJSONOutput> => {
    if (signal.aborted) return {};
    if (!isPreToolUseInput(input)) return {};

    const toolName = input.tool_name;
    const toolInput = input.tool_input as Record<string, unknown>;

    // ── Bash: command-level checks ────────────────────────────────────────────
    if (toolName === "Bash") {
      const command = typeof toolInput.command === "string" ? toolInput.command : "";
      const { blocked, reason } = isDangerousCommand(command);

      if (blocked) {
        return {
          hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: `Security: ${reason}`,
          },
        };
      }

      return {};
    }

    // ── Write|Edit: file-level checks ─────────────────────────────────────────
    if (toolName === "Write" || toolName === "Edit") {
      const filePath = typeof toolInput.file_path === "string" ? toolInput.file_path : "";
      if (!filePath) return {};

      if (isProtectedFile(filePath)) {
        return {
          hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: `Security: Cannot modify protected file: ${path.basename(filePath)}`,
          },
        };
      }

      if (isOutsideProject(filePath, projectDir)) {
        return {
          hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: `Security: Cannot write outside project directory. File: ${filePath}, Project: ${projectDir}`,
          },
        };
      }

      return {};
    }

    return {};
  };
}
