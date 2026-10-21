"""Extraction result types and the built-in Markdown/text extractors.

Every extractor returns an `ExtractedDoc`: ordered sections, each with its
source location. Locations are only what the extractor actually knows; page
numbers are never invented.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from okf_mcp_server.src.knowledge.bundle import FENCE, HEADING, split_sections

# Bump when extraction output changes, so rebuilds re-extract unchanged files
# instead of reusing stale results (2: Docling formulas kept as text;
# 3: source frontmatter title/description kept).
EXTRACTOR_VERSION = 3
NATIVE_SUFFIXES = {".md", ".markdown", ".txt"}
DOCLING_SUFFIXES = {".pdf", ".docx", ".pptx", ".xlsx", ".html", ".htm", ".csv"}
SUPPORTED_SUFFIXES = NATIVE_SUFFIXES | DOCLING_SUFFIXES


@dataclass
class ExtractedSection:
    """A heading-delimited run of extracted content."""

    title: str
    level: int
    markdown: str
    location: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedDoc:
    """Extractor output for one source file."""

    extractor: str
    sections: List[ExtractedSection]
    title: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


def extract_native(path: Path) -> ExtractedDoc:
    """Extract Markdown or plain text without third-party dependencies."""
    text = path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    skipped = 0
    source_meta: Dict[str, Any] = {}
    if path.suffix.lower() != ".txt" and text.startswith("---\n"):
        # Strip existing frontmatter (Hugo, Jekyll, MkDocs...) from the body,
        # keeping only its title and description; `_okf.yaml` still overrides them.
        source_lines = text.split("\n")
        for end in range(1, len(source_lines)):
            if source_lines[end].strip() == "---":
                try:
                    loaded = yaml.safe_load("\n".join(source_lines[1:end]))
                except yaml.YAMLError:
                    loaded = None
                source_meta = loaded if isinstance(loaded, dict) else {}
                skipped = end + 1
                while skipped < len(source_lines) and not source_lines[skipped]:
                    skipped += 1
                text = "\n".join(source_lines[skipped:])
                break
    if path.suffix.lower() == ".txt":
        line_count = text.count("\n") + 1
        return ExtractedDoc(
            extractor="native-text",
            sections=[
                ExtractedSection(
                    "", 0, text.strip(), {"lines": [1 + skipped, line_count + skipped]}
                )
            ],
        )

    lines = text.split("\n")
    headings: List[int] = []
    in_fence = False
    for number, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and HEADING.match(line):
            headings.append(number)
    bounds = headings + [len(lines) + 1]

    sections: List[ExtractedSection] = []
    title = None
    parsed = split_sections(text)
    offset = 0 if parsed and parsed[0].title else -1  # -1: a preamble comes first
    for i, sec in enumerate(parsed):
        k = i + offset
        start = (1 if k < 0 else bounds[k]) + skipped
        end = bounds[k + 1] - 1 + skipped
        if sec.level == 1 and title is None:
            title = sec.title
        location: Dict[str, Any] = {"lines": [start, end]}
        if sec.title:
            location["section"] = sec.title
        sections.append(ExtractedSection(sec.title, sec.level, sec.text, location))
    meta_title = source_meta.get("title")
    meta_description = source_meta.get("description")
    return ExtractedDoc(
        extractor="native-markdown",
        sections=sections,
        title=" ".join(meta_title.split())
        if isinstance(meta_title, str) and meta_title.strip()
        else title,
        description=(
            " ".join(meta_description.split())
            if isinstance(meta_description, str) and meta_description.strip()
            else None
        ),
    )


def extract(path: Path, artifacts_path: Optional[Path] = None) -> ExtractedDoc:
    """Dispatch to the right extractor for a file suffix.

    Raises:
        ValueError: For unsupported file types.
    """
    suffix = path.suffix.lower()
    if suffix in NATIVE_SUFFIXES:
        return extract_native(path)
    if suffix in DOCLING_SUFFIXES:
        # Imported lazily: Docling is the optional `ingest` extra.
        from okf_mcp_server.src.ingest.docling_adapter import extract_with_docling

        return extract_with_docling(path, artifacts_path)
    raise ValueError(f"unsupported file type: {suffix or '(none)'}")
