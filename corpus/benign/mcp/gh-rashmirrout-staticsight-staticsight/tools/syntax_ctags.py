"""Ctags-driven scope extraction and regex/brace-depth control-flow skeletons."""

from __future__ import annotations

import re

from ..config import Config, is_cpp_file, load_config
from ..core import md
from ..core.cpp_text import balanced_parens, strip_code
from ..engines.ctags import BLOCK_KINDS, FUNCTION_KINDS, Tag, ctags_for_file, innermost
from ..engines.git import changed_lines
from ..core.paths import read_lines, resolve_in_workspace
from ..core.errors import InvalidArgument

MAX_SCOPE_LINES = 150
MAX_SKELETON_LINES = 3000
MAX_SKELETON_NODES = 150


def _check_cpp(rel: str) -> None:
    if not is_cpp_file(rel):
        raise InvalidArgument(f"`{rel}` is not a C/C++ source or header file.")


def _window_ranges(start: int, end: int, target: int) -> list[tuple[int, int]]:
    """Line ranges to show for a scope; big scopes are elided around the target line."""
    if end - start + 1 <= MAX_SCOPE_LINES:
        return [(start, end)]
    ranges = [(start, min(end, start + 14)), (max(start, target - 30), min(end, target + 30)), (max(start, end - 9), end)]
    merged: list[tuple[int, int]] = []
    for a, b in sorted(ranges):
        if merged and a <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


def _render_ranges(lines: list[str], ranges: list[tuple[int, int]], marks: set[int]) -> list[str]:
    width = len(str(ranges[-1][1]))
    out: list[str] = []
    prev_end = None
    for a, b in ranges:
        if prev_end is not None and a > prev_end + 1:
            out.append(f"{' ' * (width + 1)} … {b and a - prev_end - 1} lines elided …")
        out.extend(md.numbered_code(lines[a - 1 : b], a, marks, width))
        prev_end = b
    return out


async def enclosing_scope_report(cfg: Config, file_path: str, target_line: int) -> str:
    abs_path, rel = resolve_in_workspace(cfg.workspace_root, file_path)
    _check_cpp(rel)
    lines = read_lines(abs_path)
    if target_line < 1 or target_line > len(lines):
        raise InvalidArgument(f"Line {target_line} is out of range: `{rel}` has {len(lines)} lines.")
    tags = await ctags_for_file(cfg, rel)
    scope = innermost(tags, target_line, BLOCK_KINDS - {"namespace"}) or innermost(tags, target_line, BLOCK_KINDS)
    if scope is None or (scope.kind == "namespace" and scope.end - scope.line + 1 > MAX_SCOPE_LINES):
        a, b = max(1, target_line - 12), min(len(lines), target_line + 12)
        out = [
            f"### 📄 FILE-LEVEL CONTEXT: `{rel}` L{target_line}",
            "_No enclosing function/class found by ctags (global scope, preprocessor block, or code ctags could not parse)._",
        ]
        if scope is not None:
            out.append(f"- **Enclosing namespace:** `{scope.qualified}` (L{scope.line}-{scope.end})")
        out += ["```cpp", *md.numbered_code(lines[a - 1 : b], a, {target_line}), "```"]
        return "\n".join(out)
    start, end = scope.line, min(scope.end, len(lines))
    out = [
        f"### 📦 ENCLOSING SCOPE: `{scope.qualified}` ({scope.kind})",
        f"- **File:** `{rel}` L{start}-{end} ({md.plural(end - start + 1, 'line')})",
    ]
    if scope.kind in ("function", "macro"):
        out.append(f"- **Signature:** {md.code_span(scope.display_signature)}")
    if scope.scope:
        out.append(f"- **Parent:** {scope.scope_kind or 'scope'} `{scope.scope}`")
    ranges = _window_ranges(start, end, target_line)
    if len(ranges) > 1:
        out.append(f"- _Large scope: showing head, ±30 lines around L{target_line}, and tail._")
    out += ["```cpp", *_render_ranges(lines, ranges, {target_line}), "```"]
    return "\n".join(out)


async def get_enclosing_scope(file_path: str, target_line: int) -> str:
    """Returns the innermost C++ function/method/class/struct/namespace that encloses a given line, with its qualified name, signature, parent scope, line range and the line-numbered source (the target line is marked with >). Use when you have a file:line (from a diff, stack trace, or another tool) and need the full surrounding code without reading the whole file."""
    return await enclosing_scope_report(load_config(), file_path, target_line)


