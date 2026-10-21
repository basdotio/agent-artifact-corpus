/**
 * First-class Goal revision, bounded history, and sidecar persistence.
 * Not a second execution engine: DSH session events remain the authority
 * for what actually ran.
 */
import { mkdirSync, readFileSync, writeFileSync, renameSync, rmSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { join } from 'node:path';
import type { ActionKind } from './goal-facts.js';
import { redactValue } from './redact.js';
import {
  defaultConstraintsForMode,
  mergeConstraints,
  parseConstraints,
  parseExecutionMode,
  type ExecutionMode,
  type GoalConstraints,
} from './goal-constraints.js';

export const HISTORY_PERSIST_MAX = 200;
export const HISTORY_WIRE_MAX = 20;
export const REVISION_REASON_MAX = 200;
export const GOAL_CONTROL_CAP = 256;

export type GoalHistoryType =
  | 'goal_created'
  | 'goal_revised'
  | 'goal_resumed'
  | 'step_started'
  | 'step_completed'
  | 'step_blocked'
  | 'step_deferred'
  | 'approval_requested'
  | 'approval_resolved'
  | 'question_requested'
  | 'question_answered'
  | 'constraint_rejected'
  | 'step_skipped'
  | 'goal_completed'
  | 'goal_cancelled';

export interface GoalRevisionSnapshot {
  revision: number;
  previous_revision?: number;
  goal: string;
  plan?: string;
  mode: ExecutionMode;
  revision_reason: string;
  created_at: string;
  constraints: GoalConstraints;
}

export interface GoalHistoryEvent {
  seq: number;
  timestamp: string;
  goal_id: string;
  revision: number;
  type: GoalHistoryType;
  step_id?: string;
  metadata?: Record<string, unknown>;
}

export interface BlockedStepRecord {
  step_id: string;
  reason: string;
  seq: number;
  superseded?: boolean;
}

export interface GoalRecord {
  goal_id: string;
  session_id: string;
  revision: number;
  mode: ExecutionMode;
  constraints: GoalConstraints;
  goal: string;
  plan?: string;
  created_at: string;
  updated_at: string;
  revision_reason?: string;
  revisions: GoalRevisionSnapshot[];
  deferred_step_ids: string[];
  completed_action_kinds: ActionKind[];
  active_blockers?: BlockedStepRecord[];
  superseded_step_ids?: string[];
  history: GoalHistoryEvent[];
  history_seq: number;
}

/** Compact revision row for folded UI / wire payloads. No goal/plan text. */
export interface FoldedRevision {
  revision: number;
  previous_revision?: number;
  revision_reason: string;
  created_at: string;
}

export interface GoalSupervisionView {
  goal_id: string;
  revision: number;
  mode: ExecutionMode;
  card: string;
  revision_history_folded: boolean;
  revision_history: FoldedRevision[];
  previous_revision?: number;
  revisions?: GoalRevisionSnapshot[];
}

export interface CreateGoalInput {
  sessionId: string;
  goal: string;
  plan?: string;
  mode?: ExecutionMode;
  constraints?: GoalConstraints;
  now?: number;
  revisionReason?: string;
}

export interface ReviseGoalInput {
  goal?: string;
  plan?: string;
  mode?: ExecutionMode;
  constraints?: GoalConstraints;
  expectedRevision?: number;
  deferredStepIds?: string[];
  resumeStepIds?: string[];
  completedActionKinds?: ActionKind[];
  revisionReason?: string;
  now?: number;
}

export function isGoalSemanticallyEqual(
  record: GoalRecord,
  goal: string,
  plan?: string,
  mode?: ExecutionMode,
  constraints?: GoalConstraints,
): boolean {
  if (record.goal.trim() !== goal.trim()) return false;
  if ((record.plan ?? '').trim() !== (plan ?? '').trim()) return false;
  if (mode !== undefined && record.mode !== parseExecutionMode(mode)) return false;
  if (constraints !== undefined) {
    const merged = mergeConstraints(defaultConstraintsForMode(record.mode), constraints);
    if (JSON.stringify(record.constraints) !== JSON.stringify(merged)) return false;
  }
  return true;
}

export function pruneBlockers(record: GoalRecord, completedKinds: Iterable<ActionKind>): void {
  if (!record.active_blockers) return;
  const completed = new Set(completedKinds);
  record.active_blockers = record.active_blockers.filter((b) => !completed.has(b.step_id as ActionKind));
}

export interface GoalStoreIo {
  read(sessionId: string): string | undefined;
  write(sessionId: string, json: string): void;
}

function iso(ms: number): string {
  return new Date(ms).toISOString();
}

function clipReason(reason: string | undefined, fallback: string): string {
  const text = (reason ?? fallback).trim();
  if (text === '') return fallback;
  return text.length <= REVISION_REASON_MAX ? text : text.slice(0, REVISION_REASON_MAX);
}

function snapshotOf(record: GoalRecord, reason: string, at: string): GoalRevisionSnapshot {
  return {
    revision: record.revision,
    ...(record.revision > 1 ? { previous_revision: record.revision - 1 } : {}),
    goal: record.goal,
    ...(record.plan === undefined ? {} : { plan: record.plan }),
    mode: record.mode,
    revision_reason: reason,
    created_at: at,
    constraints: { ...record.constraints },
  };
}

function pushHistory(
  record: GoalRecord,
  type: GoalHistoryType,
  at: string,
  extra?: { step_id?: string; metadata?: Record<string, unknown> },
): void {
  record.history_seq += 1;
  const metadata = extra?.metadata === undefined
    ? undefined
    : redactValue(extra.metadata) as Record<string, unknown>;
  const event: GoalHistoryEvent = {
    seq: record.history_seq,
    timestamp: at,
    goal_id: record.goal_id,
    revision: record.revision,
    type,
    ...(extra?.step_id === undefined ? {} : { step_id: extra.step_id }),
    ...(metadata === undefined ? {} : { metadata }),
  };
  record.history.push(event);
  if (record.history.length > HISTORY_PERSIST_MAX) {
    record.history = record.history.slice(record.history.length - HISTORY_PERSIST_MAX);
  }
}

export function createGoalRecord(input: CreateGoalInput): GoalRecord {
  const now = input.now ?? Date.now();
  const at = iso(now);
  const mode = parseExecutionMode(input.mode);
  const constraints = mergeConstraints(defaultConstraintsForMode(mode), input.constraints);
  const reason = clipReason(input.revisionReason, 'goal_created');
  const record: GoalRecord = {
    goal_id: `goal-${input.sessionId}`,
    session_id: input.sessionId,
    revision: 1,
    mode,
    constraints,
    goal: input.goal,
    ...(input.plan === undefined ? {} : { plan: input.plan }),
    created_at: at,
    updated_at: at,
    revision_reason: reason,
    revisions: [],
    deferred_step_ids: [],
    completed_action_kinds: [],
    active_blockers: [],
    superseded_step_ids: [],
    history: [],
    history_seq: 0,
  };
  record.revisions.push(snapshotOf(record, reason, at));
  pushHistory(record, 'goal_created', at, { metadata: { reason, mode } });
  return record;
}

export function applyRevision(record: GoalRecord, input: ReviseGoalInput, type: 'goal_revised' | 'goal_resumed'): GoalRecord {
  if (input.expectedRevision !== undefined && input.expectedRevision !== record.revision) {
    throw new Error(`REVISION_CONFLICT: expected revision ${input.expectedRevision}, but current revision is ${record.revision}`);
  }
  const now = input.now ?? Date.now();
  const at = iso(now);
  const next: GoalRecord = {
    ...record,
    revisions: [...record.revisions],
    deferred_step_ids: [...record.deferred_step_ids],
    completed_action_kinds: [...record.completed_action_kinds],
    active_blockers: record.active_blockers ? [...record.active_blockers] : [],
    superseded_step_ids: record.superseded_step_ids ? [...record.superseded_step_ids] : [],
    history: [...record.history],
    constraints: { ...record.constraints },
  };
  next.revision = record.revision + 1;
  next.updated_at = at;
  if (input.goal !== undefined) next.goal = input.goal;
  if (input.plan !== undefined) next.plan = input.plan;
  if (input.mode !== undefined) {
    next.mode = parseExecutionMode(input.mode);
    next.constraints = mergeConstraints(defaultConstraintsForMode(next.mode), next.constraints);
  }
  if (input.constraints !== undefined) {
    next.constraints = mergeConstraints(next.constraints, input.constraints);
  }
  if (input.completedActionKinds !== undefined) {
    next.completed_action_kinds = uniqueKinds([
      ...next.completed_action_kinds,
      ...input.completedActionKinds,
    ]);
  }
  if (input.deferredStepIds !== undefined && input.deferredStepIds.length > 0) {
    next.deferred_step_ids = uniqueStrings([...next.deferred_step_ids, ...input.deferredStepIds]);
  }
  if (input.resumeStepIds !== undefined) {
    if (input.resumeStepIds.length === 0) {
      next.deferred_step_ids = [];
    } else {
      const resume = new Set(input.resumeStepIds);
      next.deferred_step_ids = next.deferred_step_ids.filter((id) => !resume.has(id));
    }
  }
  const reason = clipReason(
    input.revisionReason,
    type === 'goal_resumed' ? 'user_resumed_goal' : 'user_modified_goal',
  );
  next.revision_reason = reason;
  next.revisions.push(snapshotOf(next, reason, at));
  pushHistory(next, type, at, {
    metadata: {
      reason,
      ...(input.deferredStepIds === undefined ? {} : { deferred: input.deferredStepIds }),
      ...(input.resumeStepIds === undefined ? {} : { resumed: input.resumeStepIds }),
    },
  });
  if (input.deferredStepIds !== undefined) {
    for (const stepId of input.deferredStepIds) {
      pushHistory(next, 'step_deferred', at, { step_id: stepId, metadata: { reason } });
    }
  }
  return next;
}

export function appendGoalEvent(
  record: GoalRecord,
  type: GoalHistoryType,
  extra?: { step_id?: string; metadata?: Record<string, unknown>; now?: number },
): GoalRecord {
  const next: GoalRecord = {
    ...record,
    revisions: [...record.revisions],
    deferred_step_ids: [...record.deferred_step_ids],
    completed_action_kinds: [...record.completed_action_kinds],
    history: [...record.history],
    constraints: { ...record.constraints },
    updated_at: iso(extra?.now ?? Date.now()),
  };
  pushHistory(next, type, next.updated_at, extra);
  return next;
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.filter((item) => item.trim() !== ''))];
}

