#!/usr/bin/env python3
"""Weekly intake of ClawHub skills the registry's own pipeline calls malicious.

WHAT THIS IS. OpenClaw publishes `OpenClaw/clawhub-security-signals-live` on Hugging Face every
Sunday: one row per public skill version with its sanitized SKILL.md, its bundle files, and the
verdicts of VirusTotal, the static scanner, SkillSpector and the GPT judge (`clawscan_verdict`).
Of 82,739 rows, a few hundred are judged `malicious`. Those are the only wild-malicious feed
this corpus has that keeps producing; everything else surveyed was a one-off snapshot. This
script turns each week's new malicious rows into sample trees a person can read, and nothing
more: the registry's verdict is a scanner's opinion (Monash measured the judge at 61%
sensitivity), so a row becomes a corpus sample only after someone has read it and written the
deciding line into manifest/corpora.yaml.

THE FLOW, each week:

    scripts/intake-clawhub.py              # fetch + queue + status
    … a person reads cache/clawhub-live/_queue/READ-LIST.md and records each decision in
      manifest/corpora.yaml under the `clawhub-live` entry: dimension_overrides for a sample
      that stays, exclude_samples for one that does not …
    scripts/intake-clawhub.py promote      # decided trees move to _extracted/
    make derive-write E=clawhub-live && make validate

THREE HARD RULES, enforced here rather than remembered:

  1. HELD-OUT STAYS HELD OUT. `agent-skill-malware` (yoonholee) is this corpus's held-out set:
     ClawHub skills no scanner author has read. A candidate whose SKILL.md matches one of
     those rows by normalised hash OR by skill name is refused, and the queue step refuses to
     run at all unless manifest/pins/heldout-skillmd-sha256.json exists (`heldout-pin`
     writes it from the layer-2 cache). The pin file holds hashes and names, never content.
  2. AT MOST 5 PER AUTHOR, EVER. ClawHub campaigns are one publisher re-publishing one lure
     under many slugs (DataDog's set had 54 of 204 from one account). The cap counts queued
     and derived samples together across all weeks; excluded ones do not count.
  3. NOTHING IS LABELLED HERE. The tree, a sidecar with the registry's signals, and a read
     list. Class is the manifest's constant; the dimension and the quoted line are the
     reader's, in dimension_overrides, exactly as datadog-ai-skills is done.

LICENCE. OpenClaw's documentation states "All skills published on ClawHub are licensed under
MIT-0" and "ClawHub does not support per-skill license overrides" (docs.openclaw.ai/clawhub/
skill-format, read 2026-10-29), and the dataset itself is MIT. MIT-0 is in the permissive set,
so every sample's licence is recorded as MIT-0 — EXCEPT that a bundle shipping its own LICENSE
file or a `license:` line is flagged on the read list, because the acceptable-usage policy
forbids republishing someone else's code and such a file is the sign of it. The reader decides;
`promote` writes the licence pins file from what the reader left in place.

POOLS. `--pools` picks which of the registry's verdicts become candidates (default
`malicious`). The registry's verdict only chooses what gets read; the reading decides
the class, so a pool is worth taking whenever reading it finds samples. `suspicious` was left
out at first (the survey found the frozen set's suspicious tier inconsistent with its own
paper); on 2026-10-29 all 116 queued suspicious rows were read by two models and none was kept (of
92 vt-flagged and 23 unknown, one was), so the default stays `malicious` and the others are
there for a re-check, not for every week. Also
available: `vt-flagged` (judged clean, but at least one VirusTotal engine says malicious) and
`unknown` (no judge verdict). Each pool is cached as its own snapshot.

WHAT IS DELIBERATELY NOT TAKEN. Rows the registry
hides from its API (the sanitized export is the only legal copy, and it is what is used);
anything from the `packageReleases` table (plugins are not skills).

Network: the Hugging Face datasets-server `/filter` endpoint returns the malicious rows in
three pages when it is up; when it is not, the 2.8 GB export is streamed and filtered line by
line, which takes about ten minutes. Either way the rows are cached per dataset commit under
cache/clawhub-live/snapshots/ so a re-run is free.

Run: python3 scripts/intake-clawhub.py [fetch|queue|promote|status|heldout-pin] [--force]
Tests: python3 -m pytest scripts/test_intake_clawhub.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENTRY = "clawhub-live"
HF_REPO = "OpenClaw/clawhub-security-signals-live"
HF_API = f"https://huggingface.co/api/datasets/{HF_REPO}"
HF_FILTER = "https://datasets-server.huggingface.co/filter"
HF_EXPORT = f"https://huggingface.co/datasets/{HF_REPO}/resolve/{{commit}}/data/latest.jsonl"
REGISTRY = "https://clawhub.ai"

CACHE = ROOT / "cache" / ENTRY
SNAPSHOTS = CACHE / "snapshots"
QUEUE = CACHE / "_queue"
EXTRACTED = CACHE / "_extracted"
STATE = ROOT / "manifest" / "pins" / "clawhub-intake.json"
HELDOUT_PIN = ROOT / "manifest" / "pins" / "heldout-skillmd-sha256.json"
LICENSE_PINS = ROOT / "manifest" / "pins" / "clawhub-licenses.json"
HELDOUT_SOURCE = ROOT / "cache" / "agent-skill-malware" / "skills.jsonl"
MANIFEST = ROOT / "manifest" / "corpora.yaml"

PER_AUTHOR_CAP = 5
REGISTRY_LICENSE = "MIT-0"
PAGE = 100
UA = "agent-artifact-corpus intake-clawhub (https://github.com/basdotio/agent-artifact-corpus)"

URL_HOST = re.compile(r"\b(?:https?|ftp|wss?)://(?:[^/\s\"'<>@]+@)?([a-z0-9.\-]+)", re.I)
LICENSE_LINE = re.compile(r"^\s*license\s*:\s*(\S.*)$", re.I | re.M)


# ----------------------------------------------------------------------------- small helpers

def slugify(s: str, limit: int = 40) -> str:
    return (re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower() or "unnamed")[:limit].rstrip("-")


def norm_hash(text: str) -> str:
    """The same normalisation prep-agent-skill-malware.py uses, so the two agree on 'same'."""
    return hashlib.sha256(text.strip().encode()).hexdigest()


def tree_name(row: dict) -> str:
    """<owner>-<slug>-<version>: owner-qualified because ClawHub slugs are not unique, versioned
    because a campaign re-publishes under new versions and each is a different artifact."""
    owner, _, skill = row["skill_slug"].partition("/")
    return f"{slugify(owner, 30)}-{slugify(skill, 40)}-{slugify(row.get('skill_version') or '0', 16)}"


def owner_of(row: dict) -> str:
    return row["skill_slug"].partition("/")[0].lower()


def front_matter(text: str) -> str:
    parts = text.split("---", 2)
    return parts[1] if len(parts) >= 3 and text.lstrip().startswith("---") else ""


RESERVED_HOST = re.compile(r"(^|\.)(example\.(com|net|org)|example|test|invalid|localhost)$|^127\.|^0\.0\.0\.0$")


def hosts_in(texts: list[str]) -> set[str]:
    """URL hosts worth comparing: not a placeholder (`api.example.com`, `localhost`), not a
    template residue (`https://...`), lower-cased, credentials and port stripped."""
    out: set[str] = set()
    for t in texts:
        for h in URL_HOST.findall(t):
            h = h.lower().strip(".")
            if not re.search(r"[a-z0-9]", h) or RESERVED_HOST.search(h):
                continue
            out.add(h)
    return out


def licence_signs(row: dict) -> list[str]:
    """What in the artifact claims a licence of its own: a LICENSE* file, or a `license:` line in
    the front matter. Not a verdict — the registry's terms say MIT-0 — but the reader has to see
    it, because a foreign LICENSE file is how a republished third-party skill looks."""
    signs = []
    for f in row.get("skill_bundle_content") or []:
        base = pathlib.PurePosixPath(f["path"]).name.lower()
        if base.startswith("license") or base.startswith("licence") or base == "copying":
            first = (f.get("content") or "").strip().splitlines()[:1]
            signs.append(f"{f['path']}: {first[0][:80] if first else '(empty)'}")
    m = LICENSE_LINE.search(front_matter(row["skill_md_content"]))
    if m:
        signs.append(f"front matter license: {m.group(1).strip()[:60]}")
    return signs


def http_json(url: str, tries: int = 4, timeout: int = 120):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(min(60, 5 * 2**i))
    raise RuntimeError(f"{url}: {last}")


def load_json(p: pathlib.Path, default):
    return json.loads(p.read_text()) if p.exists() else default


def jsonl_lines(p: pathlib.Path) -> list[str]:
    """Non-empty lines of a JSON-lines file. Split on "\\n" only: str.splitlines() also breaks on
    U+2028, U+0085 and friends, which skill text carries inside JSON strings and which then cut a
    row in two."""
    return [l for l in p.read_text().split("\n") if l.strip()]


def save_json(p: pathlib.Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------- fetch

def current_commit() -> str:
    return http_json(HF_API)["sha"]


def fetch_malicious_via_filter(commit: str) -> list[dict] | None:
    """The datasets-server filter: cheap, and down often enough that the caller has a fallback.
    None means 'could not'; an empty list would mean 'no malicious rows', which is a different
    statement and is not believed from this endpoint without a total to back it."""
    where = urllib.parse.quote("\"clawscan_verdict\"='malicious'")
    rows: list[dict] = []
    offset, total = 0, None
    while True:
        url = (f"{HF_FILTER}?dataset={HF_REPO}&config=default&split=latest&where={where}"
               f"&offset={offset}&length={PAGE}")
        try:
            page = http_json(url, tries=3, timeout=180)
        except RuntimeError as e:
            print(f"  filter endpoint unavailable ({str(e)[:120]}); falling back to the export stream")
            return None
        if "error" in page:
            print(f"  filter endpoint: {page['error'][:120]}; falling back to the export stream")
            return None
        total = page.get("num_rows_total", total)
        rows.extend(r["row"] for r in page.get("rows", []))
        offset += PAGE
        if total is None or offset >= total or not page.get("rows"):
            break
    if total is None or len(rows) != total:
        print(f"  filter returned {len(rows)} rows for a stated total of {total}; not trusted")
        return None
    return rows


POOLS = {
    "malicious": lambda r: r.get("clawscan_verdict") == "malicious",
    "suspicious": lambda r: r.get("clawscan_verdict") == "suspicious",
    "vt-flagged": lambda r: r.get("clawscan_verdict") == "clean" and (r.get("virustotal_malicious_count") or 0) > 0,
    "unknown": lambda r: r.get("clawscan_verdict") == "unknown",
}
DEFAULT_POOLS = ("malicious",)


def pool_of(row: dict) -> str | None:
    return next((name for name, keep in POOLS.items() if keep(row)), None)


def fetch_pools_via_stream(commit: str, pools: tuple[str, ...]) -> dict[str, list[dict]]:
    url = HF_EXPORT.format(commit=commit)
    print(f"  streaming {url} (about 2.8 GB; only rows in {', '.join(pools)} are kept)")
    out: dict[str, list[dict]] = {p: [] for p in pools}
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    n = 0
    with urllib.request.urlopen(req, timeout=600) as r:
        for raw in r:
            n += 1
            # Cheap prefilter: a clean row with no VirusTotal hit is the overwhelming majority.
            if "vt-flagged" not in pools and b'"clean"' in raw and b'"malicious"' not in raw and b'"suspicious"' not in raw and b'"unknown"' not in raw:
                continue
            row = json.loads(raw)
            p = pool_of(row)
            if p in out:
                out[p].append(row)
            if n % 10000 == 0:
                print(f"    {n} rows read, " + ", ".join(f"{k} {len(v)}" for k, v in out.items()))
    print(f"  {n} rows read, " + ", ".join(f"{k} {len(v)}" for k, v in out.items()))
    return out


def fetch_malicious_via_stream(commit: str) -> list[dict]:
    return fetch_pools_via_stream(commit, ("malicious",))["malicious"]


def snapshot(commit: str, pool: str) -> pathlib.Path:
    return SNAPSHOTS / f"{commit}.{pool}.jsonl"


def fetch(force: bool = False, pools: tuple[str, ...] = DEFAULT_POOLS) -> tuple[str, list[pathlib.Path]] | None:
    """(commit, one snapshot per pool). A pool already cached for this commit is not refetched,
    so adding a pool later costs one stream, not a re-queue of the others."""
    state = load_json(STATE, {})
    commit = current_commit()
    missing = [p for p in pools if not snapshot(commit, p).exists()]
    if not missing:
        print(f"fetch: snapshots for {commit[:12]} already cached ({', '.join(pools)})")
        return commit, [snapshot(commit, p) for p in pools]
    if state.get("last_commit") == commit and not force and set(missing) <= set(state.get("pools_fetched", ["malicious"])):
        print(f"fetch: no new export since {state.get('last_fetched')} (commit {commit[:12]}); --force to refetch")
        return None
    print(f"fetch: dataset commit {commit[:12]}, pools {', '.join(missing)}")
    got: dict[str, list[dict]] = {}
    if missing == ["malicious"]:
        rows = fetch_malicious_via_filter(commit)
        if rows is not None:
            got = {"malicious": rows}
    if not got:
        got = fetch_pools_via_stream(commit, tuple(missing))
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    for p, rows in got.items():
        with snapshot(commit, p).open("w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"fetch: {len(rows)} {p} rows cached at {snapshot(commit, p).relative_to(ROOT)}")
    return commit, [snapshot(commit, p) for p in pools]


# ----------------------------------------------------------------------------- held-out pin

def heldout_pin() -> None:
    if not HELDOUT_SOURCE.exists():
        sys.exit(f"heldout-pin: {HELDOUT_SOURCE.relative_to(ROOT)} is missing; run scripts/prep-agent-skill-malware.py first")
    hashes, names = set(), set()
    for line in jsonl_lines(HELDOUT_SOURCE):
        if not line.strip():
            continue
        row = json.loads(line)
        hashes.add(norm_hash(row["content"]))
        # skill_name carries a per-row suffix (`auto-updater-161ks`, `agent-browser-6aigix9qi2tu`);
        # the slug is the part a ClawHub row would carry. A suffix is random when it mixes
        # letters and digits — `-model` or `-pi` is a word and stays.
        names.add(row["skill_name"].lower())
        base, _, tail = row["skill_name"].lower().rpartition("-")
        if base and 4 <= len(tail) <= 12 and re.search(r"[0-9]", tail) and re.search(r"[a-z]", tail):
            names.add(base)
    save_json(HELDOUT_PIN, {
        "what": "normalised SKILL.md hashes and skill names of the held-out set (agent-skill-malware), so intake-clawhub.py can refuse them without holding their content",
        "source": "cache/agent-skill-malware/skills.jsonl, written by scripts/prep-agent-skill-malware.py",
        "written": date.today().isoformat(),
        "sha256": sorted(hashes),
        "names": sorted(names),
    })
    print(f"heldout-pin: {len(hashes)} hashes, {len(names)} names -> {HELDOUT_PIN.relative_to(ROOT)}")


# ----------------------------------------------------------------------------- queue

def layer1_skill_hashes() -> dict[str, str]:
    have = {}
    for p in (ROOT / "corpus").glob("*/skills/*/SKILL.md"):
        have[norm_hash(p.read_text(errors="replace"))] = p.parent.name
    return have


WILD_TREE_PREFIXES = ("dd-", "ch-")   # datadog-ai-skills and this entry: the wild campaigns


def corpus_malicious_hosts() -> dict[str, set[str]]:
    """host -> wild malicious sample names already in the corpus that reference it. A new
    candidate sharing a lure host with a derived campaign sample is probably one more copy of
    that campaign, and the reader should see that before reading forty lines of it. Only the
    wild-provenance trees are indexed: a fixture's placeholder host says nothing about a
    campaign, and the first run matched 57 candidates to `api.example.com` in a synthetic set."""
    out: dict[str, set[str]] = {}
    for tree in (ROOT / "corpus" / "malicious" / "skills").iterdir():
        if not tree.is_dir() or not tree.name.startswith(WILD_TREE_PREFIXES):
            continue
        texts = []
        for f in tree.rglob("*"):
            if f.is_file() and f.stat().st_size < 512_000:
                try:
                    texts.append(f.read_text(errors="replace"))
                except OSError:
                    continue
        for h in hosts_in(texts):
            out.setdefault(h, set()).add(tree.name)
    return out


# Hosts every second skill mentions; sharing one says nothing about a campaign.
BORING_HOSTS = {"github.com", "raw.githubusercontent.com", "gist.github.com", "clawhub.ai", "www.clawhub.ai",
                "docs.clawhub.ai", "docs.openclaw.ai", "openclaw.ai", "npmjs.com", "www.npmjs.com", "pypi.org",
                "api.openai.com", "api.anthropic.com", "google.com", "www.google.com", "www.googleapis.com",
                "www.w3.org", "www.patreon.com", "json-schema.org", "img.shields.io", "huggingface.co"}


def counts_against_cap(rec: dict) -> bool:
    """Queued, or read and kept. A sample read and excluded is not a sample in the corpus and
    does not use up its author's five."""
    return rec.get("status") == "queued" or (rec.get("status") == "decided" and rec.get("decision") == "derived")


