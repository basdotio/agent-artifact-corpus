/**
 * Reconcile Goal todos against structured tool facts.
 * Never scans assistant summary text.
 */
import {
  successfulKinds,
  type ActionKind,
  type GoalFacts,
} from './goal-facts.js';

export interface ReconcileTodo {
  content: string;
  status: string;
}

export interface ReconcileInput {
  todos?: ReconcileTodo[];
  facts: GoalFacts;
  /** Kinds that are currently waiting / blocked and must not flip to completed. */
  waitingKinds?: ActionKind[];
  /** Contents whose todo must stay in_progress (waiting/blocked step). */
  waitingContents?: string[];
  /** Waiting/blocked with no inferred kind: keep a current step in_progress. */
  holdInProgress?: boolean;
}

const RELEASE_COMMIT = /\brelease\s+commit\b/i;

/**
 * Map a todo line onto at most one action kind using an explicit lexicon.
 * Unmatched lines stay untouched later.
 */
export function classifyTodoKind(content: string): ActionKind | undefined {
  const text = content.toLowerCase();
  if (/\bnpm\b/.test(text) && /\bpublish\b/.test(text)) return 'npm_publish';
  if (/\bpublish\b/.test(text) && !RELEASE_COMMIT.test(text)) return 'npm_publish';
  if (/\btag\b/.test(text)) return 'git_tag';
  if (/\bpush\b/.test(text)) return 'git_push';
  if (/\bgithub\s+release\b/.test(text) || /\bgh\s+release\b/.test(text)) return 'github_release';
  if (/\brelease\b/.test(text) && !RELEASE_COMMIT.test(text) && !/\bpush\b/.test(text)) {
    return 'github_release';
  }
  return undefined;
}

function waitingSet(input: ReconcileInput): { kinds: Set<ActionKind>; contents: Set<string> } {
  return {
    kinds: new Set(input.waitingKinds ?? []),
    contents: new Set(input.waitingContents ?? []),
  };
}

function isWaitingTodo(todo: ReconcileTodo, kind: ActionKind | undefined, waiting: { kinds: Set<ActionKind>; contents: Set<string> }): boolean {
  if (waiting.contents.has(todo.content)) return true;
  if (kind !== undefined && waiting.kinds.has(kind)) return true;
  return false;
}

/**
 * Overlay reconciled statuses onto the last todo/write snapshot.
 * Agent-authored `completed` is never rolled back.
 */
export function reconcileTodos(input: ReconcileInput): ReconcileTodo[] | undefined {
  const todos = input.todos ?? input.facts.todos;
  if (todos === undefined) return undefined;
  const succeeded = successfulKinds(input.facts);
  const waiting = waitingSet(input);
  const usedKinds = new Set<ActionKind>();
  const holdAny = input.holdInProgress === true && waiting.kinds.size === 0 && waiting.contents.size === 0;
  let promoted = false;

  return todos.map((todo) => {
    if (todo.status === 'completed') return todo;
    const kind = classifyTodoKind(todo.content);
    const holdThis = isWaitingTodo(todo, kind, waiting) || (holdAny && !promoted);
    if (holdThis) {
      promoted = true;
      return todo.status === 'in_progress' ? todo : { ...todo, status: 'in_progress' };
    }
    if (kind === undefined || !succeeded.has(kind) || usedKinds.has(kind)) return todo;
    usedKinds.add(kind);
    return { ...todo, status: 'completed' };
  });
}