# --------------------------------------------------------------------------- skeleton
_CONTROL = re.compile(
    r"(?:\}\s*)*(else\s+if|if|else|switch|case|default|for|while|do|try|catch|return|co_return|throw|break|continue|goto)\b"
)
_LOCK = re.compile(r"\b(?:lock_guard|unique_lock|scoped_lock|shared_lock)\b|(?:\.|->)(?:lock|lock_shared|try_lock)\s*\(\s*\)")
_UNLOCK = re.compile(r"(?:\.|->)(?:unlock|unlock_shared)\s*\(\s*\)")
_RELEASE = re.compile(
    r"\b(?:free|fclose|munmap|close|closesocket|CloseHandle|CloseServiceHandle|RegCloseKey|FindClose|LocalFree|GlobalFree|"
    r"HeapFree|VirtualFree|CoTaskMemFree|SysFreeString|\w*[Rr]elease\w*|\w*[Dd]ealloc\w*|\w+_free)\s*\(|\bdelete\b"
)
_ALLOC = re.compile(
    r"\b(?:malloc|calloc|realloc|strdup|strndup|fopen|mmap|open|socket|accept|CreateFile\w*|CreateEvent\w*|CreateMutex\w*|"
    r"CreateSemaphore\w*|CreateThread|CreateProcess\w*|OpenProcess|OpenThread|OpenService\w*|OpenSCManager\w*|"
    r"CreateService\w*|FindFirstFile\w*|CoTaskMemAlloc|SysAllocString\w*|\w*[Aa]lloc\w*|\w*[Aa]cquire\w*)\s*\(|\bnew\b"
)
_COM_RELEASE = re.compile(r"(\w+)\s*(?:->|\.)\s*Release\s*\(")
_ASSIGN_VAR = re.compile(r"(\w+)\s*=(?!=)")
_RELEASE_VAR = re.compile(r"\bdelete(?:\s*\[\s*\])?\s+(\w+)|\(\s*&?\s*(\w+)")
_BRANCH_KEYS = {"if", "else if", "switch", "for", "while", "catch"}


def _null_checked(var: str, cond: str) -> bool:
    v = re.escape(var)
    return bool(
        re.search(
            rf"!\s*{v}\b|\b{v}\s*==\s*(?:nullptr|NULL|0|INVALID_HANDLE_VALUE|INVALID_SOCKET|-1)(?!\w)|"
            rf"\b(?:nullptr|NULL|INVALID_HANDLE_VALUE|INVALID_SOCKET)\s*==\s*{v}\b|\b{v}\s*<\s*0\b",
            cond,
        )
    )


def _leaks(pending: dict[str, int], detail: str, conds: dict[int, str]) -> list[str]:
    active = " ".join(conds.values())
    return [
        f"`{v}` (L{ln})"
        for v, ln in sorted(pending.items(), key=lambda kv: (kv[1], kv[0]))
        if not re.search(rf"\b{re.escape(v)}\b", detail) and not _null_checked(v, active)
    ]


