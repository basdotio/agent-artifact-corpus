"""MCP server, generated from the analyzer registry.

Every registered analyzer becomes an MCP tool automatically, with its options
turned into typed parameters from the same `Option` declarations the CLI uses.
Registering a new analyzer -- built-in or third-party -- exposes it over MCP
with no edit here, which is the whole point of routing both surfaces through
one declaration.

The pre-0.2 server hand-wrote seven wrappers and needed a `redirect_stdout`
shim, because the analyzers printed progress to stdout and would otherwise
corrupt the JSON-RPC stream. Progress now goes to stderr by construction, so
the shim is gone rather than merely relocated.

Requires the ``mcp`` extra::

    pip install "drydock[mcp]"
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any, Sequence

from .core.output import dumps
from .core.registry import AnalysisContext, Analyzer, Option, available
from .core.walker import WalkPolicy

__all__ = ["build_server", "serve"]


def _run_analyzer(analyzer: Analyzer, project_path: str, opts: dict[str, Any]) -> str:
    """Execute one analyzer and return its JSON payload as text."""
    root = Path(project_path).expanduser()
    if not root.exists():
        return dumps({"error": f"project path not found: {project_path}"})
    if not root.is_dir():
        return dumps({"error": f"not a directory: {project_path}"})

    include_tests = bool(opts.pop("include_tests", True))
    max_files = opts.pop("max_files", None)

    ctx = AnalysisContext(
        root,
        policy=WalkPolicy(
            include_tests=include_tests,
            max_files=int(max_files) if max_files else None,
        ),
    )
    known = {o.name for o in analyzer.options}
    call_opts = {o.name: o.default for o in analyzer.options}
    call_opts.update({k: v for k, v in opts.items() if k in known})

    try:
        return dumps(analyzer.run(ctx, **call_opts))
    except Exception as exc:
        return dumps({"error": f"{type(exc).__name__}: {exc}", "analyzer": analyzer.name})


def _make_tool(analyzer: Analyzer):
    """Build a typed callable for `analyzer` that FastMCP can introspect.

    FastMCP derives its JSON schema from the function signature, so the
    signature is constructed from the analyzer's `Option` list and attached
    via ``__signature__``.
    """

    def tool(**kwargs: Any) -> str:
        project_path = kwargs.pop("project_path")
        return _run_analyzer(analyzer, project_path, kwargs)

    params = [
        inspect.Parameter(
            "project_path", inspect.Parameter.KEYWORD_ONLY, annotation=str
        )
    ]
    annotations: dict[str, Any] = {"project_path": str, "return": str}

    for opt in analyzer.options:
        params.append(
            inspect.Parameter(
                opt.name,
                inspect.Parameter.KEYWORD_ONLY,
                default=opt.default,
                annotation=opt.type,
            )
        )
        annotations[opt.name] = opt.type

    # Scope controls every analyzer understands, mirroring the CLI. Skip any an
    # analyzer already declares, so a plugin naming one of these cannot produce
    # a duplicate-parameter signature and take the whole server down at import.
    declared = {p.name for p in params}
    for extra_name, extra_default, extra_type in (
        ("include_tests", True, bool),
        ("max_files", 0, int),
    ):
        if extra_name in declared:
            continue
        params.append(
            inspect.Parameter(
                extra_name,
                inspect.Parameter.KEYWORD_ONLY,
                default=extra_default,
                annotation=extra_type,
            )
        )
        annotations[extra_name] = extra_type

    tool.__signature__ = inspect.Signature(params, return_annotation=str)  # type: ignore[attr-defined]
    tool.__annotations__ = annotations
    tool.__name__ = f"drydock_{analyzer.name}"
    tool.__doc__ = _tool_doc(analyzer)
    return tool


def _tool_doc(analyzer: Analyzer) -> str:
    lines = [analyzer.description.strip(), "", "Args:",
             "    project_path: Absolute or relative path to the project root."]
    for opt in analyzer.options:
        lines.append(f"    {opt.name}: {opt.help} (default: {opt.default!r})")
    lines.append("    include_tests: Include files classified as tests (default: True).")
    lines.append("    max_files: Stop after N files, 0 for no limit (default: 0).")
    return "\n".join(lines)


def _run_extract(project_path: str, cluster: int = -1, dir: str = "", files: str = "",
                  component: str = "", output: str = "", closure: bool = True,
                  dry_run: bool = True, include_tests: bool = True,
                  max_files: int = 0) -> str:
    """Execute extraction and return results as JSON.

    By default (dry_run=True), plans only without writing files. Pass dry_run=False
    and an output path to materialize the extraction.
    """
    from .extract import (
        plan_extraction,
        select_by_cluster,
        select_by_dir,
        select_by_files,
    )
    from .extract.engine import execute_plan, ExtractionError
    from .extract.rewriters import rewriter_for

    root = Path(project_path).expanduser()
    if not root.exists():
        return dumps({"error": f"project path not found: {project_path}"})
    if not root.is_dir():
        return dumps({"error": f"not a directory: {project_path}"})

    try:
        # Validate exactly one selection
        selections = [
            (cluster != -1, "cluster", cluster),
            (bool(dir), "dir", dir),
            (bool(files), "files", files),
        ]
        active = [s for s in selections if s[0]]
        if len(active) != 1:
            return dumps({
                "error": "exactly one selection required (cluster, dir, or files)"
            })

        # Build context
        ctx = AnalysisContext(
            root,
            policy=WalkPolicy(
                include_tests=include_tests,
                max_files=int(max_files) if max_files else None,
            ),
        )

        # Select files
        # active[0] is (is_set, name, value). Unpacking the flag into
        # `selection_type` made every comparison below compare a bool to a
        # string, so `--dir` silently fell through to the file-list branch and
        # extraction over MCP never matched anything.
        _flag, selection_type, selection_arg = active[0]
        if selection_type == "cluster":
            selected = select_by_cluster(ctx, cluster)
        elif selection_type == "dir":
            selected = select_by_dir(ctx, dir)
        else:  # files
            selected = select_by_files(ctx, files.split(","))

        if not selected:
            return dumps({"error": f"no files matched selection ({selection_type})"})

        # Plan the extraction
        plan = plan_extraction(
            ctx,
            selected,
            component=component or "",
            closure=closure,
            include_tests=include_tests,
        )

        # Plan-only mode (dry_run=True)
        if dry_run or not output:
            return dumps(plan)

        # Execute mode
        out_path = Path(output).expanduser()
        result = execute_plan(
            plan,
            out_path,
            force=False,
            allow_blocking=False,
            rewriter_for=rewriter_for,
        )

        return dumps({
            "plan": plan,
            "result": result.summary(),
        })

    except ExtractionError as exc:
        return dumps({"error": str(exc), "kind": "extraction_error"})
    except Exception as exc:
        return dumps({
            "error": f"{type(exc).__name__}: {exc}",
            "kind": "internal_error"
        })


def _catalog_search(query: str, kind: str = "", limit: int = 25) -> str:
    """Full-text search across ingested repositories and components.

    Answers the primary question the catalog exists to solve: "Do I already have
    a component or capability that does X?" Search indexes repository names,
    component names, contracts, and extracted public symbols.
    """
    from .catalog.store import Catalog

    try:
        catalog = Catalog()
        hits = catalog.search(query, kind=kind or None, limit=limit)
        return dumps([{
            "subject_id": h.subject_id,
            "subject_kind": h.subject_kind,
            "repo_id": h.repo_id,
            "title": h.title,
            "snippet": h.snippet,
            "rank": h.rank,
        } for h in hits])
    finally:
        catalog.close()


def _catalog_list() -> str:
    """List all ingested repositories in the catalog."""
    from .catalog.store import Catalog

    try:
        catalog = Catalog()
        repos = catalog.repos()
        return dumps([{
            "id": r.id,
            "name": r.name,
            "source": r.source,
            "commit_sha": r.commit_sha,
            "branch": r.branch,
            "languages": r.languages,
            "file_count": r.file_count,
            "ingested_at": r.ingested_at,
        } for r in repos])
    finally:
        catalog.close()


def _catalog_components(repo: str = "", kind: str = "", language: str = "",
                        min_cohesion: float = 0.0, stored_only: bool = False) -> str:
    """List components in the catalog with optional filtering.

    Args:
        repo: Filter by repository id (empty = all repos).
        kind: Filter by component kind (seam, cluster, directory, manual).
        language: Filter by programming language.
        min_cohesion: Minimum cohesion score (0.0-1.0); 0 = no filter.
        stored_only: Show only components whose code is stored in the catalog.
    """
    from .catalog.store import Catalog

    try:
        catalog = Catalog()
        components = catalog.components(
            repo_id=repo or None,
            kind=kind or None,
            language=language or None,
            min_cohesion=min_cohesion if min_cohesion > 0 else None,
            stored_only=stored_only,
        )
        return dumps([{
            "id": c.id,
            "repo_id": c.repo_id,
            "name": c.name,
            "kind": c.kind,
            "contract": c.contract,
            "cohesion": c.cohesion,
            "languages": c.languages,
            "file_count": c.file_count,
            "is_stored": c.is_stored,
            "summary": c.summary,
        } for c in components])
    finally:
        catalog.close()


def _catalog_facts(repo: str = "") -> str:
    """List architectural facts discovered during analysis.

    Facts capture high-level observations about a repository's structure
    and architecture, with evidence that could guide refactoring.

    Args:
        repo: Filter by repository id (empty = all repos).
    """
    from .catalog.store import Catalog

    try:
        catalog = Catalog()
        facts = catalog.facts(repo_id=repo or None)
        return dumps([{
            "id": f.id,
            "repo_id": f.repo_id,
            "principle": f.principle,
            "name": f.name,
            "verdict": f.verdict,
            "summary": f.summary,
            "derived": f.derived,
            "recorded_at": f.recorded_at,
        } for f in facts])
    finally:
        catalog.close()


def _catalog_ingest(project_path: str, store: bool = False) -> str:
    """Ingest a project into the catalog, recording its structure and components.

    This mutates the user's catalog and should only be called when explicitly
    requested. Idempotent: ingesting the same commit twice updates existing
    records rather than creating duplicates.

    Args:
        project_path: Absolute or relative path to the project to ingest.
        store: If True, store extracted component code trees in the catalog.
               Without this, only metadata is recorded.
    """
    from pathlib import Path
    from .catalog.store import Catalog
    from .core.output import Reporter

    try:
        root = Path(project_path).expanduser()
        if not root.exists():
            return dumps({"error": f"project path not found: {project_path}"})
        if not root.is_dir():
            return dumps({"error": f"not a directory: {project_path}"})

        try:
            from .catalog.ingest import ingest
        except ImportError as exc:
            return dumps({"error": f"ingest module not available: {exc}"})

        catalog = Catalog()
        reporter = Reporter(quiet=True)
        result = ingest(
            catalog,
            root,
            store_components=store,
            reporter=reporter,
        )

        return dumps({
            "repo_id": result.repo_id,
            "components_recorded": result.components_recorded,
            "components_stored": result.components_stored,
            "facts_recorded": result.facts_recorded,
            "capabilities_recorded": result.capabilities_recorded,
            "failures": result.failures if result.failures else None,
        })
    except Exception as exc:
        return dumps({"error": f"{type(exc).__name__}: {exc}"})


def build_server(name: str = "drydock"):
    """Construct a FastMCP server exposing every registered analyzer."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "the MCP server needs the 'mcp' package: pip install 'drydock[mcp]'"
        ) from exc

    blurb = "Software architecture analysis: map, decompose and extract codebases"

    # The FastMCP constructor renamed this argument across releases
    # (`description` -> `instructions`), and the pre-0.2 server hard-coded the
    # older spelling, so it raised TypeError against a current `mcp` install.
    # Probe the signature rather than pinning to one version.
    try:
        accepted = set(inspect.signature(FastMCP.__init__).parameters)
    except (TypeError, ValueError):  # pragma: no cover
        accepted = set()

    for keyword in ("instructions", "description"):
        if keyword in accepted:
            server = FastMCP(name, **{keyword: blurb})
            break
    else:  # pragma: no cover - very old or very new signature
        server = FastMCP(name)

    for analyzer in available().values():
        server.add_tool(
            _make_tool(analyzer),
            name=f"drydock_{analyzer.name}",
            description=analyzer.summary,
        )

    # Add hand-written extraction tool
    server.add_tool(
        _run_extract,
        name="drydock_extract",
        description=(
            "Extract a component from a project as a standalone package. "
            "By default returns a reviewable plan without writing files. "
            "Requires exactly one selection: cluster, dir, or files."
        ),
    )

    # Add hand-written catalog tools
    server.add_tool(
        _catalog_search,
        name="drydock_catalog_search",
        description=(
            "Search the catalog for components, repositories, or capabilities. "
            "This is the primary tool for answering: Do I already have something "
            "that does X? Full-text search across names, contracts, and public symbols."
        ),
    )

    server.add_tool(
        _catalog_list,
        name="drydock_catalog_list",
        description=(
            "List all ingested repositories in the catalog."
        ),
    )

    server.add_tool(
        _catalog_components,
        name="drydock_catalog_components",
        description=(
            "List components in the catalog with optional filtering by repository, "
            "kind, language, cohesion score, and storage status."
        ),
    )

    server.add_tool(
        _catalog_facts,
        name="drydock_catalog_facts",
        description=(
            "List architectural facts (high-level findings) about repositories, "
            "with evidence that may guide refactoring decisions."
        ),
    )

    server.add_tool(
        _catalog_ingest,
        name="drydock_catalog_ingest",
        description=(
            "Ingest a project into the catalog, recording its structure and components. "
            "This operation mutates the user's catalog. Idempotent: ingesting the same "
            "commit twice updates existing records rather than duplicating them."
        ),
    )

    return server


def serve(argv: Sequence[str] | None = None) -> int:
    """Run the MCP server over stdio."""
    server = build_server()
    tools = ", ".join(f"drydock_{n}" for n in available())
    print(f"drydock mcp: serving {tools}", file=sys.stderr, flush=True)
    server.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(serve())
