"""Build and publish an OKF snapshot from a folder of source documents.

One concept per source document. Frontmatter is filled deterministically
from file metadata, the ingestion run and the optional `_okf.yaml` config in
the source root; no generative model is involved.

A build writes a new snapshot beside the published one, validates it, builds
its index and only then switches `current`. Unchanged sources (same content
hash) reuse the previous snapshot's extraction instead of re-running Docling.
"""

import fcntl
import hashlib
import json
import re
import secrets
import shutil
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import yaml

from okf_mcp_server.src.ingest.extract import (
    EXTRACTOR_VERSION,
    SUPPORTED_SUFFIXES,
    ExtractedDoc,
    ExtractedSection,
    extract,
)
from okf_mcp_server.src.knowledge.access import normalize_access
from okf_mcp_server.src.knowledge.bundle import (
    FENCE,
    HEADING,
    OKF_VERSION,
    slugify,
    split_frontmatter,
    split_sections,
)
from okf_mcp_server.src.knowledge.embed import LazyEmbedder, unavailable_reason
from okf_mcp_server.src.knowledge.index import build_index, load_vectors
from okf_mcp_server.src.knowledge.snapshot import (
    Snapshot,
    SnapshotError,
    current_snapshot,
    publish,
)
from okf_mcp_server.src.knowledge.validate import validate_bundle
from okf_mcp_server.src.settings import settings

# Builds embed through the lazy wrapper: no model load when every vector is reused.
get_embedder = LazyEmbedder

CONFIG_FILE = "_okf.yaml"
STATUSES = ("draft", "stable", "deprecated")

try:
    PRODUCER = f"okf-ingest/{version('okf-mcp-server')}"
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    PRODUCER = "okf-ingest/0.1.0"


@dataclass
class BuildReport:
    """Outcome of one ingestion run."""

    snapshot_id: str
    published: bool = False
    concepts: int = 0
    passages: int = 0
    reused: int = 0
    failures: Dict[str, str] = field(default_factory=dict)
    problems: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    pruned: List[str] = field(default_factory=list)
    embedded: int = 0
    vectors_reused: int = 0
    embedding_model: str = ""
    skipped: Dict[str, str] = field(default_factory=dict)
    changes: List[Tuple[str, str]] = field(default_factory=list)