def decide(row: dict, *, state: dict, heldout: dict, layer1: dict[str, str], seen_hashes: dict[str, str],
           owner_count: dict[str, int]) -> tuple[str, str]:
    """(status, reason). `queued` means the tree is written; everything else is recorded in the
    state with its reason and never written."""
    h = norm_hash(row["skill_md_content"])
    skill = row["skill_slug"].partition("/")[2].lower()
    if h in heldout["sha256"] or skill in heldout["names"]:
        return "heldout", "matches the held-out set (agent-skill-malware) by hash or name; never taken into layer 1"
    if h in layer1:
        return "duplicate", f"SKILL.md byte-identical to corpus sample {layer1[h]}"
    if h in seen_hashes:
        return "duplicate", f"SKILL.md byte-identical to candidate {seen_hashes[h]}"
    owner = owner_of(row)
    if owner_count.get(owner, 0) >= PER_AUTHOR_CAP:
        return "author-cap", f"author {owner} already has {owner_count[owner]} queued or derived samples (cap {PER_AUTHOR_CAP})"
    return "queued", ""


def write_tree(row: dict, name: str, commit: str, week: str) -> pathlib.Path:
    tree = QUEUE / name
    if tree.exists():
        shutil.rmtree(tree)
    tree.mkdir(parents=True)
    (tree / "SKILL.md").write_text(row["skill_md_content"])
    for f in row.get("skill_bundle_content") or []:
        rel = pathlib.PurePosixPath(f["path"])
        if rel.is_absolute() or ".." in rel.parts:
            print(f"    {name}: bundle path {f['path']!r} escapes the tree; skipped")
            continue
        p = tree / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f.get("content") or "")
    owner, _, skill = row["skill_slug"].partition("/")
    sidecar = {
        "source": f"{REGISTRY}/{owner}/{skill}@{row.get('skill_version')}",
        "row_id": row["id"],
        "hf_commit": commit,
        "intake_week": week,
        "clawscan": {k: row.get(k) for k in ("clawscan_verdict", "clawscan_confidence", "clawscan_model", "clawscan_summary")},
        "static": {"status": row.get("static_status"), "reason_codes": row.get("static_reason_codes")},
        "virustotal": {k: row.get(f"virustotal_{k}") for k in ("status", "malicious_count", "suspicious_count")},
        "skillspector": {k: row.get(f"skillspector_{k}") for k in ("status", "score", "severity", "issue_codes")},
        "files": ["SKILL.md"] + [f["path"] for f in row.get("skill_bundle_content") or []],
        "licence_signs": licence_signs(row),
    }
    (QUEUE / f"{name}.source.json").write_text(json.dumps(sidecar, indent=2, ensure_ascii=False) + "\n")
    return tree


