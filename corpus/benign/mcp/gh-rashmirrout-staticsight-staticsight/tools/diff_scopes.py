"""get_diff_scopes: map the current git diff to C++ scopes, detect signature/layout/header/macro changes."""

from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..config import Config, is_cpp_file, is_header, load_config
from ..core import md
from ..engines.ctags import BLOCK_KINDS, FUNCTION_KINDS, TYPE_KINDS, Tag, ctags_for_files, ctags_for_temp, innermost
from ..engines.git import DiffInfo, FileDiff, collect_diff, show_blob
from ..core.paths import matches_glob, read_lines
from ..core.errors import StaticSightError

_DEFINE = re.compile(r"^\s*#\s*define\s+(\w+)")
SCOPE_KINDS = BLOCK_KINDS - {"namespace"}


@dataclass
class ScopeChange:
    tag: Tag
    lines: set[int] = field(default_factory=set)
    removed: int = 0
    is_new: bool = False
    signature_changed: str = ""  # "old -> new"
    layout: bool = False  # data members / virtuals changed inside a class/struct/union/enum

    @property
    def kind(self) -> str:
        return self.tag.kind


@dataclass
class FileReport:
    diff: FileDiff
    scopes: list[ScopeChange] = field(default_factory=list)
    file_level: set[int] = field(default_factory=set)
    macros: list[str] = field(default_factory=list)
    removed_symbols: list[Tag] = field(default_factory=list)
    include_changes: bool = False


@dataclass
class DiffScopes:
    info: DiffInfo
    reports: list[FileReport]
    other_files: list[FileDiff]

    def changed_functions(self) -> list[tuple[FileReport, ScopeChange]]:
        return [(r, s) for r in self.reports for s in r.scopes if s.kind in FUNCTION_KINDS]

    def changed_types(self) -> list[tuple[FileReport, ScopeChange]]:
        return [(r, s) for r in self.reports for s in r.scopes if s.kind in TYPE_KINDS]

    def changed_headers(self) -> list[FileReport]:
        return [r for r in self.reports if is_header(r.diff.path)]


def _sig_key(t: Tag) -> str:
    return re.sub(r"\s+", " ", f"{t.return_type} {t.signature}".strip())


async def _old_tags(cfg: Config, sha: str, fd: FileDiff) -> list[Tag] | None:
    blob = await show_blob(cfg, sha, fd.old_path)
    if blob is None:
        return None
    suffix = os.path.splitext(fd.old_path)[1] or ".cpp"
    with tempfile.TemporaryDirectory(prefix="staticsight-") as tmp:
        p = Path(tmp) / f"old{suffix}"
        p.write_text(blob, encoding="utf-8", errors="replace")
        return await ctags_for_temp(cfg, p, fd.old_path)


