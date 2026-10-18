#!/usr/bin/env python3
"""Fetch a SEEDED, risk-stratified subset of SkillHarm's poisoned skills into cache/ with
sidecar labels, as a second held-out recall set beside agent-skill-malware.

WHY SELECTIVE. The dataset is a tree of 879 runnable Harbor task environments; the poisoned
skill inside each is the only part a static scanner is pointed at. `corpus fetch` would clone
the whole snapshot. This pulls, for each selected sample, the DIRECTORY of the poisoned skill
(the `skills/<name>/` ancestor of the manifest's `target_path`) and nothing else.

WHY SEEDED AND STRATIFIED. 687 fixed-payload samples over 12 risk types, skewed; ten per risk,
drawn with a fixed seed from the ids sorted, is a sample a reader can rebuild and that gives
every risk the same weight. The count is a ceiling: a risk with fewer than ten contributes all
it has, and the per-risk numbers are printed.

FIXTURE, NOT WILD. Every sample names the model that wrote it (`design_agent_id`). The entry's
hazards say so and `corpus score` keeps fixture rates apart from wild ones; the labels here
carry the realisation and the designer so a consumer can split further.

LABELS ARE LOCAL. Written beside each tree under cache/ in the layer-1 shape so a runner can read
class, surface and source. Severity is the constant `high` (the benchmark calls every sample an
attack and scores a deterministic attack-success signal); the dimension is a per-RISK map
written here, provisional, never validated — the note in each label says so.

--vendor: THE LAYER-1 SHAPE. `--vendor N` fetches N per risk into cache/skillharm/_vendor/<id>/,
each as the skillsgoat layout `corpus derive` reads — `meta.yaml` (the upstream's own coordinates
and nothing of ours: risk_id and realization as categories) beside a `skill/` tree — so the
manifest's derive rule, not this script, decides class, severity, dimension, evasion and tier,
with the fidelity stated there.
The seeded order is the same as the held-out draw's, so the first ten of each risk are the P-059
held-out set and N=20 is a superset of it; once vendored, those samples are layer 1 and the
held-out reading has to be drawn again from the rows that are not. `_selected/` is untouched: the
P-059 result directories name those paths.

--heldout N [--skip M]: THE NEXT HELD-OUT. Draws N per risk from the same seeded order AFTER its
first M (default 20: the vendored rows), so it can never overlap layer 1 or the spent P-059 draw,
into cache/skillharm/_heldout/<id>/ beside a sidecar label like `_selected/`'s, PDFs included (a
redirect_to_new_pdf tree without its PDF is not a sample), and writes samples-heldout.jsonl. A risk
with fewer than M+N rows gives what is left, and the counts are printed. Local only, like
`_selected/`: the reading it exists for is totals, and nothing here is a corpus label.
"""

import hashlib
import json
import pathlib
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENTRY = "skillharm"
PIN = "cc21f90982ea"                     # manifest/corpora.yaml
API = "https://huggingface.co/api/datasets/osunlp/SkillHarm"
RESOLVE = "https://huggingface.co/datasets/osunlp/SkillHarm/resolve"
CACHE = ROOT / "cache" / ENTRY
OUT = CACHE / "_selected"
SEED = 20261015
PER_RISK = 10
VENDOR = ROOT / "cache" / ENTRY / "_vendor"
HELDOUT = ROOT / "cache" / ENTRY / "_heldout"
MAX_FILE_BYTES = 200_000
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".tar", ".mp4", ".mp3",
              ".pptx", ".docx", ".xlsx", ".bin", ".so", ".parquet", ".db", ".sqlite"}

# risk_id -> corpus dimension. Provisional: written from the risk's definition in the dataset
# README, not from reading each sample.
DIMENSION = {
    "data_exfiltration": "exfiltration",
    "output_manipulation": "injection",
    "poisoning": "injection",
    "goal_hijacking": "injection",
    "proxy_attack": "injection",
    "privilege_escalation": "permission",
    "unauthorized_file_modification": "filesystem",
    "system_corruption": "filesystem",
    "anti_forensics": "filesystem",
    "backdoor_injection": "backdoor",
    "malware_deployment": "execution",
    "dos": "resource-abuse",
}