def iso(dt: datetime) -> str:
    """ISO 8601 with an explicit UTC `Z` suffix, second precision."""
    return (
        dt.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def load_config(source_root: Path) -> Dict[str, Any]:
    """Load `_okf.yaml` (optional).

    Raises:
        ValueError: If the config is malformed.
    """
    path = source_root / CONFIG_FILE
    if not path.is_file():
        return {}
    config = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(config, dict):
        raise ValueError(f"{CONFIG_FILE} must be a mapping")
    for key in ("types", "documents", "access"):
        if not isinstance(config.get(key) or {}, dict):
            raise ValueError(f"{CONFIG_FILE}: `{key}` must be a mapping")
    for prefix, rule in (config.get("access") or {}).items():
        if rule is None:
            raise ValueError(f"{CONFIG_FILE}: access[{prefix!r}] is empty")
        try:
            normalize_access(rule)
        except (ValueError, TypeError, AttributeError) as e:
            raise ValueError(f"{CONFIG_FILE}: access[{prefix!r}]: {e}") from e
    for rel, doc in (config.get("documents") or {}).items():
        if not isinstance(doc, dict):
            raise ValueError(f"{CONFIG_FILE}: documents[{rel!r}] must be a mapping")
        if doc.get("status", "draft") not in STATUSES:
            raise ValueError(
                f"{CONFIG_FILE}: documents[{rel!r}].status must be one of {STATUSES}"
            )
        if "access" in doc:
            if doc["access"] is None:
                # An empty entry would drop the folder rule and fall back to the default.
                raise ValueError(f"{CONFIG_FILE}: documents[{rel!r}].access is empty")
            try:
                normalize_access(doc["access"])
            except (ValueError, TypeError, AttributeError) as e:
                raise ValueError(
                    f"{CONFIG_FILE}: documents[{rel!r}].access: {e}"
                ) from e
        for event in doc.get("verified") or []:
            if (
                not isinstance(event, dict)
                or not event.get("by")
                or not event.get("at")
            ):
                raise ValueError(
                    f"{CONFIG_FILE}: documents[{rel!r}].verified needs `by` and `at`"
                )
    return config


SOURCE_ACL_FILE = ".okf/access.json"


def load_source_acls(source_root: Path) -> Dict[str, List[str]]:
    """Per-file permissions recorded by connectors from source systems.

    Every `.okf/access.json` under the source root maps paths relative to its
    own folder to principal lists (each connector mirrors into a subfolder).
    They are rewritten on every sync, so permission changes and revocations
    in the source reach the next build.

    Raises:
        ValueError: If a file is malformed.
    """
    acls: Dict[str, List[str]] = {}
    for path in sorted(source_root.rglob(SOURCE_ACL_FILE)):
        base = path.parent.parent.relative_to(source_root).as_posix()
        prefix = "" if base == "." else base + "/"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for rel, rule in data.items():
                acls[prefix + str(rel)] = normalize_access(rule) or []
        except (ValueError, TypeError, AttributeError) as e:
            raise ValueError(f"{path.relative_to(source_root)}: {e}") from e
    return acls


def access_for(
    rel: str, config: Dict[str, Any], source_acls: Dict[str, List[str]]
) -> Optional[List[str]]:
    """Access list for a document: per-document config, then source, then prefix rule.

    None means no rule applies; the server's OKF_DEFAULT_ACCESS then decides.
    """
    doc = (config.get("documents") or {}).get(rel) or {}
    if "access" in doc:
        return normalize_access(doc["access"])
    if rel in source_acls:
        return source_acls[rel]
    rules = config.get("access") or {}
    matches = [p for p in rules if rel.startswith(p)]
    if matches:
        return normalize_access(rules[max(matches, key=len)])
    return None


def discover(source_root: Path) -> List[Path]:
    """Source files under the root, sorted; hidden files and the config are skipped."""
    files = []
    for path in sorted(source_root.rglob("*")):
        rel = path.relative_to(source_root)
        if not path.is_file() or any(p.startswith(".") for p in rel.parts):
            continue
        if rel.as_posix() == CONFIG_FILE:
            continue
        files.append(path)
    return files


def source_id_for(rel: str) -> str:
    """Stable source ID derived from the source-relative path."""
    return "src-" + hashlib.sha256(rel.encode()).hexdigest()[:16]


def assign_concept_ids(rels: List[str]) -> Dict[str, str]:
    """Map source-relative paths to unique concept IDs mirroring the folders.

    Same-stem files get the extension appended (`budget-xlsx`), reserved
    names `index`/`log` get a `-doc` suffix, and remaining clashes a counter.
    """

    def base(rel: str, with_suffix: bool) -> str:
        path = Path(rel)
        dirs = [slugify(p, "folder") for p in path.parent.parts]
        stem = slugify(path.stem, "document")
        if stem in ("index", "log"):
            stem += "-doc"
        if with_suffix:
            stem += "-" + slugify(path.suffix.lstrip("."), "file")
        return "/".join(dirs + [stem])

    plain: Dict[str, List[str]] = {}
    for rel in rels:
        plain.setdefault(base(rel, False), []).append(rel)
    ids: Dict[str, str] = {}
    used: set = set()
    for rel in sorted(rels):
        cid = base(rel, len(plain[base(rel, False)]) > 1)
        candidate, n = cid, 2
        while candidate in used:
            candidate, n = f"{cid}-{n}", n + 1
        used.add(candidate)
        ids[rel] = candidate
    return ids


def type_for(rel: str, config: Dict[str, Any]) -> str:
    """Concept type: per-document override, else longest matching path prefix, else default."""
    doc = (config.get("documents") or {}).get(rel) or {}
    if doc.get("type"):
        return str(doc["type"])
    matches = [p for p in (config.get("types") or {}) if rel.startswith(p)]
    if matches:
        return str(config["types"][max(matches, key=len)])
    return str(config.get("default_type") or "Reference")


def _escape_headings(markdown: str) -> str:
    """Escape heading-like lines so extracted text cannot create new sections."""
    out, in_fence = [], False
    for line in markdown.split("\n"):
        if FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and HEADING.match(line):
            line = "\\" + line
        out.append(line)
    return "\n".join(out)


def render_body(sections: List[ExtractedSection]) -> Tuple[str, List[ExtractedSection]]:
    """Render sections as Markdown; returns (body, sections actually written)."""
    written: List[ExtractedSection] = []
    chunks: List[str] = []
    for sec in sections:
        text = _escape_headings(sec.markdown.strip())
        if not sec.title.strip() and not text:
            continue
        if sec.title.strip():
            heading = (
                "#" * max(1, min(sec.level or 1, 6)) + " " + " ".join(sec.title.split())
            )
            chunks.append(f"{heading}\n\n{text}" if text else heading)
        else:
            if written:
                # An untitled section after the first would merge into its predecessor.
                chunks[-1] += f"\n\n{text}"
                written[-1] = ExtractedSection(
                    written[-1].title,
                    written[-1].level,
                    written[-1].markdown + "\n\n" + sec.markdown,
                    written[-1].location,
                )
                continue
            chunks.append(text)
        written.append(sec)
    return "\n\n".join(chunks).strip() + "\n", written


def render_concept(frontmatter: Dict[str, Any], body: str) -> str:
    """Serialize a concept document."""
    fm = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{fm}---\n\n{body}"


def _extraction_record(
    source_id: str,
    rel: str,
    uri: str,
    revision: str,
    doc: ExtractedDoc,
    slugs: List[str],
) -> Dict[str, Any]:
    return {
        "source_id": source_id,
        "path": rel,
        "uri": uri,
        "revision": revision,
        "extractor": doc.extractor,
        "title": doc.title,
        "description": doc.description,
        "sections": [
            {
                "slug": slug,
                "title": sec.title,
                "level": sec.level,
                "markdown": sec.markdown,
                "location": sec.location,
            }
            for slug, sec in zip(slugs, doc.sections)
        ],
        "docling": doc.raw,
    }


def _doc_from_record(record: Dict[str, Any]) -> ExtractedDoc:
    return ExtractedDoc(
        extractor=record["extractor"],
        title=record.get("title"),
        description=record.get("description"),
        raw=record.get("docling"),
        sections=[
            ExtractedSection(
                s["title"], s["level"], s["markdown"], s.get("location") or {}
            )
            for s in record["sections"]
        ],
    )


def _write_indexes(bundle: Path, bundle_title: str) -> None:
    """Write an `index.md` in every directory (spec §8)."""
    dirs = sorted({bundle} | {p for p in bundle.rglob("*") if p.is_dir()})
    for directory in dirs:
        subdirs = sorted(p for p in directory.iterdir() if p.is_dir())
        concepts = sorted(
            p for p in directory.glob("*.md") if p.name not in ("index.md", "log.md")
        )
        lines: List[str] = []
        if directory == bundle:
            lines += ["---", f'okf_version: "{OKF_VERSION}"', "---", ""]
        if subdirs:
            lines.append("# Subdirectories\n")
            for sub in subdirs:
                count = sum(
                    1 for p in sub.rglob("*.md") if p.name not in ("index.md", "log.md")
                )
                lines.append(
                    f"* [{sub.name}]({sub.name}/index.md) - {count} concept(s)"
                )
            lines.append("")
        if concepts:
            heading = bundle_title if directory == bundle else directory.name
            lines.append(f"# {heading}\n")
            for path in concepts:
                fm, _ = split_frontmatter(path.read_text(encoding="utf-8"))
                summary = fm.get("description") or fm.get("type")
                status = fm.get("status")
                if status == "deprecated":
                    summary = f"{summary} (deprecated)"
                lines.append(
                    f"* [{fm.get('title') or path.stem}]({path.name}) - {summary}"
                )
            lines.append("")
        (directory / "index.md").write_text("\n".join(lines), encoding="utf-8")


def _write_log(
    bundle: Path, previous: Optional[Path], changes: List[Tuple[str, str]], today: str
) -> None:
    """Prepend today's changes to the carried-over `log.md` (spec §9)."""
    old = (
        previous.read_text(encoding="utf-8") if previous and previous.is_file() else ""
    )
    body = old.split("\n", 1)[1].lstrip("\n") if old.startswith("# ") else old
    if not changes:
        new = body
    else:
        entries = "\n".join(f"* **{kind}**: {text}" for kind, text in changes)
        if body.startswith(f"## {today}\n"):
            first, _, rest = body.partition("\n")
            new = (
                f"{first}\n{entries}\n{rest.lstrip(chr(10))}"
                if rest
                else f"{first}\n{entries}\n"
            )
        else:
            new = f"## {today}\n{entries}\n\n{body}"
    (bundle / "log.md").write_text(
        "# Knowledge Update Log\n\n" + new.rstrip("\n") + "\n", encoding="utf-8"
    )


class BuildLockedError(ValueError):
    """Raised when another build holds the data directory."""


@contextmanager
def _build_lock(data_dir: Path) -> Iterator[None]:
    """Exclusive, non-blocking lock so builds cannot run concurrently.

    The OS releases it when the process exits, even if it is killed.
    """
    with open(data_dir / ".build.lock", "w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise BuildLockedError(
                f"another okf-ingest build is running on {data_dir}; wait for it to finish"
            ) from e
        yield


def build(
    source_root: Path,
    data_dir: Path,
    artifacts_path: Optional[Path] = None,
    allow_failures: bool = False,
    now: Optional[datetime] = None,
    keep: int = 3,
    embeddings: bool = True,
) -> BuildReport:
    """Ingest `source_root` into a new snapshot and publish it if it validates.

    After publishing, only the `keep` newest snapshots are kept (at least 2,
    so the previous snapshot always survives).

    Raises:
        ValueError: For a missing source, a data directory inside the source,
            an invalid `_okf.yaml`, or another build already running.
    """
    if keep < 2:
        raise ValueError("keep must be at least 2 so the previous snapshot survives")
    source_root = source_root.resolve()
    if not source_root.is_dir():
        raise ValueError(f"source directory not found: {source_root}")
    data_dir = data_dir.resolve()
    if data_dir.is_relative_to(source_root):
        raise ValueError("snapshot data directory must be outside the source directory")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "snapshots").mkdir(exist_ok=True)
    with _build_lock(data_dir):
        # Holding the lock, any staging folder belongs to an interrupted build.
        for stale in (data_dir / "snapshots").glob(".building-*"):
            shutil.rmtree(stale, ignore_errors=True)
        report = _build(
            source_root, data_dir, artifacts_path, allow_failures, now, embeddings
        )
        if report.published:
            report.pruned = prune_snapshots(data_dir, keep)
        return report


