/**
 * Goal execution modes and structured constraints.
 * Constraints can only tighten DSH sandbox / approval, never raise them.
 */
import { classifyCommand, type ActionKind, type GoalFacts, type ToolFact } from './goal-facts.js';

export type ExecutionMode = 'standard' | 'minimal' | 'strict';

export type ActionClass =
  | 'filesystem.read'
  | 'filesystem.write'
  | 'filesystem.scan'
  | 'process.exec'
  | 'process.spawn'
  | 'git.read'
  | 'git.mutate'
  | 'npm.publish'
  | 'github.release'
  | 'network'
  | 'credentials.metadata'
  | 'workspace.read'
  | 'workspace.write'
  | 'temp.read'
  | 'temp.write'
  | 'external_path.read'
  | 'external_path.write';

export const ACTION_CLASSES: readonly ActionClass[] = [
  'filesystem.read',
  'filesystem.write',
  'filesystem.scan',
  'process.exec',
  'process.spawn',
  'git.read',
  'git.mutate',
  'npm.publish',
  'github.release',
  'network',
  'credentials.metadata',
  'workspace.read',
  'workspace.write',
  'temp.read',
  'temp.write',
  'external_path.read',
  'external_path.write',
];

export interface GoalConstraints {
  read_only?: boolean;
  allow_workspace_scan?: boolean;
  max_changed_files?: number;
  allowed_actions?: ActionClass[];
  forbidden_actions?: ActionClass[];
}

export interface ConstraintDecision {
  allow: boolean;
  reason?: string;
  action_class?: ActionClass;
  kind?: ActionKind;
}

const WRITE_TOOL_NAMES = new Set([
  'write', 'edit', 'str_replace', 'insert', 'replace', 'apply_patch', 'str-replace-editor',
  'rename', 'move', 'delete', 'rm', 'cp', 'mv',
]);

const SCAN_TOOL_NAMES = new Set([
  'glob', 'grep', 'rg', 'find', 'ls', 'tree', 'du', 'fd',
]);

const READ_TOOL_NAMES = new Set([
  'read', 'cat', 'head', 'tail', 'type',
]);

const NETWORK_TOOL_NAMES = new Set([
  'web_fetch', 'web_search', 'fetch', 'curl', 'wget',
]);

const DESTRUCTIVE_KINDS: readonly ActionKind[] = ['git_push', 'git_tag', 'npm_publish', 'github_release'];

const SCAN_COMMAND = /(?:Get-ChildItem|gci|dir|Get-FileHash|Get-ChildItem)\b[\s\S]*?(?:-Recurse|\/s\b)|(?:\bfind\s+(?:\.|\/|\w:\\)|\bfind\s+-)|(?:\bGet-ChildItem\b(?![\s\S]{0,80}-File\b))/i;
const RECURSIVE_LIST = /(?:Get-ChildItem|gci)\b/i;
const RECURSE_FLAG = /(?:-Recurse|-r\b|\/s\b|--recursive)/i;
const HASH_TREE = /Get-FileHash\b[\s\S]*-Recurse|\bhash\b[\s\S]*workspace/i;

