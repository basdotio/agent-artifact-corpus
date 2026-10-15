"""
make_rating_sheet.py - turn a batch of the user's raw inputs into a BLIND rating
sheet they fill in a spreadsheet, so measuring accuracy is a fast, unbiased, human
task. See ../references/04-measure-and-optimize.md.

Why blind: the sheet deliberately does NOT show the model's guess. If the human sees
the guess they anchor to it and the measured accuracy comes out fake-high
(confirmation bias). They label from scratch.

Usage:
  python make_rating_sheet.py inputs.txt rating_sheet.csv --labels topic --n 50
- inputs.txt: one raw input per line (or a .jsonl with a --field, default "text").
- --labels: comma-separated question names to create a blank column for (e.g.
  "topic" or "department,urgency"). Column headers MUST match the question names your
  predict() returns, so evaluate.load_labeled_csv lines them up.
- --n: random sample size (all if fewer). --seed for reproducibility.

The human opens rating_sheet.csv in Excel/Google Sheets, fills each label column with
the correct answer from the fixed category list (leave a row blank to skip it), saves,
and feeds it to evaluate.load_labeled_csv.
"""

import argparse
import csv
import json
import random


def load_inputs(path, field):
    rows = []
    with open(path) as f:
        if path.endswith(".jsonl"):
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    rows.append(str(obj.get(field, obj)))
        else:
            for line in f:
                if line.strip():
                    rows.append(line.rstrip("\n"))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs")
    ap.add_argument("out")
    ap.add_argument("--labels", default="topic", help="comma-separated question names")
    ap.add_argument("--field", default="text", help="jsonl field holding the text")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    rows = load_inputs(a.inputs, a.field)
    random.Random(a.seed).shuffle(rows)
    sample = rows[: a.n]
    label_cols = [c.strip() for c in a.labels.split(",") if c.strip()]

    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "text"] + label_cols)
        for i, t in enumerate(sample):
            w.writerow([i, t] + [""] * len(label_cols))

    print("Wrote %d blind rating rows to %s." % (len(sample), a.out))
    print(
        "Fill the %s column(s) with the correct answer, then run evaluate."
        % ", ".join(label_cols)
    )
    if len(rows) < a.n:
        print("Note: only %d inputs available, sampled all of them." % len(rows))


if __name__ == "__main__":
    main()