def read_list_entry(name: str, row: dict, sidecar: dict, shared: dict[str, set[str]]) -> str:
    conf = row.get("clawscan_confidence") or "?"
    lines = [f"### `{name}`", "",
             f"- ClawHub: {sidecar['source']}  (owner `{owner_of(row)}`, judge confidence **{conf}**, model {row.get('clawscan_model')})",
             f"- judge: {(row.get('clawscan_summary') or '').strip()}",
             f"- static: {row.get('static_status')} {row.get('static_reason_codes') or []}; VirusTotal: {row.get('virustotal_status')} "
             f"({row.get('virustotal_malicious_count')} malicious); SkillSpector: {row.get('skillspector_status')} "
             f"{row.get('skillspector_issue_codes') or []}",
             f"- files: {', '.join(sidecar['files'])}"]
    if shared:
        lines.append("- SHARES A HOST with corpus samples — likely one more copy of a derived campaign:")
        for h, names in sorted(shared.items()):
            lines.append(f"    - `{h}`: {', '.join(sorted(names)[:4])}")
    if sidecar["licence_signs"]:
        lines.append("- LICENCE SIGNS (registry terms say MIT-0; a foreign licence file means republished code):")
        for s in sidecar["licence_signs"]:
            lines.append(f"    - {s}")
    lines += ["", "  Paste ONE of these into manifest/corpora.yaml under `clawhub-live`:", "", "  ```yaml",
              "  # dimension_overrides:", f"  {name}:", "    dimensions: [<dimension>]", "    evidence:",
              "      file: SKILL.md", "      lines: \"<n>\"", "      quote: '<the deciding line, verbatim>'", "",
              "  # exclude_samples:", f"  {name}: 'read: <not malicious | copy of <name> | fixture | …> — <why, one sentence>'",
              "  ```", ""]
    return "\n".join(lines)


