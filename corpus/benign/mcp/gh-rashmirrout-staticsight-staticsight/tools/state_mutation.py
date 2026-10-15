"""track_state_mutations: classify reads/writes of a variable and check lock/atomic protection per access."""

from __future__ import annotations

import re

from ..config import Config, is_cpp_file, load_config
from ..core import md
from ..core.cpp_text import strip_code
from ..core.locks import LockWalker, line_events
from ..engines.ctags import FUNCTION_KINDS, Tag, innermost, try_ctags_for_files
from ..core.paths import read_lines, resolve_in_workspace
from ..engines.rg import rg_search
from ..core.errors import InvalidArgument, StaticSightError
from .graph_gtags import normalize_symbol

_LOCK_DECL = re.compile(r"\b(lock_guard|unique_lock|scoped_lock|shared_lock)\b")
_ATOMIC_DECL = re.compile(r"\bstd::atomic\b|\batomic\s*<|\b_Atomic\b|\batomic_\w+\b")
_MUTATING_METHODS = (
    r"push_back|push_front|emplace\w*|insert\w*|erase|clear|reset|swap|assign|resize|pop_\w+|push|store|exchange|"
    r"fetch_\w+|compare_exchange\w*|append|set\w*|add\w*|remove\w*|update\w*"
)


def _access_kind(code: str, sym: str) -> str:
    s = re.escape(sym)
    if re.search(rf"\b{s}\s*(?:\[[^\]]*\]\s*)*(?:=(?!=)|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|\+\+|--)", code) or re.search(
        rf"(?:\+\+|--)\s*(?:[\w\]\)]+\s*(?:\.|->)\s*)*{s}\b", code
    ):
        return "write"
    if re.search(rf"\b{s}\s*(?:\.|->)\s*(?:{_MUTATING_METHODS})\s*\(", code):
        return "mutating call"
    if re.search(rf"&\s*{s}\b(?!\s*\()", code) and not re.search(rf"&&\s*{s}\b", code):
        return "address taken"
    return "read"


def _active_locks(stripped: list[str], fn: Tag, line: int) -> list[tuple[str, int]]:
    """Locks alive at `line` inside fn, honouring block scope for RAII guards and explicit unlocks."""
    walker = LockWalker()
    for n in range(fn.line, line):
        walker.step(stripped[n - 1], n)
    return [(h.kind, h.line) for h in walker.held]


def _is_ctor_dtor(fn: Tag) -> bool:
    short = fn.short_name
    cls = fn.scope.rsplit("::", 1)[-1] if fn.scope else ""
    return short.startswith("~") or (bool(cls) and short == cls)


def _cell(text: str) -> str:
    return md.clip(text.strip(), 70).replace("|", "\\|").replace("`", "'")


