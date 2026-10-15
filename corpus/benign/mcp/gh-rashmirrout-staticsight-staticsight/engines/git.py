"""git helpers: base-ref resolution and a `git diff -U0` hunk parser."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..config import Config
from ..core.errors import InvalidArgument, StaticSightError
from ..core.paths import read_lines
from .base import run_engine

DEFAULT_BASE_CANDIDATES = ("origin/main", "origin/master", "main", "master")
_HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


class NotAGitRepo(StaticSightError):
    title = "Not a git repository"


@dataclass
class FileDiff:
    path: str
    old_path: str
    status: str  # modified | added | deleted | renamed | untracked
    added_lines: set[int] = field(default_factory=set)
    removed_at: dict[int, int] = field(default_factory=dict)  # new-side anchor line -> removed line count
    additions: int = 0
    deletions: int = 0
    binary: bool = False

    @property
    def touched_lines(self) -> set[int]:
        return set(self.added_lines) | set(self.removed_at)


@dataclass
class DiffInfo:
    base_sha: str
    base_label: str
    files: list[FileDiff]

    def get(self, path: str) -> FileDiff | None:
        for f in self.files:
            if f.path == path:
                return f
        return None


async def _git(cfg: Config, *args: str, check: bool = True) -> str:
    res = await run_engine("git", ["-c", "core.quotepath=off", *args], cwd=cfg.workspace_root, timeout=cfg.timeout_s)
    if check and res.returncode != 0:
        err = res.stderr.strip()
        if "not a git repository" in err.lower():
            raise NotAGitRepo(
                f"`{cfg.workspace_root}` is not inside a git repository.",
                "Set WORKSPACE_ROOT to the root of a git checkout.",
            )
        raise StaticSightError(f"`git {' '.join(args[:2])}` failed: {err[:300]}")
    return res.stdout


async def _rev(cfg: Config, ref: str) -> str | None:
    res = await run_engine(
        "git", ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd=cfg.workspace_root, timeout=cfg.timeout_s
    )
    sha = res.stdout.strip()
    return sha if res.returncode == 0 and sha else None


async def _merge_base(cfg: Config, ref: str) -> str | None:
    res = await run_engine("git", ["merge-base", "HEAD", ref], cwd=cfg.workspace_root, timeout=cfg.timeout_s)
    sha = res.stdout.strip()
    return sha if res.returncode == 0 and sha else None


async def head_sha(cfg: Config) -> str:
    """Current HEAD commit, or '' when git is unavailable or the repo has no commits."""
    try:
        return await _rev(cfg, "HEAD") or ""
    except StaticSightError:
        return ""


async def resolve_base(cfg: Config, base_ref: str = "") -> tuple[str, str]:
    """Return (sha, human label) for the diff base."""
    await _git(cfg, "rev-parse", "--git-dir")
    ref = (base_ref or cfg.base_ref).strip()
    if ref:
        if ref.startswith("-"):
            raise InvalidArgument(f"`{ref}` is not a valid git ref.")
        sha = await _rev(cfg, ref)
        if not sha:
            raise InvalidArgument(f"git ref `{ref}` does not exist.", "Use a branch, tag or commit, e.g. `origin/main`.")
        mb = await _merge_base(cfg, ref)
        if mb and mb != sha:
            return mb, f"merge-base with `{ref}` ({mb[:10]})"
        return sha, f"`{ref}` ({sha[:10]})"
    for cand in DEFAULT_BASE_CANDIDATES:
        if await _rev(cfg, cand):
            mb = await _merge_base(cfg, cand)
            if mb:
                return mb, f"merge-base with `{cand}` ({mb[:10]})"
    head = await _rev(cfg, "HEAD")
    if not head:
        raise StaticSightError("The repository has no commits yet.", "Commit something or pass base_ref.")
    return head, f"`HEAD` ({head[:10]}), no origin/main or origin/master found"


def _unquote(p: str) -> str:
    p = p.rstrip("\t")
    if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
        p = p[1:-1].encode("latin-1", "backslashreplace").decode("unicode_escape", errors="replace")
    return p


def parse_diff(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    cur: FileDiff | None = None
    in_hunk = False
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r'^diff --git (?:"?a/)(.+?)"? (?:"?b/)(.+?)"?$', line)
            a, b = (m.group(1), m.group(2)) if m else ("", "")
            cur = FileDiff(path=b, old_path=a, status="modified")
            files.append(cur)
            in_hunk = False
            continue
        if cur is None:
            continue
        if not in_hunk:
            if line.startswith("new file mode"):
                cur.status = "added"
            elif line.startswith("deleted file mode"):
                cur.status = "deleted"
            elif line.startswith("rename from "):
                cur.old_path = _unquote(line[len("rename from "):])
                cur.status = "renamed"
            elif line.startswith("rename to "):
                cur.path = _unquote(line[len("rename to "):])
                cur.status = "renamed"
            elif line.startswith("Binary files "):
                cur.binary = True
            elif line.startswith("--- "):
                p = _unquote(line[4:])
                if p != "/dev/null" and p.startswith("a/"):
                    cur.old_path = p[2:]
            elif line.startswith("+++ "):
                p = _unquote(line[4:])
                if p == "/dev/null":
                    cur.status = "deleted"
                    cur.path = cur.old_path
                elif p.startswith("b/"):
                    cur.path = p[2:]
        m = _HUNK.match(line)
        if m:
            in_hunk = True
            old_count = int(m.group(2)) if m.group(2) is not None else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) is not None else 1
            if new_count > 0:
                cur.added_lines.update(range(new_start, new_start + new_count))
            if old_count > 0:
                anchor = new_start if new_count > 0 else max(new_start, 1)
                cur.removed_at[anchor] = cur.removed_at.get(anchor, 0) + old_count
            continue
        if in_hunk:
            if line.startswith("+"):
                cur.additions += 1
            elif line.startswith("-"):
                cur.deletions += 1
            elif line.startswith("diff --git "):
                in_hunk = False
    return files


async def collect_diff(cfg: Config, base_ref: str = "", include_untracked: bool = True, path: str | None = None) -> DiffInfo:
    sha, label = await resolve_base(cfg, base_ref)
    args = ["diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "-M", sha, "--"]
    if path:
        args.append(path)
    files = parse_diff(await _git(cfg, *args))
    if include_untracked:
        ls_args = ["ls-files", "--others", "--exclude-standard", "-z", "--"]
        if path:
            ls_args.append(path)
        out = await _git(cfg, *ls_args)
        for rel in sorted(p for p in out.split("\0") if p):
            fd = FileDiff(path=rel, old_path=rel, status="untracked")
            try:
                n = len(read_lines(cfg.workspace_root / rel))
            except StaticSightError:
                n = 0
            except OSError:
                n = 0
            fd.added_lines = set(range(1, n + 1))
            fd.additions = n
            files.append(fd)
    files.sort(key=lambda f: f.path)
    return DiffInfo(base_sha=sha, base_label=label, files=files)


async def show_blob(cfg: Config, sha: str, path: str) -> str | None:
    res = await run_engine("git", ["show", f"{sha}:{path}"], cwd=cfg.workspace_root, timeout=cfg.timeout_s)
    if res.returncode != 0:
        return None
    return res.stdout


async def changed_lines(cfg: Config, rel_path: str, base_ref: str = "") -> set[int]:
    """Best-effort: lines of rel_path touched by the current diff (empty when git is unavailable)."""
    try:
        info = await collect_diff(cfg, base_ref, path=rel_path)
    except StaticSightError:
        return set()
    fd = info.get(rel_path)
    return fd.touched_lines if fd else set()
