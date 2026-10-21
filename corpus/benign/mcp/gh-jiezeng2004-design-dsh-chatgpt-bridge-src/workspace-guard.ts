/**
 * Workspace Concurrency Guard: Single mutable session lock, baseline
 * Git HEAD / dirty status snapshot, pre-mutation drift detection, and
 * cross-session operation provenance tracking.
 */
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { stat } from 'node:fs/promises';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { normalizePath } from './paths.js';

const execFileAsync = promisify(execFile);

export interface WorkspaceLockHolder {
  sessionId: string;
  goalId: string;
  workspacePath: string;
  lockedAt: number;
}

export interface WorkspaceBaseline {
  workspacePath: string;
  headSha?: string;
  dirtyFiles: string[];
  /** Hash of tracked diffs plus untracked path metadata at capture time. */
  workspaceFingerprint?: string;
  timestamp: number;
}

export interface MutationRecord {
  sessionId: string;
  goalId: string;
  stepId?: string;
  type: string;
  details?: string;
  timestamp: number;
}

export class WorkspaceConcurrencyGuard {
  private readonly locks = new Map<string, WorkspaceLockHolder>(); // normalizedPath -> lock
  private readonly sessionLocks = new Map<string, string>(); // sessionId -> normalizedPath
  private readonly mutations = new Map<string, MutationRecord[]>(); // normalizedPath -> mutations

  /**
   * Attempt to acquire an exclusive mutable session lock for a workspace.
   * Read-only sessions do not need to acquire this lock.
   */
  acquireMutableLock(
    workspacePath: string,
    sessionId: string,
    goalId: string,
    isExistingHolderActive = true,
    override = false,
  ): { success: boolean; holder?: WorkspaceLockHolder; warning?: string } {
    const key = normalizePath(workspacePath);
    const existing = this.locks.get(key);

    if (existing !== undefined && existing.sessionId !== sessionId) {
      if (!isExistingHolderActive || override) {
        this.sessionLocks.delete(existing.sessionId);
        this.locks.set(key, { sessionId, goalId, workspacePath: key, lockedAt: Date.now() });
        this.sessionLocks.set(sessionId, key);
        return {
          success: true,
          ...(isExistingHolderActive && override ? {
            warning: `Workspace mutable lock overridden. Previous holder: session ${existing.sessionId}, goal ${existing.goalId}`,
          } : {}),
        };
      }
      return { success: false, holder: existing };
    }

    const holder: WorkspaceLockHolder = {
      sessionId,
      goalId,
      workspacePath: key,
      lockedAt: Date.now(),
    };
    this.locks.set(key, holder);
    this.sessionLocks.set(sessionId, key);
    return { success: true, holder };
  }

  /** Release mutable lock held by a session upon completion or cancellation. */
  releaseLock(sessionId: string): boolean {
    const key = this.sessionLocks.get(sessionId);
    if (key === undefined) return false;
    this.sessionLocks.delete(sessionId);
    const holder = this.locks.get(key);
    if (holder?.sessionId === sessionId) {
      this.locks.delete(key);
      return true;
    }
    return false;
  }

  getLock(workspacePath: string): WorkspaceLockHolder | undefined {
    return this.locks.get(normalizePath(workspacePath));
  }

  /** Record a mutating operation (write, commit, tag, publish) for provenance. */
  recordMutation(workspacePath: string, record: Omit<MutationRecord, 'timestamp'>): void {
    const key = normalizePath(workspacePath);
    const list = this.mutations.get(key) ?? [];
    list.push({ ...record, timestamp: Date.now() });
    if (list.length > 100) list.shift();
    this.mutations.set(key, list);
  }

  getLastMutation(workspacePath: string): MutationRecord | undefined {
    const list = this.mutations.get(normalizePath(workspacePath));
    return list === undefined || list.length === 0 ? undefined : list[list.length - 1];
  }

