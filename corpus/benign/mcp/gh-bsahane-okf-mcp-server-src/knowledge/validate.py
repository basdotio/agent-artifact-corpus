"""OKF v0.2 conformance checks (spec §11) plus this producer's own shape checks."""

import re
from pathlib import Path
from typing import List

from okf_mcp_server.src.knowledge.bundle import (
    OKF_VERSION,
    BundleError,
    parse_instant,
    split_frontmatter,
)

_LOG_DATE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")


def validate_bundle(bundle_root: Path) -> List[str]:
    """Return a list of problems; empty means the bundle passed.

    Spec §11: every non-reserved `.md` has parseable frontmatter with a
    non-empty `type`; `index.md` has no frontmatter except `okf_version` at the
    root; `log.md` date headings use `YYYY-MM-DD`. Producer checks: our
    `generated`, `sources` and timestamp fields have the documented shapes.
    """
    problems: List[str] = []
    root = bundle_root.resolve()
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as e:
            problems.append(f"{rel}: cannot read document: {e}")
            continue
        if path.name == "index.md":
            if text.startswith("---"):
                try:
                    fm, _ = split_frontmatter(text)
                except BundleError as e:
                    problems.append(f"{rel}: {e}")
                    continue
                if path.parent != root or set(fm) - {"okf_version"}:
                    problems.append(
                        f"{rel}: only the root index.md may carry frontmatter (okf_version)"
                    )
                if (
                    path.parent == root
                    and "okf_version" in fm
                    and str(fm["okf_version"]) != OKF_VERSION
                ):
                    problems.append(f"index.md: okf_version should be {OKF_VERSION!r}")
            continue
        if path.name == "log.md":
            for line in text.splitlines():
                if line.startswith("## ") and not _LOG_DATE.match(line):
                    problems.append(
                        f"{rel}: log date heading must be YYYY-MM-DD: {line!r}"
                    )
            continue
        try:
            fm, _ = split_frontmatter(text)
        except BundleError as e:
            problems.append(f"{rel}: {e}")
            continue
        if not isinstance(fm.get("type"), str) or not fm["type"].strip():
            problems.append(f"{rel}: frontmatter needs a non-empty `type`")
        generated = fm.get("generated")
        if generated is not None:
            if not isinstance(generated, dict) or not generated.get("by"):
                problems.append(f"{rel}: `generated` needs `by`")
            elif "at" in generated and not _has_offset(generated["at"]):
                problems.append(
                    f"{rel}: `generated.at` must be ISO 8601 with a UTC offset"
                )
        sources = fm.get("sources", [])
        if not isinstance(sources, list):
            problems.append(f"{rel}: `sources` must be a list")
            sources = []
        for source in sources:
            if not isinstance(source, dict) or not source.get("resource"):
                problems.append(f"{rel}: every `sources` entry needs `resource`")
        verified = fm.get("verified", [])
        if isinstance(verified, dict):
            verified = [verified]
        if not isinstance(verified, list):
            problems.append(f"{rel}: `verified` must be a mapping or list")
            verified = []
        for event in verified:
            if (
                not isinstance(event, dict)
                or not isinstance(event.get("by"), str)
                or not event["by"].strip()
                or not _has_offset(event.get("at"))
            ):
                problems.append(
                    f"{rel}: `verified` needs `by` and an ISO 8601 `at` with offset"
                )
        if "stale_after" in fm and not _has_offset(fm["stale_after"]):
            problems.append(f"{rel}: `stale_after` must be ISO 8601 with a UTC offset")
        if fm.get("status", "stable") not in ("draft", "stable", "deprecated"):
            problems.append(f"{rel}: `status` must be draft, stable or deprecated")
    return problems


def _has_offset(value: object) -> bool:
    """True if value is an ISO 8601 instant with an explicit offset."""
    if isinstance(value, str):
        return parse_instant(value) is not None and bool(
            re.search(r"(Z|[+-]\d{2}:?\d{2})$", value.strip())
        )
    instant = parse_instant(value)
    return instant is not None and getattr(value, "tzinfo", None) is not None
