#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PS1_SCRIPT="$SCRIPT_DIR/update-changelog.ps1"

usage() {
  cat <<'USAGE'
Usage: update-changelog.sh [options]

Options:
  --version <X.Y.Z>
  --from-tag <tag>
  --changelog-path <path>    Default: docs/CHANGELOG.md
  --apply                    Apply generated section to changelog
  --include-merges           Include merge commits
  --include-hashes           Include commit hashes (audit only)
  --no-consolidation         Per-commit lines (debug only)
  --output-path <path>       Write generated section to this file
  -h, --help                 Show this help
USAGE
}

VERSION=""
FROM_TAG=""
CHANGELOG_PATH="docs/CHANGELOG.md"
APPLY=0
INCLUDE_MERGES=0
INCLUDE_HASHES=0
NO_CONSOLIDATION=0
OUTPUT_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      VERSION="${2:-}"
      shift 2
      ;;
    --from-tag)
      FROM_TAG="${2:-}"
      shift 2
      ;;
    --changelog-path)
      CHANGELOG_PATH="${2:-}"
      shift 2
      ;;
    --apply)
      APPLY=1
      shift
      ;;
    --include-merges)
      INCLUDE_MERGES=1
      shift
      ;;
    --include-hashes)
      INCLUDE_HASHES=1
      shift
      ;;
    --no-consolidation)
      NO_CONSOLIDATION=1
      shift
      ;;
    --output-path)
      OUTPUT_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown option '$1'" >&2
      usage >&2
      exit 1
      ;;
  esac
done

run_pwsh() {
  local runner="$1"
  shift
  local args=()
  [[ -n "$VERSION" ]] && args+=("-Version" "$VERSION")
  [[ -n "$FROM_TAG" ]] && args+=("-FromTag" "$FROM_TAG")
  [[ -n "$CHANGELOG_PATH" ]] && args+=("-ChangelogPath" "$CHANGELOG_PATH")
  [[ "$APPLY" -eq 1 ]] && args+=("-Apply")
  [[ "$INCLUDE_MERGES" -eq 1 ]] && args+=("-IncludeMerges")
  [[ "$INCLUDE_HASHES" -eq 1 ]] && args+=("-IncludeHashes")
  [[ "$NO_CONSOLIDATION" -eq 1 ]] && args+=("-NoConsolidation")
  [[ -n "$OUTPUT_PATH" ]] && args+=("-OutputPath" "$OUTPUT_PATH")
  "$runner" -NoProfile -ExecutionPolicy Bypass -File "$PS1_SCRIPT" "${args[@]}"
}

if command -v pwsh >/dev/null 2>&1; then
  if run_pwsh pwsh; then
    exit 0
  fi
  echo "Warning: pwsh failed; falling back to Python changelog generator." >&2
fi

if command -v powershell >/dev/null 2>&1; then
  if run_pwsh powershell; then
    exit 0
  fi
  echo "Warning: powershell failed; falling back to Python changelog generator." >&2
fi

# Python fallback when PowerShell is unavailable
python3 - "$VERSION" "$FROM_TAG" "$CHANGELOG_PATH" "$APPLY" "$INCLUDE_MERGES" "$INCLUDE_HASHES" "$NO_CONSOLIDATION" "$OUTPUT_PATH" <<'PY'
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

version_arg, from_tag_arg, changelog_path_arg, apply_arg, include_merges_arg, include_hashes_arg, no_consolidation_arg, output_path_arg = sys.argv[1:9]
apply_arg = apply_arg == "1"
include_merges_arg = include_merges_arg == "1"
include_hashes_arg = include_hashes_arg == "1"
no_consolidation_arg = no_consolidation_arg == "1"

PREAMBLE = """# Changelog

All notable changes to XerahS will be documented in this file.

The format follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html):

- **MAJOR** (x): Breaking changes (0 while unreleased)
- **MINOR** (y): New features and enhancements
- **PATCH** (z): Bug fixes and patches

---

"""