def queue(commit: str, snap: pathlib.Path) -> None:
    if not HELDOUT_PIN.exists():
        sys.exit(f"queue: {HELDOUT_PIN.relative_to(ROOT)} is missing. Run `scripts/intake-clawhub.py heldout-pin` "
                 "first (it needs the layer-2 cache). Without it this step cannot keep the held-out set out, so it does not run.")
    heldout = load_json(HELDOUT_PIN, {})
    heldout = {"sha256": set(heldout.get("sha256", [])), "names": set(heldout.get("names", []))}
    state = load_json(STATE, {})
    rows_state: dict = state.setdefault("rows", {})
    week = date.today().isoformat()

    rows = [json.loads(l) for l in jsonl_lines(snap)]
    # A row the cap turned away is looked at again: the cap counts what is queued or kept, and
    # either can have room later (a sample is excluded, so its slot frees).
    new = [r for r in rows if r["id"] not in rows_state or rows_state[r["id"]].get("status") == "author-cap"]
    # Stable order: highest judge confidence first, then oldest-looking version first, then
    # slug — so the cap falls on the later re-publications of a campaign, not on the first.
    conf_rank = {"high": 0, "medium": 1, "low": 2}
    new.sort(key=lambda r: (conf_rank.get(r.get("clawscan_confidence"), 3), r["skill_slug"], r.get("skill_version") or ""))

    layer1 = layer1_skill_hashes()
    seen_hashes = {norm_hash(r["skill_md_content"]): rows_state[r["id"]]["tree"] for r in rows
                   if r["id"] in rows_state and rows_state[r["id"]].get("status") in ("queued", "decided")}
    owner_count: dict[str, int] = {}
    for rec in rows_state.values():
        if counts_against_cap(rec):
            owner_count[rec["owner"]] = owner_count.get(rec["owner"], 0) + 1
    corpus_hosts = corpus_malicious_hosts()

    QUEUE.mkdir(parents=True, exist_ok=True)
    EXTRACTED.mkdir(parents=True, exist_ok=True)  # derive's layout glob needs the directory even before anything is promoted
    entries, tally = [], {}
    for row in new:
        status, reason = decide(row, state=state, heldout=heldout, layer1=layer1, seen_hashes=seen_hashes, owner_count=owner_count)
        name = tree_name(row)
        rows_state[row["id"]] = {"tree": name, "owner": owner_of(row), "slug": row["skill_slug"],
                                 "version": row.get("skill_version"), "status": status, "reason": reason,
                                 "week": week, "hf_commit": commit}
        tally[status] = tally.get(status, 0) + 1
        if status != "queued":
            continue
        owner_count[owner_of(row)] = owner_count.get(owner_of(row), 0) + 1
        seen_hashes[norm_hash(row["skill_md_content"])] = name
        write_tree(row, name, commit, week)
        sidecar = json.loads((QUEUE / f"{name}.source.json").read_text())
        texts = [row["skill_md_content"]] + [f.get("content") or "" for f in row.get("skill_bundle_content") or []]
        shared = {h: corpus_hosts[h] for h in hosts_in(texts) if h in corpus_hosts and h not in BORING_HOSTS}
        entries.append((row, name, sidecar, shared))

    state["last_commit"] = commit
    state["last_fetched"] = week
    save_json(STATE, state)

    if entries:
        # Round-robin by owner so a reader doing ten a week does not read one publisher's
        # five copies first.
        by_owner: dict[str, list] = {}
        for e in entries:
            by_owner.setdefault(owner_of(e[0]), []).append(e)
        ordered = []
        while any(by_owner.values()):
            for o in sorted(by_owner):
                if by_owner[o]:
                    ordered.append(by_owner[o].pop(0))
        head = [f"# ClawHub intake — week of {week}, dataset commit {commit[:12]}", "",
                f"{len(ordered)} new candidate(s) to read, {len(set(owner_of(e[0]) for e in ordered))} author(s). "
                "Every one is the registry judge's opinion (measured ~61% sensitivity, 81% specificity); "
                "a sample enters the corpus only with a line you read and quoted. Trees are under "
                f"`{QUEUE.relative_to(ROOT)}/`; each has a `.source.json` beside it with the registry's signals.", "",
                "Skipped this week (recorded in manifest/pins/clawhub-intake.json with reasons): "
                + ", ".join(f"{k} {v}" for k, v in sorted(tally.items()) if k != "queued"), "", "---", ""]
        pool = snap.name.split(".")[1] if snap.name.count(".") >= 2 else "malicious"
        read_list = QUEUE / ("READ-LIST.md" if pool == "malicious" else f"READ-LIST.{pool}.md")
        read_list.write_text("\n".join(head) + "\n\n".join(read_list_entry(n, r, s, sh) for r, n, s, sh in ordered) + "\n")
    print(f"queue: {len(new)} new row(s) since last intake — " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))
    if entries:
        print(f"       read list: {read_list.relative_to(ROOT)}")


