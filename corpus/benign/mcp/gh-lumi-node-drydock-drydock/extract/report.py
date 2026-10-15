"""Render extraction plans and component documentation as markdown."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import ExtractionPlan

__all__ = ["render_extraction_md", "render_component_readme"]


def render_extraction_md(plan: ExtractionPlan, result=None) -> str:
    """Render extraction plan as markdown (fills the template structure).

    Args:
        plan: The extraction plan to render.
        result: Optional ExtractionResult (unused but kept for future use).

    Returns:
        Markdown string describing the extraction plan.
    """
    lines: list[str] = []

    # Title.
    lines.append(f"# Extraction Plan: {plan.component}")
    lines.append("")

    # Source section.
    lines.append("## Source")
    lines.append("")
    lines.append("| Attribute | Value |")
    lines.append("|-----------|-------|")
    lines.append(f"| **Project** | {plan.project} |")
    lines.append(f"| **Component** | {plan.component} |")
    lines.append(f"| **Source Root** | `{plan.source_root}` |")
    if plan.source_commit:
        lines.append(f"| **Commit** | `{plan.source_commit}` |")
    lines.append("")

    # Scope: Files to Extract.
    lines.append("## Files Extracted")
    lines.append("")
    lines.append("### Selected Files")
    lines.append("")

    selected_files = sorted(
        [f for f in plan.files if f.reason == "selected"],
        key=lambda f: f.destination
    )
    if selected_files:
        for pf in selected_files:
            lines.append(f"- `{pf.destination}` (from `{pf.source}`)")
    else:
        lines.append("*(none)*")
    lines.append("")

    # Closure files.
    lines.append("### Pulled by Closure")
    lines.append("")
    closure_files = sorted(
        [f for f in plan.files if f.reason == "closure"],
        key=lambda f: f.destination
    )
    if closure_files:
        for pf in closure_files:
            lines.append(f"- `{pf.destination}` (from `{pf.source}`)")
    else:
        lines.append("*(none)*")
    lines.append("")

    # Package-init files.
    lines.append("### Package Initialization Files (auto-added)")
    lines.append("")
    init_files = sorted(
        [f for f in plan.files if f.reason == "package-init"],
        key=lambda f: f.destination
    )
    if init_files:
        for pf in init_files:
            lines.append(f"- `{pf.destination}` (from `{pf.source}`)")
    else:
        lines.append("*(none)*")
    lines.append("")

    # Dependencies section.
    lines.append("## Dependencies")
    lines.append("")

    lines.append("### External (Third-Party)")
    lines.append("")
    has_external = any(plan.external_deps.values())
    if has_external:
        for lang in sorted(plan.external_deps.keys()):
            deps = sorted(plan.external_deps[lang])
            if deps:
                lines.append(f"**{lang.title()}:**")
                for dep in deps:
                    lines.append(f"- `{dep}`")
                lines.append("")
    else:
        lines.append("*(none)*")
    lines.append("")

    # Breakages section (grouped by severity).
    lines.append("## Issues")
    lines.append("")

    blocking = sorted(
        [b for b in plan.breakages if b.severity == "blocking"],
        key=lambda b: (b.kind, b.file)
    )
    warnings = sorted(
        [b for b in plan.breakages if b.severity == "warning"],
        key=lambda b: (b.kind, b.file)
    )
    infos = sorted(
        [b for b in plan.breakages if b.severity == "info"],
        key=lambda b: (b.kind, b.file)
    )

    if blocking:
        lines.append("### Blocking Issues")
        lines.append("")
        for b in blocking:
            lines.append(f"**`{b.kind}` in `{b.file}`**")
            lines.append("")
            lines.append(f"Detail: {b.detail}")
            if b.target:
                lines.append(f"Target: `{b.target}`")
            if b.hint:
                lines.append(f"Hint: {b.hint}")
            lines.append("")

    if warnings:
        lines.append("### Warnings")
        lines.append("")
        for b in warnings:
            lines.append(f"**`{b.kind}` in `{b.file}`**")
            lines.append("")
            lines.append(f"Detail: {b.detail}")
            if b.target:
                lines.append(f"Target: `{b.target}`")
            if b.hint:
                lines.append(f"Hint: {b.hint}")
            lines.append("")

    if infos:
        lines.append("### Info")
        lines.append("")
        for b in infos:
            lines.append(f"**`{b.kind}` in `{b.file}`**")
            lines.append("")
            lines.append(f"Detail: {b.detail}")
            if b.target:
                lines.append(f"Target: `{b.target}`")
            if b.hint:
                lines.append(f"Hint: {b.hint}")
            lines.append("")

    if not (blocking or warnings or infos):
        lines.append("*(none)*")
        lines.append("")

    # Summary statistics.
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Total files | {len(plan.files)} |")
    lines.append(f"| Selected | {plan.selected_count} |")
    lines.append(f"| Pulled by closure | {plan.closure_count} |")
    lines.append(f"| Languages | {', '.join(sorted(plan.languages)) or 'none'} |")
    lines.append(f"| Blocking issues | {len(blocking)} |")
    lines.append(f"| Warnings | {len(warnings)} |")
    lines.append(f"| Safe to extract | {'Yes' if plan.is_safe else 'No'} |")
    lines.append("")

    # Footer.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    lines.append("---")
    lines.append("")
    lines.append(f"*Generated: {now}*")

    return "\n".join(lines) + "\n"


def render_component_readme(plan: ExtractionPlan) -> str:
    """Render component README describing what was extracted and how to use it.

    Returns:
        Markdown string for the component's README.
    """
    lines: list[str] = []

    # Title and intro.
    lines.append(f"# {plan.component}")
    lines.append("")
    lines.append(f"Extracted from [`{plan.project}`]({plan.source_root})")
    if plan.source_commit:
        lines.append(f" at commit `{plan.source_commit[:8]}`")
    lines.append("")
    lines.append("")

    # What this component is.
    lines.append("## About")
    lines.append("")
    lines.append(
        "This component was extracted using "
        "[Drydock](https://github.com/Lumi-node/Drydock), "
        "an agentic toolchest for analyzing and extracting software components. "
        "It is not hand-written or independently maintained; it is a "
        "structural copy of part of another project."
    )
    lines.append("")

    # Source information.
    lines.append("## Source")
    lines.append("")
    lines.append(f"- **Project**: {plan.project}")
    lines.append(f"- **Location**: {plan.source_root}")
    if plan.source_commit:
        lines.append(f"- **Commit**: {plan.source_commit}")
    lines.append("")

    # Files.
    lines.append("## Contents")
    lines.append("")
    lines.append(f"This component includes {len(plan.files)} file(s):")
    lines.append("")

    # Group by language for clarity.
    by_lang: dict[str | None, list] = {}
    for pf in sorted(plan.files, key=lambda f: f.destination):
        lang = pf.lang or "other"
        by_lang.setdefault(lang, []).append(pf)

    for lang in sorted(by_lang.keys()):
        files = by_lang[lang]
        lines.append(f"**{lang.title()}** ({len(files)} file(s)):")
        for pf in files:
            reason_label = {
                "selected": "selected",
                "closure": "pulled by closure",
                "package-init": "auto-generated",
                "test": "test",
                "asset": "asset",
            }.get(pf.reason, pf.reason)
            lines.append(f"- `{pf.destination}` ({reason_label})")
        lines.append("")

    # Dependencies.
    lines.append("## Dependencies")
    lines.append("")

    has_deps = any(plan.external_deps.values())
    if has_deps:
        for lang in sorted(plan.external_deps.keys()):
            deps = sorted(plan.external_deps[lang])
            if deps:
                lines.append(f"**{lang.title()}:**")
                for dep in deps:
                    lines.append(f"- {dep}")
                lines.append("")
    else:
        lines.append("No external dependencies.")
        lines.append("")

    # Installation.
    lines.append("## Installation")
    lines.append("")

    build_files = []
    if "python" in plan.languages:
        build_files.append("pyproject.toml (Python)")
    if "rust" in plan.languages:
        build_files.append("Cargo.toml (Rust)")
    if "go" in plan.languages:
        build_files.append("go.mod (Go)")
    if "javascript" in plan.languages or "typescript" in plan.languages:
        build_files.append("package.json (JavaScript/TypeScript)")

    if build_files:
        lines.append("Build file(s) generated:")
        for bf in build_files:
            lines.append(f"- {bf}")
        lines.append("")
        lines.append("Install dependencies using your language's package manager.")
    else:
        lines.append("No build files were generated for this component.")
    lines.append("")

    # Issues.
    if plan.breakages:
        lines.append("## Known Issues")
        lines.append("")

        blocking = [b for b in plan.breakages if b.severity == "blocking"]
        if blocking:
            lines.append("**Blocking (must be resolved):**")
            lines.append("")
            for b in blocking:
                lines.append(f"- {b.detail}")
                if b.hint:
                    lines.append(f"  *Hint: {b.hint}*")
            lines.append("")

        warnings = [b for b in plan.breakages if b.severity == "warning"]
        if warnings:
            lines.append("**Warnings:**")
            lines.append("")
            for b in warnings:
                lines.append(f"- {b.detail}")
                if b.hint:
                    lines.append(f"  *Hint: {b.hint}*")
            lines.append("")
    else:
        lines.append("## Status")
        lines.append("")
        lines.append("No known issues.")
        lines.append("")

    # Footer.
    lines.append("---")
    lines.append("")
    lines.append(
        "*This README was generated automatically by Drydock during extraction. "
        "For documentation on the original component, see the source project.*"
    )

    return "\n".join(lines) + "\n"