def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True)

repo_root = Path(run(["git", "rev-parse", "--show-toplevel"]).stdout.strip())
os.chdir(repo_root)

def resolve_version(requested: str) -> str:
    if requested:
        if not re.match(r"^\d+\.\d+\.\d+$", requested):
            raise SystemExit(f"Error: invalid version '{requested}'")
        return requested
    props = (repo_root / "Directory.Build.props").read_text(encoding="utf-8")
    m = re.search(r"<Version>\s*(\d+\.\d+\.\d+)\s*</Version>", props)
    if not m:
        raise SystemExit("Error: could not resolve <Version>")
    return m.group(1)

def resolve_from_tag(requested: str):
    if requested:
        return requested
    proc = run(["git", "describe", "--tags", "--abbrev=0"])
    return proc.stdout.strip() if proc.returncode == 0 and proc.stdout.strip() else None

def tag_exists(version: str) -> bool:
    tag = f"v{version}"
    if run(["git", "show-ref", "--verify", "--quiet", f"refs/tags/{tag}"]).returncode == 0:
        return True
    return run(["git", "ls-remote", "--exit-code", "--tags", "origin", f"refs/tags/{tag}"]).returncode == 0

def version_heading(version: str) -> str:
    if tag_exists(version):
        return f"## [v{version}](https://github.com/ShareX/XerahS/releases/tag/v{version})"
    return f"## v{version}"

def is_noise(subject: str) -> bool:
    patterns = [
        r"^\[v\d+\.\d+\.\d+\]\s+\[CI\]\s+Release\s+v\d+\.\d+\.\d+$",
        r"(?i)hourly review (tracker|state)",
        r"(?i)clawpatch",
        r"(?i)xerahs-review:",
        r"(?i)tracker:",
        r"(?i)\[hourly\]",
        r"(?i)pre-commit:.*state JSON",
        r"(?i)XIP\d{4} state JSON",
        r"(?i)^\[v[\d.]+\]\s+\[(Docs|Meta|CI)\]\s+(Bump version|Update hourly review|Record .+ in tracker)",
    ]
    return any(re.search(p, subject) for p in patterns)

def categorize(subject: str):
    m = re.match(r"^\[v\d+\.\d+\.\d+\]\s+\[(?P<t>[^\]]+)\]\s+(?P<d>.+)$", subject)
    if m:
        ctype = m.group("t").strip().lower()
        desc = m.group("d").strip()
        component = "Core"
        p = re.match(r"^(?P<c>[A-Za-z0-9\/ .&+\-]+):\s*(?P<r>.+)$", desc)
        if p:
            component = p.group("c").strip().title()
            desc = p.group("r").strip()
        return category_from_type(ctype), component, desc
    return "Changed", "Core", subject.strip()

def category_from_type(ctype: str) -> str:
    return {
        "feat": "Features", "feature": "Features", "fix": "Fixes", "refactor": "Refactor",
        "build": "Build", "ci": "Build", "docs": "Documentation", "doc": "Documentation",
        "test": "Testing", "tests": "Testing", "perf": "Performance",
    }.get(ctype, "Changed")

