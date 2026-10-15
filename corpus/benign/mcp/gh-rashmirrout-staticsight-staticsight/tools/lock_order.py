"""track_lock_order: repository-wide lock-acquisition order, potential deadlock cycles, locks held across blocking calls."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import Config, load_config
from ..core import md
from ..core.cpp_text import strip_code
from ..core.errors import StaticSightError
from ..core.locks import LOCK_TRIGGERS, RECURSIVE_KINDS, LockWalker, line_events
from ..core.paths import matches_glob, read_lines
from ..engines.ctags import FUNCTION_KINDS, try_ctags_for_files
from ..engines.rg import rg_search

_BLOCKING = re.compile(
    r"\b(send|sendto|sendmsg|recv|recvfrom|recvmsg|connect|accept|select|poll|epoll_wait|fopen|fread|fwrite|fflush|"
    r"sleep|usleep|nanosleep|Sleep|SleepEx|WaitForSingleObject|WaitForSingleObjectEx|WaitForMultipleObjects|"
    r"ReadFile|WriteFile|DeviceIoControl|CreateFileW?|CreateFileA|WinHttpSendRequest|WinHttpReceiveResponse|"
    r"sleep_for|sleep_until)\s*\("
)
_CALL = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
_COND_BEFORE = re.compile(r"\b(?:if|else|for|while|case|switch|default)\b|\?")
_BRACELESS_HEAD = re.compile(r"^\s*(?:\}\s*)?(?:(?:else\s+)?if\s*\(.*\)|for\s*\(.*\)|while\s*\(.*\)|else)\s*$")


def _conditional(stripped: list[str], n: int, col: int) -> bool:
    """The acquisition on line n is guarded: a condition before it on the line, or a brace-less if/else/loop above."""
    if _COND_BEFORE.search(stripped[n - 1][:col]):
        return True
    k = n - 2
    while k >= 0 and not stripped[k].strip():
        k -= 1
    return k >= 0 and bool(_BRACELESS_HEAD.match(stripped[k]))
_NOT_CALLS = {
    "if", "for", "while", "switch", "return", "sizeof", "alignof", "decltype", "static_cast", "reinterpret_cast",
    "const_cast", "dynamic_cast", "catch", "throw", "noexcept", "defined", "static_assert", "typeid", "alignas",
    "assert", "new", "delete", "operator",
}
MAX_CYCLE = 4


@dataclass(frozen=True)
class Edge:
    first: str       # lock held
    second: str      # lock taken while `first` is held
    path: str
    fn: str
    line_first: int
    line_second: int
    via: str         # "" or the called function that takes `second`


def _key(mx: str, cls: str) -> str:
    """Bare member-like names are qualified with the enclosing class, so `m_lock` of two classes stays distinct."""
    return f"{cls}::{mx}" if cls and re.fullmatch(r"[A-Za-z_]\w*", mx) else mx


def _cls(fn_scope: str) -> str:
    return fn_scope.rsplit("::", 1)[-1] if fn_scope else ""


@dataclass
class _Fn:
    name: str
    qualified: str
    path: str
    cls: str
    acquired: dict   # key -> (line, kind, unconditional: taken at the top level of the body)


async def analyse(cfg: Config, path_glob: str = ""):
    res = await rg_search(cfg, LOCK_TRIGGERS)
    files = sorted(p for p in res.files if not path_glob or matches_glob(p, path_glob))
    tags_by_file = await try_ctags_for_files(cfg, files)
    fns: list[_Fn] = []
    edges: list[Edge] = []
    blocking: list[tuple[str, str, int, str, list[str]]] = []  # path, fn, line, call, held keys
    calls: list[tuple[_Fn, int, str, list[tuple[str, int, str]]]] = []  # fn, line, callee, held (key, line, kind)
    self_reacquire: list[tuple[str, str, int, str, str]] = []  # path, fn, line, key, via
    for path in files:
        try:
            stripped = strip_code(read_lines(cfg.workspace_root / path))
        except StaticSightError:
            continue
        funcs = sorted((t for t in tags_by_file.get(path, []) if t.kind in FUNCTION_KINDS and t.end), key=lambda t: t.line)
        for t in funcs:
            cls = _cls(t.scope)
            f = _Fn(t.short_name, t.qualified, path, cls, {})
            fns.append(f)
            walker = LockWalker()
            for n in range(t.line, min(t.end, len(stripped)) + 1):
                code = stripped[n - 1]

                def on_acquire(e, held, n=n, f=f, walker=walker):
                    new_keys = [_key(m, f.cls) for m in e.mutexes]
                    top = walker.depth <= 1 and not _conditional(stripped, n, e.col)
                    for k in new_keys:
                        prev = f.acquired.get(k)
                        if prev is None or (top and not prev[2]):
                            f.acquired[k] = (n, e.kind, top)
                    for h in held:
                        for hm in h.mutexes:
                            hk = _key(hm, f.cls)
                            for k in new_keys:
                                if hk == k:
                                    if e.kind not in RECURSIVE_KINDS and h.kind not in RECURSIVE_KINDS:
                                        self_reacquire.append((path, f.qualified, n, k, ""))
                                else:
                                    edges.append(Edge(hk, k, path, f.qualified, h.line, n, ""))

                walker.step(code, n, on_acquire)
                open_held = walker.open_held()
                if not open_held:
                    continue
                held = [(_key(m, cls), h.line, h.kind) for h in open_held for m in h.mutexes]
                if not held:
                    continue
                bm = _BLOCKING.search(code)
                if bm:
                    blocking.append((path, f.qualified, n, bm.group(1), [k for k, _, _ in held]))
                if line_events(code):
                    continue
                for m in _CALL.finditer(code):
                    name = m.group(1)
                    if name in _NOT_CALLS or name == t.short_name or re.fullmatch(r"[A-Z][A-Z0-9_]*", name):
                        continue
                    before = code[: m.start()].rstrip()
                    if (before.endswith(".") or before.endswith("->")) and not before.endswith("this->"):
                        continue  # a call on another object takes that object's locks, not ours
                    calls.append((f, n, name, held))
    # one call level: a function called while holding A that itself takes B gives A -> B
    by_name: dict[str, list[_Fn]] = {}
    for f in fns:
        if f.acquired:
            by_name.setdefault(f.name, []).append(f)
    for f, n, callee, held in calls:
        for g in by_name.get(callee, []):
            if g.cls and f.cls and g.cls != f.cls:
                continue  # same short name on an unrelated class
            for k, (gl, gkind, gtop) in sorted(g.acquired.items()):
                for hk, hl, hkind in held:
                    if hk == k:
                        # only a lock the callee always takes; `if (acquireLock) AcquireSRWLock...` is a common pattern
                        if gtop and gkind not in RECURSIVE_KINDS and hkind not in RECURSIVE_KINDS:
                            self_reacquire.append((f.path, f.qualified, n, k, g.qualified))
                    else:
                        edges.append(Edge(hk, k, f.path, f.qualified, hl, n, g.qualified))
    return fns, edges, blocking, self_reacquire


def find_cycles(edges: list[Edge]) -> list[list[str]]:
    graph: dict[str, set[str]] = {}
    for e in edges:
        graph.setdefault(e.first, set()).add(e.second)
    cycles: list[list[str]] = []
    for start in sorted(graph):
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for nxt in sorted(graph.get(node, ()), reverse=True):
                if nxt == start and len(path) >= 2:
                    cycles.append(path[:])
                elif nxt > start and nxt not in path and len(path) < MAX_CYCLE:
                    stack.append((nxt, path + [nxt]))
    return sorted(cycles, key=lambda c: (len(c), c))


def _ev(e: Edge) -> str:
    how = f"via `{e.via}()` at L{e.line_second}" if e.via else f"at L{e.line_second}"
    return f"`{e.path}:{e.line_first}` in `{e.fn}`: holds `{e.first}` (L{e.line_first}), takes `{e.second}` {how}"


def _involves(key: str, symbol: str) -> bool:
    return not symbol or key == symbol or key.rsplit("::", 1)[-1].rsplit(".", 1)[-1] == symbol


async def lock_order_report(cfg: Config, path_glob: str = "", symbol: str = "",
                            focus: set[tuple[str, str]] | None = None) -> str:
    """`focus` = {(path, qualified function)}: review mode, only findings about the locks those functions take
    (returns "" when there are none)."""
    symbol = (symbol or "").strip()
    fns, edges, blocking, selfre = await analyse(cfg, path_glob)
    scope = f"`{symbol}`" if symbol else (f"`{path_glob}`" if path_glob else "repository")
    title = f"### 🔀 LOCK ORDER: {scope}" if focus is None else "### 🔀 LOCK ORDER: locks taken by changed functions"
    locking_fns = [f for f in fns if f.acquired]
    keys = sorted({k for f in locking_fns for k in f.acquired})
    only_keys: set[str] | None = None
    if focus is not None:
        only_keys = {k for f in fns if (f.path, f.qualified) in focus for k in f.acquired}
        only_keys |= {k for e in edges if (e.path, e.fn) in focus for k in (e.first, e.second)}
        if not only_keys:
            return ""
        blocking = [b for b in blocking if (b[0], b[1]) in focus]
        selfre = [x for x in selfre if (x[0], x[1]) in focus]
    if not locking_fns:
        return f"{title}\n✅ No lock acquisitions found" + (f" in files matching `{path_glob}`." if path_glob else ".")

    def keep(ks) -> bool:
        ks = list(ks)
        return any(_involves(k, symbol) for k in ks) and (only_keys is None or any(k in only_keys for k in ks))

    cycles = [c for c in find_cycles(edges) if keep(c)]
    if focus is not None and not cycles and not selfre and not blocking:
        return ""
    pairs: dict[tuple[str, str], list[Edge]] = {}
    for e in edges:
        pairs.setdefault((e.first, e.second), []).append(e)
    out = [title, f"Scanned {md.plural(len(locking_fns), 'function')} that take locks in "
                  f"{md.plural(len({f.path for f in locking_fns}), 'file')}: {md.plural(len(keys), 'lock')}, "
                  f"{md.plural(len(pairs), 'ordering pair')}."]
    if cycles:
        out.append(f"\n⚠️ **{md.plural(len(cycles), 'potential deadlock cycle')}** (locks taken in opposite orders):")
        items = []
        for i, c in enumerate(cycles, 1):
            ring = " → ".join(f"`{k}`" for k in c + [c[0]])
            lines = [f"{i}. {ring}"]
            for a, b in zip(c, c[1:] + [c[0]]):
                ev = sorted(pairs[(a, b)], key=lambda e: (e.path, e.line_first, e.line_second, e.via))
                lines.append(f"   - {_ev(ev[0])}" + (f" (+{len(ev) - 1} more)" if len(ev) > 1 else ""))
            items.append("\n".join(lines))
        out += md.truncate_list(items, cfg.max_results, "cycles", "Pass symbol or path_glob to focus.")
    else:
        out.append("\n✅ No lock-order cycles found" + (f" involving `{symbol}`." if symbol else "."))
    sre = sorted({s for s in selfre if keep([s[3]])})
    if sre:
        out.append("\n⚠️ **Same lock taken twice** (self-deadlock for non-recursive mutexes):")
        out += md.truncate_list(
            [f"- `{p}:{n}` in `{fn}`: `{k}` is already held" + (f", and `{via}()` takes it again" if via else "")
             for p, fn, n, k, via in sre], cfg.max_results, "sites")
    blk = sorted({(p, fn, n, call, tuple(sorted(set(ks)))) for p, fn, n, call, ks in blocking if keep(ks)})
    if blk:
        out.append("\n⏳ **Locks held across blocking calls** (latency, and deadlock if the other side needs the lock):")
        out += md.truncate_list([f"- `{p}:{n}` in `{fn}`: `{call}()` while holding " + ", ".join(f"`{k}`" for k in ks)
                                 for p, fn, n, call, ks in blk], cfg.max_results, "sites")
    order = sorted(((a, b), ev) for (a, b), ev in pairs.items() if keep([a, b]))
    if order and not only_keys:
        out.append("\n**Acquisition order** (A → B: B is taken while A is held):")
        out += md.truncate_list(
            [f"- `{a}` → `{b}`: {md.plural(len(ev), 'place')}, e.g. `{ev[0].path}:{ev[0].line_second}` in `{ev[0].fn}`"
             + (f" via `{ev[0].via}()`" if ev[0].via else "")
             for (a, b), ev in ((k, sorted(v, key=lambda e: (e.path, e.line_second, e.via))) for k, v in order)],
            cfg.max_results, "pairs")
    out.append("\n_Heuristic: locks matched by name (members qualified by class), order taken inside each function "
               "plus one call level; aliases, lock hierarchies and runtime conditions are not modelled._")
    return "\n".join(out)


async def track_lock_order(path_glob: str = "", symbol: str = "") -> str:
    """Finds potential deadlocks: builds the lock-acquisition order of the whole repository (which lock is taken while another is held, inside each function and through one level of calls) and reports cycles where two code paths take the same locks in opposite orders, the same non-recursive lock taken twice, and locks held across blocking calls (send/recv, file I/O, Sleep, WaitForSingleObject). Recognises std guards (lock_guard, unique_lock, scoped_lock, shared_lock), .lock(), std::lock, Win32 critical sections and SRW locks, and RAII lock wrappers. Use when the diff adds or reorders locks, calls into locking code while holding a lock, or when investigating hangs."""
    return await lock_order_report(load_config(), path_glob, symbol)
