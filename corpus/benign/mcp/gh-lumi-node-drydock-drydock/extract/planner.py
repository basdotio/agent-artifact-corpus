"""Turn a selection of files into a reviewable extraction plan.

The planner answers the question `boundaries` deliberately does not: given
that you want these files, what actually has to come with them, and what will
be broken if it does not?

Three things it will not do quietly:

* Pull in a dependency without saying so. Anything dragged along by the
  transitive closure is marked ``reason="closure"``, so the difference between
  what was asked for and what came with it is visible in the plan.
* Leave a package unimportable. Selecting ``pkg/a.py`` without
  ``pkg/__init__.py`` produces a package Python cannot import; the missing
  ``__init__`` is added as ``reason="package-init"``.
* Hide the cost of leaving. Files *outside* the selection that import *into*
  it are reported as ``external-dependent`` breakages -- those are the call
  sites that will break in the project you are extracting from, which is the
  half of the story a naive copy silently omits.
"""

from __future__ import annotations

from collections import deque
from pathlib import PurePosixPath
from typing import Iterable, Sequence

from ..core.models import FileId, SourceFile
from ..core.registry import AnalysisContext
from .models import Breakage, ExtractionPlan, PlannedFile

__all__ = [
    "plan_extraction",
    "select_by_cluster",
    "select_by_dir",
    "select_by_files",
    "select_by_seam",
    "list_seams",
]

_INIT_NAMES = {"__init__.py"}


# --------------------------------------------------------------------------
# selection
# --------------------------------------------------------------------------

def select_by_dir(ctx: AnalysisContext, prefix: str) -> set[FileId]:
    """Every source file under `prefix` (matched by path segment)."""
    parts = tuple(p for p in prefix.strip("/").split("/") if p)
    out: set[FileId] = set()
    for sf in ctx.source_files():
        if tuple(sf.id.split("/"))[: len(parts)] == parts:
            out.add(sf.id)
    return out


def select_by_files(ctx: AnalysisContext, files: Iterable[str]) -> set[FileId]:
    known = {sf.id for sf in ctx.walk.files}
    return {f for f in (x.strip() for x in files) if f in known}


def list_seams(ctx: AnalysisContext) -> list[dict]:
    """Contract-shaped cut points, best first. See `drydock.arch.seams`."""
    from ..arch.graph import build_graph
    from ..arch.seams import find_seams

    return [s.as_dict() for s in find_seams(ctx, build_graph(ctx))]


def select_by_seam(ctx: AnalysisContext, contract: str) -> set[FileId]:
    """The contract plus everything that implements it.

    Consumers are deliberately excluded: they keep depending on the contract
    from outside, which is exactly what a plug point is for. Including them
    would drag half the codebase along and defeat the seam.
    """
    from ..arch.graph import build_graph
    from ..arch.seams import find_seams

    graph = build_graph(ctx)
    for seam in find_seams(ctx, graph):
        if seam.contract == contract or seam.contract.endswith("/" + contract.lstrip("/")):
            return set(seam.unit)
    return set()


def select_by_cluster(ctx: AnalysisContext, cluster_id: int) -> set[FileId]:
    """Files in a cluster reported by the boundaries analyzer."""
    from ..core.registry import registry

    analyzer = registry.get("boundaries")
    if analyzer is None:  # pragma: no cover
        return set()
    result = analyzer.run(ctx, **{o.name: o.default for o in analyzer.options})
    for cluster in result.get("clusters", []):
        if cluster.get("id") == cluster_id:
            return set(cluster.get("files", []))
    return set()


# --------------------------------------------------------------------------
# planning
# --------------------------------------------------------------------------

