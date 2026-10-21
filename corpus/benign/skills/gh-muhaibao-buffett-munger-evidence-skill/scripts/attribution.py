#!/usr/bin/env python3
"""Query-time attribution: raw speaker-label variants and reviewed document-level attribution.

The corpus keeps speaker labels exactly as the source printed them (including
transcription typos). Filtering maps a requested person to every reviewed raw
label, so a typo in a CNBC transcript does not hide a passage. Passages with no
speaker label are only attributed through the reviewed document list in
assets/attribution_map.json, and every such result carries its basis and caution.
"""
import argparse
import json
from pathlib import Path

from library import speaker_name

MAP_PATH = Path(__file__).resolve().parent.parent / "assets" / "attribution_map.json"

# Reviewed 2026-10-09 against the chunks carrying each label. All variants occur
# only in CNBC Berkshire meeting transcripts. Deliberately excluded: "JIMMY BUFFETT",
# "GREGG WARREN"/"GREGGORY WARREN" (other people), "Participant (source label WARREN)"
# (a Daily Journal questioner) and "Unverified speaker (source labels Warren Buffett)"
# (an interview passage whose content shows a different speaker).
LABEL_VARIANTS = {
    "Warren Buffett": ["Warren Buffett", "WARREN BUFEFTT", "WARREN BUFFETTT", "WARREN BUFFTT",
                       "WAREEN BUFFETT", "WARREB BUFFETT", "WAWRREN BUFFETT",
                       "WARREN BUFFETT (IN PROGRESS)"],
    "Charlie Munger": ["Charlie Munger", "CHALIE MUNGER", "CHARLIE"],
}
PRINCIPALS = tuple(LABEL_VARIANTS)
_CANONICAL = {label: person for person, labels in LABEL_VARIANTS.items() for label in labels}
LEVELS = ("strict", "author", "unassigned")


def labels_for(speaker):
    """All raw labels that denote the requested speaker (falls back to the exact name)."""
    name = speaker_name(speaker)
    if name is None:
        return []
    return list(LABEL_VARIANTS.get(name, [name]))


def canonical(label):
    """Map a raw chunk label to Buffett/Munger, or None for anyone else / unassigned."""
    if label is None:
        return None
    return _CANONICAL.get(label)


def load_map(path=None):
    path = Path(path or MAP_PATH)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("documents", {})


def author_documents(speaker, path=None):
    """Documents whose unlabelled passages may be attributed to this person, with basis."""
    name = speaker_name(speaker)
    return {doc: entry for doc, entry in load_map(path).items() if entry.get("person") == name}


def basis(row_speaker, document_id, speaker, doc_map):
    """Explain why a returned passage is associated with the requested person."""
    if row_speaker is not None:
        person = canonical(row_speaker) or row_speaker
        result = {"basis": "chunk-speaker", "person": person}
        if row_speaker != person:
            result["raw_label"] = row_speaker
        return result
    entry = doc_map.get(document_id)
    if speaker and entry:
        return {"basis": entry["basis"], "person": entry["person"], "caution": entry["caution"]}
    return {"basis": "unassigned", "person": None,
            "caution": "Speaker is unassigned; establish authorship from the source before attributing."}


# Rules used by `propose` to suggest documents for review. Proposals are not
# applied until written into assets/attribution_map.json by a reviewer.
RULES = [
    {"series": "wesco-shareholder-letters", "author": "Charles T. Munger", "person": "Charlie Munger",
     "basis": "document-author",
     "caution": "Sole-signed Wesco letter; letters embed quotations and tables, so confirm the sentence is Munger's own prose."},
    {"series": "buffett-other-writings", "author": "Warren E. Buffett", "person": "Warren Buffett",
     "basis": "document-author",
     "caution": "Buffett-authored essay; it quotes and tabulates other investors' records, so confirm the sentence is Buffett's own prose."},
    {"series": "historical-berkshire-annual-letters", "author": "Warren Buffett", "person": "Warren Buffett",
     "basis": "document-author",
     "caution": "Buffett-signed letter extracted by OCR; unlabelled pages may include tables or quoted material."},
    {"series": "wesco-meeting-notes", "author": None, "person": "Charlie Munger",
     "basis": "meeting-notes-principal",
     "caution": "Third-party notes of a Munger-chaired meeting: paraphrase, not verbatim; may contain questions, other speakers and note-taker comments. Never quote as Munger's words."},
    {"series": None, "title_contains": "Wesco Annual Meeting", "person": "Charlie Munger",
     "basis": "meeting-notes-principal",
     "caution": "Third-party notes of a Munger-chaired meeting: paraphrase, not verbatim; may contain questions, other speakers and note-taker comments. Never quote as Munger's words."},
    {"series": "munger-pasadena-conversation-notes", "author": None, "person": "Charlie Munger",
     "basis": "meeting-notes-principal",
     "caution": "Third-party notes of a Munger conversation: paraphrase, not verbatim; may include questions and note-taker comments."},
    {"series": "daily-journal-meetings", "source_type": "meeting_notes", "person": "Charlie Munger",
     "basis": "meeting-notes-principal",
     "caution": "Third-party notes of a Munger-chaired Daily Journal meeting: unlabelled passages may be questions, other speakers or reporter commentary."},
    {"series": "munger-writings-worldly", "author_prefix": "Attributed to Charles T. Munger", "person": "Charlie Munger",
     "basis": "archive-attributed",
     "caution": "Authorship rests on the Worldly archive attribution; the copy has no byline."},
]


def propose(corpus):
    rows = corpus.db.execute(
        "SELECT d.id,d.title,d.source_type,d.metadata,sum(c.speaker IS NULL) AS unlabelled "
        "FROM documents d JOIN chunks c ON c.document_id=d.id GROUP BY d.id HAVING unlabelled>0").fetchall()
    proposals = {}
    for row in rows:
        meta = json.loads(row["metadata"])
        for rule in RULES:
            if rule.get("series") and meta.get("series") != rule["series"]:
                continue
            if rule.get("series") is None and rule.get("title_contains") and rule["title_contains"] not in row["title"]:
                continue
            if rule.get("author") and meta.get("author") != rule["author"]:
                continue
            if rule.get("author_prefix") and not str(meta.get("author", "")).startswith(rule["author_prefix"]):
                continue
            if rule.get("source_type") and row["source_type"] != rule["source_type"]:
                continue
            proposals[row["id"]] = {"person": rule["person"], "basis": rule["basis"], "caution": rule["caution"],
                                    "title": row["title"], "unlabelled_chunks": row["unlabelled"]}
            break
    return proposals


def main():
    from retrieve import open_corpus
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("propose", help="List documents the rules would attribute; review before saving")
    sub.add_parser("show", help="Show the reviewed map and label variants")
    args = parser.parse_args()
    corpus = open_corpus(args.library)
    try:
        if args.command == "propose":
            output = {"proposals": propose(corpus),
                      "note": "Proposals only. Review each document, then save into assets/attribution_map.json."}
        else:
            output = {"label_variants": LABEL_VARIANTS, "documents": load_map()}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    finally:
        corpus.close()


if __name__ == "__main__":
    main()
