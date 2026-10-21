#!/usr/bin/env python3
"""Validate source-backed Markdown Wiki pages; search them as synthesis only."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from library import speaker_name
from retrieve import LocalModel, open_corpus, query_terms

# concept: an idea; case: one real decision (situation -> reasons -> outcome -> later view);
# mistake: an admitted error; declined: questions they refused or called too hard;
# filter: a decision screen they state; pattern: a cross-case regularity (editorial).
PAGE_TYPES = ("concept", "case", "mistake", "declined", "filter", "pattern")


def read_page(path):
    text = Path(path).read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("Expected JSON frontmatter between --- delimiters")
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError("Missing frontmatter closing delimiter")
    metadata = json.loads(parts[0][4:])
    if metadata.get("kind") != "synthesis" or not metadata.get("title") or not metadata.get("subjects"):
        raise ValueError("Require kind=synthesis, title and subjects")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", metadata.get("reviewed_on", "")):
        raise ValueError("Require reviewed_on date")
    if metadata.setdefault("page_type", "concept") not in PAGE_TYPES:
        raise ValueError("page_type must be one of " + ", ".join(PAGE_TYPES))
    return metadata, parts[1]


def evidence_entries(corpus, chunk_ids, first_label=1):
    """Frontmatter evidence records for chunks, hashed exactly as validate_page checks them."""
    entries = []
    for offset, chunk_id in enumerate(chunk_ids):
        row = corpus.db.execute("SELECT c.*,d.raw_sha256,d.metadata,d.title,d.url FROM chunks c "
                                "JOIN documents d ON d.id=c.document_id WHERE c.id=?", (chunk_id,)).fetchone()
        if row is None:
            raise ValueError("Unknown chunk id: " + chunk_id)
        entries.append({"label": f"E{first_label + offset}", "chunk_id": chunk_id, "raw_sha256": row["raw_sha256"],
                        "text_sha256": hashlib.sha256(row["text"].encode()).hexdigest(),
                        "metadata_sha256": hashlib.sha256(row["metadata"].encode()).hexdigest(),
                        "speaker": row["speaker"],
                        "_readable": {"title": row["title"], "url": row["url"], "locator": json.loads(row["locator"])}})
    return entries


def validate_page(corpus, path):
    try:
        meta, body = read_page(path)
        errors = []
        anchors = {}
        for item in meta.get("evidence", []):
            label = item.get("label")
            if not label or label in anchors:
                errors.append("Missing or repeated evidence label")
                continue
            anchors[label] = item
            row = corpus.db.execute("SELECT c.*,d.raw_sha256,d.metadata FROM chunks c "
                                    "JOIN documents d ON d.id=c.document_id WHERE c.id=?", (item.get("chunk_id"),)).fetchone()
            if row is None:
                errors.append(f"{label}: chunk no longer exists")
                continue
            if item.get("raw_sha256") != row["raw_sha256"]:
                errors.append(f"{label}: source file version changed")
            if item.get("text_sha256") != hashlib.sha256(row["text"].encode()).hexdigest():
                errors.append(f"{label}: extracted passage text changed")
            metadata_hash = hashlib.sha256(row["metadata"].encode()).hexdigest()
            if item.get("metadata_sha256") != metadata_hash:
                errors.append(f"{label}: source attribution/metadata changed")
            if item.get("speaker") != row["speaker"]:
                errors.append(f"{label}: speaker changed")
        if not anchors:
            errors.append("No original evidence references")
        used = set(re.findall(r"\[(E\d+)\]", body))
        if not used:
            errors.append("No claim-level evidence labels in body")
        for label in used - anchors.keys():
            errors.append(f"{label}: undefined evidence label")
        for label in anchors.keys() - used:
            errors.append(f"{label}: evidence is not tied to body")
        # Only mechanically validate links. This cannot establish entailment.
        return {"path": str(Path(path).resolve()), "title": meta["title"], "subjects": meta["subjects"],
                "page_type": meta["page_type"],
                "status": "source-links-current" if not errors else "needs-review", "errors": errors,
                "evidence_count": len(anchors), "reviewed_on": meta["reviewed_on"],
                "note": "Mechanical provenance check only; verify each synthesis against source context."}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return {"path": str(path), "status": "needs-review", "errors": [str(exc)]}


def pages_in(directory):
    directory = Path(directory)
    if not directory.exists():
        return []
    # Index and log are navigation, not evidence-backed topic pages.
    return sorted(p for p in directory.glob("*.md") if p.name not in {"index.md", "log.md"})


def search_pages(corpus, directory, query, models_dir=None, speaker=None, limit=3, page_types=None):
    pages, rejected = [], []
    for path in pages_in(directory):
        result = validate_page(corpus, path)
        if result["status"] != "source-links-current":
            rejected.append(result)
            continue
        meta, body = read_page(path)
        if speaker and speaker_name(speaker) not in meta["subjects"]:
            continue
        if page_types and meta["page_type"] not in page_types:
            continue
        pages.append((path, meta, body, result))
    if not pages:
        return {"kind": "synthesis-navigation", "results": [], "needs_review": rejected}
    mode, warnings = "lexical", []
    scores = []
    if models_dir:
        try:
            model = LocalModel(models_dir, max_tokens=512)
            query_vector = model.embed([query], query=True)[0]
            texts = [meta["title"] + "\n" + meta.get("summary", "") + "\n" + " ".join(meta.get("keywords", []))
                     for _, meta, _, _ in pages]
            scores = list(model.embed(texts) @ query_vector)
            mode = "semantic"
        except (ImportError, OSError, ValueError) as exc:
            warnings.append("Wiki lexical fallback: " + str(exc))
    if not scores:
        terms = query_terms(query)
        scores = [sum((meta["title"] + "\n" + body).lower().count(term.lower()) for term in terms)
                  for _, meta, body, _ in pages]
    order = sorted(range(len(pages)), key=lambda i: (-float(scores[i]), str(pages[i][0])))
    results = []
    for i in order[:limit]:
        if mode == "lexical" and scores[i] == 0:
            continue
        path, meta, body, validation = pages[i]
        results.append({"path": str(path.resolve()), "title": meta["title"], "kind": "synthesis",
                        "page_type": meta["page_type"],
                        "summary": meta.get("summary", ""), "score": float(scores[i]),
                        "evidence": meta["evidence"], "validation": validation})
    return {"kind": "synthesis-navigation", "mode_used": mode, "results": results,
            "needs_review": rejected, "warnings": warnings,
            "note": "Wiki scores are navigation hints. Return to original evidence; Wiki pages are not independent sources."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--wiki-dir", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    query = sub.add_parser("search")
    query.add_argument("query")
    query.add_argument("--speaker")
    query.add_argument("--lexical-only", action="store_true")
    query.add_argument("--limit", type=int, default=3)
    query.add_argument("--type", action="append", choices=PAGE_TYPES, dest="page_types",
                       help="Restrict to page types (repeatable), e.g. --type case --type mistake")
    evidence = sub.add_parser("evidence", help="Print frontmatter evidence records for chunk ids")
    evidence.add_argument("chunk_ids", nargs="+")
    evidence.add_argument("--first-label", type=int, default=1)
    args = parser.parse_args()
    corpus = open_corpus(args.library)
    try:
        directory = args.wiki_dir or corpus.root / "wiki"
        if args.command == "check":
            results = [validate_page(corpus, path) for path in pages_in(directory)]
            output = {"pages": len(results), "needs_review": sum(p["status"] != "source-links-current" for p in results),
                      "by_type": {t: sum(p.get("page_type") == t for p in results) for t in PAGE_TYPES},
                      "results": results}
        elif args.command == "evidence":
            output = {"evidence": evidence_entries(corpus, args.chunk_ids, args.first_label),
                      "note": "Drop the _readable helper field before saving frontmatter; read each passage before citing it."}
        else:
            output = search_pages(corpus, directory, args.query,
                                  None if args.lexical_only else corpus.root / "retrieval" / "models",
                                  args.speaker, args.limit, args.page_types)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if args.command == "check" and output["needs_review"]:
            raise SystemExit(1)
    finally:
        corpus.close()


if __name__ == "__main__":
    main()
