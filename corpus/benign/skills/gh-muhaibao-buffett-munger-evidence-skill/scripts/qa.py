#!/usr/bin/env python3
"""Question -> answer units from labelled meeting and interview transcripts.

Purpose: find how Buffett and Munger actually answered questions similar to a
new one (structure, length, whether they declined, who spoke), and measure
their answer-style distributions. Units are derived navigation, not evidence:
cite the underlying chunks after opening them with library.py show.

Segmentation is heuristic: a new unit starts when a non-principal speaker
(questioner, moderator) speaks at length after Buffett or Munger has answered.
Other responders (Abel, Jain, Combs, Weschler, Sokol; Daily Journal's Salzman, Myhill-Jones) stay inside the
answer. Unlabelled meeting notes (Wesco, early Daily Journal) are not segmented.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import time

import attribution
from library import speaker_name
from retrieve import LocalModel, atomic_json, fingerprint, open_corpus, query_terms
from setup_retrieval import MODELS, sha256

QA_VERSION = 1
SOURCE_TYPES = ("annual_meeting", "interview", "transcript")
RESPONDER = re.compile(r"\b(ABEL|JAIN|COMBS|WESCHLER|SOKOL|SALZMAN|MYHILL)", re.I)
# Speaker labels printed inside transcript text, e.g. "WARREN BUFFETT:" (all caps only, so ordinary
# sentences ending in a colon are not mistaken for labels).
CAPS_LABEL = re.compile(r"^\s*[A-Z][A-Z0-9 .,'’()&/-]{1,60}:\s*")
PROCEDURAL = re.compile(r"welcome|earnings|adjourn|business meeting|election|vote|voting|motion|lunch|break\b|"
                        r"introduc|movie|proxy|shareholder proposal|second the|so moved|preliminary", re.I)
# Lexical markers only: they flag candidate declines/abstentions for review, they do not classify.
DECLINE_MARKERS = re.compile(r"\b(I don't know|we don't know|I have no idea|no idea|can't predict|cannot predict|"
                             r"don't make (?:macro|market|economic) forecasts|not going to (?:predict|forecast|comment|tell)|"
                             r"too hard|too tough|too difficult|outside (?:my|our) circle|don't have any view|"
                             r"don't have an opinion|no opinion)\b", re.I)
NOTHING_TO_ADD = re.compile(r"nothing (?:further |more )?to add|I have nothing|nothing more to say", re.I)
INTERJECTION_CHARS = 40


def words(text):
    return len(re.findall(r"[A-Za-z0-9']+", text))


def label_end(text, speaker=None):
    """Length of a leading speaker label ("WARREN BUFFETT:" or the chunk's own label), else 0."""
    match = CAPS_LABEL.match(text)
    if match:
        return match.end()
    head = text.lstrip()
    if speaker and head.lower().startswith(speaker.lower() + ":"):
        return len(text) - len(head) + len(speaker) + 1
    return 0


def strip_label(text, speaker=None):
    return text[label_end(text, speaker):].strip()


def documents(corpus):
    placeholders = ",".join("?" * len(SOURCE_TYPES))
    return corpus.db.execute(
        f"SELECT * FROM documents WHERE source_type IN ({placeholders}) ORDER BY year,id", SOURCE_TYPES).fetchall()


def turns_of(corpus, document_id):
    turns = []
    for row in corpus.db.execute("SELECT id,speaker,text,locator FROM chunks WHERE document_id=? ORDER BY ordinal",
                                 (document_id,)):
        locator = json.loads(row["locator"])
        # A printed label starts a new turn even for the same speaker: transcripts drop short interjections.
        starts_turn = label_end(row["text"], row["speaker"]) > 0
        if turns and turns[-1]["speaker"] == row["speaker"] and not starts_turn:
            turns[-1]["text"] += "\n" + row["text"]
            turns[-1]["chunk_ids"].append(row["id"])
            if locator.get("section") and locator["section"] not in turns[-1]["sections"]:
                turns[-1]["sections"].append(locator["section"])
            continue
        turns.append({"speaker": row["speaker"], "text": row["text"], "chunk_ids": [row["id"]],
                      "sections": [locator["section"]] if locator.get("section") else []})
    return turns


def role(turn):
    if attribution.canonical(turn["speaker"]):
        return "principal"
    if turn["speaker"] and RESPONDER.search(turn["speaker"]):
        return "responder"
    return "other"


def segment(turns):
    """Group turns into units of question turns followed by answer turns."""
    units, current = [], None
    for turn in turns:
        kind = role(turn)
        if kind == "other":
            answered = current is not None and any(t["role"] != "other" for t in current["answer"])
            short = len(strip_label(turn["text"], turn["speaker"])) < INTERJECTION_CHARS and "?" not in turn["text"]
            if current is not None and answered and short:
                current["answer"].append(dict(turn, role="other"))
                continue
            if current is None or answered:
                current = {"question": [], "answer": []}
                units.append(current)
            current["question"].append(turn)
        else:
            if current is None:
                current = {"question": [], "answer": []}
                units.append(current)
            current["answer"].append(dict(turn, role=kind))
    return units


def unit_record(doc, index, unit):
    question_text = "\n".join(strip_label(t["text"], t["speaker"]) for t in unit["question"]).strip()
    answer_turns, words_by = [], defaultdict(int)
    for turn in unit["answer"]:
        person = attribution.canonical(turn["speaker"])
        text = strip_label(turn["text"], turn["speaker"])
        count = words(text)
        words_by[person or ("responder" if turn["role"] == "responder" else "other")] += count
        answer_turns.append({"speaker": turn["speaker"], "person": person, "role": turn["role"],
                             "words": count, "text": text, "chunk_ids": turn["chunk_ids"]})
    principals = [t for t in answer_turns if t["person"]]
    sections = list(dict.fromkeys(s for t in unit["question"] + unit["answer"] for s in t["sections"]))
    first = next((t for t in answer_turns if t["role"] != "other"), None)
    munger_text = " ".join(t["text"] for t in answer_turns if t["person"] == "Charlie Munger")
    principal_text = " ".join(t["text"] for t in principals)
    return {
        "id": f"{doc['id']}#{index}", "document_id": doc["id"], "title": doc["title"], "date": doc["date"],
        "year": doc["year"], "source_type": doc["source_type"], "sections": sections,
        "question": {"text": question_text, "speakers": list(dict.fromkeys(t["speaker"] for t in unit["question"])),
                     "words": words(question_text), "chunk_ids": [c for t in unit["question"] for c in t["chunk_ids"]]},
        "answer": {"turns": answer_turns, "first_responder": (first["person"] or first["speaker"]) if first else None,
                   "words_by": dict(words_by)},
        "flags": {"has_question": bool(question_text), "has_principal_answer": bool(principals),
                  "procedural": bool(PROCEDURAL.search(" ".join(sections) + " " + question_text[:200]))
                  or words(question_text) < 6,
                  "decline_markers": sorted({m.group(0).lower() for m in DECLINE_MARKERS.finditer(principal_text)}),
                  "munger_nothing_to_add": bool(NOTHING_TO_ADD.search(munger_text))},
    }


def build_units(corpus):
    records = []
    for doc in documents(corpus):
        # Transcripts reorganized by speaker (questions grouped apart from answers) cannot be paired by adjacency.
        if json.loads(doc["metadata"]).get("qa_segmentable") is False:
            continue
        turns = turns_of(corpus, doc["id"])
        if not any(role(t) == "principal" for t in turns):
            continue
        for index, unit in enumerate(segment(turns)):
            record = unit_record(doc, index, unit)
            if record["flags"]["has_question"] and record["flags"]["has_principal_answer"]:
                records.append(record)
    return records


def qa_dir(corpus):
    return corpus.root / "qa"


def build(corpus, models_dir, batch_size=32, threads=4, embed=True):
    import numpy as np
    directory = qa_dir(corpus)
    directory.mkdir(parents=True, exist_ok=True)
    before = fingerprint(corpus)
    records = build_units(corpus)
    pairs_path = directory / "pairs.jsonl"
    temp = pairs_path.with_name(pairs_path.name + ".tmp")
    temp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    temp.replace(pairs_path)
    manifest = {"version": QA_VERSION, "corpus_fingerprint": before, "units": len(records),
                "pairs_sha256": sha256(pairs_path), "embedded": False}
    if embed:
        model = LocalModel(models_dir, max_tokens=256, threads=threads)
        vectors = np.zeros((len(records), 384), dtype=np.float32)
        for start in range(0, len(records), batch_size):
            batch = records[start:start + batch_size]
            vectors[start:start + len(batch)] = model.embed([r["question"]["text"][:1500] for r in batch], query=True)
        np.save(directory / "vectors.npy", vectors, allow_pickle=False)
        manifest.update(embedded=True, model=MODELS["embedding"], max_tokens=256,
                        vectors_sha256=sha256(directory / "vectors.npy"))
    if fingerprint(corpus) != before:
        raise ValueError("Corpus changed while building Q&A units; not activated")
    manifest["built_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    atomic_json(directory / "manifest.json", manifest)
    return {k: manifest[k] for k in ("units", "embedded", "built_at")}


def status(corpus):
    directory = qa_dir(corpus)
    try:
        manifest = json.loads((directory / "manifest.json").read_text())
    except (OSError, ValueError):
        return {"ready": False, "reason": "Q&A units not built"}
    if manifest.get("version") != QA_VERSION:
        return {"ready": False, "reason": "Q&A format version mismatch"}
    if manifest["corpus_fingerprint"] != fingerprint(corpus):
        return {"ready": False, "reason": "corpus changed; Q&A units are stale"}
    if sha256(directory / "pairs.jsonl") != manifest["pairs_sha256"]:
        return {"ready": False, "reason": "pairs.jsonl checksum mismatch"}
    semantic = bool(manifest.get("embedded")) and (directory / "vectors.npy").exists() and \
        sha256(directory / "vectors.npy") == manifest.get("vectors_sha256")
    return {"ready": True, "units": manifest["units"], "semantic": semantic, "built_at": manifest["built_at"]}


def load(corpus):
    with (qa_dir(corpus) / "pairs.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def keep(record, answered_by=None, year_from=None, year_to=None, exclude_documents=(), include_procedural=False):
    if record["document_id"] in set(exclude_documents or ()):
        return False
    if not include_procedural and record["flags"]["procedural"]:
        return False
    year = record["year"]
    if year_from is not None and (year is None or year < year_from):
        return False
    if year_to is not None and (year is None or year > year_to):
        return False
    if answered_by:
        person = speaker_name(answered_by)
        return record["answer"]["words_by"].get(person, 0) > 0
    return True


def summarize(record, opening=400):
    turns = []
    for turn in record["answer"]["turns"]:
        if turn["role"] == "other":
            continue
        turns.append({"speaker": turn["person"] or turn["speaker"], "words": turn["words"],
                      "opening": turn["text"][:opening], "chunk_ids": turn["chunk_ids"][:3]})
    return {"id": record["id"], "date": record["date"], "title": record["title"], "sections": record["sections"],
            "question": record["question"]["text"][:700], "first_responder": record["answer"]["first_responder"],
            "words_by": record["answer"]["words_by"], "flags": record["flags"], "answer_turns": turns}


def search(corpus, query, models_dir, limit=5, rerank_query=None, rerank=True, threads=4, **filters):
    import numpy as np
    state = status(corpus)
    if not state["ready"]:
        raise ValueError(state["reason"])
    records = load(corpus)
    selected = [i for i, r in enumerate(records) if keep(r, **filters)]
    warnings, mode = [], "lexical"
    scores = {}
    if state["semantic"]:
        try:
            model = LocalModel(models_dir, max_tokens=256, threads=threads)
            vectors = np.load(qa_dir(corpus) / "vectors.npy", mmap_mode="r", allow_pickle=False)
            values = vectors @ model.embed([query], query=True)[0]
            scores = {i: float(values[i]) for i in selected}
            mode = "semantic"
        except (ImportError, OSError, ValueError) as exc:
            warnings.append("Q&A lexical fallback: " + str(exc))
    if not scores:
        terms = [t.lower() for t in query_terms(query)]
        for i in selected:
            text = records[i]["question"]["text"].lower()
            scores[i] = float(sum(text.count(t) for t in terms))
    order = sorted(selected, key=lambda i: (-scores[i], records[i]["id"]))[:max(limit * 6, 30)]
    reranked = False
    if rerank and order:
        try:
            ranker = LocalModel(models_dir, "reranker", max_tokens=512, threads=threads)
            texts = []
            for i in order:
                answer = " ".join(t["text"] for t in records[i]["answer"]["turns"] if t["person"])[:600]
                texts.append(f"Question: {records[i]['question']['text'][:900]}\nAnswer opening: {answer}")
            logits = ranker.rerank(rerank_query or query, texts)
            order = [i for _, i in sorted(zip(logits, order), key=lambda pair: -pair[0])]
            reranked = True
        except (ImportError, OSError, ValueError) as exc:
            warnings.append("Q&A reranker unavailable; kept first-stage order: " + str(exc))
    results = [dict(summarize(records[i]), score=scores[i]) for i in order[:limit]
               if mode == "semantic" or scores[i] > 0]
    return {"query": query, "mode_used": mode, "reranked": reranked, "warnings": warnings, "results": results,
            "note": "Real Q&A units as structure/length anchors. Not evidence until the cited chunks are opened; "
                    "segmentation is heuristic and may merge or split questions."}


def describe(values):
    if not values:
        return {"n": 0}
    values = sorted(values)
    q = statistics.quantiles(values, n=4) if len(values) > 1 else [values[0]] * 3
    return {"n": len(values), "p25": round(q[0]), "median": round(q[1]), "p75": round(q[2]), "max": values[-1]}


def stats(corpus, source_type="annual_meeting"):
    records = [r for r in load(corpus) if not r["flags"]["procedural"]
               and (source_type is None or r["source_type"] == source_type)]
    out = {"units": len(records), "source_type": source_type or "all"}
    buffett = [r["answer"]["words_by"].get("Warren Buffett", 0) for r in records]
    munger = [r["answer"]["words_by"].get("Charlie Munger", 0) for r in records]
    out["buffett_words_when_speaking"] = describe([b for b in buffett if b])
    out["munger_words_when_speaking"] = describe([m for m in munger if m])
    both = [r for r in records if r["answer"]["words_by"].get("Warren Buffett") and r["answer"]["words_by"].get("Charlie Munger")]
    out["units_with_both"] = len(both)
    if both:
        followups = [r for r in both if r["answer"]["first_responder"] == "Warren Buffett"]
        munger_follow = [r["answer"]["words_by"]["Charlie Munger"] for r in followups]
        out["munger_after_buffett"] = {
            "units": len(followups),
            "words": describe(munger_follow),
            "share_at_most_15_words": round(sum(w <= 15 for w in munger_follow) / len(munger_follow), 3) if munger_follow else None,
            "share_at_most_50_words": round(sum(w <= 50 for w in munger_follow) / len(munger_follow), 3) if munger_follow else None,
            "nothing_to_add_marker_share": round(sum(r["flags"]["munger_nothing_to_add"] for r in followups) / len(followups), 3)}
    out["first_responder"] = dict(Counter(r["answer"]["first_responder"] for r in records).most_common(6))
    out["decline_marker_share"] = round(sum(bool(r["flags"]["decline_markers"]) for r in records) / len(records), 3) if records else None
    by_decade = defaultdict(lambda: {"units": 0, "buffett": [], "munger": []})
    for r in records:
        decade = f"{(r['year'] // 10) * 10}s" if r["year"] else "unknown"
        by_decade[decade]["units"] += 1
        if r["answer"]["words_by"].get("Warren Buffett"):
            by_decade[decade]["buffett"].append(r["answer"]["words_by"]["Warren Buffett"])
        if r["answer"]["words_by"].get("Charlie Munger"):
            by_decade[decade]["munger"].append(r["answer"]["words_by"]["Charlie Munger"])
    out["by_decade"] = {k: {"units": v["units"], "buffett_median_words": describe(v["buffett"]).get("median"),
                            "munger_median_words": describe(v["munger"]).get("median")} for k, v in sorted(by_decade.items())}
    out["note"] = ("Word counts of transcript text per unit; segmentation is heuristic. Decline and 'nothing to add' "
                   "figures count lexical markers, not reviewed classifications.")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", required=True, type=Path)
    parser.add_argument("--models-dir", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--no-embed", action="store_true")
    b.add_argument("--threads", type=int, default=4)
    sub.add_parser("status")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--rerank-query")
    s.add_argument("--answered-by")
    s.add_argument("--year-from", type=int)
    s.add_argument("--year-to", type=int)
    s.add_argument("--exclude-document", action="append", default=[], dest="exclude_documents")
    s.add_argument("--include-procedural", action="store_true")
    s.add_argument("--no-rerank", action="store_true")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--output", type=Path)
    st = sub.add_parser("stats")
    st.add_argument("--source-type", default="annual_meeting", help="annual_meeting (default), interview, transcript, or all")
    sh = sub.add_parser("show")
    sh.add_argument("unit_id")
    args = parser.parse_args()
    corpus = open_corpus(args.library)
    models_dir = args.models_dir or corpus.root / "retrieval" / "models"
    try:
        if args.command == "build":
            result = build(corpus, models_dir, threads=args.threads, embed=not args.no_embed)
        elif args.command == "status":
            result = status(corpus)
        elif args.command == "stats":
            result = stats(corpus, None if args.source_type == "all" else args.source_type)
        elif args.command == "show":
            result = next((r for r in load(corpus) if r["id"] == args.unit_id), None)
            if result is None:
                raise SystemExit("Unknown unit id: " + args.unit_id)
        else:
            result = search(corpus, args.query, models_dir, limit=args.limit, rerank_query=args.rerank_query,
                            rerank=not args.no_rerank, answered_by=args.answered_by, year_from=args.year_from,
                            year_to=args.year_to, exclude_documents=args.exclude_documents,
                            include_procedural=args.include_procedural)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                atomic_json(args.output, result)
                result = {"saved": str(args.output.resolve()), "mode_used": result["mode_used"],
                          "reranked": result["reranked"], "results": len(result["results"]), "warnings": result["warnings"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        corpus.close()


if __name__ == "__main__":
    main()