def get(url: str, attempts: int = 4) -> bytes:
    for i in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            if i == attempts - 1:
                raise
            time.sleep(2 * (i + 1))
    raise RuntimeError("unreachable")


def revision() -> str:
    """The full commit id the manifest's short pin names."""
    for page in range(0, 10):
        commits = json.loads(get(f"{API}/commits/main?p={page}"))
        if not commits:
            break
        for c in commits:
            if c["id"].startswith(PIN):
                return c["id"]
    sys.exit(f"no commit of osunlp/SkillHarm starts with {PIN}")


def skill_dir(target_path: str) -> str:
    parts = target_path.split("/")
    if "skills" in parts[:-1]:
        i = parts.index("skills")
        return "/".join(parts[:i + 2])
    return "/".join(parts[:-1])


def label(sample_id: str, s: dict, rev: str, added: str) -> str:
    dim = DIMENSION.get(s["risk_id"], "injection")
    return f"""# Written by scripts/prep-skillharm.py into cache/ — layer 2, selected subset, local only.
# A sidecar in the layer-1 shape so a runner can read class, surface and source; it is not a
# corpus label and `make validate` never sees it.
id: {sample_id}
class: malicious
surface: skills
kind: skill
entry: .

origin:
  type: derived
  source: "https://huggingface.co/datasets/osunlp/SkillHarm @ {rev[:12]}"
  license: CC-BY-4.0
  note: "FPP sample {s['sample_id']}: task {s['task_id']}, risk {s['risk_id']}, realization {s['realization']}, designed by {s['design_agent_id']}; the poisoned skill's directory only"
  added: {added}
  labeled_before_run: false
  derived_from:
    entry: {ENTRY}
    sample: {s['path']}
    fidelity: "class and severity are constants (every sample is an attack); the dimension is a per-risk map written in the script, provisional and unvalidated"

basis:
  class: upstream
  assumption: "the benchmark places this sample under risk {s['risk_id']} and scores it with a deterministic attack-success signal; nothing beyond that was read here"

truth:
  dimensions: [{dim}]
  severity: high
  tier: plain
  evasion: []
  note: "severity constant; dimension mapped from risk_id {s['risk_id']} by scripts/prep-skillharm.py, not read; realization {s['realization']}"
"""


