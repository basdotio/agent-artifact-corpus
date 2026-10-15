"""``drydock extract`` command-line interface.

Extract a component from a project and materialize it as a standalone package.
The command operates in two modes:

* **Plan mode (no -o)**: Analyze the extraction, report what will happen and what
  will break, and write nothing. This is the safe default.
* **Execute mode (-o OUTPUT)**: Materialize the plan into a new package at OUTPUT.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Sequence

from . import (
    ExtractionError,
    plan_extraction,
    rewriter_for,
    select_by_cluster,
    select_by_dir,
    select_by_files,
)
from .engine import execute_plan
from .planner import list_seams, select_by_seam
from ..core.cli import EXIT_OK, EXIT_ERROR, EXIT_USAGE, add_common_arguments
from ..core.output import Reporter, dumps, write_output
from ..core.registry import AnalysisContext
from ..core.walker import WalkPolicy

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the extract command."""
    parser = argparse.ArgumentParser(
        prog="drydock extract",
        description=(
            "Extract a component from a project, producing a standalone package.\n\n"
            "Extraction is a two-step process: first plan (print what will happen),\n"
            "then execute (materialize the result). The default is plan-only; pass\n"
            "-o to write files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("project_path", help="Path to the project root")

    # Selection: exactly one required
    selection = parser.add_argument_group("selection (exactly one required)")
    selection.add_argument(
        "--cluster",
        type=int,
        default=-1,
        metavar="N",
        help="Extract a cluster by id (from boundaries analyzer)",
    )
    selection.add_argument(
        "--dir",
        default="",
        metavar="PATH",
        help="Extract everything under a directory path",
    )
    selection.add_argument(
        "--files",
        default="",
        metavar="FILE,...",
        help="Extract explicit comma-separated file list",
    )
    selection.add_argument(
        "--seam",
        default="",
        metavar="CONTRACT",
        help=(
            "Extract a plugin seam: the module declaring a contract plus every "
            "module implementing it. Consumers stay behind and keep depending "
            "on the contract, which is what the plug point is for. "
            "Use --list-seams to see the candidates"
        ),
    )
    selection.add_argument(
        "--list-seams",
        action="store_true",
        help="List contract-shaped cut points, best first, and exit",
    )

    # Extraction options
    options = parser.add_argument_group("extraction options")
    options.add_argument(
        "--component",
        default="",
        metavar="NAME",
        help="Name of the extracted component / root package (default: inferred from selection)",
    )
    options.add_argument(
        "--no-closure",
        dest="closure",
        action="store_false",
        default=True,
        help="Take only selected files; internal deps become blocking breakages",
    )
    options.add_argument(
        "--copy-package-inits",
        dest="copy_package_inits",
        action="store_true",
        default=False,
        help=(
            "Copy the original package __init__.py files instead of synthesizing "
            "minimal markers. Their re-exports are then followed by the closure, "
            "which can pull in a great deal more than was selected"
        ),
    )
    options.add_argument(
        "--force",
        action="store_true",
        help="Replace a non-empty destination directory",
    )
    options.add_argument(
        "--allow-blocking",
        dest="allow_blocking",
        action="store_true",
        help="Proceed despite blocking breakages (extraction may not stand alone)",
    )

    # Output options (reuse the standard set)
    add_common_arguments(parser)

    return parser


def _validate_component_name(name: str) -> str:
    """Validate that a component name is a safe identifier.

    Returns the name if valid, raises ValueError otherwise.
    """
    if not name:
        return name  # Will be inferred later
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", name):
        raise ValueError(
            f"unsafe component name '{name}'; "
            "must start with a letter or underscore, contain only alphanumerics, "
            "underscores, and hyphens"
        )
    return name


def _infer_component_name(selection_type: str, selection_arg: str) -> str:
    """Infer a component name from the selection."""
    if selection_type == "dir":
        # Use the basename of the directory
        parts = [p for p in selection_arg.strip("/").split("/") if p]
        if parts:
            return parts[-1]
    elif selection_type == "cluster":
        return f"cluster-{selection_arg}"
    elif selection_type == "seam":
        # Name the component after the package the contract lives in, which is
        # what the seam actually is -- `langs/base.py` -> `langs`.
        parts = [p for p in selection_arg.strip("/").split("/")[:-1] if p]
        if parts:
            return parts[-1]
    # Fallback
    return "extracted"


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and execute extraction command."""
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(argv)

    reporter = Reporter(quiet=args.quiet)

    # --- Validation ---

    root = Path(args.project_path)
    if not root.exists():
        print(f"error: project path not found: {root}", file=sys.stderr)
        return EXIT_USAGE
    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return EXIT_USAGE

    if args.list_seams:
        _p = WalkPolicy(
            include_tests=args.include_tests,
            max_files=args.max_files,
            follow_symlinks=args.follow_symlinks,
        )
        _extra = getattr(args, "skip_dir", None)
        if _extra:
            _p = _p.with_extra_skips(_extra)
        ctx = AnalysisContext(root, policy=_p, reporter=reporter)
        seams = list_seams(ctx)
        if args.markdown:
            lines = [f"# Plugin seams: {ctx.root.name}", ""]
            if not seams:
                lines.append("No contract with two or more implementations.")
            for s_ in seams:
                lines += [
                    f"## `{s_['contract']}` — {s_['verdict']} "
                    f"(cohesion {s_['cohesion']})",
                    "",
                    f"{s_['implementer_count']} implementers, "
                    f"{s_['escape_count']} escaping dependencies",
                    "",
                    "```",
                    f"drydock extract {args.project_path} --seam {s_['contract']} -o OUT",
                    "```",
                    "",
                ]
            write_output("\n".join(lines), args.output, reporter)
        else:
            write_output(dumps({"seams": seams}), args.output, reporter)
        return EXIT_OK



    # Exactly one selection required
    selections = [
        (args.cluster != -1, "cluster", args.cluster),
        (bool(args.dir), "dir", args.dir),
        (bool(args.files), "files", args.files),
        (bool(args.seam), "seam", args.seam),
    ]
    active = [s for s in selections if s[0]]

    if len(active) == 0:
        print(
            "error: no selection provided; use exactly one of "
            "--cluster, --dir, --files or --seam",
            file=sys.stderr,
        )
        return EXIT_USAGE

    if len(active) > 1:
        names = ", ".join(f"--{s[1]}" for s in active)
        print(
            f"error: multiple selections provided ({names}); use exactly one",
            file=sys.stderr,
        )
        return EXIT_USAGE

    _, selection_type, selection_arg = active[0]

    # Validate project path
    # Validate and infer component name
    try:
        component = _validate_component_name(args.component)
        if not component:
            component = _infer_component_name(selection_type, str(selection_arg))
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_USAGE

    # --- Plan the extraction ---

    reporter.step(f"analyzing {root}")
    try:
        policy = WalkPolicy(
            include_tests=args.include_tests,
            max_files=args.max_files,
            follow_symlinks=args.follow_symlinks,
        )
        extra = getattr(args, "skip_dir", None)
        if extra:
            policy = policy.with_extra_skips(extra)

        ctx = AnalysisContext(root, policy=policy, reporter=reporter)

        # Select files based on the selection type
        if selection_type == "cluster":
            selected = select_by_cluster(ctx, int(selection_arg))
        elif selection_type == "dir":
            selected = select_by_dir(ctx, selection_arg)
        elif selection_type == "seam":
            selected = select_by_seam(ctx, selection_arg)
        else:  # files
            selected = select_by_files(ctx, selection_arg.split(","))

        if not selected:
            print(
                f"error: no files matched the selection ({selection_type})",
                file=sys.stderr,
            )
            return EXIT_USAGE

        # Plan the extraction
        plan = plan_extraction(
            ctx,
            selected,
            component=component,
            closure=args.closure,
            include_tests=args.include_tests,
            copy_package_inits=args.copy_package_inits,
            selection={
                "kind": selection_type,
                "value": selection_arg,
                "closure": args.closure,
                "include_tests": args.include_tests,
                "copy_package_inits": args.copy_package_inits,
            },
        )

    except ExtractionError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:
        print(
            f"error: planning failed: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return EXIT_ERROR

    # --- Plan-only mode (no -o): print and exit ---

    if not args.output:
        if args.markdown:
            text = _render_plan_markdown(plan)
        else:
            text = dumps(plan, compact=args.compact)
        write_output(text, None, reporter)
        return EXIT_ERROR if not plan.is_safe else EXIT_OK

    # --- Execute mode (with -o) ---

    output_path = Path(args.output)

    try:
        reporter.step(f"executing extraction to {output_path}")
        result = execute_plan(
            plan,
            output_path,
            reporter=reporter,
            force=args.force,
            allow_blocking=args.allow_blocking,
            rewriter_for=rewriter_for,
        )

        # Write packaging files (guard imports for parallel development)
        try:
            from .packaging import generate_packaging
            reporter.step("generating packaging files")
            packaging_files = generate_packaging(plan)
            for rel_path, content in packaging_files.items():
                file_path = output_path / rel_path
                file_path.write_text(content, encoding="utf-8")
        except ImportError:
            reporter.warn("packaging module not ready; skipping package.json/pyproject.toml generation")

        # Write extraction report (guard imports for parallel development)
        try:
            from .report import render_extraction_md, render_component_readme
            reporter.step("generating documentation")
            extraction_md = output_path / "EXTRACTION.md"
            extraction_md.write_text(render_extraction_md(plan, result), encoding="utf-8")
            readme = output_path / "README.md"
            readme.write_text(render_component_readme(plan), encoding="utf-8")
        except ImportError:
            reporter.warn("report module not ready; skipping EXTRACTION.md/README.md generation")

        reporter.step(f"extraction complete: {result.files_written} files written")
        return EXIT_OK

    except ExtractionError as e:
        print(f"error: {e}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as e:
        print(
            f"error: extraction failed: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return EXIT_ERROR


def _render_plan_markdown(plan) -> str:
    """Render an ExtractionPlan as readable markdown."""
    lines = [
        f"# Extraction Plan: {plan.component}",
        "",
        f"**Project:** {plan.project}",
        f"**Selected files:** {plan.selected_count}",
        f"**Total files:** {len(plan.files)} (including closure)",
        f"**Safe to extract:** {'Yes' if plan.is_safe else 'No'}",
        "",
    ]

    if plan.languages:
        lines.extend([
            "## Languages",
            "",
            "- " + "\n- ".join(plan.languages),
            "",
        ])

    if plan.external_deps:
        lines.extend([
            "## External Dependencies",
            "",
        ])
        for ecosystem, deps in sorted(plan.external_deps.items()):
            lines.append(f"**{ecosystem}:**")
            for dep in sorted(deps):
                lines.append(f"  - {dep}")
            lines.append("")

    if plan.files:
        lines.extend([
            "## Files to Extract",
            "",
            f"**Selected ({plan.selected_count}):**",
            "",
        ])
        for pf in plan.files:
            if pf.reason == "selected":
                rewrites = f" ({pf.rewrites} rewrites)" if pf.rewrites else ""
                lines.append(f"- `{pf.destination}`{rewrites}")
        lines.append("")

        if plan.closure_count:
            lines.extend([
                f"**Pulled by closure ({plan.closure_count}):**",
                "",
            ])
            for pf in plan.files:
                if pf.reason == "closure":
                    rewrites = f" ({pf.rewrites} rewrites)" if pf.rewrites else ""
                    lines.append(f"- `{pf.destination}`{rewrites}")
            lines.append("")

    if plan.breakages:
        lines.extend([
            "## Issues",
            "",
        ])
        blocking = plan.blocking
        if blocking:
            lines.extend([
                f"**Blocking ({len(blocking)}):** These must be resolved before extraction:",
                "",
            ])
            for b in blocking[:10]:
                lines.append(f"- {b.kind}: {b.detail}")
                if b.hint:
                    lines.append(f"  Hint: {b.hint}")
            if len(blocking) > 10:
                lines.append(f"- ... and {len(blocking) - 10} more")
            lines.append("")

        warnings = [b for b in plan.breakages if b.severity == "warning"]
        if warnings:
            lines.extend([
                f"**Warnings ({len(warnings)}):**",
                "",
            ])
            for b in warnings[:10]:
                lines.append(f"- {b.kind}: {b.detail}")
            if len(warnings) > 10:
                lines.append(f"- ... and {len(warnings) - 10} more")
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