def plan_extraction(
    ctx: AnalysisContext,
    selected: set[FileId],
    *,
    component: str,
    closure: bool = True,
    include_tests: bool = True,
    copy_package_inits: bool = False,
    selection: dict | None = None,
) -> ExtractionPlan:
    """Build an `ExtractionPlan` for `selected`.

    `closure=True` follows internal imports and brings the dependencies along.
    `closure=False` takes only what was selected and reports every internal
    dependency left behind as a blocking breakage -- useful when the intent is
    to extract an interface and reimplement underneath it.
    """
    index = ctx.index
    by_id = {sf.id: sf for sf in ctx.walk.files}

    forward, reverse, unresolved, ambiguous, external = _build_edges(ctx)

    included: dict[FileId, str] = {f: "selected" for f in sorted(selected)}
    breakages: list[Breakage] = []

    if closure:
        # Closure and package-__init__ inclusion are mutually recursive and must
        # be iterated to a fixpoint. Running the closure once and *then* adding
        # __init__.py files leaves those inits' own imports unclosed: extracting
        # a subpackage pulled in its parent __init__.py, which re-exported five
        # sibling modules that were never included, and the extracted package
        # failed to import. Keep going until nothing new is added.
        queue: deque[FileId] = deque(selected)
        while True:
            while queue:
                current = queue.popleft()
                for dep in sorted(forward.get(current, ())):
                    if dep not in included:
                        included[dep] = "closure"
                        queue.append(dep)

            added = False
            for fid in list(included):
                for init in _missing_inits(fid, included, by_id):
                    included[init] = "package-init"
                    added = True
                    # Only follow an __init__'s own imports when the operator
                    # asked for the original file. A synthesized stub has none.
                    if copy_package_inits:
                        queue.append(init)
            if not added:
                break
    else:
        for src in sorted(selected):
            for dep in sorted(forward.get(src, ())):
                if dep not in selected:
                    breakages.append(
                        Breakage(
                            kind="missing-internal-dep",
                            severity="blocking",
                            file=src,
                            target=dep,
                            detail=f"{src} imports {dep}, which is not in the selection",
                            hint="re-run with closure enabled, or stub this dependency",
                        )
                    )

    # A package directory that loses its __init__.py is not importable.
    for fid in list(included):
        for init in _missing_inits(fid, included, by_id):
            included.setdefault(init, "package-init")

    if not include_tests:
        included = {
            f: r for f, r in included.items()
            if not (by_id.get(f) and by_id[f].role == "test")
        }

    # Callers left behind in the source project.
    for fid in sorted(included):
        for dependent in sorted(reverse.get(fid, ())):
            if dependent not in included:
                breakages.append(
                    Breakage(
                        kind="external-dependent",
                        severity="warning",
                        file=fid,
                        target=dependent,
                        detail=f"{dependent} imports {fid} and is not being extracted",
                        hint="that import will break in the source project",
                    )
                )

    for fid in sorted(included):
        for raw in sorted(unresolved.get(fid, ())):
            breakages.append(
                Breakage(
                    kind="unresolved-import",
                    severity="warning",
                    file=fid,
                    target=raw,
                    detail=f"{fid} imports {raw!r}, which could not be resolved",
                    hint="verify by hand whether this is third-party or internal",
                )
            )
        for raw in sorted(ambiguous.get(fid, ())):
            breakages.append(
                Breakage(
                    kind="ambiguous-import",
                    severity="warning",
                    file=fid,
                    target=raw,
                    detail=f"{fid} imports {raw!r}, which matched several candidates",
                )
            )

    root_prefix = _common_dir(included)
    files: list[PlannedFile] = []

    # The component root itself must be a package, or the extracted tree is a
    # namespace package: `import langpack.langs` works only by accident of
    # sys.path, and packaging back ends cannot find anything to ship. Nothing
    # in the source maps to `<component>/__init__.py`, so it is synthesized.
    needs_root_init = any(
        (by_id.get(f) and by_id[f].lang == "python") for f in included
    ) and not any(
        _destination(f, root_prefix, component) == f"{component}/__init__.py"
        for f in included
    )
    dest_seen: dict[str, FileId] = {}
    for fid in sorted(included):
        sf = by_id.get(fid)
        dest = _destination(fid, root_prefix, component)
        if dest in dest_seen:
            breakages.append(
                Breakage(
                    kind="name-collision",
                    severity="blocking",
                    file=fid,
                    target=dest_seen[dest],
                    detail=f"{fid} and {dest_seen[dest]} both map to {dest}",
                    hint="extract a narrower selection, or rename one file",
                )
            )
        dest_seen[dest] = fid
        files.append(
            PlannedFile(
                source=fid,
                destination=dest,
                reason=included[fid],  # type: ignore[arg-type]
                lang=sf.lang if sf else None,
                synthesized=(
                    included[fid] == "package-init" and not copy_package_inits
                ),
            )
        )

    if needs_root_init:
        files.append(
            PlannedFile(
                source="",
                destination=f"{component}/__init__.py",
                reason="package-init",
                lang="python",
                synthesized=True,
            )
        )

    files.sort(key=lambda f: f.destination)

    plan = ExtractionPlan(
        project=ctx.root.name,
        source_commit=_git_commit(ctx.root),
        source_root=str(ctx.root),
        component=component,
        files=files,
        breakages=breakages,
        external_deps=_external_requirements(ctx, set(included), external),
        module_map=_module_map(included, root_prefix, component, by_id),
        languages=sorted({f.lang for f in files if f.lang}),
        # Record HOW the files were chosen, not just which ones. Without this
        # the manifest lists an outcome that cannot be reproduced against a
        # later commit -- the whole point of recording provenance.
        selection=dict(selection or {}),
    )
    return plan


