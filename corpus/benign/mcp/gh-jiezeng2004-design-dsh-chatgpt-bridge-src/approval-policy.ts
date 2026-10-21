/**
 * Approval Policy v2: Risk-tiered auto-approval, capability grants,
 * and guaranteed reachable terminal states.
 */
import {
  classesForTool,
  hasShellControlOperator,
  isCompleteBuildCommand,
  isCompleteTestCommand,
  type ActionClass,
} from './goal-constraints.js';

export type RiskLevel = 'L0' | 'L1' | 'L2' | 'L3';
export type ApprovalDecision = 'auto_approve' | 'require_human' | 'deny';

export interface UserApprovalPolicy {
  read?: 'auto' | 'ask';
  test?: 'auto' | 'ask';
  build?: 'auto' | 'ask';
  workspaceWrite?: 'auto' | 'ask';
  localCommit?: 'auto' | 'ask';
  externalWrite?: 'auto' | 'ask';
  gitPush?: 'auto' | 'ask';
  npmPublish?: 'auto' | 'ask';
  githubRelease?: 'auto' | 'ask';
  secrets?: 'deny' | 'ask';
  dangerFullAccess?: 'deny' | 'ask';
}

export const DEFAULT_APPROVAL_POLICY: UserApprovalPolicy = {
  read: 'auto',
  test: 'auto',
  build: 'auto',
  workspaceWrite: 'auto',
  localCommit: 'auto',
  externalWrite: 'ask',
  gitPush: 'ask',
  npmPublish: 'ask',
  githubRelease: 'ask',
  secrets: 'deny',
  dangerFullAccess: 'ask',
};

const FORCE_PUSH = /\bgit\s+push\b[\s\S]*?(?:--force|-f\b|--force-with-lease)/i;
const NPM_UNPUBLISH = /\bnpm\s+unpublish\b/i;
const RAW_SECRET_ACCESS = /(?:\.env|\.credentials|apiKey|secret|id_rsa|private_key)\b/i;
const LOCAL_COMMIT_CMD = /\bgit\s+(?:add|commit)\b/i;
const GIT_PUSH_CMD = /\bgit\s+push\b/i;
const NPM_PUBLISH_CMD = /\bnpm\s+publish\b/i;
const GH_RELEASE_CMD = /\bgh\s+release\b/i;
export interface ApprovalEvaluation {
  level: RiskLevel;
  capability: ActionClass | 'danger-full-access' | 'system.destructive';
  decision: ApprovalDecision;
  reason: string;
}

