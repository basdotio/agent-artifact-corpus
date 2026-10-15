"""Engine discovery + capability checks (used by get_index_status, `staticsight doctor`, and the ctags adapter)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..core.errors import StaticSightError, ToolFailed, ToolMissing
from ..platform import current
from .base import find_engine

# (engine, level) - level: required | recommended | optional
ENGINES: list[tuple[str, str]] = [
    ("ctags", "required"),
    ("rg", "required"),
    ("git", "required"),
    ("cppcheck", "recommended"),
    ("global", "optional"),
    ("gtags", "optional"),
]
PURPOSE = {
    "ctags": "scopes, signatures, skeletons (Universal Ctags with JSON)",
    "rg": "fast text search: struct risks, includes, mutations, fallbacks",
    "git": "diffs, base refs, changed-line markers",
    "cppcheck": "run_file_static_audit",
    "global": "precise callers/definitions (ripgrep fallback without it)",
    "gtags": "builds the GNU Global index",
}
EXUBERANT_HINT = (
    "This is not Universal Ctags with JSON support (Exuberant Ctags and some minimal builds lack it). "
    "Install Universal Ctags; on Windows note that `scoop install ctags` is Exuberant - use "
    "`scoop bucket add extras; scoop install universal-ctags` or `winget install UniversalCtags.Ctags`."
)


@dataclass
class EngineStatus:
    name: str
    level: str
    path: str = ""
    version: str = ""
    ok: bool = False
    problem: str = ""
    hint: str = ""


_cache: dict[tuple[str, str], EngineStatus] = {}


async def _first_line(tool: str, exe: str, args: list[str]) -> str:
    try:
        res = await current().run(exe, args, cwd=str(Path.home()), timeout=10, display_name=tool)
    except (StaticSightError, OSError):
        return ""
    for ln in (res.stdout + "\n" + res.stderr).splitlines():
        if ln.strip():
            return ln.strip()
    return ""


async def probe(tool: str, level: str = "") -> EngineStatus:
    level = level or dict(ENGINES).get(tool, "optional")
    exe = find_engine(tool)
    if exe is None:
        return EngineStatus(tool, level, problem="not found on PATH", hint=current().install_hint(tool) or "")
    key = (tool, exe)
    if key in _cache:
        return _cache[key]
    st = EngineStatus(tool, level, path=exe, ok=True)
    st.version = await _first_line(tool, exe, ["--version"])
    if tool == "ctags":
        features = ""
        try:
            res = await current().run(exe, ["--list-features"], cwd=str(Path.home()), timeout=10, display_name=tool)
            features = res.stdout
        except (StaticSightError, OSError):
            pass
        if "exuberant" in st.version.lower() or "json" not in features.lower():
            st.ok = False
            st.problem = f"`{st.version or 'ctags'}` has no JSON output"
            st.hint = EXUBERANT_HINT
    _cache[key] = st
    return st


async def probe_all() -> list[EngineStatus]:
    return [await probe(t, lvl) for t, lvl in ENGINES]


async def ensure_ctags() -> None:
    """Fail fast with a precise message when ctags is missing or cannot emit JSON."""
    st = await probe("ctags")
    if not st.path:
        raise ToolMissing("ctags", st.hint or None)
    if not st.ok:
        raise ToolFailed(st.problem, st.hint)


def clear_cache() -> None:
    _cache.clear()
