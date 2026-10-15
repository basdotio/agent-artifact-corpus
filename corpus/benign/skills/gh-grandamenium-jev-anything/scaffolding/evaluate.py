"""
evaluate.py - measure a Jev classifier against labeled data and store each run, so
you can optimize (mostly the criteria) and re-measure. See
../references/04-measure-and-optimize.md.

Contract (you provide two things):
1. predict(example) -> dict of predictions for that input, e.g.
       {"department": "billing", "urgency": 2,
        "_confidence": {"department": 0.97, "urgency": 0.81},
        "_cost": 1.7e-05}
   Use YOUR integration inside predict (it calls Jev). "_confidence" and "_cost" are
   optional; include them to get calibration and cost reporting. For a choice/label
   question return the label; for a score question return the number.
2. labeled: a list of (example, expected) pairs, where expected maps question name
   to the correct answer, e.g. ({...email...}, {"department": "billing", "urgency": 3}).

Then call evaluate(predict, labeled). It writes results/run-<timestamp>.json and
prints a summary plus the change vs the previous run.

Score answers count as correct within +/- 0.5 of the expected level (tune below).
"""

import csv
import json
import math
import os
import random
import time
from collections import defaultdict

SCORE_TOLERANCE = 0.5


def load_labeled_csv(path, text_key="text"):
    """Load a filled rating sheet (from make_rating_sheet.py) into a labeled list.
    Columns: id, text, and one column PER question named after that question, holding
    the human's correct answer. Blank answer cells are skipped (unlabeled rows).
    Numeric answers are coerced to float so score questions compare correctly.
    """
    labeled = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            expected = {}
            for k, v in row.items():
                if k in ("id", "text") or v is None or str(v).strip() == "":
                    continue
                s = str(v).strip()
                try:
                    expected[k] = (
                        float(s) if s.replace(".", "", 1).lstrip("-").isdigit() else s
                    )
                except ValueError:
                    expected[k] = s
            if expected:
                labeled.append(
                    ({text_key: row.get("text", ""), "id": row.get("id")}, expected)
                )
    return labeled


def split(labeled, test_frac=0.4, seed=0):
    """Shuffle and split into (train, test). Tune criteria on train; report on test.
    Reporting the accuracy on data you never tuned against is what keeps the number
    honest. Small sets: test_frac 0.4 keeps enough on both sides."""
    items = list(labeled)
    random.Random(seed).shuffle(items)
    k = max(1, int(round(len(items) * test_frac)))
    return items[k:], items[:k]


def wilson_ci(correct, n, z=1.96):
    """95% Wilson confidence interval for an accuracy proportion. With small n the
    interval is wide - report it so nobody over-reads a 40-item sample."""
    if n == 0:
        return (None, None)
    p = correct / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (round(max(0.0, center - half), 3), round(min(1.0, center + half), 3))


def errors(predict, labeled):
    """Return the misclassified items so you can READ why they are wrong before
    tuning criteria. Each entry: {id, text, question, expected, got}."""
    out = []
    for ex, expected in labeled:
        pred = predict(ex)
        for q, exp in expected.items():
            got = pred.get(q)
            if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
                wrong = abs(exp - got) > SCORE_TOLERANCE
            else:
                wrong = got != exp
            if wrong:
                out.append(
                    {
                        "id": ex.get("id"),
                        "text": ex.get("text", "")[:200],
                        "question": q,
                        "expected": exp,
                        "got": got,
                    }
                )
    return out


