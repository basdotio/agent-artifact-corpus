"""``drydock catalog`` command-line interface.

Manages the user's library of ingested repositories and reusable components.
Queries the accumulated catalog, ingests new repositories, and stores extracted
components for composition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .store import Catalog, default_root
from ..core.output import Reporter, dumps, write_output

__all__ = ["main"]

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the catalog command."""
    parser = argparse.ArgumentParser(
        prog="drydock catalog",
        description=(
            "Manage your library of ingested repositories and extracted components.\n\n"
            "The catalog accumulates analyzed repositories and their reusable components,\n"
            "indexed for search and composition."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="catalog sub-command")

    # --- ingest ---
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest a project into the catalog",
    )
    ingest_parser.add_argument(
        "project", help="Path to the project to ingest"
    )
    ingest_parser.add_argument(
        "--store", action="store_true",
        help="Store extracted component code trees in the catalog",
    )
    ingest_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )
    ingest_parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress progress output on stderr",
    )

    # --- list ---
    list_parser = subparsers.add_parser(
        "list",
        help="List ingested repositories",
    )
    list_parser.add_argument(
        "--markdown", "-m", action="store_true",
        help="Render for humans (default: JSON, like every other drydock command)",
    )
    list_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )

    # --- show ---
    show_parser = subparsers.add_parser(
        "show",
        help="Show details of a repository",
    )
    show_parser.add_argument(
        "repo", help="Repository id or name to show",
    )
    show_parser.add_argument(
        "--markdown", "-m", action="store_true",
        help="Render for humans (default: JSON, like every other drydock command)",
    )
    show_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )

    # --- components ---
    comp_parser = subparsers.add_parser(
        "components",
        help="List components in the catalog",
    )
    comp_parser.add_argument(
        "--repo", metavar="ID", default="",
        help="Filter by repository id",
    )
    comp_parser.add_argument(
        "--kind", metavar="KIND", default="",
        help="Filter by component kind (seam, cluster, directory, manual)",
    )
    comp_parser.add_argument(
        "--lang", metavar="LANG", default="",
        help="Filter by programming language",
    )
    comp_parser.add_argument(
        "--min-cohesion", metavar="SCORE", type=float, default=0.0,
        help="Filter by minimum cohesion score (0.0-1.0)",
    )
    comp_parser.add_argument(
        "--stored", action="store_true",
        help="Show only components whose code is stored in the catalog",
    )
    comp_parser.add_argument(
        "--markdown", "-m", action="store_true",
        help="Render for humans (default: JSON, like every other drydock command)",
    )
    comp_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )

    # --- search ---
    search_parser = subparsers.add_parser(
        "search",
        help="Search the catalog",
    )
    search_parser.add_argument(
        "query", help="Search query",
    )
    search_parser.add_argument(
        "--kind", metavar="KIND", default="",
        help="Filter by subject kind (repo, component, capability, fact)",
    )
    search_parser.add_argument(
        "--limit", metavar="N", type=int, default=25,
        help="Maximum results to return (default: 25)",
    )
    search_parser.add_argument(
        "--markdown", "-m", action="store_true",
        help="Render for humans (default: JSON, like every other drydock command)",
    )
    search_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )

    # --- diagram ---
    diag_parser = subparsers.add_parser(
        "diagram",
        help="Generate a diagram of a repository",
    )
    diag_parser.add_argument(
        "repo", help="Repository id or name to diagram",
    )
    diag_parser.add_argument(
        "--kind", metavar="KIND", default="layers",
        help="Diagram kind (layers, packages, seam)",
    )
    diag_parser.add_argument(
        "--seam", metavar="CONTRACT", default="",
        help="For seam diagrams, the contract to focus on",
    )
    diag_parser.add_argument(
        "--markdown", "-m", action="store_true",
        help="Render for humans (default: JSON, like every other drydock command)",
    )
    diag_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )

    # --- stats ---
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show catalog statistics",
    )
    stats_parser.add_argument(
        "--markdown", "-m", action="store_true",
        help="Render for humans (default: JSON, like every other drydock command)",
    )
    stats_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )

    # --- forget ---
    forget_parser = subparsers.add_parser(
        "forget",
        help="Remove a repository from the catalog",
    )
    forget_parser.add_argument(
        "repo", help="Repository id to remove",
    )
    forget_parser.add_argument(
        "--keep-content", action="store_true",
        help="Keep stored component code trees",
    )
    forget_parser.add_argument(
        "--yes", action="store_true",
        help="Skip confirmation and proceed with deletion",
    )
    forget_parser.add_argument(
        "--markdown", "-m", action="store_true",
        help="Render for humans (default: JSON, like every other drydock command)",
    )
    forget_parser.add_argument(
        "--catalog", metavar="PATH", default="",
        help="Catalog root (default: ~/.drydock; can also use DRYDOCK_CATALOG env var)",
    )

    # One vocabulary, applied after every subparser is built rather than
    # inside each one. Adding these per-subcommand is exactly how they drifted:
    # no catalog subcommand accepted `-o` at all, and `--quiet` reached only
    # `ingest` while `--markdown` reached only the others. A user meets that in
    # their first minute, because `-o` works on all ten analyzers.
    for sub in subparsers.choices.values():
        have = {a.dest for a in sub._actions}
        if "output" not in have:
            sub.add_argument("--output", "-o", metavar="FILE",
                             help="Write to FILE instead of stdout")
        if "markdown" not in have:
            sub.add_argument("--markdown", "-m", action="store_true",
                             help="Render for humans (default: JSON)")
        if "quiet" not in have:
            sub.add_argument("--quiet", "-q", action="store_true",
                             help="Suppress progress output on stderr")

    return parser


