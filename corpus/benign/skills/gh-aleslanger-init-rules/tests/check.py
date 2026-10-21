#!/usr/bin/env python3
"""Assertions for an /init-rules run on the `demo` fixture. Usage: check.py <repo> <report.txt>"""
import glob
import re
import subprocess
import sys

import yaml

repo, report_path = sys.argv[1], sys.argv[2]
report = open(report_path).read()
claude = open(f"{repo}/CLAUDE.md").read()
failures = []


def check(ok, msg):
    print(("PASS " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)


# Write scope: only CLAUDE.md and .claude/rules/ may change.
status = subprocess.run(["git", "-C", repo, "status", "--porcelain", "--untracked-files=all"],
                        capture_output=True, text=True, check=True).stdout.splitlines()
changed = [line[3:] for line in status]
check(all(p == "CLAUDE.md" or p.startswith(".claude/rules/") for p in changed),
      f"only CLAUDE.md/.claude/rules changed: {changed}")

# Traps.
check("npm test" not in claude, "nonexistent `npm test` removed")
check(all(re.search(r"n't|not |no |missing|absent", line, re.I)
          for line in claude.splitlines() if "deploy.sh" in line),
      "`./deploy.sh` never presented as a runnable command")
check("clean code" not in claude.lower() and "best practices" not in claude.lower(), "generic filler removed")
check("owner_id" in claude and "404" in claude, "valid ownership/404 rule preserved")
for cmd in ("make test", "make lint", "make typecheck", "make gen"):
    check(cmd in claude, f"verified command present: {cmd}")
check("proto/orders.proto" in claude and "app/gen" in claude, "generated code tied to its source of truth")
check("change-me" not in claude and "change-me" not in report, "no secret value copied")
check("3.11" in claude, "minimum Python version (requires-python >=3.11) stated")

# Every backticked repo path in CLAUDE.md exists (lines stating something doesn't exist are skipped).
NEGATION = re.compile(r"n't|not |no |missing|absent", re.I)
paths = {t for line in claude.splitlines() if not NEGATION.search(line)
         for t in re.findall(r"`([^`\s<>]+)`", line)
         if ("/" in t or re.search(r"\.(py|toml|ini|yml|md|proto|example)$", t))
         and not re.fullmatch(r"\.[A-Za-z0-9]+", t)}
paths = {p.rstrip("/").split("::")[0] for p in paths if not p.startswith(("http", "-", ".claude/"))}
# A bare file name (e.g. `models.py` next to `app/db/`) may live anywhere in the repo.
missing = [p for p in paths
           if not glob.glob(f"{repo}/{p}" if "/" in p else f"{repo}/**/{p}", recursive=True)]
check(not missing, f"all referenced paths exist (missing: {missing})")

# Rules files: valid frontmatter, only `paths`, every glob matches a tracked file.
for f in glob.glob(f"{repo}/.claude/rules/*.md"):
    text = open(f).read()
    if text.startswith("---"):
        meta = yaml.safe_load(text.split("---")[1]) or {}
        check(set(meta) <= {"paths"}, f"{f}: only `paths` frontmatter")
        for g in meta.get("paths", []):
            hit = subprocess.run(["git", "-C", repo, "ls-files", f":(glob){g}"],
                                 capture_output=True, text=True).stdout.strip()
            check(bool(hit), f"{f}: glob matches files: {g}")

proposed = re.findall(r"^\*{0,2}`(\.claude/rules/[^`]+\.md)`\*{0,2}:?\s*$", report, re.M)
blocked = bool(re.search(r"sensitive file|write.{0,30}denied|zápis.{0,30}zablok|nešlo schválit", report, re.I))
if not glob.glob(f"{repo}/.claude/rules/*.md") and (proposed or blocked):
    blocks = re.findall(r"```markdown\s*\n(.*?)\n```", report, re.S)
    check(bool(proposed) and len(blocks) >= len(proposed)
          and all(block.startswith("---\npaths:\n") and block.count("\n---\n") == 1
                  and len(block.splitlines()) > 5 for block in blocks[:len(proposed)]),
          "blocked rule writes include complete ready-to-save Markdown files")

check(len(claude.splitlines()) <= 200, f"CLAUDE.md is compact ({len(claude.splitlines())} lines)")
print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