def get_platform_xip_label(subject: str):
    m = re.search(r"(?i)XIP(\d{4})", subject)
    if not m:
        return None
    xip_num = m.group(1)
    xip = f"XIP{xip_num}"
    pm = re.search(r"(?i)\bP(\d+)\b", subject)
    p = f" P{pm.group(1)}" if pm else ""

    if re.search(r"(?i)macOS|MacOS|Carbon|ScreenCaptureKit|Info\.plist|codesign|notarize|package-mac|CGWindowList|sck_capture", subject):
        platform = "macOS"
    elif re.search(r"(?i)Linux|Wayland|wl-copy|xclip|portal|notify-send|rpm|\.deb", subject):
        platform = "Linux"
    elif xip_num == "0078":
        platform = "macOS"
    elif xip_num == "0079":
        platform = "Linux"
    else:
        return None

    topic_patterns = [
        (r"(?i)hotkey", "Hotkeys"),
        (r"(?i)notification|notify-send", "Notifications"),
        (r"(?i)clipboard|wl-copy|xclip", "Clipboard"),
        (r"(?i)monitor|mixed-DPI|DPI|normalizer", "Mixed-DPI"),
        (r"(?i)Info\.plist|bundle", "App bundle"),
        (r"(?i)permission|Screen Recording", "Permissions"),
        (r"(?i)window|CGWindowList|sck_capture", "Window capture"),
        (r"(?i)ScreenCaptureKit", "ScreenCaptureKit"),
        (r"(?i)codesign|notarize|DMG|package-mac", "Packaging"),
        (r"(?i)INSTALL|KNOWN_ISSUES|documentation|docs", "Documentation"),
    ]
    topic = "Platform"
    for pattern, name in topic_patterns:
        if re.search(pattern, subject):
            topic = name
            break

    return f"{platform} — {topic} ({xip}{p})"

def consolidation_bucket(subject: str, category: str, component: str):
    if re.search(r"(?i)(pipe-drain|pipe-fill|stderr).*(deadlock|timeout)", subject):
        platform = "Linux" if re.search(r"(?i)Linux|Wayland|gsettings|xdotool|xrandr|grim|slurp", subject) else (
            "macOS" if re.search(r"(?i)macOS|MacOS|osascript|pbpaste|pbcopy", subject) else component)
        return (
            f"{category}|{platform}|pipe",
            platform,
            f"{platform} service helpers: drain stderr and bound subprocess waits to prevent pipe-fill deadlocks",
        )
    label = get_platform_xip_label(subject)
    if label:
        clean = re.sub(r"^\[v\d+\.\d+\.\d+\]\s+\[[^\]]+\]\s+", "", subject)
        clean = re.sub(r"(?i)^XIP\d{4}\s+P\d+:\s*", "", clean).strip()
        return f"{category}|{label}|xip", label, clean
    if re.search(r"(?i)ShareX\.ImageEditor", subject):
        return f"{category}|ImageEditor|sharex", "ShareX.ImageEditor", "ShareX.ImageEditor submodule updates"
    if category == "Documentation" and re.search(r"(?i)(Add|Update|Refresh)\s+2026-\d{2}-\d{2}.*blog", subject):
        return "Documentation|blog|series", "Blog", "Blog drafts (2026 series, add/update)"
    if category == "Documentation" and re.search(r"(?i)\b(XIP\d+|IEIP\d+)", subject):
        return "Documentation|xip|series", "Proposals", "XIP/IEIP proposals and related documentation"
    if category == "Documentation" and component.lower() == "linux":
        return "Documentation|Linux|docs", "Linux", "Linux install and capture documentation"
    if (category == "Changed" or category == "Features") and re.search(r"(?i)multipart(\s+upload)?|S3\s+multipart", subject):
        return f"{category}|{component}|multipart", component, "Multipart upload support (S3, abstractions, coverage)"
    return None

def get_commits(from_tag, include_merges):
    rng = "HEAD" if not from_tag else f"{from_tag}..HEAD"
    cmd = ["git", "log", rng, "--pretty=format:%h\x1f%s\x1f%an"]
    if not include_merges:
        cmd.append("--no-merges")
    proc = run(cmd)
    if proc.returncode != 0:
        raise SystemExit("Error: git log failed")
    rows = []
    for line in proc.stdout.splitlines():
        parts = line.split("\x1f")
        if len(parts) >= 3:
            rows.append({"hash": parts[0], "subject": parts[1]})
    return rows