def main() -> int:
    added = date.today().isoformat()
    vendor = 0
    heldout, skip = 0, 20
    shard, shards = 0, 1
    for i, a in enumerate(sys.argv):
        if a == "--vendor" and i + 1 < len(sys.argv):
            vendor = int(sys.argv[i + 1])
        if a == "--heldout" and i + 1 < len(sys.argv):
            heldout = int(sys.argv[i + 1])
        if a == "--skip" and i + 1 < len(sys.argv):
            skip = int(sys.argv[i + 1])
        if a == "--shard" and i + 1 < len(sys.argv):
            # k/n: fetch only every n-th selected tree starting at k. The selection is the same
            # in every shard (same seed, same order), so n shards cover it exactly once between
            # them and never touch the same tree; the work list is written by shard 0/n only.
            shard, shards = (int(x) for x in sys.argv[i + 1].split("/"))
    if vendor and heldout:
        print("--vendor and --heldout draw different sets; pass one")
        return 2
    per_risk, out_root = (vendor, VENDOR) if vendor else ((heldout, HELDOUT) if heldout else (PER_RISK, OUT))
    first = skip if heldout else 0
    CACHE.mkdir(parents=True, exist_ok=True)
    rev = revision()
    manifest_path = CACHE / "MANIFEST.json"
    if not manifest_path.exists():
        manifest_path.write_bytes(get(f"{RESOLVE}/{rev}/MANIFEST.json"))
    m = json.loads(manifest_path.read_text())
    fpp = m["fpp"]

    by_risk: dict[str, list[dict]] = {}
    seen: set[str] = set()
    dupes = 0
    for s in fpp:
        # The upstream manifest lists at least one sample twice; one tree, one sample.
        if s["sample_id"] in seen:
            dupes += 1
            continue
        seen.add(s["sample_id"])
        by_risk.setdefault(s["risk_id"], []).append(s)
    if dupes:
        print(f"  {dupes} duplicate row(s) in the upstream manifest, counted once")
    rng = random.Random(SEED)
    chosen = []
    print(f"{ENTRY} @ {rev[:12]}: {len(fpp)} FPP samples over {len(by_risk)} risks; {per_risk} per risk, seed {SEED}" + (" (vendor layout)" if vendor else (f" (held-out: after the first {first} per risk)" if heldout else "")))
    for risk in sorted(by_risk):
        pool = sorted(by_risk[risk], key=lambda s: s["sample_id"])
        rng.shuffle(pool)
        take = pool[first:first + per_risk]
        chosen.extend(take)
        print(f"  {risk:<32} {len(take):>3} of {len(pool)}")

    work = []
    fetched = skipped = 0
    for n, s in enumerate(chosen, 1):
        if (n - 1) % shards != shard:
            continue
        sdir = skill_dir(s["target_path"])
        remote = f"{s['path']}/{sdir}"
        try:
            entries = json.loads(get(f"{API}/tree/{rev}/{remote}?recursive=true"))
        except urllib.error.HTTPError as e:
            print(f"  {s['sample_id']}: cannot list {remote}: {e}")
            skipped += 1
            continue
        dest = (out_root / s["sample_id"] / "skill") if vendor else (out_root / s["sample_id"])
        dest.mkdir(parents=True, exist_ok=True)
        already = sum(1 for _ in dest.rglob("*") if _.is_file())
        files = 0
        for e in entries:
            if already:
                # Fetched by an earlier run; the label is rewritten, the bytes are not refetched.
                files = already
                break
            if e.get("type") != "file":
                continue
            rel = e["path"][len(remote) + 1:]
            suffix = pathlib.Path(rel).suffix.lower()
            # The held-out draw skipped every binary, PDFs included — so its redirect_to_new_pdf
            # trees are a SKILL.md pointing at a guide that is not there, and a scanner was
            # quiet on them for want of a payload, not for want of a rule. The vendored layout
            # carries the PDF (5–13 KB each in the trees listed): a binary-container sample
            # without its container is not a sample.
            if (suffix in BINARY_EXT and not ((vendor or heldout) and suffix == ".pdf")) or (e.get("size") or 0) > MAX_FILE_BYTES:
                continue
            p = dest / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(get(f"{RESOLVE}/{rev}/{e['path']}"))
            files += 1
            time.sleep(0.05)
        if files == 0:
            print(f"  {s['sample_id']}: nothing fetched from {remote}")
            skipped += 1
            continue
        # Short and unique: the manifest's sample_id runs past 120 characters and two of them
        # share their first 120, so the id is the risk plus a hash of the full sample_id; the
        # full id is in the label's note and derived_from.
        digest = hashlib.sha256(s["sample_id"].encode()).hexdigest()[:10]
        sample_id = f"mal-skill-sh-{s['risk_id'].replace('_', '-')}-{digest}"
        if vendor:
            # The upstream's own coordinates, nothing of ours: the derive rule maps them.
            (out_root / s["sample_id"] / "meta.yaml").write_text(
                f"id: {s['risk_id'].replace('_', '-')}-{digest}\n"
                f"categories: [{s['risk_id']}, {s['realization']}]\n"
                f"# upstream: sample_id {s['sample_id']}, task {s['task_id']}, designer {s['design_agent_id']}, path {s['path']}\n")
        else:
            dest.with_suffix(".yaml").write_text(label(sample_id, s, rev, added))
        work.append({"sample": sample_id, "path": dest.relative_to(ROOT).as_posix(),
                     "class": "malicious", "surface": ["skills"]})
        fetched += 1
        if n % 20 == 0:
            print(f"  … {n}/{len(chosen)}", flush=True)
    if shards > 1:
        print(f"shard {shard}/{shards}: {fetched} tree(s) fetched, {skipped} skipped; no work list from a shard — run once more without --shard to write it (every tree is then already fetched)")
        return 0
    worklist = "samples-vendor.jsonl" if vendor else ("samples-heldout.jsonl" if heldout else "samples.jsonl")
    (CACHE / worklist).write_text("".join(json.dumps(w) + "\n" for w in work))
    print(f"{fetched} tree(s) under {out_root.relative_to(ROOT)}/, {skipped} skipped; work list {CACHE.relative_to(ROOT)}/{worklist}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