def build_skeleton(
    lines: list[str], start: int, end: int, label: str | None, rel: str, changed: set[int]
) -> str:
    stripped_all = strip_code(lines)
    nodes: list[str] = []
    depth = 0
    pending: dict[str, int] = {}
    conds: dict[int, str] = {}
    single: tuple[int, str] | None = None
    stats = {"returns": 0, "early": 0, "throws": 0, "loops": 0, "warnings": 0}

    def emit(d: int, n: int, text: str) -> None:
        prefix = "│   " * max(d - 1, 0) + "├── "
        mark = " ✏️" if n in changed else ""
        nodes.append(f"{prefix}[L{n}] {text}{mark}")

    def exit_text(kw: str, detail: str, early: bool) -> str:
        stats["throws" if kw == "throw" else "returns"] += 1
        if early:
            stats["early"] += 1
        text = ("🛑 " if early else "↩ ") + kw.upper()
        if detail:
            text += " " + detail
        leaks = _leaks(pending, detail, conds)
        if leaks:
            stats["warnings"] += 1
            text += f" ⚠️ {'early exit; ' if early else ''}{', '.join(leaks)} not released on this path"
        return text

    def inline_stmt(after_code: str, after_orig: str, d: int, n: int) -> None:
        im = re.match(r"^(return|co_return|throw|break|continue|goto)\b", after_code)
        if not im:
            return
        ikw = im.group(1)
        semi = after_code.find(";")
        idetail = md.clip(after_orig[len(ikw) : semi if semi >= 0 else len(after_orig)].strip(), 80)
        if ikw in ("return", "co_return", "throw"):
            emit(d + 1, n, exit_text(ikw, idetail, True))
        else:
            emit(d + 1, n, f"{ikw.upper()} {idetail}".rstrip())

    first = md.clip(lines[start - 1].strip(), 100)
    header_mark = " ✏️" if start in changed else ""
    for n in range(start, end + 1):
        code = stripped_all[n - 1]
        orig = lines[n - 1]
        s = code.strip()
        tmp, lead = s, 0
        while tmp.startswith("}"):
            lead += 1
            tmp = tmp[1:].lstrip()
        eff = depth - lead
        opens, closes = code.count("{"), code.count("}")
        depth += opens - closes
        if n == start or not s:
            continue
        for k in [k for k in conds if k > eff]:
            del conds[k]
        if single is not None:
            eff = max(eff, single[0] + 1)
            conds[eff] = single[1]
            single = None
            if s == "{":
                continue
        tags: list[str] = []
        if _LOCK.search(code):
            tags.append("🔒 LOCK")
        if _UNLOCK.search(code):
            tags.append("🔓 UNLOCK")
        rel_m = _RELEASE.search(code)
        if rel_m:
            com = _COM_RELEASE.search(code)
            vm = None if com else _RELEASE_VAR.search(code, rel_m.start())
            var = com.group(1) if com else ((vm.group(1) or vm.group(2)) if vm else "")
            tags.append(f"📤 RELEASE `{var}`" if var else "📤 RELEASE")
            if var:
                pending.pop(var, None)
        else:
            alloc_m = _ALLOC.search(code)
            if alloc_m:
                am = _ASSIGN_VAR.search(code, 0, alloc_m.start())
                var = am.group(1) if am else ""
                tags.append(f"📥 ALLOC `{var}`" if var else "📥 ALLOC")
                if var:
                    pending[var] = n
        offset = len(code) - len(code.lstrip())
        m = _CONTROL.match(code, offset)
        if not m:
            if tags:
                emit(eff, n, f"{' · '.join(tags)} — {md.clip(orig.strip(), 80)}")
            continue
        kw = re.sub(r"\s+", " ", m.group(1))
        kw_end = m.end()
        tag_suffix = (" · " + " · ".join(tags)) if tags else ""
        if kw in _BRANCH_KEYS:
            bp = balanced_parens(code, kw_end)
            detail = md.clip(orig[bp[0] + 1 : bp[1]].strip(), 80) if bp else ""
            if kw in ("for", "while"):
                stats["loops"] += 1
            emit(eff, n, (f"{kw.upper()} ({detail})" if detail else kw.upper()) + tag_suffix)
            after_idx = bp[1] + 1 if bp else kw_end
            after_code = code[after_idx:].strip()
            after_orig = orig[after_idx:].strip()
            cond = detail if kw in ("if", "else if", "while") else ""
            if not after_code:
                single = (eff, cond)
            elif after_code.startswith("{"):
                conds[eff + 1] = cond
            else:
                inline_stmt(after_code, after_orig, eff, n)
        elif kw in ("else", "do", "try"):
            emit(eff, n, kw.upper() + tag_suffix)
            after_code = code[kw_end:].strip()
            after_orig = orig[kw_end:].strip()
            if not after_code:
                single = (eff, "")
            elif after_code.startswith("{"):
                conds[eff + 1] = ""
            else:
                inline_stmt(after_code, after_orig, eff, n)
        elif kw in ("case", "default"):
            colon = code.find(":", kw_end)
            detail = md.clip(orig[kw_end : colon if colon >= 0 else len(orig)].strip(), 80)
            emit(eff, n, (f"{kw.upper()} {detail}".rstrip()) + tag_suffix)
        elif kw in ("return", "co_return", "throw"):
            semi = code.find(";", kw_end)
            detail = md.clip(orig[kw_end : semi if semi >= 0 else len(orig)].strip(), 80)
            emit(eff, n, exit_text(kw, detail, eff >= 2) + tag_suffix)
        else:  # break / continue / goto
            semi = code.find(";", kw_end)
            detail = md.clip(orig[kw_end : semi if semi >= 0 else len(orig)].strip(), 80)
            emit(eff, n, (f"{kw.upper()} {detail}".rstrip()) + tag_suffix)
    title = f"`{label}` (`{rel}` L{start}-{end})" if label else f"`{rel}` L{start}-{end}"
    if not nodes:
        return f"### 🌿 BRANCH SKELETON: {title}\n✅ No control-flow branches, locks or allocations found in this range."
    summary = (
        f"Paths: {md.plural(stats['returns'], 'return')}, {md.plural(stats['throws'], 'throw')} "
        f"({md.plural(stats['early'], 'early exit')}), {md.plural(stats['loops'], 'loop')}"
    )
    if stats["warnings"]:
        summary += f"; ⚠️ {md.plural(stats['warnings'], 'potential leak path')}"
    body_nodes = md.truncate_list(nodes, MAX_SKELETON_NODES, "nodes", "Pass a narrower start_line/end_line range.")
    out = [
        f"### 🌿 BRANCH SKELETON: {title}",
        summary + ".",
        "```text",
        f"[L{start}] ENTRY {first}{header_mark}",
        *body_nodes,
        "```",
        "_✏️ changed in diff · 🛑 early exit · ⚠️ heuristic (comment/string-stripped text + brace depth, not a compiler)._",
    ]
    return "\n".join(out)