def _format_list(repos: list) -> str:
    """Format repos for human-readable output."""
    if not repos:
        return "(empty catalog)"

    lines = []
    for repo in repos:
        label = f"{repo.name}"
        if repo.commit_sha:
            label += f"  @ {repo.short_commit}"
        langs = " ".join(repo.languages) if repo.languages else "(unknown)"
        lines.append(f"{label:<50}  {langs}")
        if repo.source:
            lines.append(f"  {repo.source}")
        lines.append("")
    return "\n".join(lines)


def _format_components(components: list, catalog_root: Path) -> str:
    """Format components for human-readable output."""
    if not components:
        return "(no components)"

    lines = []
    for comp in components:
        stored = " [stored]" if comp.is_stored else ""
        cohesion_str = f"{comp.cohesion:.2f}" if comp.cohesion is not None else "—"

        label = f"{comp.name:<40} {comp.kind:<10} {cohesion_str}"
        lines.append(label + stored)

        if comp.contract:
            lines.append(f"  contract: {comp.contract}")
        if comp.languages:
            lines.append(f"  languages: {', '.join(comp.languages)}")
        if comp.summary:
            lines.append(f"  {comp.summary}")
        lines.append("")

    return "\n".join(lines)


def _format_stats(stats: dict) -> str:
    """Format stats for human-readable output."""
    lines = [
        f"Catalog: {stats['root']}",
        f"Schema version: {stats['schema_version']}",
        "",
        f"Repositories: {stats['repos']}",
        f"Components: {stats['components']}",
        f"  Stored: {stats['components_stored']}",
        f"Facts: {stats['facts']}",
        f"Capabilities: {stats['capabilities']}",
    ]
    if stats.get('languages'):
        lines.append(f"Languages: {', '.join(stats['languages'])}")
    return "\n".join(lines)


def _format_search(hits: list) -> str:
    """Format search results for human-readable output."""
    if not hits:
        return "(no matches)"

    lines = []
    by_kind = {}
    for hit in hits:
        kind = hit.subject_kind
        if kind not in by_kind:
            by_kind[kind] = []
        by_kind[kind].append(hit)

    for kind in sorted(by_kind.keys()):
        lines.append(f"{kind}:")
        for hit in by_kind[kind]:
            lines.append(f"  {hit.title:<60} {hit.rank:+.2f}")
            if hit.snippet:
                lines.append(f"    {hit.snippet}")
        lines.append("")

    return "\n".join(lines)



def _emit(args, text: str) -> None:
    """Send a payload to --output if given, otherwise stdout.

    Every handler goes through here. Adding `--output` to the parsers without
    this is the dead-flag bug in miniature: the flag parsed, was accepted, and
    did nothing -- which is worse than not offering it, because the caller
    believes the file was written.
    """
    write_output(text, getattr(args, "output", None),
                 Reporter(quiet=getattr(args, "quiet", False)))