def prune_snapshots(data_dir: Path, keep: int) -> List[str]:
    """Delete all but the `keep` newest snapshots; never the published one.

    Snapshot IDs start with a UTC timestamp, so name order is age order.
    Safe while the server runs: requests resolve `current` once, and open
    files stay readable after deletion on POSIX systems.
    """
    current = current_snapshot(data_dir).id
    ids = sorted(
        p.name
        for p in (data_dir / "snapshots").iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )
    doomed = [i for i in ids[:-keep] if i != current]
    for snapshot_id in doomed:
        shutil.rmtree(data_dir / "snapshots" / snapshot_id, ignore_errors=True)
    return doomed


def _build(
    source_root: Path,
    data_dir: Path,
    artifacts_path: Optional[Path],
    allow_failures: bool,
    now: Optional[datetime],
    embeddings: bool = True,
) -> BuildReport:
    now = now or datetime.now(timezone.utc)
    config = load_config(source_root)
    docs_config = config.get("documents") or {}
    source_acls = load_source_acls(source_root)

    prev: Optional[Snapshot] = None
    prev_manifest: Dict[str, Dict[str, Any]] = {}
    try:
        prev = current_snapshot(data_dir)
        prev_manifest = json.loads(prev.manifest.read_text(encoding="utf-8"))["sources"]
    except (SnapshotError, FileNotFoundError, KeyError, json.JSONDecodeError):
        prev, prev_manifest = None, {}

    snapshot_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3)
    report = BuildReport(snapshot_id=snapshot_id)
    work = data_dir / "snapshots" / f".building-{snapshot_id}"
    snap = Snapshot(id=snapshot_id, root=work)
    snap.bundle.mkdir(parents=True)
    snap.extraction.mkdir()

    files = discover(source_root)
    rels = [p.relative_to(source_root).as_posix() for p in files]
    for rel in docs_config:
        if rel not in rels:
            report.warnings.append(
                f"{CONFIG_FILE}: documents[{rel!r}] matches no source file"
            )
    concept_ids = assign_concept_ids(rels)
    vanished_by_revision = {
        entry["revision"]: (sid, entry)
        for sid, entry in prev_manifest.items()
        if entry["path"] not in rels
    }
    manifest: Dict[str, Dict[str, Any]] = {}
    renamed: set = set()
    first_by_revision: Dict[str, str] = {}

    for path, rel in zip(files, rels):
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            # Real folders hold archives, diagrams and the like; they are
            # reported but must not block publishing the documents we can read.
            report.skipped[rel] = f"unsupported file type {path.suffix or '(none)'}"
            continue
        sid = source_id_for(rel)
        try:
            if not path.resolve(strict=True).is_relative_to(source_root):
                raise ValueError("source file resolves outside the source directory")
            content = path.read_bytes()
            stat = path.stat()
        except (OSError, ValueError, RuntimeError) as e:
            report.failures[rel] = f"{type(e).__name__}: {e}"
            continue
        revision = "sha256:" + hashlib.sha256(content).hexdigest()
        deprecated = {
            r
            for r, c in docs_config.items()
            if isinstance(c, dict) and c.get("status") == "deprecated"
        }
        if (
            revision in first_by_revision
            and not {rel, first_by_revision[revision]} & deprecated
        ):
            report.warnings.append(
                f"{rel} has the same content as {first_by_revision[revision]}; "
                "mark one deprecated in _okf.yaml or remove it"
            )
        first_by_revision.setdefault(revision, rel)
        uri = path.as_uri()
        prior = prev_manifest.get(sid)
        renamed_from = None
        if prior is None and revision in vanished_by_revision:
            renamed_from = vanished_by_revision.pop(revision)
            renamed.add(renamed_from[0])
            prior = renamed_from[1]
        doc: Optional[ExtractedDoc] = None
        if (
            prev
            and prior
            and prior["revision"] == revision
            and prior.get("extractor_version") == EXTRACTOR_VERSION
        ):
            old = prev.extraction / f"{renamed_from[0] if renamed_from else sid}.json"
            if old.is_file():
                doc = _doc_from_record(json.loads(old.read_text(encoding="utf-8")))
                report.reused += 1
        if doc is None:
            try:
                doc = extract(path, artifacts_path)
            except Exception as e:  # noqa: BLE001 - every extractor failure is reported per file
                report.failures[rel] = f"{type(e).__name__}: {e}"
                continue

        if not any(s.markdown.strip() for s in doc.sections):
            # Empty files, and scans where OCR found nothing, would publish
            # concepts with no evidence.
            report.failures[rel] = "no text extracted (empty file or unreadable scan)"
            continue
        body, written = render_body(doc.sections)
        slugs = [s.slug for s in split_sections(body)]
        if len(slugs) != len(written):
            report.failures[rel] = "internal error: section mapping mismatch"
            continue
        doc.sections = written

        cfg = docs_config.get(rel) or {}
        unchanged = prior is not None and prior["revision"] == revision
        generated_at = iso(now)
        if prior is not None and unchanged and prior.get("generated_at"):
            generated_at = prior["generated_at"]
        fm: Dict[str, Any] = {
            "type": type_for(rel, config),
            "title": str(cfg.get("title") or doc.title or _fallback_title(rel, doc)),
        }
        if cfg.get("description") or doc.description:
            fm["description"] = str(cfg.get("description") or doc.description)
        fm["resource"] = uri
        if cfg.get("tags"):
            fm["tags"] = [str(t) for t in cfg["tags"]]
        fm["sources"] = [
            {
                "id": sid,
                "resource": uri,
                "title": Path(rel).name,
                "last_modified": iso(
                    datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                ),
            }
        ]
        fm["generated"] = {"by": PRODUCER, "at": generated_at}
        if cfg.get("verified"):
            fm["verified"] = [
                {"by": str(v["by"]), "at": _iso_value(v["at"])} for v in cfg["verified"]
            ]
        fm["status"] = str(cfg.get("status") or "draft")
        if cfg.get("stale_after"):
            fm["stale_after"] = _iso_value(cfg["stale_after"])
        fm["source_revision"] = revision
        fm["source_path"] = rel
        access = access_for(rel, config, source_acls)
        if access is not None:
            fm["access"] = access

        cid = concept_ids[rel]
        target = snap.bundle / f"{cid}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_concept(fm, body), encoding="utf-8")
        record = _extraction_record(sid, rel, uri, revision, doc, slugs)
        (snap.extraction / f"{sid}.json").write_text(
            json.dumps(record, ensure_ascii=False), encoding="utf-8"
        )
        manifest[sid] = {
            "path": rel,
            "concept_id": cid,
            "revision": revision,
            "extractor": doc.extractor,
            "extractor_version": EXTRACTOR_VERSION,
            "generated_at": generated_at,
        }
        link = f"[{fm['title']}](/{cid}.md)"
        if renamed_from:
            report.changes.append(
                ("Rename", f"{link} (was `{renamed_from[1]['path']}`)")
            )
        elif prior is None:
            report.changes.append(("Creation", f"Added {link}"))
        elif not unchanged:
            report.changes.append(("Update", f"Re-extracted {link}"))

    for sid, entry in prev_manifest.items():
        if entry["path"] not in rels and sid not in renamed:
            report.changes.append(("Deletion", f"Removed `{entry['path']}`"))

    report.concepts = len(manifest)
    _write_indexes(snap.bundle, str(config.get("bundle_title") or "Concepts"))
    _write_log(
        snap.bundle,
        prev.bundle / "log.md" if prev else None,
        report.changes,
        now.date().isoformat(),
    )
    (work / "manifest.json").write_text(
        json.dumps(
            {
                "snapshot_id": snapshot_id,
                "created_at": iso(now),
                "source_root": str(source_root),
                "sources": manifest,
                "skipped": report.skipped,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if report.failures:
        (work / "failures.json").write_text(
            json.dumps(report.failures, indent=2), encoding="utf-8"
        )

    report.problems += validate_bundle(snap.bundle)
    if report.problems or (report.failures and not allow_failures):
        shutil.rmtree(work)
        return report

    embedder = None
    if embeddings:
        reason = unavailable_reason()
        if reason:
            report.warnings.append(f"semantic index skipped: {reason}")
        else:
            embedder = get_embedder()
    stats: Dict[str, int] = {}
    reuse = load_vectors(prev.index, embedder.model_id) if embedder and prev else {}
    report.passages = build_index(
        snap.bundle,
        snap.extraction,
        snap.index,
        snapshot_id,
        embedder,
        reuse,
        stats,
        vector_backend=settings.OKF_VECTOR_BACKEND,
    )
    report.embedded = stats.get("embedded", 0)
    report.vectors_reused = stats.get("vectors_reused", 0)
    report.embedding_model = embedder.model_id if embedder else ""
    final = data_dir / "snapshots" / snapshot_id
    work.rename(final)
    publish(data_dir, Snapshot(id=snapshot_id, root=final))
    report.published = True
    return report


# UUIDs, long hex strings and bare numbers: names from exports and DMS systems.
_MACHINE_NAME = re.compile(
    r"^(?:[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}|[0-9a-f]{16,}|[\d_\- ]+)$",
    re.IGNORECASE,
)


def _fallback_title(rel: str, doc: ExtractedDoc) -> str:
    """Title when neither config nor extractor gives one.

    A readable file name wins. A machine-generated one (UUID, hex, digits)
    falls back to the first heading, which is usually the document title.
    """
    if _MACHINE_NAME.match(Path(rel).stem.strip()):
        first = next((s.title for s in doc.sections if s.title.strip()), "")
        if first:
            return " ".join(first.split())[:200]
    return _title_from_filename(rel)


def _title_from_filename(rel: str) -> str:
    """`cost-centres.xlsx` -> `Cost centres`."""
    words = " ".join(Path(rel).stem.replace("_", " ").replace("-", " ").split())
    return words[:1].upper() + words[1:] if words else rel


def _iso_value(value: Any) -> str:
    """Normalize a config timestamp (YAML may load it as a datetime) to ISO 8601 with offset."""
    if isinstance(value, datetime):
        return iso(value if value.tzinfo else value.replace(tzinfo=timezone.utc))
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text  # left as-is so validation reports it
    return iso(parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc))