# --------------------------------------------------------------------------
# internals
# --------------------------------------------------------------------------

def _build_edges(ctx: AnalysisContext):
    """Forward/reverse internal edges plus the unresolved and external tallies."""
    forward: dict[FileId, set[FileId]] = {}
    reverse: dict[FileId, set[FileId]] = {}
    unresolved: dict[FileId, set[str]] = {}
    ambiguous: dict[FileId, set[str]] = {}
    external: dict[FileId, set[str]] = {}

    index = ctx.index
    for sf in ctx.source_files():
        for imp in ctx.imports(sf):
            res = index.resolve(imp, from_file=sf.id, lang=sf.lang or "")
            if res.targets:
                for tgt in res.targets:
                    if tgt == sf.id:
                        continue
                    forward.setdefault(sf.id, set()).add(tgt)
                    reverse.setdefault(tgt, set()).add(sf.id)
            elif res.ambiguous:
                ambiguous.setdefault(sf.id, set()).add(imp.raw)
            elif res.external:
                external.setdefault(sf.id, set()).add(imp.raw)
            elif imp.raw:
                unresolved.setdefault(sf.id, set()).add(imp.raw)

    return forward, reverse, unresolved, ambiguous, external


def _missing_inits(
    fid: FileId, included: dict[FileId, str], by_id: dict[FileId, SourceFile]
) -> list[FileId]:
    """`__init__.py` files needed to keep `fid` importable."""
    if not fid.endswith(".py"):
        return []
    out: list[FileId] = []
    parts = fid.split("/")[:-1]
    while parts:
        candidate = "/".join(parts + ["__init__.py"])
        if candidate in by_id and candidate not in included:
            out.append(candidate)
        parts = parts[:-1]
    return out


def _common_dir(files: Iterable[FileId]) -> str:
    """Deepest directory prefix shared by all files, by whole segments."""
    parts_list = [f.split("/")[:-1] for f in files]
    if not parts_list:
        return ""
    shared: list[str] = []
    for level in zip(*parts_list):
        if len(set(level)) == 1:
            shared.append(level[0])
        else:
            break
    return "/".join(shared)


def _destination(fid: FileId, root_prefix: str, component: str) -> str:
    rel = fid[len(root_prefix):].lstrip("/") if root_prefix else fid
    return f"{component}/{rel}" if rel else f"{component}/{PurePosixPath(fid).name}"


def _module_map(
    included: dict[FileId, str],
    root_prefix: str,
    component: str,
    by_id: dict[FileId, SourceFile],
) -> dict[str, str]:
    """Old dotted module path -> new dotted module path, for the rewriters."""
    mapping: dict[str, str] = {}
    for fid in sorted(included):
        sf = by_id.get(fid)
        if not sf or sf.lang != "python":
            continue
        old = _dotted(fid)
        rel = fid[len(root_prefix):].lstrip("/") if root_prefix else fid
        new = _dotted(f"{component}/{rel}")
        if old and new:
            mapping[old] = new
    return mapping


def _git_commit(root) -> str | None:
    """Commit the extraction was taken from, so provenance is checkable.

    Recorded on the plan (not only in the engine's manifest) because the
    generated pyproject.toml and EXTRACTION.md both cite it, and an
    extraction whose origin cannot be pinned down is a good deal less useful
    six months later.
    """
    import subprocess

    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root, capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return (r.stdout.strip() or None) if r.returncode == 0 else None


def _dotted(path: str) -> str:
    p = PurePosixPath(path)
    parts = list(p.parts)
    if p.name in _INIT_NAMES:
        parts = parts[:-1]
    else:
        parts[-1] = p.stem
    return ".".join(parts)


def _external_requirements(
    ctx: AnalysisContext, included: set[FileId], external: dict[FileId, set[str]]
) -> dict[str, list[str]]:
    """Third-party packages the extracted files still need, by ecosystem."""
    import sys

    stdlib = getattr(sys, "stdlib_module_names", frozenset())
    by_lang: dict[str, set[str]] = {}
    by_id = {sf.id: sf for sf in ctx.walk.files}

    for fid in included:
        sf = by_id.get(fid)
        if not sf or not sf.lang:
            continue
        for raw in external.get(fid, ()):  # noqa: B007
            top = raw.split(".")[0].split("::")[0].split("/")[0].lstrip("@")
            if not top:
                continue
            if sf.lang == "python" and top in stdlib:
                continue
            by_lang.setdefault(sf.lang, set()).add(top)

    return {k: sorted(v) for k, v in by_lang.items()}
