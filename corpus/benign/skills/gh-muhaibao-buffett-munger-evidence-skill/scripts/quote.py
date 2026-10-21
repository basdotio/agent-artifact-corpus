#!/usr/bin/env python3
"""Return the complete original sentence(s) around a phrase, so answers never quote fragments.

A truncated quote can drop the condition, negation or qualifier that changes its meaning. Given a chunk
and a phrase from it, this returns every sentence the phrase touches, from the start of the first to the
end of the last, joining neighbouring passages by the same speaker when a sentence crosses a chunk
boundary. Speaker labels printed in transcripts ("WARREN BUFFETT:") are removed from the quote.
"""
import argparse
import json
import re
from pathlib import Path

from qa import label_end
from retrieve import open_corpus

ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "st", "co", "inc", "corp", "ltd", "jr", "sr", "vs", "etc", "e.g", "i.e",
                 "u.s", "u.k", "no", "nos", "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct",
                 "nov", "dec", "approx", "fig", "vol", "p", "pp", "gov", "gen", "sen", "rep"}
CLOSERS = "\"'”’»)]」』）"
CJK_END = re.compile(r"[。！？!?](?:[" + re.escape(CLOSERS) + r"])*")
LATIN_END = re.compile(r"[.!?](?:[" + re.escape(CLOSERS) + r"])*(?=\s|$)")


def _is_abbreviation(text, dot):
    """True when the period at index `dot` ends an abbreviation or an initial rather than a sentence."""
    if text[dot] != ".":
        return False
    word = re.search(r"([A-Za-z][A-Za-z.]*)$", text[:dot])
    if not word:
        return False
    token = word.group(1).lower()
    if token in ABBREVIATIONS or len(token) == 1:          # "Mr.", "Co.", "Charles T. Munger"
        return True
    return bool(re.fullmatch(r"(?:[a-z]\.)+[a-z]", token))  # "U.S", "i.e"


def sentence_spans(text):
    """[(start, end)] sentence spans; handles English and Chinese terminal punctuation."""
    ends = []
    for m in CJK_END.finditer(text):
        if text[m.start()] in "。！？":
            ends.append(m.end())
    for m in LATIN_END.finditer(text):
        if not _is_abbreviation(text, m.start()):
            ends.append(m.end())
    spans, start = [], 0
    for end in sorted(set(ends)):
        if end <= start:
            continue
        if text[start:end].strip():
            spans.append((start, end))
        start = end
    if text[start:].strip():
        spans.append((start, len(text)))
    trimmed = []
    for s, e in spans:
        while s < e and text[s].isspace():
            s += 1
        trimmed.append((s, e))
    return trimmed


def _normalize(text):
    return " ".join(text.split())


def _joiner(left, right):
    if not left or not right:
        return ""
    return "" if re.match(r"[　-鿿＀-￯]", left[-1]) and re.match(r"[　-鿿＀-￯]", right[0]) else " "


def quote(corpus, chunk_id, match, before=0, after=0, reach=2):
    row = corpus.db.execute("SELECT * FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown chunk id: " + chunk_id)
    rows = corpus.db.execute("SELECT * FROM chunks WHERE document_id=? AND ordinal BETWEEN ? AND ? ORDER BY ordinal",
                             (row["document_id"], row["ordinal"] - reach, row["ordinal"] + reach)).fetchall()
    # A sentence can continue into a neighbouring chunk only if the same speaker is talking.
    target = next(i for i, r in enumerate(rows) if r["id"] == chunk_id)
    lo = target
    while lo > 0 and rows[lo - 1]["speaker"] == row["speaker"] and not label_end(rows[lo]["text"], rows[lo]["speaker"]):
        lo -= 1
    hi = target
    while hi + 1 < len(rows) and rows[hi + 1]["speaker"] == row["speaker"] and not label_end(rows[hi + 1]["text"], rows[hi + 1]["speaker"]):
        hi += 1
    pieces, offsets, text = [], [], ""
    for r in rows[lo:hi + 1]:
        part = _normalize(r["text"][label_end(r["text"], r["speaker"]):])
        sep = _joiner(text, part)
        offsets.append((r["id"], len(text) + len(sep), len(text) + len(sep) + len(part)))
        text += sep + part
        pieces.append(r)
    t_start, t_end = next((s, e) for cid, s, e in offsets if cid == chunk_id)
    needle = _normalize(match).casefold()
    found = text.casefold().find(needle, t_start)
    if found < 0 or found >= t_end:
        raise ValueError("Phrase not found in the chunk (after whitespace normalisation): " + match)
    spans = sentence_spans(text)
    first = next(i for i, (s, e) in enumerate(spans) if s <= found < e or found < s)
    last = next(i for i, (s, e) in enumerate(spans) if s < found + len(needle) <= e or found + len(needle) <= s)
    first, last = max(0, first - before), min(len(spans) - 1, last + after)
    q_start, q_end = spans[first][0], spans[last][1]
    used = [cid for cid, s, e in offsets if s < q_end and e > q_start]
    doc = corpus.db.execute("SELECT * FROM documents WHERE id=?", (row["document_id"],)).fetchone()
    meta = json.loads(doc["metadata"])
    item = corpus.evidence(row, full=True)
    result = {
        "quote": text[q_start:q_end].strip(),
        "sentences": last - first + 1,
        "speaker": row["speaker"],
        "chunk_ids": used,
        "title": doc["title"], "date": doc["date"], "url": doc["url"], "locator": json.loads(row["locator"]),
        "source_type": doc["source_type"], "primary_status": doc["primary_status"],
        "transcript_quality": meta.get("transcript_quality"),
        "evidence_eligibility": item["evidence_eligibility"],
    }
    notes = []
    if doc["source_type"] == "translation":
        notes.append("Translation, not the original wording: label it 译文 and give the original language source where one exists"
                     + (f" ({meta['translation_of']})." if meta.get("translation_of") else "."))
    if not item["evidence_eligibility"]["exact_quote_candidate"]:
        notes.append("Not verified verbatim (third-party, rough or OCR text): say so next to the quote.")
    if row["speaker"] is None:
        notes.append("Speaker is unassigned in the source; establish who wrote or said it before attributing.")
    result["notes"] = notes
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("chunk_id")
    parser.add_argument("--match", required=True, help="A phrase copied from the chunk text")
    parser.add_argument("--before", type=int, default=0, help="Extra complete sentences before")
    parser.add_argument("--after", type=int, default=0, help="Extra complete sentences after")
    args = parser.parse_args()
    corpus = open_corpus(args.library)
    try:
        print(json.dumps(quote(corpus, args.chunk_id, args.match, args.before, args.after), ensure_ascii=False, indent=2))
    finally:
        corpus.close()


if __name__ == "__main__":
    main()