function uniqueKinds(values: ActionKind[]): ActionKind[] {
  return [...new Set(values)];
}

export function sliceHistory(
  history: readonly GoalHistoryEvent[],
  sinceSeq?: number,
  max = HISTORY_WIRE_MAX,
): GoalHistoryEvent[] {
  const filtered = sinceSeq === undefined ? [...history] : history.filter((event) => event.seq > sinceSeq);
  if (filtered.length <= max) return filtered;
  return filtered.slice(filtered.length - max);
}

export function supervisionGoal(record: GoalRecord): GoalSupervisionView {
  const revision_history = foldRevisionHistory(record);
  return {
    goal_id: record.goal_id,
    revision: record.revision,
    mode: record.mode,
    card: goalCardLabel(record),
    revision_history_folded: revision_history.length > 1,
    revision_history,
    ...(record.revision > 1 ? { previous_revision: record.revision - 1 } : {}),
  };
}

export function reconstructGoalRecord(sessionId: string, goal = '', plan?: string): GoalRecord {
  return createGoalRecord({ sessionId, goal, plan, revisionReason: 'reconstructed_from_session' });
}

/** Native DSH get_goal payload. A null `goal` is the observed Agent-native miss. */
export type NativeGetGoalResult = { goal: unknown } | null | undefined;