export function evaluateApproval(
  toolName: string,
  command?: string,
  policy: UserApprovalPolicy = DEFAULT_APPROVAL_POLICY,
  context: { externalWrite?: boolean } = {},
): ApprovalEvaluation {
  const mergedPolicy: UserApprovalPolicy = { ...DEFAULT_APPROVAL_POLICY, ...policy };
  const cmd = command ?? '';
  const classes = classesForTool(toolName, command);

  // --- L3: Highest Risk / Destructive / Sensitive (Never auto-approve) ---
  if (FORCE_PUSH.test(cmd) || NPM_UNPUBLISH.test(cmd)) {
    return {
      level: 'L3',
      capability: 'system.destructive',
      decision: 'require_human',
      reason: 'Destructive / force operation requires explicit human confirmation',
    };
  }

  if (RAW_SECRET_ACCESS.test(cmd) || RAW_SECRET_ACCESS.test(toolName)) {
    if (mergedPolicy.secrets === 'deny') {
      return {
        level: 'L3',
        capability: 'credentials.metadata',
        decision: 'deny',
        reason: 'Raw secret file access is denied by policy',
      };
    }
    return {
      level: 'L3',
      capability: 'credentials.metadata',
      decision: 'require_human',
      reason: 'Raw secret access requires explicit human confirmation',
    };
  }

  if (toolName.toLowerCase() === 'danger-full-access') {
    return {
      level: 'L3',
      capability: 'danger-full-access',
      decision: mergedPolicy.dangerFullAccess === 'deny' ? 'deny' : 'require_human',
      reason: 'Broad danger-full-access grant requires explicit human confirmation',
    };
  }

  // A shell payload with control operators is multiple operations. Never let
  // one recognized prefix grant approval to the rest of the payload.
  if (cmd !== '' && hasShellControlOperator(cmd)) {
    return {
      level: 'L1',
      capability: 'process.exec',
      decision: 'require_human',
      reason: 'Compound shell command requires explicit human confirmation',
    };
  }

  // --- L2: Manual Approval Required by default (Publishing / Remote / Release) ---
  if (GH_RELEASE_CMD.test(cmd) || classes.includes('github.release')) {
    const dec = mergedPolicy.githubRelease === 'auto' ? 'auto_approve' : 'require_human';
    return {
      level: 'L2',
      capability: 'github.release',
      decision: dec,
      reason: 'GitHub Release operation',
    };
  }

  if (NPM_PUBLISH_CMD.test(cmd) || classes.includes('npm.publish')) {
    const dec = mergedPolicy.npmPublish === 'auto' ? 'auto_approve' : 'require_human';
    return {
      level: 'L2',
      capability: 'npm.publish',
      decision: dec,
      reason: 'NPM package publish operation',
    };
  }

  if (GIT_PUSH_CMD.test(cmd)) {
    const dec = mergedPolicy.gitPush === 'auto' ? 'auto_approve' : 'require_human';
    return {
      level: 'L2',
      capability: 'git.mutate',
      decision: dec,
      reason: 'Remote git push operation',
    };
  }

  // --- L1: Local state changes (Workspace edits, commits, build) ---
  if (LOCAL_COMMIT_CMD.test(cmd)) {
    const dec = mergedPolicy.localCommit === 'auto' ? 'auto_approve' : 'require_human';
    return {
      level: 'L1',
      capability: 'git.mutate',
      decision: dec,
      reason: 'Local git commit operation',
    };
  }

  if (classes.includes('filesystem.write')) {
    if (context.externalWrite === true) {
      const dec = mergedPolicy.externalWrite === 'auto' ? 'auto_approve' : 'require_human';
      return {
        level: 'L1',
        capability: 'external_path.write',
        decision: dec,
        reason: 'Write outside the managed workspace',
      };
    }
    const dec = mergedPolicy.workspaceWrite === 'auto' ? 'auto_approve' : 'require_human';
    return {
      level: 'L1',
      capability: 'filesystem.write',
      decision: dec,
      reason: 'Workspace file write operation',
    };
  }

  // --- L0: Low Risk / Read-Only / Automated test (Default Auto-Approve) ---
  if (isCompleteTestCommand(cmd)) {
    const dec = mergedPolicy.test === 'ask' ? 'require_human' : 'auto_approve';
    return {
      level: 'L0',
      capability: 'process.spawn',
      decision: dec,
      reason: 'Automated test suite execution (process spawn)',
    };
  }

  if (isCompleteBuildCommand(cmd)) {
    const dec = mergedPolicy.build === 'ask' ? 'require_human' : 'auto_approve';
    return {
      level: 'L0',
      capability: 'process.exec',
      decision: dec,
      reason: 'Build step execution',
    };
  }

  if (classes.includes('git.read')) {
    return {
      level: 'L0',
      capability: 'git.read',
      decision: mergedPolicy.read === 'ask' ? 'require_human' : 'auto_approve',
      reason: 'Read-only git query (status/log/diff/rev-parse)',
    };
  }

  if (classes.includes('filesystem.read') || classes.includes('filesystem.scan') || classes.includes('temp.read') || classes.includes('temp.write')) {
    return {
      level: 'L0',
      capability: 'filesystem.read',
      decision: mergedPolicy.read === 'ask' ? 'require_human' : 'auto_approve',
      reason: 'Read-only or transient temp file operation',
    };
  }

  // Unrecognized operations are not auto-approved: L0 only covers known-safe classes.
  return {
    level: 'L1',
    capability: classes[0] ?? 'process.exec',
    decision: 'require_human',
    reason: 'Unrecognized operation requires confirmation',
  };
}