def merge_by_component(entries):
    merged = {}
    for e in entries:
        key = e["component"]
        merged.setdefault(key, {"category": e["category"], "component": key, "descs": set(), "hashes": set()})
        merged[key]["descs"].add(e["desc"])
        merged[key]["hashes"].update(e["hashes"])
    out = []
    for item in merged.values():
        descs = sorted(item["descs"])
        if len(descs) <= 1:
            text = descs[0] if descs else ""
        elif len(descs) <= 3:
            text = "; ".join(descs)
        else:
            text = "; ".join(descs[:2]) + "; and related changes"
        out.append({**item, "desc": text})
    return out

def build_section(version: str, commits):
    grouped = {}
    for row in commits:
        if is_noise(row["subject"]):
            continue
        category, component, desc = categorize(row["subject"])
        key = f"{category}|{component}|{desc}"
        if not no_consolidation_arg:
            bucket = consolidation_bucket(row["subject"], category, component)
            if bucket:
                key, component, desc = bucket[0], bucket[1], bucket[2]
        entry = grouped.setdefault(key, {"category": category, "component": component, "desc": desc, "hashes": set()})
        entry["hashes"].add(row["hash"])

    order = ["Features", "Fixes", "Refactor", "Build", "Documentation", "Testing", "Performance", "Changed"]
    by_cat = defaultdict(list)
    for e in grouped.values():
        by_cat[e["category"]].append(e)

    lines = [version_heading(version), ""]
    for cat in order:
        entries = merge_by_component(by_cat.get(cat, []))
        if not entries:
            continue
        lines.append(f"### {cat}")
        for e in sorted(entries, key=lambda x: (x["component"], x["desc"])):
            if include_hashes_arg:
                hashes = ", ".join(sorted(e["hashes"]))
                lines.append(f"- **{e['component']}**: {e['desc']} ({hashes})")
            else:
                lines.append(f"- **{e['component']}**: {e['desc']}")
        lines.append("")

    if len(lines) == 2:
        lines.extend(["### Changed", "- No user-facing commits were detected in this range.", ""])

    lines.extend(["---", ""])
    return "\n".join(lines).rstrip() + "\n"

def ensure_preamble(content: str) -> str:
    if re.match(r"(?m)^#\s*Changelog\s*$", content):
        return content
    return PREAMBLE + content.lstrip()

def upsert(content: str, version: str, section: str) -> str:
    escaped = re.escape(version)
    pattern = re.compile(rf"(?ms)^## (?:v{escaped}|\[v{escaped}\]\([^)]+\))\s*$.*?(?=^## (?:v\d+\.\d+\.\d+|\[v\d+\.\d+\.\d+\])|\Z)")
    if pattern.search(content):
        return pattern.sub(section.rstrip() + "\n\n", content)
    m = re.search(r"(?m)^---\s*$", content)
    if m:
        idx = m.end()
        return content[:idx] + "\n\n" + section.rstrip() + "\n" + content[idx:]
    return section.rstrip() + "\n\n" + content

version = resolve_version(version_arg)
from_tag = resolve_from_tag(from_tag_arg)
commits = get_commits(from_tag, include_merges_arg)
section = build_section(version, commits)

if output_path_arg:
    out = Path(output_path_arg)
    if not out.is_absolute():
        out = repo_root / out
    out.write_text(section, encoding="utf-8")

if apply_arg:
    changelog = Path(changelog_path_arg)
    if not changelog.is_absolute():
        changelog = repo_root / changelog
    existing = ensure_preamble(changelog.read_text(encoding="utf-8-sig"))
    changelog.write_text(upsert(existing, version, section), encoding="utf-8")

print(f"Target version : v{version}")
print(f"From tag       : {from_tag or '(none)'}")
print(f"Commits parsed : {len(commits)}")
if apply_arg:
    print(f"Applied to     : {changelog_path_arg}")
if output_path_arg:
    print(f"Draft output   : {output_path_arg}")
print()
print(section, end="")
print()
print("Rewrite pass: compress categories, merge trivial patch versions, polish platform/XIP bullets before publishing.", file=sys.stderr)
PY
