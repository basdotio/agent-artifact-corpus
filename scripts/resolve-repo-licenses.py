#!/usr/bin/env python3
"""Resolve the licence of every ORIGINATING repository behind the samples that reached layer 1
through a dataset rather than directly from GitHub.

Why this exists. SkillMD-138K and skillet are compilations: their own licence (CC-BY-4.0, MIT)
covers the curation, and each upstream says so in as many words — every SKILL.md "retains the
copyright and license of its original author/repository". For 2,470 trees the label's
origin.license was the compilation's licence, not the author's, which is the wrong field for
layer 1's rule (docs/licensing.md: permissive upstream licences only, attributed per author).

What it does. Reads origin.source from every md-* and sk-* label, collects the GitHub
repositories, asks the GitHub GraphQL API for each repository's licenseInfo.spdxId in batches,
and writes manifest/pins/repo-licenses.json: one record per repository with the SPDX id GitHub
reports (or NONE / NOT_FOUND), the date, and how it was obtained. The derive rule reads that file
through `license_from`, so a re-derivation reproduces the same labels without a network.

It never edits a label; `corpus derive --write` does that from the pins file. Red line 2: the
summary it prints names how many repositories fall outside the permissive set, because those
samples leave the denominator and the exclusion has to be reported with both figures.

Usage: scripts/resolve-repo-licenses.py [--refresh] [--apply]   (needs `gh auth status` to pass)
  --apply rewrites origin.license in the labels from the pins file (what derive --write would do)
"""
import datetime
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PINS = ROOT / "manifest" / "pins" / "repo-licenses.json"
LABEL_GLOBS = ["corpus/benign/skills/md-*.yaml", "corpus/benign/skills/sk-*.yaml"]
REPO_RE = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
BATCH = 50

# The set layer 1 admits. Anything else is reported, never silently kept.
PERMISSIVE = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "CC0-1.0",
              "CC-BY-4.0", "Unlicense", "0BSD", "MIT-0", "BSD-3-Clause-Clear", "Zlib",
              "MPL-2.0"}


def repos_from_labels() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for g in LABEL_GLOBS:
        for f in sorted(ROOT.glob(g)):
            src = ""
            for line in f.read_text().splitlines():
                if line.startswith("  source:"):
                    src = line
                    break
            m = REPO_RE.search(src)
            if not m:
                print(f"  ! {f.name}: no github repository in origin.source", file=sys.stderr)
                continue
            key = f"{m.group(1)}/{m.group(2)}"
            out.setdefault(key, []).append(f.stem)
    return out


def gh_graphql(query: str) -> dict:
    p = subprocess.run(["gh", "api", "graphql", "-f", f"query={query}"],
                       capture_output=True, text=True)
    if p.returncode != 0 and not p.stdout:
        sys.exit(f"gh api graphql failed: {p.stderr.strip()}")
    return json.loads(p.stdout)


def resolve(repos: list[str]) -> dict[str, dict]:
    today = datetime.date.today().isoformat()
    found: dict[str, dict] = {}
    for i in range(0, len(repos), BATCH):
        chunk = repos[i:i + BATCH]
        parts = []
        for j, r in enumerate(chunk):
            owner, name = r.split("/", 1)
            parts.append(f'r{j}: repository(owner: "{owner}", name: "{name}") '
                         '{ nameWithOwner isFork licenseInfo { spdxId } }')
        data = gh_graphql("query { " + " ".join(parts) + " }")
        got = data.get("data") or {}
        for j, r in enumerate(chunk):
            node = got.get(f"r{j}")
            if node is None:
                found[r] = {"license": "NOT_FOUND", "checked": today, "via": "github-graphql"}
                continue
            lic = (node.get("licenseInfo") or {}).get("spdxId") or "NONE"
            if lic == "NOASSERTION":
                lic = "OTHER"   # GitHub saw a LICENSE file it could not classify
            found[r] = {"license": lic, "checked": today, "via": "github-graphql",
                        "name": node.get("nameWithOwner", r), "fork": bool(node.get("isFork"))}
        print(f"  {min(i + BATCH, len(repos))}/{len(repos)}", file=sys.stderr)
    return found


def apply(repos: dict[str, list[str]], pins: dict[str, dict]) -> int:
    """Rewrite origin.license in every label from the pins file. This is what `corpus derive
    --write` produces once the entry is fetched; it is here so the labels can be brought in
    line without re-fetching a 138,133-row parquet. Only the one line changes."""
    changed = 0
    for repo, samples in repos.items():
        lic = pins.get(repo, {}).get("license")
        if not lic:
            continue
        for stem in samples:
            f = ROOT / "corpus" / "benign" / "skills" / f"{stem}.yaml"
            lines = f.read_text().splitlines(keepends=True)
            for i, line in enumerate(lines):
                if line.startswith("  license: "):
                    if line != f"  license: {lic}\n":
                        lines[i] = f"  license: {lic}\n"
                        f.write_text("".join(lines))
                        changed += 1
                    break
    return changed


def main() -> int:
    refresh = "--refresh" in sys.argv
    repos = repos_from_labels()
    pins = json.loads(PINS.read_text()) if PINS.exists() and not refresh else {}
    todo = [r for r in sorted(repos) if r not in pins]
    print(f"{len(repos)} repositories behind {sum(len(v) for v in repos.values())} labels; "
          f"{len(todo)} to resolve", file=sys.stderr)
    if todo:
        pins.update(resolve(todo))
        PINS.write_text(json.dumps(dict(sorted(pins.items())), indent=2) + "\n")

    if "--apply" in sys.argv:
        print(f"applied: {apply(repos, pins)} label(s) changed", file=sys.stderr)

    # Red line 2: the exclusion, with both figures, every run.
    tally: dict[str, int] = {}
    outside = 0
    for r, samples in repos.items():
        lic = pins.get(r, {}).get("license", "?")
        tally[lic] = tally.get(lic, 0) + len(samples)
        if lic not in PERMISSIVE:
            outside += len(samples)
    total = sum(len(v) for v in repos.values())
    print("\nlabels by originating repository licence:")
    for lic, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        flag = "" if lic in PERMISSIVE else "   <- outside layer 1"
        print(f"  {lic:<16} {n:>5}{flag}")
    print(f"\n{total} labels; {total - outside} on permissive repositories, {outside} not "
          f"({outside / total:.1%}). A rate over the permissive set is a rate over "
          f"permissively licensed repositories, not over what people publish.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
