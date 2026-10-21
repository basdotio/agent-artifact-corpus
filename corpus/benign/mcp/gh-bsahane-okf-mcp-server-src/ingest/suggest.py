"""Draft an `_okf.yaml` from a source folder, for a person to review.

Heuristics only; every suggestion carries a comment saying why. Nothing is
marked `verified`, since only an owner can confirm content.
"""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Tuple

from okf_mcp_server.src.ingest.extract import SUPPORTED_SUFFIXES
from okf_mcp_server.src.ingest.pipeline import discover

# Folder or filename word -> OKF type. Order matters: first match wins.
TYPE_WORDS = [
    (("policy", "policies", "richtlinie"), "Policy"),
    (("sop", "procedure", "procedures", "process"), "SOP"),
    (("runbook", "runbooks", "playbook", "playbooks"), "Runbook"),
    (("standard", "standards"), "Standard"),
    (("guide", "guides", "howto", "how-to", "manual", "manuals"), "Guide"),
    (("training",), "Training"),
    (("template", "templates"), "Template"),
    (("contract", "contracts", "agreement", "agreements"), "Contract"),
]
_YEAR = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
_WORDS = re.compile(r"[a-z]+")


def _type_for_words(text: str) -> str:
    words = set(_WORDS.findall(text.lower()))
    for keys, type_ in TYPE_WORDS:
        if words & set(keys):
            return type_
    return ""


def _q(value: str) -> str:
    """Quote a YAML key or value safely."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def suggest_config(source_root: Path) -> str:
    """Return a commented `_okf.yaml` suggestion for `source_root`."""
    source_root = source_root.resolve()
    files = [p for p in discover(source_root) if p.suffix.lower() in SUPPORTED_SUFFIXES]
    rels = [p.relative_to(source_root).as_posix() for p in files]

    # Folder prefixes whose own name implies a type (deepest prefix wins at build time).
    types: Dict[str, str] = {}
    for rel in rels:
        parts = rel.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            type_ = _type_for_words(parts[depth - 1])
            if type_:
                types["/".join(parts[:depth]) + "/"] = type_

    notes: Dict[str, Tuple[str, str]] = {}  # rel -> (status, reason)

    # Identical content: keep the shortest name, deprecate the copies.
    by_hash: Dict[str, List[str]] = {}
    for path, rel in zip(files, rels):
        by_hash.setdefault(hashlib.sha256(path.read_bytes()).hexdigest(), []).append(
            rel
        )
    for copies in by_hash.values():
        if len(copies) > 1:
            keep = min(copies, key=lambda r: (len(r), r))
            for rel in copies:
                if rel != keep:
                    notes[rel] = ("deprecated", f"same content as {keep}")

    # Same name apart from a year: the newest is current, older ones superseded.
    by_stem: Dict[Tuple[str, str], List[Tuple[int, str]]] = {}
    for rel in rels:
        path = Path(rel)
        match = _YEAR.search(path.stem)
        if match is None:
            continue
        key = (str(path.parent), _YEAR.sub("", path.stem).strip(" -_().").lower())
        by_stem.setdefault(key, []).append((int(match.group(0)), rel))
    for group in by_stem.values():
        if len(group) > 1:
            newest_year, newest = max(group)
            for year, rel in group:
                if year < newest_year and rel not in notes:
                    notes[rel] = ("deprecated", f"superseded by {newest}")
            notes.setdefault(
                newest, ("stable", "newest dated version; confirm it is approved")
            )

    for rel in rels:
        if rel not in notes and re.search(r"draft", Path(rel).stem, re.IGNORECASE):
            notes[rel] = ("draft", "'draft' in the file name")

    lines = [
        "# Suggested by `okf-ingest suggest-config`. Review every entry before use:",
        "# these are guesses from folder and file names, not from reading content.",
        f"bundle_title: {_q(source_root.name)}",
        "default_type: Reference",
        "types:                      # longest matching path prefix wins",
    ]
    lines += [
        f"  {_q(prefix)}: {type_}" for prefix, type_ in sorted(types.items())
    ] or ["  {}"]
    lines.append("documents:")
    for rel in rels:
        status_reason = notes.get(rel)
        file_type = _type_for_words(Path(rel).stem)
        inherited = max((p for p in types if rel.startswith(p)), key=len, default=None)
        type_override = (
            file_type
            if file_type and (inherited is None or types[inherited] != file_type)
            else ""
        )
        if not status_reason and not type_override:
            continue
        lines.append(f"  {_q(rel)}:")
        if type_override:
            lines.append(f"    type: {type_override}          # from the file name")
        if status_reason:
            status, reason = status_reason
            lines.append(f"    status: {status}          # {reason}")
    lines += [
        "  # Owners add review state and review cycles, for example:",
        '  # "path/to/doc.pdf":',
        "  #   status: stable",
        "  #   stale_after: 2027-03-31T00:00:00Z",
        '  #   verified: [{ by: "human:owner-id", at: 2026-09-24T09:00:00Z }]',
    ]
    return "\n".join(lines) + "\n"
