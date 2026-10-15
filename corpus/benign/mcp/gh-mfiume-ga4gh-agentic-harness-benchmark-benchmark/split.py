"""The frozen dev / held-out split.

    python -m benchmark.split            # writes splits/v1.json (refuses to overwrite)

Within each category, tasks are ordered by a hash of their id and the first 30% are held out.
The file is written once and committed: tasks added later are not in it, so they never move a
task between sides. Diagnosis and the inner improvement loop read only the dev side; gains are
reported from the held-out side.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict

from .tasks import ROOT, load

PATH = ROOT / "splits" / "v1.json"
HELDOUT = 0.30


def main() -> int:
    if PATH.exists():
        print(f"{PATH} exists; the split is frozen", file=sys.stderr)
        return 1
    tasks, facts = load()
    by_cat: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        by_cat[task["category"]].append(task["id"])
    sides: dict[str, str] = {}
    for ids in by_cat.values():
        ids.sort(key=lambda i: hashlib.sha256(i.encode()).hexdigest())
        cut = round(len(ids) * HELDOUT)
        for n, task_id in enumerate(ids):
            sides[task_id] = "heldout" if n < cut else "dev"
    PATH.parent.mkdir(exist_ok=True)
    PATH.write_text(json.dumps({"version": 1, "heldout_fraction": HELDOUT, "snapshot": facts["fetched_at"],
                                "tasks": dict(sorted(sides.items()))}, indent=1) + "\n")
    counts = defaultdict(lambda: defaultdict(int))
    for task in tasks:
        counts[task["category"]][sides[task["id"]]] += 1
    for cat, c in sorted(counts.items()):
        print(f"{cat:13} dev {c['dev']:3}  heldout {c['heldout']:3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