async def analyse_diff(cfg: Config, base_ref: str = "", path_glob: str = "") -> DiffScopes:
    info = await collect_diff(cfg, base_ref)
    cpp_files = [f for f in info.files if is_cpp_file(f.path) and not f.binary and matches_glob(f.path, path_glob)]
    other = [f for f in info.files if f not in cpp_files and matches_glob(f.path, path_glob)]
    live = [f.path for f in cpp_files if f.status != "deleted"]
    tags_by_file = await ctags_for_files(cfg, live) if live else {}
    reports: list[FileReport] = []
    for fd in cpp_files:
        rep = FileReport(diff=fd)
        reports.append(rep)
        old_tags: list[Tag] | None = None
        if fd.status in ("modified", "renamed", "deleted"):
            try:
                old_tags = await _old_tags(cfg, info.base_sha, fd)
            except StaticSightError:
                old_tags = None
        if fd.status == "deleted":
            rep.removed_symbols = sorted(
                [t for t in (old_tags or []) if t.kind in SCOPE_KINDS and not t.scope], key=lambda t: t.line
            )
            continue
        tags = tags_by_file.get(fd.path, [])
        try:
            lines = read_lines(cfg.workspace_root / fd.path)
        except StaticSightError:
            lines = []
        by_key: dict[tuple, ScopeChange] = {}
        for ln in sorted(fd.touched_lines):
            probe = min(max(ln, 1), max(len(lines), 1))
            tag = innermost(tags, probe, SCOPE_KINDS)
            text = lines[probe - 1] if 0 < probe <= len(lines) else ""
            dm = _DEFINE.match(text) if ln in fd.added_lines else None
            if dm and dm.group(1) not in rep.macros:
                rep.macros.append(dm.group(1))
            if ln in fd.added_lines and re.match(r"^\s*#\s*include\b", text):
                rep.include_changes = True
            if tag is None:
                if ln in fd.added_lines and text.strip():
                    rep.file_level.add(ln)
                continue
            key = (tag.line, tag.kind, tag.qualified)
            sc = by_key.get(key)
            if sc is None:
                sc = by_key[key] = ScopeChange(tag=tag)
            if ln in fd.added_lines:
                sc.lines.add(ln)
            sc.removed += fd.removed_at.get(ln, 0)
        member_lines = {t.line for t in tags if t.kind in ("member", "enumerator")}
        for sc in by_key.values():
            span = set(range(sc.tag.line, sc.tag.end + 1))
            sc.is_new = fd.status in ("added", "untracked") or span <= fd.added_lines
            if sc.kind in TYPE_KINDS:
                touched = fd.touched_lines & span
                sc.layout = any(
                    ln in member_lines
                    or ln not in fd.added_lines
                    or (0 < ln <= len(lines) and re.search(r"\bvirtual\b", lines[ln - 1]))
                    for ln in touched
                )
        if old_tags is not None:
            old_by_name: dict[str, list[Tag]] = {}
            for t in old_tags:
                if t.kind in SCOPE_KINDS | {"prototype"}:
                    old_by_name.setdefault(t.qualified, []).append(t)
            new_names = {t.qualified for t in tags}
            for sc in by_key.values():
                olds = old_by_name.get(sc.tag.qualified)
                if not olds:
                    continue
                sc.is_new = False
                if sc.kind in ("function", "prototype", "macro"):
                    old_sigs = {_sig_key(o) for o in olds if o.kind == sc.kind}
                    new_sig = _sig_key(sc.tag)
                    if old_sigs and new_sig not in old_sigs:
                        old = sorted(old_sigs)[0]
                        sc.signature_changed = f"{old} -> {new_sig}"
            removed = [
                t for name, ts in old_by_name.items() if name not in new_names for t in ts if t.kind in SCOPE_KINDS
            ]
            rep.removed_symbols = sorted(removed, key=lambda t: (t.line, t.qualified))
            # declaration-only changes (prototypes inside headers/classes)
            for t in tags:
                touched = fd.touched_lines & set(range(t.line, t.end + 1))
                if t.kind != "prototype" or not touched:
                    continue
                old_sigs = {_sig_key(o) for o in old_by_name.get(t.qualified, []) if o.kind == "prototype"}
                key = (t.line, t.kind, t.qualified)
                if not old_sigs:
                    by_key[key] = ScopeChange(tag=t, lines=touched & fd.added_lines, is_new=True)
                elif _sig_key(t) not in old_sigs:
                    by_key[key] = ScopeChange(
                        tag=t, lines=touched & fd.added_lines, signature_changed=f"{sorted(old_sigs)[0]} -> {_sig_key(t)}"
                    )
        rep.scopes = sorted(by_key.values(), key=lambda s: (s.tag.line, s.tag.qualified))
    return DiffScopes(info=info, reports=reports, other_files=other)


def _status_label(fd: FileDiff) -> str:
    if fd.status == "renamed":
        return f"renamed from `{fd.old_path}`"
    return {"untracked": "new, untracked"}.get(fd.status, fd.status)


def _scope_line(sc: ScopeChange) -> str:
    t = sc.tag
    rng = f"L{t.line}" if t.line == t.end else f"L{t.line}-{t.end}"
    parts = [f"`{t.qualified}` ({t.kind}, {rng})"]
    if sc.is_new:
        parts.append("🆕 new")
    else:
        detail = md.compress_ranges(sc.lines) if sc.lines else ""
        if detail:
            parts.append(f"changed {detail}")
        if sc.removed:
            parts.append(f"{sc.removed} line(s) removed")
    if sc.signature_changed:
        old, new = sc.signature_changed.split(" -> ", 1)
        parts.append(f"🔁 signature `{old}` → `{new}`")
    if t.kind in TYPE_KINDS and not sc.is_new:
        parts.append("🧱 layout change (data members/virtuals)" if sc.layout else "declarations changed (no data-member change detected)")
    return "- " + " — ".join(parts)


def _new_file_line(rep: FileReport, limit: int) -> str:
    fns = [sc for sc in rep.scopes if sc.kind in FUNCTION_KINDS]
    types = [sc for sc in rep.scopes if sc.kind in TYPE_KINDS]
    macros = [sc for sc in rep.scopes if sc.kind == "macro"]
    line = f"- 🆕 new file: {md.plural(len(fns), 'function')}, {md.plural(len(types), 'type')}, {md.plural(len(macros), 'macro')}"
    names = [f"`{sc.tag.qualified}`" for sc in fns + types][: min(limit, 8)]
    if names:
        extra = len(fns) + len(types) - len(names)
        line += ": " + ", ".join(names) + (f", … (+{extra} more)" if extra > 0 else "")
    return line


