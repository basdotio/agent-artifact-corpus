#!/usr/bin/env python3
"""Draw the benign reading list for the label-correctness audit.

The corpus splits in two for this purpose, and the split decides the method:

  253 samples carry a `truth` block. That is small enough to READ ALL OF, so they are not
  sampled at all — every dimension, tier, evasion and severity claim gets checked. The
  conclusion about them is CERTAIN, sample by sample.

  3,241 benign samples carry no coordinates. The only claim about them is the word "benign",
  and verifying it means reading content with no upstream label to compare against. That can
  only be sampled, and the conclusion is an ESTIMATE with an interval.

The two never combine into one accuracy figure. They are different kinds of statement.

ALLOCATION: 60 per population, not proportional to size.
    Proportional allocation would give skillsgoat's 10 decoys a sample of one, and the whole
    reason for reporting per population is that a pooled benign rate is the error this corpus
    was founded on. Equal allocation costs the pooled figure its simplicity — it has to be
    reweighted by population size — and buys a usable number for every population separately.

PRECISION, STATED SO NOBODY OVER-READS IT: at n=60 a 95% interval is about +/-12 points.
    That is enough to find a systematic problem (a 30% error rate is unmissable) and nowhere
    near enough to separate 2% from 8%. Any figure this produces carries that interval or it
    is being misused.
"""

import hashlib
import json
import pathlib
import random
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
SEED = 20260918
PER_POPULATION = 60

GITHUB = re.compile(r"github\.com/([^/\s]+/[^/\s)]+)")


def population(label: dict) -> str:
    """The batch a sample came from — the same rule `corpus validate` groups by."""
    origin = label.get("origin", {}) or {}
    derived = origin.get("derived_from") or {}
    if derived.get("entry"):
        return derived["entry"]
    if origin.get("type") == "harvested":
        return "harvested"
    m = GITHUB.search(origin.get("source", ""))
    return m.group(1) if m else "hand-written"


def main() -> int:
    coordinate_bearing: list[str] = []
    benign: dict[str, list[str]] = {}

    for lab in sorted((ROOT / "corpus").glob("*/*/*.yaml")):
        doc = yaml.safe_load(lab.read_text())
        if not isinstance(doc, dict) or "class" not in doc:
            continue
        rel = str(lab.relative_to(ROOT))
        if doc.get("truth"):
            coordinate_bearing.append(rel)
        else:
            benign.setdefault(population(doc), []).append(rel)

    print(f"coordinate-bearing, READ ALL: {len(coordinate_bearing)}")
    print(f"benign, sampled:              {sum(len(v) for v in benign.values())} "
          f"across {len(benign)} population(s)\n")

    rng = random.Random(SEED)
    drawn: dict[str, list[str]] = {}
    for pop in sorted(benign):
        members = sorted(benign[pop])
        take = min(PER_POPULATION, len(members))
        # Seeded and sorted first, so the same corpus yields the same reading list. An
        # unseeded audit sample makes its own findings unreproducible, which is the defect
        # it exists to look for.
        drawn[pop] = sorted(rng.sample(members, take))
        pct = take / len(members) * 100
        print(f"  {pop:<32} {take:>3} of {len(members):>4}  ({pct:4.1f}%)"
              + ("   [all of it]" if take == len(members) else ""))

    total = sum(len(v) for v in drawn.values())
    print(f"\n  {'total drawn':<32} {total:>3}")
    print(f"  seed {SEED}; at n={PER_POPULATION} a 95% interval is about +/-12 points, which "
          f"finds a systematic\n  problem and cannot separate 2% from 8%")

    out = ROOT / "cache" / "audit-reading-list.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "seed": SEED,
        "per_population": PER_POPULATION,
        "coordinate_bearing": coordinate_bearing,
        "benign_sampled": drawn,
        "digest": hashlib.sha256(
            json.dumps([coordinate_bearing, drawn], sort_keys=True).encode()).hexdigest()[:16],
    }, indent=1))
    print(f"\nwritten to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