def _match_symbol(tags: list[Tag], symbol: str) -> list[Tag]:
    sym = symbol.strip()
    short = sym.rsplit("::", 1)[-1]
    out = []
    for t in tags:
        if t.kind not in FUNCTION_KINDS:
            continue
        if t.qualified == sym or t.name == sym:
            out.append(t)
        elif "::" not in sym and t.short_name == short:
            out.append(t)
        elif "::" in sym and t.qualified.endswith("::" + short) and t.qualified.endswith(sym):
            out.append(t)
    uniq: dict[int, Tag] = {}
    for t in out:
        uniq.setdefault(t.line, t)
    return [uniq[k] for k in sorted(uniq)]


async def branch_skeleton_report(
    cfg: Config, file_path: str, symbol: str = "", start_line: int = 0, end_line: int = 0, base_ref: str = ""
) -> str:
    abs_path, rel = resolve_in_workspace(cfg.workspace_root, file_path)
    _check_cpp(rel)
    lines = read_lines(abs_path)
    total = len(lines)
    label: str | None = None
    note = ""
    if symbol and symbol.strip():
        tags = await ctags_for_file(cfg, rel)
        found = _match_symbol(tags, symbol)
        if not found:
            names = sorted({t.qualified for t in tags if t.kind in FUNCTION_KINDS})
            listing = ", ".join(f"`{n}`" for n in names[:12]) or "none"
            raise InvalidArgument(
                f"No function named `{symbol}` found in `{rel}`.", f"Functions in this file: {listing}."
            )
        tag = found[0]
        start, end, label = tag.line, tag.end, tag.qualified
        if len(found) > 1:
            note = "_Overloads also at: " + ", ".join(f"L{t.line}" for t in found[1:]) + "._"
    elif start_line and end_line:
        if start_line < 1 or end_line < start_line or start_line > total:
            raise InvalidArgument(f"Invalid range L{start_line}-{end_line}: `{rel}` has {total} lines.")
        start, end = start_line, min(end_line, total)
        tags = await ctags_for_file(cfg, rel)
        fn = innermost(tags, start, FUNCTION_KINDS)
        if fn and fn.line == start:
            label = fn.qualified
    elif start_line:
        if start_line < 1 or start_line > total:
            raise InvalidArgument(f"Line {start_line} is out of range: `{rel}` has {total} lines.")
        tags = await ctags_for_file(cfg, rel)
        fn = innermost(tags, start_line, FUNCTION_KINDS) or innermost(tags, start_line, BLOCK_KINDS - {"namespace"})
        if fn is None:
            raise InvalidArgument(
                f"No function encloses `{rel}:{start_line}`.", "Pass an explicit start_line and end_line range instead."
            )
        start, end, label = fn.line, fn.end, fn.qualified
    else:
        raise InvalidArgument("Provide `symbol`, or `start_line` (optionally with `end_line`).")
    end = min(end, total, start + MAX_SKELETON_LINES - 1)
    changed = await changed_lines(cfg, rel, base_ref)
    report = build_skeleton(lines, start, end, label, rel, changed)
    return report + ("\n" + note if note else "")


async def get_branch_skeleton(file_path: str, symbol: str = "", start_line: int = 0, end_line: int = 0) -> str:
    """Returns only the control-flow skeleton of a C++ function (if/else/switch/case/for/while/do/try/catch/return/throw/break/continue/goto) as an indented tree, annotated with lock acquisitions, allocations/releases, early exits that may leak a resource, and lines changed in the current diff. Use to audit logic paths, error handling and resource pairing cheaply instead of reading the full body. Select the function by symbol name, by start_line (enclosing function), or by an explicit start_line..end_line range."""
    return await branch_skeleton_report(load_config(), file_path, symbol, start_line, end_line)


async def extract_control_flow_skeleton(file_path: str, start_line: int, end_line: int) -> str:
    """Backward-compatible alias of get_branch_skeleton for an explicit line range."""
    return await get_branch_skeleton(file_path, start_line=start_line, end_line=end_line)