def suggestions(ds: DiffScopes, limit: int) -> list[str]:
    out: list[str] = []
    for rep, sc in ds.changed_functions():
        if sc.is_new and not sc.signature_changed:
            continue
        out.append(f'`get_branch_skeleton("{rep.diff.path}", symbol="{sc.tag.qualified}")`')
        out.append(f'`get_upstream_callers("{sc.tag.short_name}")`')
    for rep in ds.reports:
        for sc in rep.scopes:
            if sc.kind == "prototype" and (sc.signature_changed or sc.is_new):
                out.append(f'`get_upstream_callers("{sc.tag.short_name}")` — declaration changed')
    for rep, sc in ds.changed_types():
        if sc.layout and not sc.is_new:
            out.append(f'`track_struct_risks("{sc.tag.short_name}")`')
    for rep in ds.reports:
        if is_header(rep.diff.path):
            out.append(f'`get_include_blast_radius("{rep.diff.path}")`')
        elif rep.diff.status != "deleted":
            out.append(f'`run_file_static_audit("{rep.diff.path}", only_changed_lines=true)`')
        for t in rep.removed_symbols:
            if t.kind in FUNCTION_KINDS:
                out.append(f'`get_upstream_callers("{t.short_name}")` — removed, check for dangling callers')
    for rep, sc in ds.changed_functions():
        if sc.is_new and not sc.signature_changed:
            out.append(f'`get_branch_skeleton("{rep.diff.path}", symbol="{sc.tag.qualified}")` — audit the new function')
    return md.truncate_list(list(dict.fromkeys(out)), limit, "suggestions")


def render_diff_scopes(ds: DiffScopes, cfg: Config, compact: bool = False) -> str:
    info = ds.info
    adds = sum(r.diff.additions for r in ds.reports)
    dels = sum(r.diff.deletions for r in ds.reports)
    out = [f"### 🧭 DIFF SCOPES vs {info.base_label}"]
    if not ds.reports and not ds.other_files:
        out.append("✅ No changes found (committed, staged, unstaged or untracked) relative to the base.")
        return "\n".join(out)
    out.append(
        f"{md.plural(len(ds.reports), 'C/C++ file')} changed (+{adds} / -{dels})"
        + (f"; {md.plural(len(ds.other_files), 'other file')} ignored" if ds.other_files else "")
        + "."
    )
    limit = cfg.max_results
    counts: dict[str, int] = {}
    for rep in ds.reports:
        counts[rep.diff.status] = counts.get(rep.diff.status, 0) + 1
    if len(ds.reports) > 1:
        out.append("By status: " + ", ".join(f"{n} {s}" for s, n in sorted(counts.items())) + ".")
    if len(ds.reports) > 20:
        out.append("_Large diff: new files are summarised; use `path_glob` to focus on one area._")
    for rep in ds.reports:
        fd = rep.diff
        kind = "header" if is_header(fd.path) else "source"
        out.append("")
        out.append(f"#### `{fd.path}` ({kind}, {_status_label(fd)}, +{fd.additions} -{fd.deletions})")
        if fd.status == "deleted":
            if rep.removed_symbols:
                names = ", ".join(f"`{t.qualified}`" for t in rep.removed_symbols[:limit])
                out.append(f"- 🗑️ file deleted; top-level symbols removed: {names}")
            else:
                out.append("- 🗑️ file deleted")
            continue
        if fd.status in ("added", "untracked"):
            out.append(_new_file_line(rep, limit))
            continue
        items = [_scope_line(sc) for sc in rep.scopes]
        out += md.truncate_list(items, limit, "changed scopes", "Use path_glob to focus on one file.")
        if rep.file_level:
            out.append(f"- file-level lines (outside any function/type): {md.compress_ranges(rep.file_level, 12)}")
        if rep.macros:
            out.append("- 🔣 macros defined/changed: " + ", ".join(f"`{m}`" for m in rep.macros[:limit]))
        if rep.include_changes:
            out.append("- 📎 #include lines changed")
        if rep.removed_symbols:
            out.append(
                "- 🗑️ removed: " + ", ".join(f"`{t.qualified}` ({t.kind})" for t in rep.removed_symbols[:limit])
            )
    if not compact:
        sugg = suggestions(ds, limit)
        if sugg:
            out += ["", "#### 🔎 Suggested next calls", *[f"- {s}" if not s.startswith("_") else s for s in sugg]]
    return "\n".join(out)


async def get_diff_scopes(base_ref: str = "", path_glob: str = "") -> str:
    """Maps every changed line of the current diff to the exact C++ function, method, class, struct, enum or macro that encloses it (via Universal Ctags). Also reports new and removed symbols, signature changes (old -> new), struct/class layout changes, header changes, deleted/renamed files, and suggests the next tool calls. Use this first to learn WHAT changed before asking who is affected."""
    cfg = load_config()
    ds = await analyse_diff(cfg, base_ref, path_glob)
    return render_diff_scopes(ds, cfg)