def _cmd_ingest(args) -> int:
    """Execute the ingest subcommand."""
    catalog = Catalog(args.catalog or None)
    project = Path(args.project)

    if not project.exists():
        print(f"error: project path not found: {project}", file=sys.stderr)
        return EXIT_USAGE

    if not project.is_dir():
        print(f"error: not a directory: {project}", file=sys.stderr)
        return EXIT_USAGE

    reporter = Reporter(quiet=args.quiet)

    try:
        from .ingest import ingest, IngestResult
    except ImportError as exc:
        print(f"error: ingest module not available: {exc}", file=sys.stderr)
        return EXIT_ERROR

    reporter.step(f"ingesting {project}")
    try:
        result: IngestResult = ingest(
            catalog,
            project,
            store_components=args.store,
            reporter=reporter,
        )

        reporter.step(f"completed: {result.components_recorded} components, "
                     f"{result.components_stored} stored")

        if result.failures:
            for phase, error in result.failures.items():
                reporter.warn(f"{phase}: {error}")

        _emit(args, dumps({
            "repo_id": result.repo_id,
            "components_recorded": result.components_recorded,
            "components_stored": result.components_stored,
            "facts_recorded": result.facts_recorded,
            "capabilities_recorded": result.capabilities_recorded,
            "failures": result.failures,
        }))

        # Nothing recorded *and* something failed means the ingest did not do
        # its job, so it must not report success -- a scripted run would go
        # green over an empty catalog. Found by ingesting under a read-only
        # HOME: the catalog could not be created, every phase failed, and this
        # returned 0. An empty repo with no failures is still a clean exit.
        if result.failures and result.components_recorded == 0:
            print(
                "error: ingest recorded nothing; "
                + "; ".join(f"{phase}: {err}" for phase, err in result.failures.items()),
                file=sys.stderr,
            )
            return EXIT_ERROR
        return EXIT_OK
    except Exception as exc:
        print(f"error: ingest failed: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def _cmd_list(args) -> int:
    """Execute the list subcommand."""
    catalog = Catalog(args.catalog or None)
    try:
        repos = catalog.repos()
        if not args.markdown:
            _emit(args, dumps([{
                "id": r.id,
                "name": r.name,
                "source": r.source,
                "commit_sha": r.commit_sha,
                "branch": r.branch,
                "languages": r.languages,
                "file_count": r.file_count,
            } for r in repos]))
        else:
            _emit(args, _format_list(repos))
        return EXIT_OK
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def _cmd_show(args) -> int:
    """Execute the show subcommand."""
    catalog = Catalog(args.catalog or None)
    try:
        repo = catalog.repo(args.repo)
        if not repo:
            # Try to find by name
            repos = catalog.repos(name=args.repo)
            if repos:
                repo = repos[0]

        if not repo:
            print(f"error: repository not found: {args.repo}", file=sys.stderr)
            return EXIT_USAGE

        components = catalog.components(repo_id=repo.id)
        facts = catalog.facts(repo_id=repo.id)

        if not args.markdown:
            _emit(args, dumps({
                "repo": {
                    "id": repo.id,
                    "name": repo.name,
                    "source": repo.source,
                    "commit_sha": repo.commit_sha,
                    "branch": repo.branch,
                    "languages": repo.languages,
                    "file_count": repo.file_count,
                    "ingested_at": repo.ingested_at,
                },
                "components": [{
                    "id": c.id,
                    "name": c.name,
                    "kind": c.kind,
                    "contract": c.contract,
                    "cohesion": c.cohesion,
                    "languages": c.languages,
                    "is_stored": c.is_stored,
                } for c in components],
                "facts": [{
                    "id": f.id,
                    "principle": f.principle,
                    "name": f.name,
                    "verdict": f.verdict,
                    "summary": f.summary,
                } for f in facts],
            }))
        else:
            lines = [f"Repository: {repo.name}"]
            if repo.commit_sha:
                lines.append(f"Commit: {repo.commit_sha}")
            lines.append(f"Source: {repo.source}")
            if repo.languages:
                lines.append(f"Languages: {', '.join(repo.languages)}")
            lines.append(f"Files: {repo.file_count}")
            lines.append("")

            if components:
                lines.append(f"Components ({len(components)}):")
                lines.append(_format_components(components, catalog.root))
            else:
                lines.append("No components recorded")

            if facts:
                lines.append(f"Architectural Facts ({len(facts)}):")
                for fact in facts:
                    lines.append(f"  {fact.name}: {fact.verdict}")
                lines.append("")

            print("\n".join(lines))
        return EXIT_OK
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def _cmd_components(args) -> int:
    """Execute the components subcommand."""
    catalog = Catalog(args.catalog or None)
    try:
        components = catalog.components(
            repo_id=args.repo or None,
            kind=args.kind or None,
            language=args.lang or None,
            min_cohesion=args.min_cohesion if args.min_cohesion > 0 else None,
            stored_only=args.stored,
        )

        if not args.markdown:
            _emit(args, dumps([{
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
            } for c in components]))
        else:
            _emit(args, _format_components(components, catalog.root))
        return EXIT_OK
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def _cmd_search(args) -> int:
    """Execute the search subcommand."""
    catalog = Catalog(args.catalog or None)
    try:
        hits = catalog.search(
            args.query,
            kind=args.kind or None,
            limit=args.limit,
        )

        if not args.markdown:
            _emit(args, dumps([{
                "subject_id": h.subject_id,
                "subject_kind": h.subject_kind,
                "repo_id": h.repo_id,
                "title": h.title,
                "snippet": h.snippet,
                "rank": h.rank,
            } for h in hits]))
        else:
            _emit(args, _format_search(hits))
        return EXIT_OK
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def _cmd_diagram(args) -> int:
    """Execute the diagram subcommand."""
    catalog = Catalog(args.catalog or None)
    try:
        repo = catalog.repo(args.repo)
        if not repo:
            # Try to find by name
            repos = catalog.repos(name=args.repo)
            if repos:
                repo = repos[0]

        if not repo:
            print(f"error: repository not found: {args.repo}", file=sys.stderr)
            return EXIT_USAGE

        try:
            from ..diagram.mermaid import diagram_repo
        except ImportError:
            print("error: diagram module not available", file=sys.stderr)
            return EXIT_ERROR

        # Generate diagram
        mermaid_text = diagram_repo(
            repo.id,
            kind=args.kind,
            seam=args.seam or None,
            catalog=catalog,
        )

        if not args.markdown:
            _emit(args, dumps({
                "repo_id": repo.id,
                "diagram_kind": args.kind,
                "mermaid": mermaid_text,
            }))
        else:
            print(mermaid_text)

        return EXIT_OK
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def _unwritable_catalog_message(catalog, exc: Exception) -> str:
    """Say what to do, not just which errno.

    The default catalog lives under $HOME, which is not writable in a lot of
    real environments -- CI runners, containers run as a non-root user, locked
    down workstations. A bare "Permission denied: '/rohome/.drydock'" does not
    tell anyone that `--catalog` and `DRYDOCK_CATALOG` exist.
    """
    return (
        f"error: cannot use the catalog at {catalog.root}: {exc}\n"
        "hint: choose a writable location with --catalog PATH "
        "or the DRYDOCK_CATALOG environment variable"
    )


def _cmd_stats(args) -> int:
    """Execute the stats subcommand."""
    catalog = Catalog(args.catalog or None)
    try:
        stats = catalog.stats()
        if not args.markdown:
            _emit(args, dumps(stats))
        else:
            _emit(args, _format_stats(stats))
        return EXIT_OK
    except PermissionError as exc:
        print(_unwritable_catalog_message(catalog, exc), file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def _cmd_forget(args) -> int:
    """Execute the forget subcommand."""
    catalog = Catalog(args.catalog or None)
    try:
        repo = catalog.repo(args.repo)
        if not repo:
            # Try to find by name
            repos = catalog.repos(name=args.repo)
            if repos:
                repo = repos[0]

        if not repo:
            print(f"error: repository not found: {args.repo}", file=sys.stderr)
            return EXIT_USAGE

        components = catalog.components(repo_id=repo.id)
        stored_count = sum(1 for c in components if c.is_stored)

        # Print what will be deleted
        print(f"Will remove:", file=sys.stderr)
        print(f"  Repository: {repo.name} ({repo.id})", file=sys.stderr)
        print(f"  Components: {len(components)}", file=sys.stderr)
        if not args.keep_content and stored_count > 0:
            print(f"  Stored code trees: {stored_count}", file=sys.stderr)

        if not args.yes:
            print(f"\nConfirm with --yes to proceed", file=sys.stderr)
            return EXIT_USAGE

        # Perform deletion
        delete_content = not args.keep_content
        result = catalog.forget(repo.id, delete_content=delete_content)

        if not args.markdown:
            _emit(args, dumps({
                "repo_id": repo.id,
                "repo_name": repo.name,
                "components_removed": result["components"],
                "content_trees_deleted": result["content_trees_deleted"],
            }))
        else:
            print(f"Removed {result['components']} components", file=sys.stderr)
            if result["content_trees_deleted"] > 0:
                print(f"Deleted {result['content_trees_deleted']} stored code trees",
                      file=sys.stderr)

        return EXIT_OK
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR
    finally:
        catalog.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and execute catalog command."""
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv or argv[0] in ("-h", "--help", "help"):
        parser = _build_parser()
        parser.print_help()
        return EXIT_OK

    parser = _build_parser()
    args = parser.parse_args(argv)

    if not args.subcommand:
        parser.print_help()
        return EXIT_USAGE

    # Dispatch to subcommand handler
    handlers = {
        "ingest": _cmd_ingest,
        "list": _cmd_list,
        "show": _cmd_show,
        "components": _cmd_components,
        "search": _cmd_search,
        "diagram": _cmd_diagram,
        "stats": _cmd_stats,
        "forget": _cmd_forget,
    }

    handler = handlers.get(args.subcommand)
    if not handler:
        print(f"error: unknown subcommand '{args.subcommand}'", file=sys.stderr)
        return EXIT_USAGE

    return handler(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