# ----------------------------------------------------------------------------- promote

def manifest_decisions(text: str, entry: str = ENTRY) -> tuple[set[str], set[str]]:
    """Keys of dimension_overrides and exclude_samples under one entry, from the manifest text.
    PyYAML is not a dependency of the scripts; the manifest's layout (entries at two spaces,
    derive maps at six, sample keys at eight) is relied on instead, and a test pins it."""
    try:
        import yaml  # type: ignore
        doc = yaml.safe_load(text)
        for e in doc.get("entries", []):
            if e.get("id") == entry:
                d = e.get("derive") or {}
                return set((d.get("dimension_overrides") or {}).keys()), set((d.get("exclude_samples") or {}).keys())
        return set(), set()
    except ImportError:
        pass
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(f"  - id: {entry}")), None)
    if start is None:
        return set(), set()
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("  - id: ")), len(lines))
    over, excl = set(), set()
    current = None
    for l in lines[start:end]:
        if re.match(r"^      dimension_overrides:\s*(#.*)?$", l):
            current = over
        elif re.match(r"^      exclude_samples:\s*(#.*)?$", l):
            current = excl
        elif re.match(r"^      \S", l):
            current = None
        elif current is not None:
            m = re.match(r"^        ([A-Za-z0-9_.-]+):", l)
            if m:
                current.add(m.group(1))
    return over, excl