const GIT_READ_COMMAND = /\bgit\s+(?:status|diff|log|show|rev-parse|ls-remote|describe|remote|config\s+--get|cat-file|branch(?!\s+-[dD]))\b/i;
const GIT_MUTATE_COMMAND = /\bgit\s+(?:add|commit|tag(?!\s+-[l\b])|push|reset|checkout\s+-b|merge|rebase|revert|worktree\s+add|branch\s+-[dD])\b/i;
const SHELL_CONTROL = /(?:&&|\|\||[;&|<>`\r\n]|\$\(|%[^%\r\n]+%|![^!\r\n]+!)/;
const TEST_COMMAND = /^(?:npm(?:\.cmd)?\s+(?:test|run\s+test)|pnpm(?:\.cmd)?\s+(?:test|run\s+test)|yarn(?:\.cmd)?\s+(?:test|run\s+test)|node(?:\.exe)?\s+--test|(?:npx(?:\.cmd)?\s+)?(?:jest|vitest|mocha)(?:\.cmd)?)(?:\s+.*)?$/i;
const BUILD_COMMAND = /^(?:npm(?:\.cmd)?\s+run\s+build|pnpm(?:\.cmd)?\s+(?:build|run\s+build)|yarn(?:\.cmd)?\s+(?:build|run\s+build)|(?:npx(?:\.cmd)?\s+)?(?:tsc|esbuild|webpack)(?:\.cmd)?|(?:npx(?:\.cmd)?\s+)?vite(?:\.cmd)?\s+build)(?:\s+.*)?$/i;

function isCompleteKnownCommand(command: string, pattern: RegExp): boolean {
  const trimmed = command.trim();
  return trimmed !== '' && !hasShellControlOperator(trimmed) && pattern.test(trimmed);
}

export function hasShellControlOperator(command: string): boolean {
  return SHELL_CONTROL.test(command);
}

/** True only when the complete shell payload is one recognized test command. */
export function isCompleteTestCommand(command: string): boolean {
  return isCompleteKnownCommand(command, TEST_COMMAND);
}

/** True only when the complete shell payload is one recognized build command. */
export function isCompleteBuildCommand(command: string): boolean {
  return isCompleteKnownCommand(command, BUILD_COMMAND);
}

export function parseExecutionMode(value: unknown): ExecutionMode {
  if (value === 'minimal' || value === 'strict' || value === 'standard') return value;
  return 'standard';
}

export function defaultConstraintsForMode(mode: ExecutionMode): GoalConstraints {
  if (mode === 'minimal') {
    return { allow_workspace_scan: false, max_changed_files: 0 };
  }
  return {};
}

/** Later values may only tighten. An omitted field does not relax an earlier one. */
export function mergeConstraints(base: GoalConstraints, extra?: GoalConstraints): GoalConstraints {
  if (extra === undefined) return { ...base };
  const allowed = intersectOptional(base.allowed_actions, extra.allowed_actions);
  const forbidden = unionOptional(base.forbidden_actions, extra.forbidden_actions);
  const maxA = base.max_changed_files;
  const maxB = extra.max_changed_files;
  let max_changed_files: number | undefined;
  if (maxA !== undefined && maxB !== undefined) max_changed_files = Math.min(maxA, maxB);
  else max_changed_files = maxB ?? maxA;
  return {
    ...(base.read_only === true || extra.read_only === true ? { read_only: true } : {}),
    ...(base.allow_workspace_scan === false || extra.allow_workspace_scan === false
      ? { allow_workspace_scan: false }
      : extra.allow_workspace_scan === true || base.allow_workspace_scan === true
        ? { allow_workspace_scan: true }
        : {}),
    ...(max_changed_files === undefined ? {} : { max_changed_files }),
    ...(allowed === undefined ? {} : { allowed_actions: allowed }),
    ...(forbidden === undefined ? {} : { forbidden_actions: forbidden }),
  };
}

function intersectOptional(a?: ActionClass[], b?: ActionClass[]): ActionClass[] | undefined {
  if (a === undefined && b === undefined) return undefined;
  if (a === undefined) return b === undefined ? undefined : uniqueClasses(b);
  if (b === undefined) return uniqueClasses(a);
  const keep = new Set(b);
  return uniqueClasses(a.filter((item) => keep.has(item)));
}

function unionOptional(a?: ActionClass[], b?: ActionClass[]): ActionClass[] | undefined {
  if (a === undefined && b === undefined) return undefined;
  return uniqueClasses([...(a ?? []), ...(b ?? [])]);
}

function uniqueClasses(values: ActionClass[]): ActionClass[] {
  return [...new Set(values)];
}

export function isWorkspaceScanCommand(command: string): boolean {
  if (HASH_TREE.test(command)) return true;
  if (SCAN_COMMAND.test(command)) return true;
  if (RECURSIVE_LIST.test(command) && RECURSE_FLAG.test(command)) return true;
  return false;
}

export function isWriteCommand(command: string): boolean {
  if (/\b(?:Set-Content|Out-File|Add-Content|New-Item|Remove-Item|Move-Item|Copy-Item|ren(?:ame)?|del|rmdir|mkdir|ni)\b/i.test(command)) {
    return true;
  }
  if (/\b(?:sed\s+-i|tee\b|rm\s|mv\s|cp\s)/i.test(command)) return true;
  const kinds = classifyCommand(command);
  return kinds.includes('git_worktree_add');
}

export function classesForTool(toolName: string, command?: string): ActionClass[] {
  const name = toolName.toLowerCase();
  const out = new Set<ActionClass>();
  if (WRITE_TOOL_NAMES.has(name)) out.add('filesystem.write');
  if (SCAN_TOOL_NAMES.has(name)) out.add('filesystem.scan');
  if (READ_TOOL_NAMES.has(name)) out.add('filesystem.read');
  if (NETWORK_TOOL_NAMES.has(name)) out.add('network');
  if (name === 'bash' || name === 'shell' || name === 'powershell' || name === 'pwsh' || name === 'cmd') {
    out.add('process.exec');
  }
  if (command !== undefined && command.trim() !== '') {
    if (isWorkspaceScanCommand(command)) out.add('filesystem.scan');
    if (isWriteCommand(command)) out.add('filesystem.write');
    if (isCompleteTestCommand(command)) out.add('process.spawn');
    if (GIT_READ_COMMAND.test(command)) out.add('git.read');
    if (GIT_MUTATE_COMMAND.test(command)) out.add('git.mutate');
    for (const kind of classifyCommand(command)) {
      if (kind === 'git_push' || kind === 'git_tag' || kind === 'git_worktree_add') out.add('git.mutate');
      if (kind === 'npm_publish' || kind === 'npm_pack') out.add('npm.publish');
      if (kind === 'github_release') out.add('github.release');
    }
  }
  return [...out];
}

export function kindForTool(command?: string): ActionKind | undefined {
  if (command === undefined || command.trim() === '') return undefined;
  return classifyCommand(command).find((kind) => kind !== 'unknown');
}

export interface EvaluateInput {
  constraints: GoalConstraints;
  completedKinds?: Iterable<ActionKind>;
  changedFileCount?: number;
  toolName: string;
  command?: string;
}

/**
 * Decide whether a tool call is allowed under Goal constraints.
 * Fail closed on violation. Missing constraints allow (DSH policy still applies).
 */
export function evaluateConstraint(input: EvaluateInput): ConstraintDecision {
  const classes = classesForTool(input.toolName, input.command);
  const kind = kindForTool(input.command);
  const completed = new Set(input.completedKinds ?? []);
  const constraints = input.constraints;

  if (kind !== undefined && DESTRUCTIVE_KINDS.includes(kind) && completed.has(kind)) {
    return { allow: false, reason: 'no_destructive_replay', action_class: classForKind(kind), kind };
  }

  if (constraints.read_only === true && classes.includes('filesystem.write')) {
    return { allow: false, reason: 'read_only', action_class: 'filesystem.write', ...(kind === undefined ? {} : { kind }) };
  }

  if (constraints.allow_workspace_scan === false && classes.includes('filesystem.scan')) {
    return { allow: false, reason: 'workspace_scan_forbidden', action_class: 'filesystem.scan', ...(kind === undefined ? {} : { kind }) };
  }

  if (
    constraints.max_changed_files !== undefined
    && classes.includes('filesystem.write')
    && (input.changedFileCount ?? 0) >= constraints.max_changed_files
  ) {
    return {
      allow: false,
      reason: 'max_changed_files',
      action_class: 'filesystem.write',
      ...(kind === undefined ? {} : { kind }),
    };
  }

  const forbidden = new Set(constraints.forbidden_actions ?? []);
  for (const action of classes) {
    if (forbidden.has(action)) {
      return { allow: false, reason: 'forbidden_action', action_class: action, ...(kind === undefined ? {} : { kind }) };
    }
  }

  const allowed = constraints.allowed_actions;
  if (allowed !== undefined && allowed.length > 0) {
    const allowSet = new Set(allowed);
    // Every classified class must be in the allow-list. process.exec alone
    // cannot sneak a scan/write through.
    if (!classes.every((action) => allowSet.has(action))) {
      const blocked = classes.find((action) => !allowSet.has(action));
      return {
        allow: false,
        reason: 'action_not_allowed',
        ...(blocked === undefined ? {} : { action_class: blocked }),
        ...(kind === undefined ? {} : { kind }),
      };
    }
  }

  return { allow: true, ...(classes[0] === undefined ? {} : { action_class: classes[0] }), ...(kind === undefined ? {} : { kind }) };
}

function classForKind(kind: ActionKind): ActionClass | undefined {
  if (kind === 'git_push' || kind === 'git_tag' || kind === 'git_worktree_add') return 'git.mutate';
  if (kind === 'npm_publish' || kind === 'npm_pack') return 'npm.publish';
  if (kind === 'github_release') return 'github.release';
  return undefined;
}

export function countWorkspaceScans(facts: GoalFacts): number {
  let count = 0;
  for (const fact of facts.tools) {
    if (classesForTool(fact.name, fact.command).includes('filesystem.scan')) count += 1;
  }
  return count;
}

export function findConstraintViolation(
  facts: GoalFacts,
  constraints: GoalConstraints,
  completedBefore?: Iterable<ActionKind>,
  changedFileCount = 0,
): { fact: ToolFact; decision: ConstraintDecision } | undefined {
  const completed = new Set(completedBefore ?? []);
  for (const fact of facts.tools) {
    const decision = evaluateConstraint({
      constraints,
      completedKinds: completed,
      changedFileCount,
      toolName: fact.name,
      command: fact.command,
    });
    if (!decision.allow && fact.ok) {
      return { fact, decision };
    }
    if (fact.ok) {
      for (const kind of fact.kinds) {
        if (kind !== 'unknown') completed.add(kind);
      }
    }
  }
  return undefined;
}

export function parseConstraints(value: unknown): GoalConstraints {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return {};
  const rec = value as Record<string, unknown>;
  const out: GoalConstraints = {};
  if (rec.read_only === true) out.read_only = true;
  if (rec.allow_workspace_scan === false) out.allow_workspace_scan = false;
  if (rec.allow_workspace_scan === true) out.allow_workspace_scan = true;
  if (typeof rec.max_changed_files === 'number' && Number.isFinite(rec.max_changed_files)) {
    out.max_changed_files = Math.max(0, Math.trunc(rec.max_changed_files));
  }
  const allowed = parseClassList(rec.allowed_actions);
  const forbidden = parseClassList(rec.forbidden_actions);
  if (allowed !== undefined) out.allowed_actions = allowed;
  if (forbidden !== undefined) out.forbidden_actions = forbidden;
  return out;
}

function parseClassList(value: unknown): ActionClass[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const out: ActionClass[] = [];
  for (const item of value) {
    if (typeof item === 'string' && (ACTION_CLASSES as readonly string[]).includes(item)) {
      out.push(item as ActionClass);
    }
  }
  return out;
}

export function findPostHocViolation(
  facts: GoalFacts,
  constraints: GoalConstraints,
): { step: string; reason: string } | undefined {
  const found = findConstraintViolation(facts, constraints, []);
  if (found === undefined) return undefined;
  // Replay is enforced on later approvals, not on the original successful run
  // (a tag create + tag push in one turn is two git_tag facts, not a replay).
  if (found.decision.reason === 'no_destructive_replay') return undefined;
  return {
    step: found.fact.command ?? found.fact.name,
    reason: found.decision.reason ?? 'constraint_rejected',
  };
}
