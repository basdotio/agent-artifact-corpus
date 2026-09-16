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
mkdir -p "$backup_root"
find "$backup_root" -maxdepth 1 -type f -name 'XIP*.md' -delete

issues_json="$(gh issue list --label xip --state all --limit 500 --json number,title,body,state,labels)"

BACKUP_ROOT="$backup_root" ISSUES_JSON="$issues_json" python3 - <<'PY'
import json
import re
import sys
from pathlib import Path

backup_root = Path(Path(__import__("os").environ["BACKUP_ROOT"]))
issues = json.loads(__import__("os").environ["ISSUES_JSON"])

def get_xip_number_from_title(title: str):
    m = re.search(r"XIP[\s\-]?(\d+)", title)
    if not m:
        return None
    return m.group(1).zfill(4)

def get_title_without_xip_prefix(title: str):
    return re.sub(r"^\[?XIP[\s\-]?\d+\]?\s*", "", title).strip()

def get_slug(title_part: str):
    s = re.sub(r"[^\x20-\x7E]", "-", title_part)
    s = re.sub(r"[^a-zA-Z0-9\s\-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"\-+", "-", s)
    s = s.strip("-").lower()
    return s or "untitled"

def get_body_content(body: str):
    if not body:
        return ""
    if re.search(r"(?s)##\s*XIP\s*Document\s*.*?^---\s*", body, flags=re.MULTILINE):
        body = re.sub(r"(?s)^.*?^---\s*", "", body, count=1, flags=re.MULTILINE)
    return body.strip()

written = 0
skipped = 0

for issue in issues:
    title = issue.get("title", "")
    num = get_xip_number_from_title(title)
    title_part = get_title_without_xip_prefix(title)
    if not num:
        print(f"Skipping #{issue.get('number')}: title has no XIP number - {title}")
        skipped += 1
        continue

    slug = get_slug(title_part)
    file_name = f"XIP{num}-{slug}.md"
    out_path = backup_root / file_name
    content = get_body_content(issue.get("body") or "")

    first_line = f"# XIP{num} {title_part}"
    lines = content.split("\n") if content else []
    if lines and re.match(r"^#\s+", lines[0]):
        rest = "\n".join(lines[1:]).lstrip()
        content = first_line + ("\n" + rest if rest else "")
    else:
        content = first_line + "\n\n" + content

    out_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    print(f"  {file_name} -> docs/proposals/xip/")
    written += 1

print("")
print(f"Synced {written} XIP(s) to docs/proposals/xip. Skipped {skipped}.")
PY
