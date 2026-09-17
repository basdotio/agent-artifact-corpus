#!/usr/bin/env python3
"""Sample SkillMD-138K into sample trees, under a stated design.

138,133 skills is not a corpus you import; it is a population you sample from, and the
sampling design decides what the resulting false-positive rate is allowed to claim. Every
number below was measured from the data before it was chosen, and the reasons are here rather
than in a commit message because this file is the design.

STRATIFY BY repo + package path, not by repo.
    One repository, NeverSight/skills_feed, holds 12.5% of all 138,133 skills — and inside it
    are 2,765 different original authors, because it is an aggregator rather than an author's
    repository. Treating it as one source is exactly the failure design.md was founded on: a
    machine-wide 12.9% that turned out to describe two authors' writing habits.
    Measured on the output this design actually produces: 2,000 samples from 1,505 repositories,
    94% of which contribute exactly one. skills_feed is still the largest single repository at
    173 samples (8.65%) — but those 173 come from 171 DIFFERENT author directories inside it,
    which is the whole point. Counting by repository understates the source diversity of an
    aggregator; counting by stratum is what makes 171 writers out of what looks like one source.
    The cost, stated because it is real: aggregators lay out paths differently
    (data/skills-md/<author>/… against skills/<category>/…), so a stratum is sometimes an
    author and sometimes a category. It is a better proxy for "one writer's habits" than the
    repository is, and it is not a clean one.

ONE SKILL PER STRATUM, 2,000 STRATA.
    Taking one per stratum means no stratum can weight the denominator more than any other,
    which is what per-source reporting needs. 2,000 keeps the corpus the same order of
    magnitude as it is today while giving it more distinct sources than every other entry
    combined.

EXCLUDE REPOSITORIES ALREADY REPRESENTED BY skillet.
    100 of skillet's 131 source repositories also appear here, so pooling the two would count
    the same repositories twice. Excluding them makes the two denominators disjoint and
    summable. Red line 2 requires both figures whenever a denominator carries an exclusion, so
    this script prints the population with and without the exclusion every time it runs: the
    cost is 447 skills of 138,133, which is 0.32%, and 180 strata of 37,307.

SEEDED.
    Same parquet, same seed, same 2,000 samples. An unseeded sample would make every published
    figure unreproducible, which is the same defect as an unpinned commit.
"""

import hashlib
import json
import pathlib
import random
import re
import shutil
import sys

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas fastparquet")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cache" / "skillmd-138k" / "train.parquet"
OUT = ROOT / "cache" / "skillmd-138k" / "extracted"

STRATA = 2_000
SEED = 20260917


def stratum_of(repo: str, path: str) -> str:
    """repo plus the directory holding the SKILL.md, which is the package inside an
    aggregator and the repository root for an author's own repository."""
    seg = path.split("/")
    inner = "/".join(seg[:-2]) if len(seg) >= 3 else (seg[0] if seg else "")
    return f"{repo}::{inner}"


def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower()
    return s[:64] or "unnamed"


def skillet_repos() -> set[str]:
    """The repositories skillet already contributes, read from the labels on disk so the two
    entries cannot drift apart."""
    out = set()
    for p in (ROOT / "corpus" / "benign" / "skills").glob("sk-*.yaml"):
        m = re.search(r'source: "https://github\.com/([^ ]+?) \(via', p.read_text())
        if m:
            out.add(m.group(1).lower())
    return out


def main() -> int:
    if not SRC.exists():
        sys.exit(f"{SRC} is missing — fetch the pinned parquet first")

    df = pd.read_parquet(SRC, engine="fastparquet")
    already = skillet_repos()

    df["_lc"] = df.repo.str.lower()
    df["_st"] = [stratum_of(r, p) for r, p in zip(df.repo, df.path)]

    excluded_mask = df._lc.isin(already)
    kept = df[~excluded_mask]

    # Red line 2: an exclusion is reported with both figures, every run, not once in a commit.
    print("population, both figures:")
    print(f"  with the overlap:    {len(df):>7} skills, {df._st.nunique():>6} strata")
    print(f"  without the overlap: {len(kept):>7} skills, {kept._st.nunique():>6} strata")
    print(f"  excluded:            {int(excluded_mask.sum()):>7} skills "
          f"({excluded_mask.sum() / len(df) * 100:.2f}%), "
          f"{df._st.nunique() - kept._st.nunique()} strata, "
          f"{df[excluded_mask]._lc.nunique()} repositories already covered by skillet")

    rng = random.Random(SEED)
    strata = sorted(kept._st.unique())
    chosen_strata = strata if len(strata) <= STRATA else rng.sample(strata, STRATA)
    chosen = set(chosen_strata)

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    names: dict[str, str] = {}
    written = 0
    for st, group in kept[kept._st.isin(chosen)].groupby("_st", sort=True):
        # One skill per stratum, picked by the lowest content hash rather than by row order, so
        # the choice does not depend on how the parquet happens to be sorted.
        row = group.sort_values("content_hash").iloc[0]

        name = slug(f"{row.repo}-{pathlib.PurePosixPath(row.path).parent.name}")
        if name in names:
            name = f"{name}-{hashlib.sha256(st.encode()).hexdigest()[:8]}"
            if name in names:
                sys.exit(f"unresolvable collision for stratum {st!r}")
        names[name] = st

        d = OUT / name
        d.mkdir()
        (d / "SKILL.md").write_text(str(row.content))
        # Provenance beside the tree, never inside it: a file in the tree is read as part of
        # the sample, which corrupted this corpus's measurements once already.
        (OUT / f"{name}.provenance.json").write_text(
            json.dumps(
                {
                    "repo": row.repo,
                    "path": row.path,
                    "content_hash": row.content_hash,
                    "source": row.source,
                    "stars": int(row.stars),
                    "stratum": st,
                },
                indent=2,
            )
        )
        written += 1

    print(f"\n{written} sample(s) extracted into {OUT.relative_to(ROOT)}")
    print(f"seed {SEED}, one skill per stratum, {len(chosen_strata)} strata drawn "
          f"of {len(strata)} available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