async def state_mutations_report(cfg: Config, symbol: str, file_path: str = "") -> str:
    sym = normalize_symbol(symbol)
    paths: list[str] = []
    if file_path and file_path.strip():
        _, rel = resolve_in_workspace(cfg.workspace_root, file_path)
        if not is_cpp_file(rel):
            raise InvalidArgument(f"`{rel}` is not a C/C++ file.")
        paths = [rel]
    res = await rg_search(cfg, sym, word=True, fixed=True, paths=paths)
    title = f"### 🔒 STATE MUTATION & ACCESS SITES: `{sym}`"
    files = sorted(res.files)
    if not files:
        return f"{title}\n✅ `{sym}` is not referenced" + (f" in `{paths[0]}`." if paths else " in any C/C++ file.")
    tags_by_file = await try_ctags_for_files(cfg, files)
    rows: list[dict] = []
    atomic_decl = False
    for path in files:
        try:
            lines = read_lines(cfg.workspace_root / path)
        except StaticSightError:
            continue
        stripped = strip_code(lines)
        tags = tags_by_file.get(path, [])
        word = re.compile(rf"\b{re.escape(sym)}\b")
        for m in res.files[path]:
            if not m.is_match or not (0 < m.line <= len(lines)) or not word.search(stripped[m.line - 1]):
                continue
            code = stripped[m.line - 1]
            decl = next(
                (t for t in tags if t.line == m.line and t.short_name == sym and t.kind in ("member", "variable", "externvar")),
                None,
            )
            fn = innermost(tags, m.line, FUNCTION_KINDS)
            if decl is not None and fn is None:
                if _ATOMIC_DECL.search(code):
                    atomic_decl = True
                rows.append({"path": path, "line": m.line, "fn": decl.scope or "(file scope)", "access": "declaration",
                             "sync": "atomic" if _ATOMIC_DECL.search(code) else "—", "text": lines[m.line - 1]})
                continue
            access = _access_kind(code, sym)
            esc = re.escape(sym)
            if (_LOCK_DECL.search(code) and re.search(rf"\(\s*[\w\.\->]*\b{esc}\b", code)) or re.search(
                rf"\b{esc}\s*(?:\.|->)\s*(?:lock|lock_shared|try_lock|unlock|unlock_shared)\s*\(", code
            ) or any(any(mx.rsplit(".", 1)[-1] == sym for mx in e.mutexes) for e in line_events(code)):
                rows.append({"path": path, "line": m.line, "fn": fn.qualified if fn else "(file scope)",
                             "access": "lock operation", "sync": "— (this is the mutex)", "text": lines[m.line - 1]})
                continue
            if fn is None:
                sync = "file scope"
            elif _is_ctor_dtor(fn):
                sync = "ctor/dtor"
            else:
                locks = _active_locks(stripped, fn, m.line)
                if locks:
                    kind, ln = locks[-1]
                    sync = f"🔒 {kind} (L{ln})"
                    if access in ("write", "mutating call") and kind == "shared_lock":
                        sync += " ⚠️ shared lock for a write"
                else:
                    sync = "❌ BARE"
            rows.append({"path": path, "line": m.line, "fn": fn.qualified if fn else "(file scope)", "access": access,
                         "sync": sync, "text": lines[m.line - 1]})
    if atomic_decl:
        for r in rows:
            if r["sync"] == "❌ BARE":
                r["sync"] = "⚛️ atomic"
    accesses = [r for r in rows if r["access"] not in ("declaration", "lock operation")]
    if not rows:
        return f"{title}\n✅ Only comment/string mentions of `{sym}` were found."
    locked = [r for r in accesses if r["sync"].startswith("🔒")]
    bare = [r for r in accesses if r["sync"] == "❌ BARE"]
    writes = [r for r in accesses if r["access"] in ("write", "mutating call")]
    lock_ops = sum(1 for r in rows if r["access"] == "lock operation")
    summary = f"{md.plural(len(accesses), 'access', 'es')} ({md.plural(len(writes), 'write')})"
    if lock_ops:
        summary += f", {md.plural(lock_ops, 'lock operation')}"
    out = [title, f"{summary} in {md.plural(len({r['path'] for r in rows}), 'file')}."]
    if atomic_decl:
        out.append("⚛️ Declared atomic: individual operations are race-free, but check compound read-modify-write sequences.")
    elif locked and bare:
        where = ", ".join(f"`{r['path']}:{r['line']}` ({r['fn']}, {r['access']})" for r in bare[:5])
        out.append(
            f"⚠️ **Inconsistent locking:** accessed under a lock in {len(locked)} place(s) but without one in {len(bare)}: {where}. "
            "Potential data race if these run concurrently."
        )
    elif bare and writes and not locked:
        out.append("ℹ️ No lock protects any access. If this state is shared across threads it is unsynchronised.")
    table = ["", "| Location | Function | Access | Sync | Code |", "|---|---|---|---|---|"]
    body = [
        f"| `{r['path']}:{r['line']}` | `{r['fn']}` | {r['access']} | {r['sync']} | `{_cell(r['text'])}` |" for r in rows
    ]
    out += table + md.truncate_list(body, cfg.max_results, "accesses", "Pass file_path to focus on one file.")
    out.append("\n_Heuristic: lock scope inferred from RAII guards/.lock() inside the enclosing function; locks held by callers are not visible._")
    return "\n".join(out)


async def track_state_mutations(symbol: str, file_path: str = "") -> str:
    """Finds every read/write of a variable or member (assignment, compound assignment, ++/--, mutating method calls) and, for each access, whether a lock (lock_guard, unique_lock, scoped_lock, shared_lock, .lock(), Win32 critical sections and SRW locks, RAII lock wrappers) or std::atomic protects it inside the enclosing function. Flags inconsistent locking (a member written under a mutex in one place and accessed bare in another), which is a likely data race. Use when the diff touches shared state, mutexes or concurrency."""
    return await state_mutations_report(load_config(), symbol, file_path)
