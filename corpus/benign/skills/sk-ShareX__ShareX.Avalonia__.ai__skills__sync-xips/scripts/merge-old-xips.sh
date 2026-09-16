#!/usr/bin/env bash
set -euo pipefail

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command not found: $1" >&2
    exit 1
  fi
}

require_cmd gh
require_cmd python3

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$script_dir"
for _ in 1 2 3 4 5; do
  repo_root="$(dirname "$repo_root")"
  if [[ -d "$repo_root/.git" ]]; then
    break
  fi
done

if [[ ! -d "$repo_root/.git" ]]; then
  echo "Error: repo root not found. Run from XerahS repo." >&2
  exit 1
fi

backup_root="$repo_root/docs/proposals/xip"

REPO_ROOT="$repo_root" BACKUP_ROOT="$backup_root" SCRIPT_DIR="$script_dir" python3 - <<'PY'
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
backup_root = Path(os.environ["BACKUP_ROOT"])
script_dir = Path(os.environ["SCRIPT_DIR"])

def run(cmd, *, input_text=None):
    return subprocess.run(
        cmd,
        text=True,
        input=input_text,
        capture_output=True,
        check=True,
    )

def get_xip_num_from_title(title: str):
    m = re.search(r"XIP[\s\-]?(\d+)", title)
    return m.group(1).zfill(4) if m else None

def get_title_without_xip_prefix(title: str):
    return re.sub(r"^\[?XIP[\s\-]?\d+\]?\s*", "", title).strip()

def get_slug(title_part: str):
    s = re.sub(r"[^\x20-\x7E]", "-", title_part)
    s = re.sub(r"[^a-zA-Z0-9\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"\-+", "-", s)
    s = s.strip("-").lower()
    return s or "untitled"

def get_xip_num_from_filename(basename: str):
    m = re.match(r"^XIP(\d+)", basename)
    return m.group(1).zfill(4) if m else None

issues_json = run([
    "gh",
    "issue",
    "list",
    "--label",
    "xip",
    "--state",
    "all",
    "--limit",
    "500",
    "--json",
    "number,title,body",
]).stdout
issues = json.loads(issues_json)

by_xip_num = {}
for issue in issues:
    xip_num = get_xip_num_from_title(issue.get("title", ""))
    if not xip_num:
        continue
    title_part = get_title_without_xip_prefix(issue.get("title", ""))
    slug = get_slug(title_part)
    canonical = f"XIP{xip_num}-{slug}.md"
    by_xip_num[xip_num] = {
        "issue_number": issue.get("number"),
        "body": issue.get("body") or "",
        "canonical": canonical,
    }

all_md = list(backup_root.rglob("XIP*.md")) if backup_root.exists() else []
old_files = []
for f in all_md:
    base = f.name
    xip_num = get_xip_num_from_filename(base)
    if not xip_num:
        continue
    canonical = by_xip_num.get(xip_num, {}).get("canonical")
    is_in_root = f.parent == backup_root
    if canonical and base == canonical and is_in_root:
        continue
    old_files.append({"path": f, "base": base, "xip_num": xip_num})

if not old_files:
    print("No legacy XIP files to merge. Exiting.")
    raise SystemExit(0)

print(f"Found {len(old_files)} legacy file(s) to merge into masters and remove.")

by_num = {}
for item in old_files:
    by_num.setdefault(item["xip_num"], []).append(item)

for xip_num in sorted(by_num.keys()):
    group = by_num[xip_num]
    master = by_xip_num.get(xip_num)

    if master:
        body = master["body"] or ""
        for item in group:
            content = item["path"].read_text(encoding="utf-8", errors="replace")
            body += f"\n\n---\n\n## Legacy content from `{item['base']}`\n\n{content}"

        print(
            f"  Merging into issue #{master['issue_number']} (XIP{xip_num}): {len(group)} file(s)"
        )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
            tmp.write(body)
            tmp_path = tmp.name
        try:
            run(["gh", "issue", "edit", str(master["issue_number"]), "--body-file", tmp_path])
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        first = group[0]
        content = first["path"].read_text(encoding="utf-8", errors="replace")
        title_part = f"XIP{xip_num}"
        for line in content.splitlines():
            m = re.match(r"^#\s+(.+)", line)
            if m:
                extracted = re.sub(r"^XIP\d+[\s:\-]*", "", m.group(1).strip())
                title_part = f"XIP{xip_num} {extracted.strip()}".strip()
                break
        if title_part == f"XIP{xip_num}":
            fallback = re.sub(r"^XIP\d+[_\-]?", "", first["base"])
            fallback = re.sub(r"\.md$", "", fallback).replace("_", " ")
            title_part = f"XIP{xip_num} {fallback}".strip()

        print(f"  Creating new issue: {title_part} (from {first['base']})")
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            run(["gh", "issue", "create", "--title", title_part, "--label", "xip", "--body-file", tmp_path])
        finally:
            Path(tmp_path).unlink(missing_ok=True)

print("Running sync-from-github.sh ...")
subprocess.run(["bash", str(script_dir / "sync-from-github.sh")], check=True)

print("Removing legacy files ...")
for item in old_files:
    p = item["path"]
    if p.exists():
        p.unlink()
        print(f"  Deleted: {item['base']}")

for sub in ("active", "complete", "parked"):
    d = backup_root / sub
    if d.exists() and not any(d.iterdir()):
        d.rmdir()
        print(f"  Removed empty folder: docs/proposals/xip/{sub}/")

print("Done. Legacy content merged into GitHub; backup synced to docs/proposals/xip/; old files removed.")
PY
