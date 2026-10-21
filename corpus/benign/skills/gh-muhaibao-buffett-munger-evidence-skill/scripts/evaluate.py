#!/usr/bin/env python3
"""Blind evaluation against real meeting answers ("does it think like them?").

1. sample: draw held-out Q&A units (fixed seed). Writes questions.jsonl (no
   answers; safe to show the answering system) and holdout.jsonl (gold; keep
   unseen until scoring). Each question carries the exclusions to apply when
   answering: drop its source document and everything after the prior year.
2. Answer each question with the skill under those exclusions; save
   answers.jsonl lines {"id", "buffett", "munger", "basket"}.
3. score: mechanical metrics plus a side-by-side judging sheet. Judgments
   (direction, core reason, decline behaviour) are recorded in judgments.jsonl
   and aggregated with `summarize`.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import re

from qa import DECLINE_MARKERS, load, words
from retrieve import atomic_json, open_corpus

SECTION_LEAK = "Section titles are withheld: CNBC titles often summarize the answer."
BASKETS = ("yes", "no", "too-hard", "not-applicable")
JUDGMENT_FIELDS = {"direction": ("agree", "partial", "disagree", "not-comparable"),
                   "core_reason": ("same", "partial", "different"),
                   "decline_behaviour": ("match", "mismatch", "n/a"),
                   "fabrication": ("none", "minor", "major")}


def eligible(record, min_answer=60, max_question=180):
    words_by = record["answer"]["words_by"]
    principal = words_by.get("Warren Buffett", 0) + words_by.get("Charlie Munger", 0)
    return (record["source_type"] == "annual_meeting" and not record["flags"]["procedural"]
            and record["year"] is not None and 12 <= record["question"]["words"] <= max_question
            and principal >= min_answer)


def sample(records, n=24, seed=20261009, munger_share=0.4, exclude_ids=()):
    """Stratify by decade; reserve a share for questions Munger answered substantively.

    exclude_ids removes units already used in earlier batches: once seen, a unit is development data."""
    rng = random.Random(seed)
    used = set(exclude_ids)
    pool = [r for r in records if eligible(r) and r["id"] not in used]
    by_decade = defaultdict(list)
    for record in pool:
        by_decade[(record["year"] // 10) * 10].append(record)
    decades = sorted(by_decade)
    chosen, used_documents = [], Counter()
    quota = {d: n // len(decades) + (1 if i < n % len(decades) else 0) for i, d in enumerate(decades)}
    for decade in decades:
        candidates = by_decade[decade][:]
        rng.shuffle(candidates)
        munger_first = [r for r in candidates if r["answer"]["words_by"].get("Charlie Munger", 0) >= 40]
        want_munger = round(quota[decade] * munger_share)
        picked = []
        for group, limit in ((munger_first, want_munger), (candidates, quota[decade])):
            for record in group:
                if len(picked) >= limit:
                    break
                # At most two questions per session keeps the set from clustering on one meeting.
                if record in picked or used_documents[record["document_id"]] >= 2:
                    continue
                picked.append(record)
                used_documents[record["document_id"]] += 1
        chosen.extend(picked)
    return chosen


def question_view(record):
    return {"id": record["id"], "year": record["year"], "date": record["date"],
            "question": record["question"]["text"],
            "exclusions": {"exclude_documents": [record["document_id"]], "year_to": record["year"] - 1},
            "instructions": "Answer as of the year before the meeting; do not search for this meeting. Who answered is withheld "
                            "because speaker choice is scored. " + SECTION_LEAK}


def gold_view(record):
    text = {p: "\n".join(t["text"] for t in record["answer"]["turns"] if t["person"] == p)
            for p in ("Warren Buffett", "Charlie Munger")}
    return {"id": record["id"], "document_id": record["document_id"], "title": record["title"],
            "sections": record["sections"], "question": record["question"]["text"],
            "first_responder": record["answer"]["first_responder"], "words_by": record["answer"]["words_by"],
            "buffett": text["Warren Buffett"], "munger": text["Charlie Munger"],
            "decline_markers": record["flags"]["decline_markers"]}


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, rows):
    Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def text_size(text):
    """Comparable size for English gold and Chinese answers: English words, or CJK chars / 1.6."""
    cjk = len(re.findall(r"[一-鿿]", text or ""))
    return words(text or "") + cjk / 1.6


def mechanical(gold, answer):
    out = {}
    for key, person in (("buffett", "Warren Buffett"), ("munger", "Charlie Munger")):
        g, a = gold["words_by"].get(person, 0), text_size(answer.get(key, ""))
        out[key] = {"gold_words": g, "answer_size": round(a), "spoke_in_gold": g > 0, "spoke_in_answer": a > 0,
                    "ratio": round(a / g, 2) if g else None}
    out["speaker_match"] = all(out[k]["spoke_in_gold"] == out[k]["spoke_in_answer"] for k in ("buffett", "munger"))
    if gold["words_by"].get("Warren Buffett") and gold["words_by"].get("Charlie Munger"):
        gold_ratio = gold["words_by"]["Charlie Munger"] / gold["words_by"]["Warren Buffett"]
        answer_ratio = (out["munger"]["answer_size"] / out["buffett"]["answer_size"]) if out["buffett"]["answer_size"] else None
        out["munger_to_buffett"] = {"gold": round(gold_ratio, 2), "answer": round(answer_ratio, 2) if answer_ratio is not None else None}
    gold_decline = bool(gold["decline_markers"])
    answer_text = " ".join(answer.get(k, "") for k in ("buffett", "munger"))
    answer_decline = answer.get("basket") == "too-hard" or bool(DECLINE_MARKERS.search(answer_text)) or bool(
        re.search(r"不知道|太难|无法预测|不预测|能力圈之外|看不懂", answer_text))
    out["decline_marker"] = {"gold": gold_decline, "answer": answer_decline}
    return out


def score(holdout, answers, out_dir):
    gold = {g["id"]: g for g in read_jsonl(holdout)}
    rows, sheet = [], ["# 盲测评分表", "",
                       "每题先读系统回答，再读真实回答。判分写入 judgments.jsonl：",
                       '`{"id", "direction": agree|partial|disagree|not-comparable, "core_reason": same|partial|different, '
                       '"decline_behaviour": match|mismatch|n/a, "fabrication": none|minor|major, "notes"}`', ""]
    for answer in read_jsonl(answers):
        g = gold.get(answer["id"])
        if g is None:
            raise ValueError("Answer for unknown id: " + answer["id"])
        metrics = mechanical(g, answer)
        rows.append({"id": answer["id"], "metrics": metrics})
        sheet += [f"## {answer['id']}（{g['title']}）", "", f"**问题**：{g['question']}", "",
                  f"**系统·巴菲特**（basket={answer.get('basket')}）：{answer.get('buffett') or '（未作答）'}", "",
                  f"**系统·芒格**：{answer.get('munger') or '（未作答）'}", "",
                  f"**真实·巴菲特**（{g['words_by'].get('Warren Buffett', 0)} 词）：{g['buffett'] or '（未发言）'}", "",
                  f"**真实·芒格**（{g['words_by'].get('Charlie Munger', 0)} 词）：{g['munger'] or '（未发言）'}", "",
                  f"机械指标：`{json.dumps(metrics, ensure_ascii=False)}`", "", "---", ""]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    atomic_json(out_dir / "mechanical.json", {"items": rows, "summary": summarize_mechanical(rows)})
    (out_dir / "judging-sheet.md").write_text("\n".join(sheet), encoding="utf-8")
    return {"items": len(rows), "summary": summarize_mechanical(rows),
            "sheet": str((out_dir / "judging-sheet.md").resolve())}


def summarize_mechanical(rows):
    if not rows:
        return {}
    n = len(rows)
    munger_gold_short = [r for r in rows if r["metrics"]["munger"]["spoke_in_gold"] and r["metrics"]["munger"]["gold_words"] <= 50]
    return {"n": n,
            "speaker_match_rate": round(sum(r["metrics"]["speaker_match"] for r in rows) / n, 3),
            "decline_marker_agreement": round(sum(r["metrics"]["decline_marker"]["gold"] == r["metrics"]["decline_marker"]["answer"]
                                                  for r in rows) / n, 3),
            "median_buffett_ratio": median([r["metrics"]["buffett"]["ratio"] for r in rows]),
            "median_munger_ratio": median([r["metrics"]["munger"]["ratio"] for r in rows]),
            "munger_brief_in_gold": len(munger_gold_short),
            "munger_brief_matched": sum(0 < r["metrics"]["munger"]["answer_size"] <= 80 for r in munger_gold_short)}


def median(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else round((values[middle - 1] + values[middle]) / 2, 2)


def summarize(judgments):
    rows = read_jsonl(judgments)
    out = {"n": len(rows)}
    for field, allowed in JUDGMENT_FIELDS.items():
        counts = Counter(r.get(field) for r in rows)
        unknown = set(counts) - set(allowed)
        if unknown:
            raise ValueError(f"{field} has invalid values: {sorted(map(str, unknown))}")
        out[field] = dict(counts)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--library", required=True, type=Path)
    s.add_argument("--out", required=True, type=Path)
    s.add_argument("--n", type=int, default=24)
    s.add_argument("--seed", type=int, default=20261009)
    s.add_argument("--exclude-batch", action="append", default=[], type=Path,
                   help="questions.jsonl of an earlier batch; its units are excluded (repeatable)")
    sc = sub.add_parser("score")
    sc.add_argument("--holdout", required=True, type=Path)
    sc.add_argument("--answers", required=True, type=Path)
    sc.add_argument("--out", required=True, type=Path)
    sm = sub.add_parser("summarize")
    sm.add_argument("--judgments", required=True, type=Path)
    args = parser.parse_args()
    if args.command == "sample":
        corpus = open_corpus(args.library)
        try:
            used = [q["id"] for path in args.exclude_batch for q in read_jsonl(path)]
            chosen = sample(load(corpus), args.n, args.seed, exclude_ids=used)
        finally:
            corpus.close()
        args.out.mkdir(parents=True, exist_ok=True)
        write_jsonl(args.out / "questions.jsonl", [question_view(r) for r in chosen])
        write_jsonl(args.out / "holdout.jsonl", [gold_view(r) for r in chosen])
        result = {"questions": str(args.out / "questions.jsonl"), "holdout": str(args.out / "holdout.jsonl"),
                  "n": len(chosen), "by_decade": dict(Counter(f"{(r['year'] // 10) * 10}s" for r in chosen)),
                  "note": "Do not open holdout.jsonl before answers are written."}
    elif args.command == "score":
        result = score(args.holdout, args.answers, args.out)
    else:
        result = summarize(args.judgments)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
