/**
 * Execution Idempotency & Evidence Cache.
 * Prevents redundant expensive/destructive actions (repeated full test suites,
 * duplicate commits, duplicate npm publishes, duplicate github releases).
 */
import { createHash, randomUUID } from 'node:crypto';
import { hasShellControlOperator, isCompleteBuildCommand, isCompleteTestCommand } from './goal-constraints.js';
import { normalizePath } from './paths.js';

export interface ExecutionEvidence {
  evidenceId: string;
  fingerprint: string;
  kind: string;
  timestamp: number;
  status: 'passed' | 'applied' | 'verified';
  summary?: string;
  details?: Record<string, unknown>;
  sessionIds?: string[];
  workspacePath?: string;
}

export interface IdempotencyCheckResult {
  isIdempotent: boolean;
  code: 'SKIPPED_ALREADY_VERIFIED' | 'SKIPPED_ALREADY_APPLIED';
  evidenceId: string;
  message: string;
  details?: Record<string, unknown>;
}

/** High-cost / side-effecting step kind used as the idempotency cache key. */
export function idempotencyKindFor(toolName: string, command?: string): string | undefined {
  const cmd = command ?? '';
  if (hasShellControlOperator(cmd)) return undefined;
  if (/\bnpm\s+publish\b/i.test(cmd) || toolName === 'npm.publish') return 'npm_publish';
  if (/\bgh\s+release\b/i.test(cmd) || toolName === 'github.release') return 'github_release';
  if (/\bgit\s+push\b/i.test(cmd)) return 'git_push';
  if (isCompleteTestCommand(cmd)) return 'test';
  if (isCompleteBuildCommand(cmd)) return 'build';
  return undefined;
}

export function isVerifiedKind(kind: string): boolean {
  return kind === 'test' || kind === 'build';
}

export const DEFAULT_EVIDENCE_CACHE_CAP = 1024;

export class ExecutionIdempotencyManager {
  private readonly evidenceCache = new Map<string, ExecutionEvidence>(); // fingerprint -> evidence
  private readonly cap: number;

  constructor(cap = DEFAULT_EVIDENCE_CACHE_CAP) {
    this.cap = cap;
  }

  /**
   * Generate a stable execution fingerprint for an operation.
   */
  computeFingerprint(input: {
    kind: string;
    command?: string;
    workspacePath: string;
    headSha?: string;
    extra?: Record<string, unknown>;
  }): string {
    const normalizedCmd = (input.command ?? '').trim().replace(/\s+/g, ' ');
    const normalizedWp = normalizePath(input.workspacePath);
    const payload = JSON.stringify({
      kind: input.kind,
      cmd: normalizedCmd,
      wp: normalizedWp,
      head: input.headSha ?? '',
      extra: input.extra ?? {},
    });
    return createHash('sha256').update(payload).digest('hex');
  }

  /**
   * Record a verified successful execution into the idempotency cache.
   */
  recordSuccess(
    fingerprint: string,
    input: {
      kind: string;
      status?: 'passed' | 'applied' | 'verified';
      summary?: string;
      details?: Record<string, unknown>;
      sessionId?: string;
      workspacePath?: string;
    },
  ): ExecutionEvidence {
    const evidenceId = `evidence-${randomUUID().slice(0, 8)}`;
    const record: ExecutionEvidence = {
      evidenceId,
      fingerprint,
      kind: input.kind,
      timestamp: Date.now(),
      status: input.status ?? 'passed',
      summary: input.summary,
      details: input.details,
      ...(input.sessionId === undefined ? {} : { sessionIds: [input.sessionId] }),
      ...(input.workspacePath === undefined ? {} : { workspacePath: input.workspacePath }),
    };
    if (this.evidenceCache.has(fingerprint)) {
      this.evidenceCache.delete(fingerprint);
    }
    this.evidenceCache.set(fingerprint, record);
    while (this.evidenceCache.size > this.cap) {
      const oldestKey = this.evidenceCache.keys().next().value;
      if (oldestKey === undefined) break;
      this.evidenceCache.delete(oldestKey);
    }
    return record;
  }

  /**
   * Check if an identical operation has already succeeded with valid evidence.
   */
  check(
    fingerprint: string,
    scope?: { sessionId?: string; workspacePath?: string },
  ): IdempotencyCheckResult | null {
    const existing = this.evidenceCache.get(fingerprint);
    if (existing === undefined) return null;

    if (scope?.sessionId !== undefined && !(existing.sessionIds ?? []).includes(scope.sessionId)) {
      existing.sessionIds = [...(existing.sessionIds ?? []), scope.sessionId];
    }
    if (existing.workspacePath === undefined && scope?.workspacePath !== undefined) {
      existing.workspacePath = scope.workspacePath;
    }

    const isTest = isVerifiedKind(existing.kind);
    const code = isTest ? 'SKIPPED_ALREADY_VERIFIED' : 'SKIPPED_ALREADY_APPLIED';
    const message = isTest
      ? `Step was already verified and passed (evidence: ${existing.evidenceId}). Skipping duplicate execution.`
      : `Step was already successfully applied (evidence: ${existing.evidenceId}). Skipping duplicate execution.`;

    return {
      isIdempotent: true,
      code,
      evidenceId: existing.evidenceId,
      message,
      details: existing.details,
    };
  }

  /** Drop cached evidence for a kind so an explicit rerun can execute again. */
  invalidateKind(kind: string): number {
    let removed = 0;
    for (const [fingerprint, evidence] of [...this.evidenceCache.entries()]) {
      if (evidence.kind === kind) {
        this.evidenceCache.delete(fingerprint);
        removed += 1;
      }
    }
    return removed;
  }

  listEvidence(filter?: { sessionId?: string; workspacePath?: string }): ExecutionEvidence[] {
    return [...this.evidenceCache.values()].filter((evidence) => {
      if (filter?.sessionId !== undefined && !(evidence.sessionIds ?? []).includes(filter.sessionId)) return false;
      if (
        filter?.workspacePath !== undefined
        && (evidence.workspacePath === undefined
          || normalizePath(evidence.workspacePath) !== normalizePath(filter.workspacePath))
      ) return false;
      return true;
    });
  }

  clear(): void {
    this.evidenceCache.clear();
  }
}
