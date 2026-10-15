"""Lock recognition shared by track_state_mutations and track_lock_order (text heuristics on comment/string-stripped code).

Recognised acquisitions:
- std RAII guards: lock_guard, unique_lock, scoped_lock, shared_lock (scoped to their block; `defer_lock` = not held)
- RAII wrappers: a type named *Lock*/*Guard*/*Locker* constructed with a mutex argument, e.g. `CAutoLock l(&m_cs);`
- manual: `m.lock()`, `m.lock_shared()`, `m.try_lock()`, `std::lock(a, b, ...)`
- Win32: EnterCriticalSection, AcquireSRWLockExclusive/Shared (Try* variants are conditional and not counted)
Releases: `m.unlock()`, `m.unlock_shared()`, LeaveCriticalSection, ReleaseSRWLockExclusive/Shared.
The TypeScript twin (core/locks.ts) implements the same rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

STD_GUARDS = ("lock_guard", "unique_lock", "scoped_lock", "shared_lock")
_STD_GUARD = re.compile(r"\b(lock_guard|unique_lock|scoped_lock|shared_lock)\b")
_STD_GUARD_DECL = re.compile(r"\b(lock_guard|unique_lock|scoped_lock|shared_lock)\b\s*(?:<[^;{}]*?>)?\s*(\w+)\s*[({]")
# RAII wrapper types must name a lock: CAutoLock, SrwExclusiveGuard, CriticalSectionLock, MutexLocker, ...
_WRAPPER_DECL = re.compile(
    r"\b([A-Z]\w*(?:Lock|Mutex|Srw|SRW|CritSec|CriticalSection)\w*)\s+(\w+)\s*([({])\s*(?=[&\w])")
# a manual lock is a whole statement: `m.lock();` (`if (auto p = weak.lock())` is weak_ptr::lock, not a mutex)
_MANUAL_LOCK = re.compile(
    r"(?:^|(?<=[;{}]))\s*([\w\]\)]+(?:\s*(?:\.|->)\s*\w+)*)\s*(?:\.|->)\s*(lock|lock_shared)\s*\(\s*\)\s*;")
_MANUAL_UNLOCK = re.compile(r"([\w\]\)]+(?:\s*(?:\.|->)\s*\w+)*)\s*(?:\.|->)\s*(unlock|unlock_shared)\s*\(\s*\)")
_STD_LOCK_MULTI = re.compile(r"\bstd::lock\s*\(")
# Try* variants are not counted: whether they hold the lock depends on their result.
_WIN_ACQUIRE = re.compile(r"\b(EnterCriticalSection|AcquireSRWLockExclusive|AcquireSRWLockShared)\s*\(")
_WIN_RELEASE = re.compile(r"\b(LeaveCriticalSection|ReleaseSRWLockExclusive|ReleaseSRWLockShared)\s*\(")
# re-entrant: taking the same lock again on the same thread does not deadlock
RECURSIVE_KINDS = {"EnterCriticalSection"}
LOCK_TRIGGERS = (
    r"\b(?:lock_guard|unique_lock|scoped_lock|shared_lock|EnterCriticalSection|AcquireSRWLock\w+|std::lock)\b|"
    r"(?:\.|->)\s*(?:lock|lock_shared)\s*\(\s*\)|"
    r"\b[A-Z]\w*(?:Lock|Mutex|Srw|SRW|CritSec|CriticalSection)\w*\s+\w+\s*[({]"
)
_IGNORED_ARGS = {"std::defer_lock", "std::adopt_lock", "std::try_to_lock", "defer_lock", "adopt_lock", "try_to_lock"}
_NOT_MUTEX = {"true", "false", "nullptr", "NULL", "TRUE", "FALSE", "this"}


@dataclass(frozen=True)
class LockEvent:
    col: int
    op: str            # "acquire" | "release"
    kind: str          # lock_guard, .lock(), EnterCriticalSection, CAutoLock, std::lock, ...
    mutexes: tuple[str, ...]  # normalised expressions ("" when unknown)
    scoped: bool       # released at the end of the enclosing block (RAII)


def _split_args(text: str, start: int) -> tuple[list[str], int]:
    """Top-level comma-separated arguments of the call whose '(' or '{' is at `start`."""
    close = {"(": ")", "{": "}"}[text[start]]
    depth, cur, args = 0, [], []
    i = start
    while i < len(text):
        ch = text[i]
        if ch == ">" and i > start and text[i - 1] == "-":
            cur.append(ch)  # `->` is member access, not a closing template bracket
        elif ch in "([{<":
            depth += 1
            if depth > 1:
                cur.append(ch)
        elif ch in ")]}>":
            depth -= 1
            if depth == 0 and ch == close:
                args.append("".join(cur))
                return [a.strip() for a in args if a.strip()], i
            cur.append(ch)
        elif ch == "," and depth == 1:
            args.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    args.append("".join(cur))
    return [a.strip() for a in args if a.strip()], len(text)


def norm_mutex(expr: str) -> str:
    e = re.sub(r"\s+", "", expr)
    e = e.lstrip("&*(").rstrip(")")
    e = re.sub(r"^this->", "", e).replace("->", ".")
    return e


def _mutexes(args: list[str]) -> tuple[str, ...]:
    out = [norm_mutex(a) for a in args if re.sub(r"\s+", "", a) not in _IGNORED_ARGS]
    return tuple(m for m in out if re.fullmatch(r"[A-Za-z_][\w.:\[\]]*", m) and m not in _NOT_MUTEX)


def line_events(code: str) -> list[LockEvent]:
    """Acquisitions and releases on one comment/string-stripped line, in column order."""
    ev: list[LockEvent] = []
    std_cols: set[int] = set()
    for m in _STD_GUARD.finditer(code):
        std_cols.add(m.start())
        if "defer_lock" in code:
            continue
        d = _STD_GUARD_DECL.match(code, m.start())
        mx: tuple[str, ...] = ()
        if d:
            mx = _mutexes(_split_args(code, d.end() - 1)[0])
        ev.append(LockEvent(m.start(), "acquire", m.group(1), mx, True))
        break  # one guard per line (as the lock-consistency table always assumed)
    for m in _WRAPPER_DECL.finditer(code):
        if m.group(1) in STD_GUARDS or any(c in std_cols for c in range(m.start(), m.end())):
            continue
        mx = _mutexes(_split_args(code, m.start(3))[0][:1])
        if mx:
            ev.append(LockEvent(m.start(), "acquire", m.group(1), mx, True))
    for m in _STD_LOCK_MULTI.finditer(code):
        mx = _mutexes(_split_args(code, m.end() - 1)[0])
        if mx:
            ev.append(LockEvent(m.start(), "acquire", "std::lock", mx, False))
    for m in _MANUAL_LOCK.finditer(code):
        ev.append(LockEvent(m.start(1), "acquire", "." + m.group(2) + "()", _mutexes([m.group(1)]), False))
    for m in _WIN_ACQUIRE.finditer(code):
        ev.append(LockEvent(m.start(), "acquire", m.group(1), _mutexes(_split_args(code, m.end() - 1)[0][:1]), False))
    for m in _MANUAL_UNLOCK.finditer(code):
        ev.append(LockEvent(m.start(), "release", "." + m.group(2) + "()", _mutexes([m.group(1)]), False))
    for m in _WIN_RELEASE.finditer(code):
        ev.append(LockEvent(m.start(), "release", m.group(1), _mutexes(_split_args(code, m.end() - 1)[0][:1]), False))
    ev.sort(key=lambda e: (e.col, e.op))
    return ev


@dataclass
class Held:
    depth: int      # block depth for RAII guards, -1 for manual locks
    kind: str
    mutexes: tuple[str, ...]
    line: int
    blocks: tuple[int, ...] = ()  # ids of the blocks open where it was taken


class LockWalker:
    """Tracks which locks are held while walking a function body line by line.

    `held` keeps manual locks until their unlock (they may span blocks). `open_held()` is stricter: only locks taken in
    a block that is still open, so a lock taken in an `if` branch is not "held" in the `else` branch or after the loop.
    """

    def __init__(self) -> None:
        self.depth = 0
        self.held: list[Held] = []
        self._blocks: list[int] = []
        self._next = 0

    def _is_open(self, h: Held) -> bool:
        return tuple(self._blocks[: len(h.blocks)]) == h.blocks

    def open_held(self) -> list[Held]:
        return [h for h in self.held if self._is_open(h)]

    def step(self, code: str, line: int, on_acquire=None) -> None:
        """Apply one line: lock events and braces in column order."""
        events = line_events(code)
        k = 0
        for i in range(len(code) + 1):
            while k < len(events) and events[k].col <= i:
                e = events[k]
                k += 1
                if e.op == "acquire":
                    if on_acquire is not None:
                        on_acquire(e, self.open_held())
                    self.held.append(Held(self.depth if e.scoped else -1, e.kind, e.mutexes, line, tuple(self._blocks)))
                else:
                    self._release(e)
            if i == len(code):
                break
            ch = code[i]
            if ch == "{":
                self.depth += 1
                self._next += 1
                self._blocks.append(self._next)
            elif ch == "}":
                self.depth -= 1
                if self._blocks:
                    self._blocks.pop()
                self.held = [h for h in self.held if h.depth == -1 or h.depth <= self.depth]

    def _release(self, e: LockEvent) -> None:
        name = e.mutexes[0] if e.mutexes else ""
        releasable = [i for i, h in enumerate(self.held) if h.depth == -1 or h.kind == "unique_lock"]
        if name:
            match = [i for i in releasable if name in self.held[i].mutexes or
                     (self.held[i].kind == "unique_lock" and not self.held[i].mutexes)]
            if match:
                self.held.pop(match[-1])
                return
        if releasable:
            self.held.pop(releasable[-1])