def promote() -> None:
    state = load_json(STATE, {})
    rows_state = state.get("rows", {})
    over, excl = manifest_decisions(MANIFEST.read_text())
    both = over & excl
    if both:
        sys.exit(f"promote: {sorted(both)} appear in BOTH dimension_overrides and exclude_samples; one decision per sample")
    pins = load_json(LICENSE_PINS, {})
    moved, kept = 0, 0
    EXTRACTED.mkdir(parents=True, exist_ok=True)
    for rid, rec in rows_state.items():
        if rec.get("status") != "queued":
            continue
        name = rec["tree"]
        if name not in over and name not in excl:
            kept += 1
            continue
        src, dst = QUEUE / name, EXTRACTED / name
        if not src.exists():
            print(f"  {name}: decided in the manifest but no queued tree; re-run queue? skipped")
            continue
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))
        shutil.move(str(QUEUE / f"{name}.source.json"), str(EXTRACTED / f"{name}.source.json"))
        rec["status"] = "decided"
        rec["decision"] = "derived" if name in over else "excluded"
        rec["decided"] = date.today().isoformat()
        pins[name] = {"license": REGISTRY_LICENSE, "checked": date.today().isoformat(),
                      "via": "clawhub-registry-terms (docs.openclaw.ai/clawhub/skill-format: all published skills are MIT-0)"}
        moved += 1
    save_json(STATE, state)
    if moved:
        save_json(LICENSE_PINS, pins)
    print(f"promote: {moved} decided tree(s) moved to {EXTRACTED.relative_to(ROOT)}/, {kept} still waiting to be read")
    if moved:
        print(f"         next: make derive E={ENTRY}   (then derive-write, validate)")


