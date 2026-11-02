#!/usr/bin/env python3
"""Write MaliciousSkillBench's in-the-wild malicious SKILL.md texts into cache/ as trees.

WHY THIS SUBSET. MaliciousSkillBench (ProtectSkills, data CC-BY-4.0) aggregates 13 sources. Two
of them, MaliciousAgentSkillsBench and SkillLeakBench, are in-the-wild skills whose own releases
ship labels only (this manifest records SkillLeakBench as metadata-only for that reason);
MaliciousSkillBench carries their full SKILL.md text. Both upstreams are MIT, and its
THIRD_PARTY_NOTICE says third-party skills keep their upstream terms. Every other source in it is
either already its own entry here, synthetic, or not licensed for redistribution.

ONE FILE PER SAMPLE. The upstreams confirmed these skills by running their scripts in a sandbox;
only SKILL.md was carried over, so a sample's malice may sit in a file that is not here. Reading
decides what is kept (the manifest's dimension_overrides); the rest is excluded by name.

The text is written exactly as the parquet holds it (HTML entities included). The sidecar
`<name>.source.json` sits BESIDE the tree, never inside it, and carries the row's coordinates.

Reproducible: the pinned parquet plus this script gives the same trees.
"""

import json
import pathlib
import sys
import urllib.request

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas pyarrow (or fastparquet)")

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENTRY = "maliciousskillbench-wild"
REV = "d4b42ce5766a6e0359c987cf59c1007cb3795a90"   # manifest/corpora.yaml
URL = f"https://huggingface.co/datasets/ProtectSkills/MaliciousSkillBench/resolve/{REV}/primary.parquet"
CACHE = ROOT / "cache" / ENTRY
OUT = CACHE / "_extracted"
SOURCES = ("MaliciousAgentSkillsBench", "SkillLeakBench")
KEEP = ("benchmark_id", "source_id", "source_name", "source_pointer", "provenance", "evidence_type",
        "structural_family_id", "normalized_hash", "exact_hash", "release_status", "attack_categories")


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    src = CACHE / "primary.parquet"
    if not src.exists():
        print(f"fetching {URL}")
        urllib.request.urlretrieve(URL, src)
    df = pd.read_parquet(src)
    rows = df[df.source_name.isin(SOURCES) & (df.label == "1") & (df.provenance == "wild")]
    OUT.mkdir(exist_ok=True)
    n = 0
    for _, r in rows.iterrows():
        if not r.skill_text:
            continue
        name = r.benchmark_id.lower()
        tree = OUT / name
        tree.mkdir(exist_ok=True)
        (tree / "SKILL.md").write_text(r.skill_text)
        side = {k: (r[k].tolist() if hasattr(r[k], "tolist") else r[k]) for k in KEEP}
        side["source"] = r.source_pointer   # the upstream dataset the skill came from; derive keys rates by it
        side["revision"] = REV
        (OUT / f"{name}.source.json").write_text(json.dumps(side, indent=1, default=str) + "\n")
        n += 1
    print(f"{ENTRY}: {n} tree(s) from {', '.join(SOURCES)} into {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
