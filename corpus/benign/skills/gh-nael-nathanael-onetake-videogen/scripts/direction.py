#!/usr/bin/env python3
"""
Pick a creative direction for a generated video, different from the last few jobs.

  run.sh direction.py JOB_DIR --mode explainer|illustrated [--seed N]

Writes JOB_DIR/direction.json = {"seed", "mode", "structure", "hook"} and prints it with the
directions of the recent jobs of that mode (sibling folders of JOB_DIR). A structure or hook used
by one of the last 5 is not picked again while an unused one is left. A job keeps its direction:
a second run prints the existing file.

The method and the narration lists are adapted from vincentfranstyo/video-gen-skill
(kit/directions.ts, MIT; see LICENSES/video-gen-skill-MIT.txt).
"""

import argparse
import random
import time
from pathlib import Path

from common import load_json, save_json

RECENT_JOBS = 5

# Opening patterns for the first line and the first title; each opens a question the video answers.
HOOKS = [
    "question: 'Why does <thing> happen?'",
    "statement: 'The story of <subject>'",
    "secret: 'What nobody tells you about <subject>'",
    "stakes: 'How <subject> changed <thing>'",
    "number: '<n> things about <subject>'",
    "contrast: '<common belief> vs what really happens'",
]

STRUCTURES = {
    "explainer": [
        "chronological: open on the most striking moment, then tell it in order",
        "mystery: pose the question, unfold clues, answer at the end",
        "chapters: 3-6 titled parts, a title scene each",
        "explainer: the idea in one line, then why, how, and what it means",
        "countdown: a ranked list building to number one",
        "myth vs fact: a common belief, then what is true",
        "problem first: the painful way, then the better way",
    ],
    "illustrated": [
        "transformation: one thing changes state, followed from start to finish",
        "journey: one object travels through every stage and ties them together",
        "zoom levels: start wide, go one level deeper per beat",
        "cause and effect: each beat's payoff triggers the next",
        "before and after: the same scene twice, with one thing changed",
        "loop: the ending flows back into the first frame",
    ],
}


def recent(job, mode):
    """Directions of the latest jobs of this mode beside `job`, oldest first."""
    found = [(p.stat().st_mtime, p.parent.name, load_json(p))
             for p in job.parent.glob("*/direction.json") if p.parent != job]
    return [{"job": name, **d} for _, name, d in sorted(found) if d.get("mode") == mode][-RECENT_JOBS:]


def pick(seed, mode, avoid):
    rng = random.Random(seed)

    def fresh(items, key):
        used = {d.get(key) for d in avoid}
        return rng.choice([x for x in items if x not in used] or items)

    return {"seed": seed, "mode": mode, "structure": fresh(STRUCTURES[mode], "structure"), "hook": fresh(HOOKS, "hook")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--mode", required=True, choices=sorted(STRUCTURES))
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()

    job = Path(a.job).resolve()
    out = job / "direction.json"
    earlier = recent(job, a.mode)
    if out.exists():
        direction = load_json(out)
    else:
        direction = pick(a.seed if a.seed is not None else time.time_ns(), a.mode, earlier)
        job.mkdir(parents=True, exist_ok=True)
        save_json(direction, out)
    print(f"structure: {direction['structure']}\nhook:      {direction['hook']}\n-> {out}")
    for d in earlier:
        print(f"recent {d['job']}: {d['structure'].split(':')[0]} / {d['hook'].split(':')[0]}")


if __name__ == "__main__":
    main()
