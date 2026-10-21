"""Read-side helpers for OKF v0.2 bundles.

Parses frontmatter with a safe YAML loader, resolves bundle-relative paths
without escaping the bundle root, splits concept bodies into sections and
derives the trust tier, lifecycle status and staleness defined by the spec.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

OKF_VERSION = "0.2"
RESERVED_FILENAMES = {"index.md", "log.md"}

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")


class BundleError(ValueError):
    """Raised for invalid bundle paths or unreadable concepts."""


@dataclass(frozen=True)
class Section:
    """One heading-delimited part of a concept body."""

    slug: str
    title: str
    level: int
    text: str


def split_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Split a markdown document into (frontmatter, body).

    Raises:
        BundleError: If the frontmatter block is missing, unterminated or not a mapping.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise BundleError("missing YAML frontmatter")
    for end in range(1, len(lines)):
        if lines[end].strip() == "---":
            break
    else:
        raise BundleError("unterminated YAML frontmatter")
    try:
        data = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as e:
        raise BundleError(f"invalid YAML frontmatter: {e}") from e
    if not isinstance(data, dict):
        raise BundleError("frontmatter must be a mapping")
    return data, "\n".join(lines[end + 1 :]).lstrip("\n")


def to_jsonable(value: Any) -> Any:
    """Convert YAML-loaded values (datetimes, dates) into JSON-safe values."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def parse_instant(value: Any) -> Optional[datetime]:
    """Parse an ISO 8601 instant; naive values are treated as UTC. None if unparseable."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def verified_events(frontmatter: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return `verified` as a list; a bare mapping is a one-element list (spec §5.2)."""
    verified = frontmatter.get("verified")
    if isinstance(verified, dict):
        return [verified]
    if isinstance(verified, list):
        return [v for v in verified if isinstance(v, dict)]
    return []


def trust_tier(frontmatter: Dict[str, Any]) -> str:
    """Derive the spec §5.3 trust tier from `verified`."""
    events = verified_events(frontmatter)
    if not events:
        return "unverified"
    if any(str(e.get("by", "")).startswith("human:") for e in events):
        return "human-reviewed"
    return "machine-confirmed"


def lifecycle_status(frontmatter: Dict[str, Any]) -> str:
    """Return `status`; absent means stable (spec §5.4)."""
    return str(frontmatter.get("status") or "stable")


def is_stale(frontmatter: Dict[str, Any], now: Optional[datetime] = None) -> bool:
    """True when now >= stale_after (spec §5.5).

    An unparseable `stale_after` is reported as stale so it is surfaced, not hidden.
    """
    if "stale_after" not in frontmatter or frontmatter["stale_after"] is None:
        return False
    instant = parse_instant(frontmatter["stale_after"])
    if instant is None:
        return True
    return (now or datetime.now(timezone.utc)) >= instant


def concept_summary(concept_id: str, frontmatter: Dict[str, Any]) -> Dict[str, Any]:
    """Frontmatter-derived summary used by browse and fetch results."""
    return {
        "concept_id": concept_id,
        "type": frontmatter.get("type"),
        "title": frontmatter.get("title") or concept_id.rsplit("/", 1)[-1],
        "description": frontmatter.get("description"),
        "tags": to_jsonable(frontmatter.get("tags") or []),
        "status": lifecycle_status(frontmatter),
        "trust_tier": trust_tier(frontmatter),
        "stale": is_stale(frontmatter),
    }


