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
    print(f"{ENTRY} @ {rev[:12]}: {len(fpp)} FPP samples over {len(by_risk)} risks; {PER_RISK} per risk, seed {SEED}")
    for risk in sorted(by_risk):
        pool = sorted(by_risk[risk], key=lambda s: s["sample_id"])
        rng.shuffle(pool)
        take = pool[:PER_RISK]
        chosen.extend(take)
        print(f"  {risk:<32} {len(take):>3} of {len(pool)}")

    work = []
    fetched = skipped = 0
    for n, s in enumerate(chosen, 1):
        sdir = skill_dir(s["target_path"])
        remote = f"{s['path']}/{sdir}"
        try:
            entries = json.loads(get(f"{API}/tree/{rev}/{remote}?recursive=true"))
        except urllib.error.HTTPError as e:
            print(f"  {s['sample_id']}: cannot list {remote}: {e}")
            skipped += 1
            continue
        dest = OUT / s["sample_id"]
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
            if pathlib.Path(rel).suffix.lower() in BINARY_EXT or (e.get("size") or 0) > MAX_FILE_BYTES:
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
        dest.with_suffix(".yaml").write_text(label(sample_id, s, rev, added))
        work.append({"sample": sample_id, "path": dest.relative_to(ROOT).as_posix(),
                     "class": "malicious", "surface": ["skills"]})
        fetched += 1
        if n % 20 == 0:
            print(f"  … {n}/{len(chosen)}", flush=True)
    (CACHE / "samples.jsonl").write_text("".join(json.dumps(w) + "\n" for w in work))
    print(f"{fetched} tree(s) under {OUT.relative_to(ROOT)}/, {skipped} skipped; work list {CACHE.relative_to(ROOT)}/samples.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