/**
 * Native get_goal and Bridge supervised Goal are different namespaces.
 * A null (or any) native lookup must not clear, replace, recreate, or
 * downgrade the sidecar record: goal_id, revision, mode, constraints, history.
 */
export function applyNativeGetGoalResult(
  record: GoalRecord | undefined,
  _native: NativeGetGoalResult,
): GoalRecord | undefined {
  return record;
}

export function parseGoalRecord(raw: string): GoalRecord | undefined {
  try {
    const value = JSON.parse(raw) as unknown;
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return undefined;
    const rec = value as Record<string, unknown>;
    if (typeof rec.goal_id !== 'string' || typeof rec.session_id !== 'string') return undefined;
    if (typeof rec.goal !== 'string') return undefined;
    const revision = typeof rec.revision === 'number' && rec.revision >= 1 ? Math.trunc(rec.revision) : 1;
    const mode = parseExecutionMode(rec.mode);
    const constraints = parseConstraints(rec.constraints);
    const revisions = Array.isArray(rec.revisions)
      ? rec.revisions.filter((item): item is GoalRevisionSnapshot => {
        return item !== null && typeof item === 'object' && typeof (item as GoalRevisionSnapshot).revision === 'number';
      })
      : [];
    const history = Array.isArray(rec.history)
      ? rec.history.filter((item): item is GoalHistoryEvent => {
        return item !== null && typeof item === 'object' && typeof (item as GoalHistoryEvent).seq === 'number';
      })
      : [];
    const deferred = Array.isArray(rec.deferred_step_ids)
      ? rec.deferred_step_ids.filter((item): item is string => typeof item === 'string')
      : [];
    const completed = Array.isArray(rec.completed_action_kinds)
      ? rec.completed_action_kinds.filter((item): item is ActionKind => typeof item === 'string')
      : [];
    return {
      goal_id: rec.goal_id,
      session_id: rec.session_id,
      revision,
      mode,
      constraints,
      goal: rec.goal,
      ...(typeof rec.plan === 'string' ? { plan: rec.plan } : {}),
      created_at: typeof rec.created_at === 'string' ? rec.created_at : new Date(0).toISOString(),
      updated_at: typeof rec.updated_at === 'string' ? rec.updated_at : new Date(0).toISOString(),
      ...(typeof rec.revision_reason === 'string' ? { revision_reason: rec.revision_reason } : {}),
      revisions,
      deferred_step_ids: deferred,
      completed_action_kinds: completed,
      history,
      history_seq: typeof rec.history_seq === 'number' ? rec.history_seq : history.at(-1)?.seq ?? 0,
    };
  } catch {
    return undefined;
  }
}