def resolve_in_bundle(bundle_root: Path, relative: str) -> Path:
    """Resolve a bundle-relative path, rejecting anything outside the bundle.

    Leading slashes are accepted (OKF bundle-absolute links). Symlinks are
    resolved before the containment check.

    Raises:
        BundleError: If the path is malformed or escapes the bundle root.
    """
    if not isinstance(relative, str) or "\x00" in relative or "\\" in relative:
        raise BundleError("invalid path")
    cleaned = relative.strip().strip("/")
    parts = [p for p in cleaned.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise BundleError("path must not contain '..'")
    root = bundle_root.resolve()
    target = root.joinpath(*parts).resolve()
    if target != root and not target.is_relative_to(root):
        raise BundleError("path is outside the knowledge bundle")
    return target


def concept_path(bundle_root: Path, concept_id: str) -> Path:
    """Map a concept ID (path without `.md`) to its file, enforcing bundle containment."""
    concept_id = (concept_id or "").strip().strip("/")
    if concept_id.endswith(".md"):
        concept_id = concept_id[:-3]
    # Case-insensitive: on APFS/NTFS "INDEX.md" opens the unfiltered index.md.
    if not concept_id or concept_id.rsplit("/", 1)[-1].lower() in ("index", "log"):
        raise BundleError("not a concept ID")
    path = resolve_in_bundle(bundle_root, concept_id + ".md")
    if not path.is_file():
        raise BundleError(f"concept not found: {concept_id}")
    return path


def read_concept(bundle_root: Path, concept_id: str) -> Tuple[Dict[str, Any], str]:
    """Read and parse one concept document."""
    path = concept_path(bundle_root, concept_id)
    return split_frontmatter(path.read_text(encoding="utf-8"))


def slugify(text: str, fallback: str = "section") -> str:
    """Lower-case, hyphen-separated slug (Unicode letters kept)."""
    slug = re.sub(r"[^\w]+", "-", text.lower(), flags=re.UNICODE).strip("-_")
    return slug or fallback


def split_sections(body: str) -> List[Section]:
    """Split a markdown body at headings outside fenced code blocks.

    Text before the first heading becomes a `preamble` section. Duplicate
    slugs get numeric suffixes in document order, so slugs are stable for
    identical bodies.
    """
    sections: List[Section] = []
    seen: Dict[str, int] = {}
    used: set[str] = set()
    title, level = "", 0
    buf: List[str] = []
    in_fence = False

    def flush() -> None:
        text = "\n".join(buf).strip("\n")
        if not title and not text.strip():
            return
        base = slugify(title) if title else "preamble"
        seen[base] = seen.get(base, 0) + 1
        slug = base if seen[base] == 1 else f"{base}-{seen[base]}"
        while slug in used:
            seen[base] += 1
            slug = f"{base}-{seen[base]}"
        used.add(slug)
        sections.append(Section(slug=slug, title=title, level=level, text=text))

    for line in body.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
        match = None if in_fence else HEADING.match(line)
        if match:
            flush()
            title, level, buf = match.group(2), len(match.group(1)), []
        else:
            buf.append(line)
    flush()
    return sections


def iter_concepts(bundle_root: Path):
    """Yield (concept_id, path) for every concept document, sorted by ID."""
    root = bundle_root.resolve()
    for path in sorted(root.rglob("*.md")):
        if path.name in RESERVED_FILENAMES or any(
            p.startswith(".") for p in path.relative_to(root).parts
        ):
            continue
        yield path.relative_to(root).with_suffix("").as_posix(), path


def list_directory(
    bundle_root: Path,
    relative: str,
    visible: Optional[Callable[[Dict[str, Any]], bool]] = None,
) -> List[Dict[str, Any]]:
    """Synthesize a directory listing from the files on disk.

    Subdirectories come first, then concepts, each sorted by name. Listings
    are always built from concept frontmatter (never by returning a stored
    `index.md`), so per-entry filtering can be applied before anything is
    returned. With `visible` (a frontmatter predicate), hidden concepts are
    omitted, directories count only visible concepts, and directories with
    none are omitted, so a listing reveals nothing the caller cannot open.

    Raises:
        BundleError: If the path is not a directory inside the bundle.
    """
    directory = resolve_in_bundle(bundle_root, relative)
    if not directory.is_dir():
        raise BundleError(f"directory not found: {relative or '/'}")
    root = bundle_root.resolve()

    def shown(path: Path) -> Optional[Dict[str, Any]]:
        try:
            fm, _ = split_frontmatter(path.read_text(encoding="utf-8"))
        except BundleError:
            return None
        return fm if visible is None or visible(fm) else None

    subdirs: List[Dict[str, Any]] = []
    concepts: List[Dict[str, Any]] = []
    for child in sorted(directory.iterdir(), key=lambda p: p.name):
        if child.name.startswith("."):
            continue
        rel = child.resolve().relative_to(root).as_posix()
        if child.is_dir():
            # ponytail: reads every concept below; cache per snapshot if large trees are slow.
            count = sum(
                1 for _, path in iter_concepts(child) if shown(path) is not None
            )
            if count or visible is None:
                subdirs.append(
                    {"kind": "directory", "path": rel, "concept_count": count}
                )
        elif child.suffix == ".md" and child.name not in RESERVED_FILENAMES:
            fm = shown(child)
            if fm is not None:
                concepts.append({"kind": "concept", **concept_summary(rel[:-3], fm)})
    return subdirs + concepts
