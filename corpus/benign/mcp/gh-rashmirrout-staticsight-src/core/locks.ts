// Lock recognition shared by track_state_mutations and track_lock_order (text heuristics on comment/string-stripped
// code). Twin of staticsight-py/src/staticsight/core/locks.py: same rules, same results.
//
// Acquisitions: std RAII guards (lock_guard, unique_lock, scoped_lock, shared_lock; `defer_lock` = not held), RAII
// wrappers whose type names a lock (CAutoLock, SrwGuard, ...) built with a mutex argument, manual `m.lock();`,
// `std::lock(a, b)`, Win32 EnterCriticalSection / AcquireSRWLockExclusive / AcquireSRWLockShared (Try* variants are
// conditional and not counted). Releases: `m.unlock()`, LeaveCriticalSection, ReleaseSRWLockExclusive/Shared.

export const STD_GUARDS = ["lock_guard", "unique_lock", "scoped_lock", "shared_lock"];
const STD_GUARD = /\b(lock_guard|unique_lock|scoped_lock|shared_lock)\b/g;
const STD_GUARD_DECL = /\b(lock_guard|unique_lock|scoped_lock|shared_lock)\b\s*(?:<[^;{}]*?>)?\s*(\w+)\s*[({]/y;
// RAII wrapper types must name a lock: CAutoLock, SrwExclusiveGuard, CriticalSectionLock, MutexLocker, ...
const WRAPPER_DECL = /\b([A-Z]\w*(?:Lock|Mutex|Srw|SRW|CritSec|CriticalSection)\w*)\s+(\w+)\s*([({])\s*(?=[&\w])/dg;
// a manual lock is a whole statement: `m.lock();` (`if (auto p = weak.lock())` is weak_ptr::lock, not a mutex)
const MANUAL_LOCK = /(?:^|(?<=[;{}]))\s*([\w\])]+(?:\s*(?:\.|->)\s*\w+)*)\s*(?:\.|->)\s*(lock|lock_shared)\s*\(\s*\)\s*;/dg;
const MANUAL_UNLOCK = /([\w\])]+(?:\s*(?:\.|->)\s*\w+)*)\s*(?:\.|->)\s*(unlock|unlock_shared)\s*\(\s*\)/g;
const STD_LOCK_MULTI = /\bstd::lock\s*\(/g;
// Try* variants are not counted: whether they hold the lock depends on their result.
const WIN_ACQUIRE = /\b(EnterCriticalSection|AcquireSRWLockExclusive|AcquireSRWLockShared)\s*\(/g;
const WIN_RELEASE = /\b(LeaveCriticalSection|ReleaseSRWLockExclusive|ReleaseSRWLockShared)\s*\(/g;
/** re-entrant: taking the same lock again on the same thread does not deadlock */
export const RECURSIVE_KINDS = new Set(["EnterCriticalSection"]);
export const LOCK_TRIGGERS =
  "\\b(?:lock_guard|unique_lock|scoped_lock|shared_lock|EnterCriticalSection|AcquireSRWLock\\w+|std::lock)\\b|" +
  "(?:\\.|->)\\s*(?:lock|lock_shared)\\s*\\(\\s*\\)|" +
  "\\b[A-Z]\\w*(?:Lock|Mutex|Srw|SRW|CritSec|CriticalSection)\\w*\\s+\\w+\\s*[({]";
const IGNORED_ARGS = new Set(["std::defer_lock", "std::adopt_lock", "std::try_to_lock", "defer_lock", "adopt_lock", "try_to_lock"]);
const NOT_MUTEX = new Set(["true", "false", "nullptr", "NULL", "TRUE", "FALSE", "this"]);

export interface LockEvent {
  col: number;
  op: "acquire" | "release";
  kind: string;
  mutexes: string[];
  scoped: boolean;
}

function splitArgs(text: string, start: number): string[] {
  const close = text[start] === "(" ? ")" : "}";
  let depth = 0;
  let cur = "";
  const args: string[] = [];
  for (let i = start; i < text.length; i++) {
    const ch = text[i];
    if (ch === ">" && i > start && text[i - 1] === "-") {
      cur += ch; // `->` is member access, not a closing template bracket
    } else if ("([{<".includes(ch)) {
      depth++;
      if (depth > 1) cur += ch;
    } else if (")]}>".includes(ch)) {
      depth--;
      if (depth === 0 && ch === close) {
        args.push(cur);
        return args.map((a) => a.trim()).filter((a) => a);
      }
      cur += ch;
    } else if (ch === "," && depth === 1) {
      args.push(cur);
      cur = "";
    } else cur += ch;
  }
  args.push(cur);
  return args.map((a) => a.trim()).filter((a) => a);
}

export function normMutex(expr: string): string {
  let e = expr.replace(/\s+/g, "");
  e = e.replace(/^[&*(]+/, "").replace(/\)+$/, "");
  return e.replace(/^this->/, "").replaceAll("->", ".");
}

function mutexes(args: string[]): string[] {
  return args
    .filter((a) => !IGNORED_ARGS.has(a.replace(/\s+/g, "")))
    .map(normMutex)
    .filter((m) => /^[A-Za-z_][\w.:[\]]*$/.test(m) && !NOT_MUTEX.has(m));
}

/** Acquisitions and releases on one comment/string-stripped line, in column order. */
export function lineEvents(code: string): LockEvent[] {
  const ev: LockEvent[] = [];
  const stdCols = new Set<number>();
  for (const m of code.matchAll(STD_GUARD)) {
    stdCols.add(m.index!);
    if (code.includes("defer_lock")) continue;
    STD_GUARD_DECL.lastIndex = m.index!;
    const d = STD_GUARD_DECL.exec(code);
    const mx = d ? mutexes(splitArgs(code, d.index + d[0].length - 1)) : [];
    ev.push({ col: m.index!, op: "acquire", kind: m[1], mutexes: mx, scoped: true });
    break; // one guard per line (as the lock-consistency table always assumed)
  }
  for (const m of code.matchAll(WRAPPER_DECL)) {
    const start = m.index!;
    const end = start + m[0].length;
    let overlaps = false;
    for (let c = start; c < end; c++) if (stdCols.has(c)) overlaps = true;
    if (STD_GUARDS.includes(m[1]) || overlaps) continue;
    const mx = mutexes(splitArgs(code, m.indices![3][0]).slice(0, 1));
    if (mx.length) ev.push({ col: start, op: "acquire", kind: m[1], mutexes: mx, scoped: true });
  }
  for (const m of code.matchAll(STD_LOCK_MULTI)) {
    const mx = mutexes(splitArgs(code, m.index! + m[0].length - 1));
    if (mx.length) ev.push({ col: m.index!, op: "acquire", kind: "std::lock", mutexes: mx, scoped: false });
  }
  for (const m of code.matchAll(MANUAL_LOCK)) {
    ev.push({ col: m.indices![1][0], op: "acquire", kind: "." + m[2] + "()", mutexes: mutexes([m[1]]), scoped: false });
  }
  for (const m of code.matchAll(WIN_ACQUIRE)) {
    ev.push({ col: m.index!, op: "acquire", kind: m[1], mutexes: mutexes(splitArgs(code, m.index! + m[0].length - 1).slice(0, 1)), scoped: false });
  }
  for (const m of code.matchAll(MANUAL_UNLOCK)) {
    ev.push({ col: m.index!, op: "release", kind: "." + m[2] + "()", mutexes: mutexes([m[1]]), scoped: false });
  }
  for (const m of code.matchAll(WIN_RELEASE)) {
    ev.push({ col: m.index!, op: "release", kind: m[1], mutexes: mutexes(splitArgs(code, m.index! + m[0].length - 1).slice(0, 1)), scoped: false });
  }
  ev.sort((a, b) => a.col - b.col || (a.op < b.op ? -1 : a.op > b.op ? 1 : 0));
  return ev;
}

export interface Held {
  depth: number; // block depth for RAII guards, -1 for manual locks
  kind: string;
  mutexes: string[];
  line: number;
  blocks: number[]; // ids of the blocks open where it was taken
}

/**
 * Tracks which locks are held while walking a function body line by line. `held` keeps manual locks until their unlock
 * (they may span blocks); `openHeld()` only returns locks taken in a block that is still open, so a lock taken in an
 * `if` branch is not "held" in the `else` branch or after the loop.
 */
export class LockWalker {
  depth = 0;
  held: Held[] = [];
  private blocks: number[] = [];
  private next = 0;

  private isOpen(h: Held): boolean {
    for (let i = 0; i < h.blocks.length; i++) if (this.blocks[i] !== h.blocks[i]) return false;
    return h.blocks.length <= this.blocks.length;
  }

  openHeld(): Held[] {
    return this.held.filter((h) => this.isOpen(h));
  }

  step(code: string, line: number, onAcquire?: (e: LockEvent, held: Held[]) => void): void {
    const events = lineEvents(code);
    let k = 0;
    for (let i = 0; i <= code.length; i++) {
      while (k < events.length && events[k].col <= i) {
        const e = events[k++];
        if (e.op === "acquire") {
          if (onAcquire) onAcquire(e, this.openHeld());
          this.held.push({ depth: e.scoped ? this.depth : -1, kind: e.kind, mutexes: e.mutexes, line, blocks: [...this.blocks] });
        } else this.release(e);
      }
      if (i === code.length) break;
      const ch = code[i];
      if (ch === "{") {
        this.depth++;
        this.blocks.push(++this.next);
      } else if (ch === "}") {
        this.depth--;
        this.blocks.pop();
        this.held = this.held.filter((h) => h.depth === -1 || h.depth <= this.depth);
      }
    }
  }

  private release(e: LockEvent): void {
    const name = e.mutexes[0] ?? "";
    const releasable = this.held.map((h, i) => [h, i] as const).filter(([h]) => h.depth === -1 || h.kind === "unique_lock").map(([, i]) => i);
    if (name) {
      const match = releasable.filter((i) => this.held[i].mutexes.includes(name) || (this.held[i].kind === "unique_lock" && !this.held[i].mutexes.length));
      if (match.length) {
        this.held.splice(match[match.length - 1], 1);
        return;
      }
    }
    if (releasable.length) this.held.splice(releasable[releasable.length - 1], 1);
  }
}