export function safeSessionFileId(sessionId: string): string {
  const cleaned = sessionId.replace(/[^A-Za-z0-9._-]/g, '_');
  return cleaned === '' ? 'session' : cleaned;
}

export function fileStoreIo(dir: string): GoalStoreIo {
  return {
    read(sessionId) {
      try {
        return readFileSync(join(dir, `${safeSessionFileId(sessionId)}.json`), 'utf8');
      } catch {
        return undefined;
      }
    },
    write(sessionId, json) {
      mkdirSync(dir, { recursive: true });
      const target = join(dir, `${safeSessionFileId(sessionId)}.json`);
      const tmp = join(dir, `${safeSessionFileId(sessionId)}.${process.pid}.${randomUUID()}.tmp`);
      try {
        writeFileSync(tmp, json, 'utf8');
        renameSync(tmp, target);
      } catch (error) {
        try {
          rmSync(tmp, { force: true });
        } catch {
          // best-effort
        }
        throw error;
      }
    },
  };
}

export function memoryStoreIo(files = new Map<string, string>()): GoalStoreIo & { files: Map<string, string> } {
  return {
    files,
    read(sessionId) {
      return files.get(sessionId);
    },
    write(sessionId, json) {
      files.set(sessionId, json);
    },
  };
}

/** FIFO-capped in-memory cache with optional sidecar persistence. */
export class GoalControlStore {
  private readonly items = new Map<string, GoalRecord>();
  private readonly cap: number;
  private readonly io?: GoalStoreIo;

  constructor(io?: GoalStoreIo, cap = GOAL_CONTROL_CAP) {
    this.io = io;
    this.cap = cap;
  }

  get(sessionId: string): GoalRecord | undefined {
    const mem = this.items.get(sessionId);
    if (mem !== undefined) return mem;
    const raw = this.io?.read(sessionId);
    if (raw === undefined) return undefined;
    const parsed = parseGoalRecord(raw);
    if (parsed === undefined) return undefined;
    this.remember(parsed);
    return parsed;
  }

  put(record: GoalRecord): GoalRecord {
    this.remember(record);
    try {
      this.io?.write(record.session_id, JSON.stringify(record));
    } catch {
      // persistence failure is not fatal: this process still has the record
    }
    return record;
  }

  private remember(record: GoalRecord): void {
    if (this.items.has(record.session_id)) this.items.delete(record.session_id);
    this.items.set(record.session_id, record);
    while (this.items.size > this.cap) {
      const first = this.items.keys().next().value;
      if (first === undefined) break;
      this.items.delete(first);
    }
  }
}

export function goalControlDir(dshHome: string): string {
  return join(dshHome, 'chatgpt-bridge', 'goals');
}

export function revisionBanner(record: GoalRecord): string {
  const deferred = record.deferred_step_ids.length === 0 ? '' : ` · deferred: ${record.deferred_step_ids.join(', ')}`;
  return `[Goal] rev ${record.revision} · ${record.mode}${deferred}`;
}

export function goalCardLabel(record: { revision: number }): string {
  return `Goal rev ${record.revision}`;
}

export function foldRevisionHistory(record: GoalRecord): FoldedRevision[] {
  return record.revisions.map((snapshot) => ({
    revision: snapshot.revision,
    ...(snapshot.previous_revision === undefined ? {} : { previous_revision: snapshot.previous_revision }),
    revision_reason: snapshot.revision_reason,
    created_at: snapshot.created_at,
  }));
}
