"""Ingest a project into the catalog.

The pipeline that fills the data layer. Orchestrates analysis, seam detection,
component extraction, and capability recording to build a queryable library of
repositories and their reusable components.

Idempotent: ingesting the same repository at the same commit twice leaves the
catalog in the same state, not doubled. Content-addressed ids make this automatic.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..arch.graph import build_graph
from ..arch.seams import find_seams
from ..core.output import Reporter
from ..core.registry import AnalysisContext
from ..extract.engine import execute_plan
from ..extract.planner import plan_extraction, select_by_cluster, select_by_seam
from .store import Catalog

__all__ = ["ingest", "IngestResult"]


@dataclass(slots=True)
class IngestResult:
    """What was recorded during an ingest."""

    repo_id: str
    repo_record_count: int = 1
    components_recorded: int = 0
    components_stored: int = 0
    facts_recorded: int = 0
    capabilities_recorded: int = 0
    stored_component_ids: list[str] = field(default_factory=list)
    failures: dict[str, str] = field(default_factory=dict)
    """Failures during ingest: phase -> error message."""


def ingest(
    catalog: Catalog,
    project_path: Path | str,
    *,
    store_components: bool = False,
    reporter: Reporter | None = None,
    include_tests: bool = True,
    max_files: int | None = None,
) -> IngestResult:
    """Ingest a project into the catalog.

    Builds the analysis context once and reuses it for everything. Records
    repository metadata, architectural facts, components (both seams and clusters),
    capabilities, and optionally stores component source trees.

    Args:
        catalog: The Catalog to write to.
        project_path: Root of the project to analyze.
        store_components: If True, extract and store source trees for seam components.
        reporter: Progress reporter (stderr). If None, creates a silent one.
        include_tests: Whether to include test files in analysis.
        max_files: Limit on files to analyze (None = no limit).

    Returns:
        IngestResult with counts of what was recorded and any failures.

    Raises:
        Nothing. Partial failures are recorded in the result; the function always
        returns with whatever succeeded.
    """
    reporter = reporter or Reporter()
    result = IngestResult(repo_id="")
    project_path = Path(project_path).resolve()

    if not project_path.is_dir():
        result.failures["init"] = f"not a directory: {project_path}"
        return result

    try:
        # Build one shared context for all analyzers
        reporter.step(f"analyzing {project_path.name}")
        ctx = AnalysisContext(
            project_path,
            policy=_walk_policy(include_tests=include_tests, max_files=max_files),
            reporter=reporter,
        )

        # Record repo metadata
        repo_record = _record_repo(
            catalog, ctx, project_path, reporter
        )
        result.repo_id = repo_record.id
        result.repo_record_count = 1

        # Record architectural findings as facts
        try:
            facts_count = _record_facts(catalog, ctx, repo_record.id, reporter)
            result.facts_recorded = facts_count
        except Exception as exc:
            result.failures["facts"] = f"{type(exc).__name__}: {exc}"
            reporter.warn(f"architecture analysis failed: {exc}")

        # Record components and capabilities
        try:
            comp_count, cap_count = _record_components(
                catalog, ctx, repo_record.id, reporter
            )
            result.components_recorded = comp_count
            result.capabilities_recorded = cap_count
        except Exception as exc:
            result.failures["components"] = f"{type(exc).__name__}: {exc}"
            reporter.warn(f"component detection failed: {exc}")

        # Store component source trees if requested
        if store_components and result.components_recorded > 0:
            try:
                stored_count, stored_ids = _store_components(
                    catalog, ctx, repo_record.id, project_path, reporter
                )
                result.components_stored = stored_count
                result.stored_component_ids = stored_ids
            except Exception as exc:
                result.failures["storage"] = f"{type(exc).__name__}: {exc}"
                reporter.warn(f"component storage failed: {exc}")

    except Exception as exc:
        result.failures["init"] = f"{type(exc).__name__}: {exc}"
        reporter.warn(f"ingest failed: {exc}")

    return result


# -- repo recording -----------------------------------------------------------


def _record_repo(
    catalog: Catalog,
    ctx: AnalysisContext,
    project_path: Path,
    reporter: Reporter,
) -> Any:
    """Record repository metadata."""
    reporter.sub("recording repository")

    name = project_path.name
    commit_sha = _get_commit_sha(project_path)
    branch = _get_branch(project_path)
    languages = sorted({f.lang for f in ctx.source_files() if f.lang})
    file_count = len(ctx.walk.files)

    from .. import __version__

    repo_record = catalog.put_repo(
        name=name,
        source=str(project_path),
        source_kind=_source_kind(project_path),
        commit_sha=commit_sha,
        branch=branch,
        languages=languages,
        file_count=file_count,
        drydock_ver=__version__,
        payload={},
    )

    return repo_record


def _source_kind(path: Path) -> str:
    """Determine if the path is a git repo, a regular directory, etc."""
    if (path / ".git").exists():
        return "git"
    return "path"


def _get_commit_sha(path: Path) -> str | None:
    """Get the current HEAD commit SHA, or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _get_branch(path: Path) -> str | None:
    """Get the current branch name, or None if not a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            return branch if branch != "HEAD" else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# -- facts recording ----------------------------------------------------------


def _record_facts(
    catalog: Catalog,
    ctx: AnalysisContext,
    repo_id: str,
    reporter: Reporter,
) -> int:
    """Run architecture analyzer and record findings as facts."""
    reporter.sub("analyzing architecture")

    from ..core.registry import get_analyzer

    analyzer = get_analyzer("architecture")
    if analyzer is None:
        reporter.warn("architecture analyzer not available")
        return 0

    try:
        result = analyzer.run(ctx, include_metrics=False)
    except Exception as exc:
        reporter.warn(f"architecture analyzer failed: {exc}")
        return 0

    principles = result.get("principles", [])
    for principle in principles:
        catalog.put_fact(
            repo_id=repo_id,
            principle=principle.get("id", "unknown"),
            name=principle.get("name", "unknown"),
            verdict=principle.get("verdict", "unknown"),
            summary=principle.get("summary", ""),
            evidence=principle.get("evidence", {}),
        )

    return len(principles)


# -- components recording -----------------------------------------------------


def _record_components(
    catalog: Catalog,
    ctx: AnalysisContext,
    repo_id: str,
    reporter: Reporter,
) -> tuple[int, int]:
    """Find and record components (seams and clusters) with capabilities."""
    reporter.sub("detecting components")

    comp_count = 0
    cap_count = 0

    # Build graph once for seam detection
    try:
        graph = build_graph(ctx)
    except Exception as exc:
        reporter.warn(f"dependency graph build failed: {exc}")
        return 0, 0

    _covered_files: set[str] = set()

    # Find and record seams
    try:
        seams = find_seams(ctx, graph)
        for seam in seams:  # Already sorted by find_seams
            comp_record = catalog.put_component(
                repo_id=repo_id,
                # Named after the package the contract lives in, not the file
                # stem: nearly every contract file is called `base.py` or
                # `types.go`, so stems collided and a catalog listing showed
                # several components all called "base".
                name=_seam_name(seam.contract),
                kind="seam",
                contract=seam.contract,
                cohesion=seam.cohesion,
                verdict=seam.verdict,
                file_count=len(seam.unit),
                languages=_languages_in_files(ctx, seam.unit),
                selection={"contract": seam.contract, "implementers": seam.implementers},
            )
            comp_count += 1

            # Record capabilities for this component
            _covered_files.update(seam.unit)
            caps = _extract_capabilities(ctx, seam.unit, repo_id)
            catalog.put_capabilities(comp_record.id, repo_id, caps)
            cap_count += len(caps)
    except Exception as exc:
        reporter.warn(f"seam detection failed: {exc}")

    # If no seams, detect and record clusters
    if comp_count == 0:
        try:
            clusters = _get_clusters(ctx)
            for cluster_id, file_ids in clusters.items():
                if not file_ids:
                    continue
                prefix = _common_prefix(file_ids)
                comp_record = catalog.put_component(
                    repo_id=repo_id,
                    name=prefix or f"cluster_{cluster_id}",
                    kind="cluster",
                    file_count=len(file_ids),
                    languages=_languages_in_files(ctx, file_ids),
                )
                comp_count += 1

                # Record capabilities for this component
                _covered_files.update(file_ids)
                caps = _extract_capabilities(ctx, file_ids, repo_id)
                catalog.put_capabilities(comp_record.id, repo_id, caps)
                cap_count += len(caps)
        except Exception as exc:
            reporter.warn(f"cluster detection failed: {exc}")

    # Index the rest of the repository. Only about a quarter of a real
    # project's modules fall inside a detected component, so without this a
    # user who ingests a repository and searches for a module they know is in
    # it gets nothing back -- which is the first thing anyone tries.
    try:
        covered = {fid for fid in _covered_files}
        remaining = tuple(
            sf.id for sf in ctx.source_files() if sf.id not in covered
        )
        if remaining:
            caps = _extract_capabilities(ctx, remaining, repo_id)
            catalog.put_capabilities(None, repo_id, caps)
            cap_count += len(caps)
            reporter.sub(
                f"indexed {len(caps)} symbols from {len(remaining)} modules "
                "outside any component"
            )
    except Exception as exc:
        reporter.warn(f"repository-wide indexing failed: {exc}")

    return comp_count, cap_count


def _languages_in_files(ctx: AnalysisContext, file_ids: tuple[str, ...]) -> list[str]:
    """Get sorted unique languages for a set of files."""
    langs = set()
    for fid in file_ids:
        sf = ctx.file(fid)
        if sf and sf.lang:
            langs.add(sf.lang)
    return sorted(langs)


def _seam_name(contract: str) -> str:
    """Name a seam after its package rather than its filename.

    Contract modules are conventionally called `base.py`, `types.go` or
    `interface.ts`, so naming a component after the file stem produced several
    components called "base" in one repository and gave a reader nothing to
    tell them apart.
    """
    parts = [p for p in contract.split("/")[:-1] if p]
    stem = contract.split("/")[-1].rsplit(".", 1)[0]
    if not parts:
        return stem
    if stem in ("base", "types", "interface", "interfaces", "protocol",
                "contract", "abc", "api", "mod", "__init__"):
        return parts[-1]
    return f"{parts[-1]}.{stem}"


def _extract_capabilities(
    ctx: AnalysisContext, file_ids: tuple[str, ...] | set[str], repo_id: str
) -> list[dict[str, Any]]:
    """Extract public symbols from files as capabilities.

    Interface already contains only public symbols, so no privacy filtering needed.
    """
    caps: list[dict[str, Any]] = []

    for fid in sorted(file_ids):
        sf = ctx.file(fid)
        if not sf:
            continue

        interface = ctx.interface(sf)
        if not interface or interface.is_empty():
            continue

        # Record classes and their public methods
        for cls in interface.classes:
            caps.append({
                "module": fid,
                "symbol": cls.name,
                "kind": "class",
                "signature": f"class {cls.name}",
                "doc": cls.doc,
                "lang": sf.lang,
            })
            # Record public methods
            for method in cls.methods:
                sig = f"{cls.name}.{method.render()}"
                caps.append({
                    "module": fid,
                    "symbol": method.name,
                    "kind": "method",
                    "signature": sig,
                    "doc": method.doc,
                    "lang": sf.lang,
                })

        # Record functions
        for func in interface.functions:
            caps.append({
                "module": fid,
                "symbol": func.name,
                "kind": "function",
                "signature": func.render(),
                "doc": func.doc,
                "lang": sf.lang,
            })

        # Record types (type definitions, enums, etc.)
        for typ in interface.types:
            caps.append({
                "module": fid,
                "symbol": typ.name,
                "kind": "type",
                "signature": f"type {typ.name}",
                "doc": typ.definition,
                "lang": sf.lang,
            })

        # Record constants
        for const in interface.constants:
            caps.append({
                "module": fid,
                "symbol": const.name,
                "kind": "constant",
                "signature": const.name,
                "doc": None,
                "lang": sf.lang,
            })

    return caps


def _get_clusters(ctx: AnalysisContext) -> dict[int, set[str]]:
    """Get component clusters from boundaries analyzer."""
    from ..core.registry import get_analyzer

    analyzer = get_analyzer("boundaries")
    if analyzer is None:
        return {}

    try:
        result = analyzer.run(ctx)
        clusters: dict[int, set[str]] = {}
        for cluster in result.get("clusters", []):
            cluster_id = cluster.get("id")
            files = set(cluster.get("files", []))
            if cluster_id is not None and files:
                clusters[cluster_id] = files
        return clusters
    except Exception:
        return {}


def _common_prefix(file_ids: set[str] | tuple[str, ...]) -> str:
    """Find the common directory prefix for a set of files."""
    if not file_ids:
        return ""
    file_list = sorted(file_ids)
    if len(file_list) == 1:
        return str(Path(file_list[0]).parent)

    parts_list = [Path(fid).parts for fid in file_list]
    common: list[str] = []
    for parts in zip(*parts_list):
        if all(p == parts[0] for p in parts):
            common.append(parts[0])
        else:
            break

    return "/".join(common) if common else ""


# -- component storage --------------------------------------------------------


def _store_components(
    catalog: Catalog,
    ctx: AnalysisContext,
    repo_id: str,
    project_path: Path,
    reporter: Reporter,
) -> tuple[int, list[str]]:
    """Extract and store component source trees."""
    reporter.sub("storing components")

    stored_count = 0
    stored_ids: list[str] = []

    # Fetch seam components only (storage is for seams)
    components = catalog.components(repo_id=repo_id, kind="seam")

    for comp in components:
        try:
            # Select files for this seam by its contract
            selection = select_by_seam(ctx, comp.contract or comp.name)
            if not selection:
                reporter.warn(f"could not select files for {comp.name}")
                continue

            # Plan the extraction with the component name
            plan = plan_extraction(ctx, selection, component=comp.name)

            # Check for blocking breakages
            blocking_breakages = [
                b for b in plan.breakages if b.severity == "blocking"
            ]
            if blocking_breakages:
                reporter.warn(
                    f"{comp.name} has {len(blocking_breakages)} blocking breakages; "
                    "skipping storage"
                )
                continue

            # Execute the extraction in a temp directory
            with tempfile.TemporaryDirectory(prefix=".drydock-ingest-") as tmpdir:
                extract_result = execute_plan(
                    plan,
                    tmpdir,
                    reporter=reporter,
                    allow_blocking=False,
                )

                # Store the extracted tree in the catalog
                if extract_result.output.exists():
                    catalog.store_component_content(comp.id, extract_result.output)
                    stored_count += 1
                    stored_ids.append(comp.id)
                    reporter.step(f"  stored {comp.name}")

        except Exception as exc:
            reporter.warn(f"failed to store {comp.name}: {exc}")

    return stored_count, stored_ids


# -- walk policy --------------------------------------------------------------


def _walk_policy(include_tests: bool = True, max_files: int | None = None):
    """Create a walk policy for analysis."""
    from ..core.walker import WalkPolicy

    return WalkPolicy(
        include_tests=include_tests,
        follow_symlinks=False,
        max_files=max_files,
    )