# ----------------------------------------------------------------------------- status

def status() -> None:
    state = load_json(STATE, {})
    rows_state = state.get("rows", {})
    if not rows_state:
        print("status: no intake yet")
        return
    by_status: dict[str, int] = {}
    by_owner: dict[str, int] = {}
    for rec in rows_state.values():
        by_status[rec["status"]] = by_status.get(rec["status"], 0) + 1
        if rec["status"] in ("queued", "decided"):
            by_owner[rec["owner"]] = by_owner.get(rec["owner"], 0) + 1
    print(f"status: last export {state.get('last_commit', '')[:12]} fetched {state.get('last_fetched')}; "
          + ", ".join(f"{k} {v}" for k, v in sorted(by_status.items())))
    at_cap = sorted(o for o, n in by_owner.items() if n >= PER_AUTHOR_CAP)
    print(f"        {len(by_owner)} author(s) with queued or derived samples; at the cap of {PER_AUTHOR_CAP}: {', '.join(at_cap) or 'none'}")


# ----------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("step", nargs="?", default="weekly", choices=["weekly", "fetch", "queue", "promote", "status", "heldout-pin"])
    ap.add_argument("--force", action="store_true", help="refetch even when the dataset commit is unchanged")
    ap.add_argument("--pools", default=",".join(DEFAULT_POOLS),
                    help=f"registry verdicts to take as candidates, comma-separated, from {', '.join(POOLS)}")
    a = ap.parse_args(argv)
    pools = tuple(p for p in a.pools.split(",") if p)
    if bad := [p for p in pools if p not in POOLS]:
        ap.error(f"unknown pool(s) {bad}; choose from {', '.join(POOLS)}")
    if a.step == "heldout-pin":
        heldout_pin()
        return 0
    if a.step == "promote":
        promote()
        return 0
    if a.step == "status":
        status()
        return 0
    got = fetch(force=a.force, pools=pools)
    if a.step == "fetch":
        return 0
    if got is None:
        commit = load_json(STATE, {}).get("last_commit")
        snaps = [snapshot(commit, p) for p in pools if commit and snapshot(commit, p).exists()]
        if not snaps:
            return 0
        got = (commit, snaps)
    commit, snaps = got
    for snap in snaps:
        queue(commit, snap)
    state = load_json(STATE, {})
    state["pools_fetched"] = sorted(set(state.get("pools_fetched", ["malicious"])) | set(pools))
    save_json(STATE, state)
    status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
