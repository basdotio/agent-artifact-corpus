/**
 * Goal, Plan, and Constraints Preflight Validator.
 * Performs static checks before agent startup to detect contradictory goals
 * (e.g., Goal requires editing files, but constraints specify read_only).
 */
import type { ExecutionMode, GoalConstraints, ActionClass } from './goal-constraints.js';

export interface PreflightResult {
  valid: boolean;
  conflicts: string[];
  suggested_constraint_delta?: string[];
}

const WRITE_KEYWORDS = [
  /\b(?:edit|modify|update|create|write|delete|patch|fix|implement|refactor)\b/i,
  /(?:修改|编辑|更新|创建|写入|删除|修复|实现|重构)/,
];

const GIT_MUTATE_KEYWORDS = [
  /\b(?:git\s+commit|git\s+push|git\s+tag|git\s+merge|git\s+reset|create\s+tag|commit\s+changes|push\s+branch)\b/i,
  /(?:提交|推送|打标签|创建标签|创建commit)/,
];

const NPM_PUBLISH_KEYWORDS = [
  /\b(?:npm\s+publish|publish\s+package|publish\s+to\s+npm|release\s+to\s+npm)\b/i,
  /(?:发布到npm|npm发布|发布包)/,
];

const GITHUB_RELEASE_KEYWORDS = [
  /\b(?:gh\s+release|github\s+release|create\s+release)\b/i,
  /(?:创建github\s*release|发布release)/,
];

const NETWORK_KEYWORDS = [
  /\b(?:npm\s+install|pnpm\s+install|yarn\s+add|curl|wget|download|fetch\s+remote|clone)\b/i,
  /(?:安装依赖|下载|拉取远程)/,
];

const EXTERNAL_WRITE_KEYWORDS = [
  /\bexternal(?:_|\s+)path\b/i,
  /\boutside (?:the )?workspace\b/i,
  /workspace\s*外/,
];

function hasIntent(text: string, patterns: RegExp[]): boolean {
  return patterns.some((p) => p.test(text));
}

export function validateGoalPreflight(input: {
  goal: string;
  plan?: string;
  constraints?: GoalConstraints;
  mode?: ExecutionMode;
}): PreflightResult {
  const text = `${input.goal}\n${input.plan ?? ''}`;
  const constraints = input.constraints ?? {};
  const conflicts: string[] = [];
  const suggestedDeltas: string[] = [];

  const forbidden = new Set(constraints.forbidden_actions ?? []);
  const allowed = constraints.allowed_actions !== undefined ? new Set(constraints.allowed_actions) : undefined;

  const isForbidden = (action: ActionClass): boolean => {
    if (forbidden.has(action)) return true;
    if (allowed !== undefined && !allowed.has(action)) return true;
    return false;
  };

  // 1. Check Filesystem Write
  const wantsWrite = hasIntent(text, WRITE_KEYWORDS);
  if (wantsWrite) {
    if (constraints.read_only === true) {
      conflicts.push('Goal requires modifying files or workspace content, but constraints.read_only is true.');
      suggestedDeltas.push('Set constraints.read_only=false');
    }
    if (isForbidden('filesystem.write')) {
      conflicts.push('Goal requires modifying files, but action class "filesystem.write" is forbidden.');
      suggestedDeltas.push('Remove "filesystem.write" from forbidden_actions or add to allowed_actions');
    }
    if (constraints.max_changed_files === 0) {
      conflicts.push('Goal requires modifying files, but constraints.max_changed_files is 0.');
      suggestedDeltas.push('Increase constraints.max_changed_files');
    }
  }

  // 2. Check Git Mutate
  const wantsGitMutate = hasIntent(text, GIT_MUTATE_KEYWORDS);
  if (wantsGitMutate) {
    if (constraints.read_only === true) {
      conflicts.push('Goal requires git commit/tag/push, but constraints.read_only is true.');
      suggestedDeltas.push('Set constraints.read_only=false');
    }
    if (isForbidden('git.mutate')) {
      conflicts.push('Goal requires git commit/tag/push, but action class "git.mutate" is forbidden.');
      suggestedDeltas.push('Remove "git.mutate" from forbidden_actions or add to allowed_actions');
    }
  }

  // 3. Check NPM Publish
  const wantsNpmPublish = hasIntent(text, NPM_PUBLISH_KEYWORDS);
  if (wantsNpmPublish) {
    if (isForbidden('npm.publish')) {
      conflicts.push('Goal requires publishing to npm, but action class "npm.publish" is forbidden.');
      suggestedDeltas.push('Remove "npm.publish" from forbidden_actions or add to allowed_actions');
    }
  }

  // 4. Check GitHub Release
  const wantsGhRelease = hasIntent(text, GITHUB_RELEASE_KEYWORDS);
  if (wantsGhRelease) {
    if (isForbidden('github.release')) {
      conflicts.push('Goal requires creating a GitHub Release, but action class "github.release" is forbidden.');
      suggestedDeltas.push('Remove "github.release" from forbidden_actions or add to allowed_actions');
    }
  }

  // 5. Check Network
  const wantsNetwork = hasIntent(text, NETWORK_KEYWORDS);
  if (wantsNetwork) {
    if (isForbidden('network')) {
      conflicts.push('Goal requires downloading packages or network access, but action class "network" is forbidden.');
      suggestedDeltas.push('Remove "network" from forbidden_actions or add to allowed_actions');
    }
  }

  // 6. Check writes outside the workspace
  if (wantsWrite && hasIntent(text, EXTERNAL_WRITE_KEYWORDS) && isForbidden('external_path.write')) {
    conflicts.push('Goal requires writing outside the workspace, but action class "external_path.write" is forbidden.');
    suggestedDeltas.push('Remove "external_path.write" from forbidden_actions or add to allowed_actions');
  }

  return {
    valid: conflicts.length === 0,
    conflicts,
    ...(suggestedDeltas.length === 0 ? {} : { suggested_constraint_delta: suggestedDeltas }),
  };
}
