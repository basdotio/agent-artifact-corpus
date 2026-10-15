"""run_file_static_audit: cppcheck on a single uncompiled file, XML parsed, findings mapped onto the diff."""

from __future__ import annotations

from ..config import Config, is_cpp_file, load_config
from ..core import md
from ..core.errors import InvalidArgument
from ..core.paths import read_lines, resolve_in_workspace
from ..engines.cppcheck import MSVC_ARGS, SEVERITY_ORDER, Finding, parse_cppcheck_xml, run_cppcheck, wants_msvc
from ..engines.ctags import FUNCTION_KINDS, innermost, try_ctags_for_files
from ..engines.git import changed_lines, collect_diff

__all__ = ["Finding", "parse_cppcheck_xml", "run_file_static_audit", "static_audit_report"]


async def static_audit_report(cfg: Config, file_path: str, only_changed_lines: bool = False, base_ref: str = "") -> str:
    abs_path, rel = resolve_in_workspace(cfg.workspace_root, file_path)
    if not is_cpp_file(rel):
        raise InvalidArgument(f"`{rel}` is not a C/C++ file.")
    lines = read_lines(abs_path)

    msvc = wants_msvc("\n".join(lines))

    async def run(include: bool):
        return await run_cppcheck(cfg, rel, abs_path, include, MSVC_ARGS if msvc else None)

    findings, elsewhere, version, parse_problem, macros = await run(True)
    retried = False
    if parse_problem:
        f2, e2, v2, p2, m2 = await run(False)
        if not p2 or len(f2) > len(findings):
            findings, elsewhere, version, parse_problem, retried = f2, e2, v2, p2, True
            macros = macros + [m for m in m2 if m not in macros]
    if base_ref:
        info = await collect_diff(cfg, base_ref, path=rel)
        fd = info.get(rel)
        changed = fd.touched_lines if fd else set()
    else:
        changed = await changed_lines(cfg, rel)
    tags = (await try_ctags_for_files(cfg, [rel])).get(rel, [])
    changed_fns = {innermost(tags, ln, FUNCTION_KINDS) for ln in changed} - {None}

    def where(f: Finding) -> str:
        if any(loc[1] in changed for loc in f.locations):
            return "diff"
        fn = innermost(tags, f.line, FUNCTION_KINDS)
        if fn is not None and fn in changed_fns:
            return "fn"
        return ""

    title = f"### 🚨 STATIC AUDIT: `{rel}`" + (f" (cppcheck {version})" if version else "")
    total = len(findings)
    if only_changed_lines:
        findings = [f for f in findings if where(f)]
    out = [title]
    if not findings:
        scope = " on changed lines/functions" if only_changed_lines else ""
        extra = f" ({total} elsewhere in the file)" if only_changed_lines and total else ""
        out.append(f"✅ No cppcheck findings{scope}{extra}.")
    else:
        counts: dict[str, int] = {}
        for f in findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        sev = ", ".join(f"{n} {s}" for s, n in sorted(counts.items(), key=lambda kv: SEVERITY_ORDER.get(kv[0], 9)))
        in_diff = sum(1 for f in findings if where(f) == "diff")
        summary = f"{md.plural(len(findings), 'finding')} ({sev}); {in_diff} on changed lines."
        if only_changed_lines and total > len(findings):
            summary += f" {total - len(findings)} more outside the change (rerun with only_changed_lines=false)."
        out.append(summary)
        items = []
        for i, f in enumerate(findings, 1):
            w = where(f)
            mark = "✏️ " if w == "diff" else ("🔶 " if w == "fn" else "")
            cwe = f" (CWE-{f.cwe})" if f.cwe and f.cwe != "0" else ""
            entry = [f"{i}. {mark}**L{f.line}** `[{f.severity}: {f.id}]` {f.msg}{cwe}"]
            if 0 < f.line <= len(lines):
                entry.append(f"   {md.code_span(lines[f.line - 1])}")
            extra_locs = [loc for loc in f.locations[1:] if loc[1] != f.line]
            if extra_locs:
                entry.append("   ↳ " + "; ".join(f"L{ln}" + (f": {md.clip(info, 80)}" if info else "") for _, ln, info in extra_locs[:4]))
            items.append("\n".join(entry))
        out += md.truncate_list(items, cfg.max_results, "findings")
    notes = []
    if msvc:
        notes.append("MSVC mode: Windows/SAL code detected, cppcheck ran with `--library=windows --platform=win64`")
    if elsewhere:
        notes.append(f"{elsewhere} finding(s) located in included headers were omitted")
    macro_txt = f" (unknown macro {', '.join(f'`{m}`' for m in macros[:3])})" if macros else ""
    if retried:
        notes.append(f"re-ran without include paths because included headers could not be parsed{macro_txt}")
    if parse_problem:
        notes.append(f"cppcheck could not fully parse this file{macro_txt}, so coverage is partial; pass defines via STATICSIGHT_CPPCHECK_ARGS")
    notes.append("zero-compile mode: includes are best-effort and missing-include diagnostics are suppressed")
    out.append("\n_" + "; ".join(notes) + ". ✏️ = on a changed line, 🔶 = inside a changed function._")
    return "\n".join(out)


async def run_file_static_audit(file_path: str, only_changed_lines: bool = False, base_ref: str = "") -> str:
    """Runs cppcheck (no compilation, best-effort includes) on one C/C++ file and returns findings sorted by severity: memory/resource leaks, null dereferences, out-of-bounds, uninitialised variables, use-after-free, bad casts, performance and portability issues. Findings on lines changed in the current diff are marked. Use on every modified .cpp/.c file during review."""
    return await static_audit_report(load_config(), file_path, only_changed_lines, base_ref)