  /** Capture baseline git HEAD SHA and dirty file status at Goal start. */
  async captureBaseline(workspacePath: string): Promise<WorkspaceBaseline> {
    const normalized = normalizePath(workspacePath);
    let headSha: string | undefined;
    let dirtyFiles: string[] = [];
    let statusRaw = '';
    let unstagedDiff = '';
    let stagedDiff = '';
    let untrackedMetadata: string[] = [];

    try {
      const { stdout: headOut } = await execFileAsync('git', ['rev-parse', 'HEAD'], {
        cwd: normalized,
        timeout: 5000,
      });
      headSha = headOut.trim();
    } catch {
      // Not a git repo or git not found
    }

    try {
      const { stdout: statusOut } = await execFileAsync('git', ['status', '--porcelain=v1', '--untracked-files=all'], {
        cwd: normalized,
        timeout: 5000,
        maxBuffer: 32 * 1024 * 1024,
      });
      statusRaw = statusOut;
      dirtyFiles = statusOut
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line.length > 0);
    } catch {
      // ignore
    }

    try {
      const { stdout } = await execFileAsync('git', ['diff', '--no-ext-diff', '--binary', '--'], {
        cwd: normalized,
        timeout: 10000,
        maxBuffer: 32 * 1024 * 1024,
      });
      unstagedDiff = stdout;
    } catch {
      // Status still provides a conservative fallback fingerprint.
    }

    try {
      const { stdout } = await execFileAsync('git', ['diff', '--cached', '--no-ext-diff', '--binary', '--'], {
        cwd: normalized,
        timeout: 10000,
        maxBuffer: 32 * 1024 * 1024,
      });
      stagedDiff = stdout;
    } catch {
      // Status still provides a conservative fallback fingerprint.
    }

    try {
      const { stdout } = await execFileAsync('git', ['ls-files', '--others', '--exclude-standard', '-z'], {
        cwd: normalized,
        timeout: 5000,
        maxBuffer: 8 * 1024 * 1024,
      });
      const untracked = stdout.split('\0').filter((item) => item !== '').sort();
      untrackedMetadata = await Promise.all(untracked.map(async (relativePath) => {
        try {
          const info = await stat(join(normalized, relativePath));
          return `${relativePath}\0${info.size}\0${Math.trunc(info.mtimeMs)}`;
        } catch {
          return `${relativePath}\0missing`;
        }
      }));
    } catch {
      // Status already contains untracked path names.
    }

    const workspaceFingerprint = createHash('sha256')
      .update(statusRaw)
      .update('\0unstaged\0')
      .update(unstagedDiff)
      .update('\0staged\0')
      .update(stagedDiff)
      .update('\0untracked\0')
      .update(untrackedMetadata.join('\0'))
      .digest('hex');

    return {
      workspacePath: normalized,
      headSha,
      dirtyFiles,
      workspaceFingerprint,
      timestamp: Date.now(),
    };
  }

  /** Detect workspace state drift since baseline. */
  async detectDrift(
    workspacePath: string,
    baseline: WorkspaceBaseline,
    currentSessionId: string,
    currentSnapshot?: WorkspaceBaseline,
  ): Promise<{ drifted: boolean; currentSha?: string; details?: string; originatingSessionId?: string }> {
    const normalized = normalizePath(workspacePath);
    try {
      const current = currentSnapshot ?? await this.captureBaseline(normalized);
      const headDrifted = baseline.headSha !== undefined && current.headSha !== baseline.headSha;
      const workspaceDrifted = baseline.workspaceFingerprint !== undefined
        && current.workspaceFingerprint !== baseline.workspaceFingerprint;
      if (headDrifted || workspaceDrifted) {
        const lastMutation = this.getLastMutation(normalized);
        const originating = lastMutation?.sessionId !== currentSessionId ? lastMutation?.sessionId : undefined;
        const changes = [
          ...(headDrifted
            ? [`Git HEAD ${baseline.headSha?.slice(0, 7) ?? 'unknown'} -> ${current.headSha?.slice(0, 7) ?? 'unknown'}`]
            : []),
          ...(workspaceDrifted ? ['working tree/index fingerprint changed'] : []),
        ];
        const details = `Workspace drifted: ${changes.join('; ')}` +
          (originating ? ` (likely from session ${originating})` : '');
        return {
          drifted: true,
          currentSha: current.headSha,
          details,
          originatingSessionId: originating,
        };
      }
    } catch {
      // ignore
    }

    return { drifted: false };
  }
}