def evaluate(predict, labeled, run_dir="results", note=""):
    os.makedirs(run_dir, exist_ok=True)
    per_q = defaultdict(
        lambda: {
            "n": 0,
            "correct": 0,
            "confusion": defaultdict(lambda: defaultdict(int)),
            "abs_err": 0.0,
            "is_score": False,
        }
    )
    calib = defaultdict(lambda: {"n": 0, "correct": 0})
    total_cost = 0.0
    rows = []

    for ex, expected in labeled:
        out = predict(ex)
        conf = out.get("_confidence", {}) or {}
        total_cost += out.get("_cost", 0.0) or 0.0
        preds = {k: v for k, v in out.items() if not k.startswith("_")}
        rows.append({"expected": expected, "got": preds})
        for q, exp in expected.items():
            got = out.get(q)
            s = per_q[q]
            s["n"] += 1
            if isinstance(exp, (int, float)) and isinstance(got, (int, float)):
                s["is_score"] = True
                s["abs_err"] += abs(exp - got)
                ok = abs(exp - got) <= SCORE_TOLERANCE
            else:
                ok = got == exp
                s["confusion"][str(exp)][str(got)] += 1
            if ok:
                s["correct"] += 1
            c = conf.get(q)
            if c is not None:
                b = (
                    "hi(>=0.8)"
                    if c >= 0.8
                    else "mid(0.5-0.8)"
                    if c >= 0.5
                    else "lo(<0.5)"
                )
                calib[b]["n"] += 1
                calib[b]["correct"] += 1 if ok else 0

    summary = {
        "note": note,
        "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_examples": len(labeled),
        "total_cost": round(total_cost, 6),
        "per_question": {},
        "calibration": {},
    }
    for q, s in per_q.items():
        e = {
            "n": s["n"],
            "accuracy": round(s["correct"] / s["n"], 3) if s["n"] else None,
            "accuracy_95ci": wilson_ci(s["correct"], s["n"]),
        }
        if s["is_score"]:
            e["mean_abs_error"] = round(s["abs_err"] / s["n"], 3)
        else:
            e["confusion"] = {k: dict(v) for k, v in s["confusion"].items()}
        summary["per_question"][q] = e
    for b, s in calib.items():
        summary["calibration"][b] = {
            "n": s["n"],
            "accuracy": round(s["correct"] / s["n"], 3) if s["n"] else None,
        }

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    path = os.path.join(run_dir, "run-%s.json" % ts)
    with open(path, "w") as f:
        json.dump({"summary": summary, "rows": rows}, f, indent=2)

    print(json.dumps(summary, indent=2))
    prev = sorted(
        f for f in os.listdir(run_dir) if f.startswith("run-") and f.endswith(".json")
    )
    if len(prev) >= 2:
        old = json.load(open(os.path.join(run_dir, prev[-2])))["summary"]
        print("\n-- change vs previous run (%s) --" % prev[-2])
        for q, e in summary["per_question"].items():
            oa = old.get("per_question", {}).get(q, {}).get("accuracy")
            if oa is not None and e.get("accuracy") is not None:
                print(
                    "  %s: %s -> %s (%+.3f)"
                    % (q, oa, e["accuracy"], e["accuracy"] - oa)
                )
    print("\nsaved %s" % path)
    return summary


if __name__ == "__main__":
    # Minimal worked example. Replace predict + labeled with your own.
    import sys

    sys.path.insert(0, os.path.dirname(__file__))
    from jev_client import decide, choice, score

    def predict(email):
        r = decide(
            state=email["text"],
            questions={
                "department": choice(
                    "Which team should handle this?",
                    {
                        "billing": "Payments, invoices, refunds, charges",
                        "technical": "Bugs, outages, errors, integrations",
                        "general": "Anything else",
                    },
                ),
                "urgency": score("How urgent is this?", ["Low", "Medium", "High"]),
            },
        )
        a = r["answers"]
        return {
            "department": a["department"]["choice"],
            "urgency": a["urgency"]["score"],
            "_confidence": {
                "department": a["department"]["confidence"],
                "urgency": a["urgency"]["confidence"],
            },
            "_cost": r.get("usage", {}).get("cost", 0.0),
        }

    labeled = [
        (
            {"text": "You charged my card twice, I want a refund now."},
            {"department": "billing", "urgency": 2},
        ),
        (
            {"text": "The dashboard has been down all morning."},
            {"department": "technical", "urgency": 2},
        ),
        (
            {"text": "What are your office hours?"},
            {"department": "general", "urgency": 0},
        ),
    ]
    evaluate(predict, labeled, note="worked example")
