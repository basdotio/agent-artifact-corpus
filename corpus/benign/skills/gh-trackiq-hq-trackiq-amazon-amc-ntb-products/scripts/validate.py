#!/usr/bin/env python3
"""Lint every skill in the repo against the TrackIQ Skill Standard.

Exits non-zero on any error, so it can gate CI. Warnings never fail the
build; they are the things a human should look at before tagging.

    python scripts/validate.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGINS = REPO / "plugins"

# Anthropic's validator rejects names containing these, and anything outside
# [a-z0-9-]. Keeping to the strictest ruleset keeps one zip portable.
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED = ("anthropic", "claude")
NAME_MAX = 64
DESC_MAX = 1024
BODY_MAX_LINES = 500
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
# Frontmatter keys accepted everywhere. Anything else risks a rejected upload.
ALLOWED_FM_KEYS = {"name", "description"}

errors: list[str] = []
warnings: list[str] = []


def err(skill: str, msg: str) -> None:
    errors.append(f"{skill}: {msg}")


def warn(skill: str, msg: str) -> None:
    warnings.append(f"{skill}: {msg}")


def parse_frontmatter(text: str, skill: str) -> tuple[dict, str]:
    """Minimal YAML frontmatter reader — flat key: value pairs plus folded
    continuation lines. Deliberately not PyYAML: no dependency, and a skill
    that needs nested frontmatter is already off-standard."""
    if not text.startswith("---\n"):
        err(skill, "SKILL.md does not start with '---' frontmatter")
        return {}, text
    end = text.find("\n---\n", 3)
    if end == -1:
        err(skill, "frontmatter is never closed with '---'")
        return {}, text
    block, body = text[4:end], text[end + 5:]

    data: dict[str, str] = {}
    key = None
    for line in block.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key = m.group(1)
            data[key] = m.group(2).strip()
        elif key:
            data[key] = (data[key] + " " + line.strip()).strip()
    return data, body


def check_skill(path: Path) -> None:
    # For a repo-root skill the folder name is whatever the clone directory
    # happens to be — the authoritative name lives in skill.json.
    skill = path.name
    if path == REPO:
        meta = path / "skill.json"
        if meta.exists():
            try:
                skill = json.loads(meta.read_text(encoding="utf-8")).get("name", path.name)
            except json.JSONDecodeError:
                pass
    skill_md = path / "SKILL.md"

    if not skill_md.exists():
        err(skill, "no SKILL.md")
        return

    text = skill_md.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text, skill)

    # --- frontmatter ------------------------------------------------------
    name = fm.get("name", "")
    if not name:
        err(skill, "frontmatter has no 'name'")
    else:
        if name != skill:
            err(skill, f"frontmatter name '{name}' != folder name '{skill}'")
        if len(name) > NAME_MAX:
            err(skill, f"name is {len(name)} chars (max {NAME_MAX})")
        if not NAME_RE.match(name):
            err(skill, f"name '{name}' must be lowercase letters, numbers and single hyphens")
        for word in RESERVED:
            if word in name:
                err(skill, f"name contains reserved word '{word}' — uploads are rejected")

    desc = fm.get("description", "")
    if not desc:
        err(skill, "frontmatter has no 'description'")
    else:
        if len(desc) > DESC_MAX:
            err(skill, f"description is {len(desc)} chars (max {DESC_MAX})")
        if len(desc) < 80:
            warn(skill, "description is very short — it is the only thing always in context")
        if "use when" not in desc.lower():
            warn(skill, "description has no 'Use when …' clause; triggering will be unreliable")
        if re.search(r"\b(I |I'll|you can)\b", desc):
            warn(skill, "description is first/second person — write it third person")

    extra = set(fm) - ALLOWED_FM_KEYS
    if extra:
        err(skill, f"non-portable frontmatter keys {sorted(extra)} — move them to skill.json")

    # --- body -------------------------------------------------------------
    lines = body.splitlines()
    if len(lines) > BODY_MAX_LINES:
        err(skill, f"SKILL.md body is {len(lines)} lines (max {BODY_MAX_LINES})")
    elif len(lines) > 300:
        warn(skill, f"SKILL.md body is {len(lines)} lines — consider moving detail into assets/")

    if "## Requires" not in body:
        err(skill, "no '## Requires' section (standard rule 7)")
    if "## Version" not in body:
        err(skill, "no '## Version' section (standard rule 8)")

    if re.search(r"[A-Za-z0-9_]\\[A-Za-z0-9_]", body):
        err(skill, "Windows-style backslash path in body — use forward slashes")
    for bad in ("/home/", "/Users/", "~/Documents", "C:\\"):
        if bad in body:
            err(skill, f"absolute local path '{bad}' in body — will not resolve for a user")

    # Referenced assets must exist, and must be one hop from SKILL.md.
    referenced = set()
    for ref in re.findall(r"`([A-Za-z0-9_./-]+\.(?:md|html|py|json|png|jpg|csv))`", body):
        referenced.add(ref)
    for ref in re.findall(r"\]\(([A-Za-z0-9_./-]+)\)", body):
        referenced.add(ref)
    for ref in sorted(referenced):
        if ref.startswith(("http", "#")):
            continue
        if not (path / ref).exists():
            err(skill, f"SKILL.md references '{ref}' which does not exist")

    # --- skill.json -------------------------------------------------------
    meta_path = path / "skill.json"
    if not meta_path.exists():
        err(skill, "no skill.json (version metadata lives here, not in frontmatter)")
        return
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        err(skill, f"skill.json is not valid JSON: {exc}")
        return

    for field in ("name", "title", "version", "updated", "summary", "requires"):
        if field not in meta:
            err(skill, f"skill.json is missing '{field}'")
    if meta.get("name") not in (None, skill):
        err(skill, f"skill.json name '{meta['name']}' != folder name '{skill}'")
    version = meta.get("version", "")
    if version and not SEMVER_RE.match(version):
        err(skill, f"version '{version}' is not MAJOR.MINOR.PATCH")
    if version and f"v{version}" not in body:
        err(skill, f"body's Version section does not state v{version} — they must match")

    # Orphaned assets are dead weight in every user's download.
    assets = path / "assets"
    if assets.is_dir():
        for f in sorted(assets.rglob("*")):
            if f.is_file():
                rel = f.relative_to(path).as_posix()
                if rel not in referenced and not any(rel in v for v in referenced):
                    warn(skill, f"'{rel}' is never referenced from SKILL.md")


def main() -> int:
    skills = sorted(
        p for p in sorted(set(REPO.glob("plugins/*/skills/*")) | set(REPO.glob("skills/*"))) if p.is_dir() and not p.name.startswith("_")
    )
    # Single-skill repos put SKILL.md at the repo root so GitHub's
    # "Download ZIP" produces a claude.ai-uploadable file. The repo IS the
    # skill, named after itself.
    if (REPO / "SKILL.md").exists():
        skills = [REPO] + skills
    if not skills:
        print("No skills found at repo root, skills/ or plugins/*/skills/")
        return 1

    for path in skills:
        check_skill(path)

    for w in warnings:
        print(f"  warn   {w}")
    for e in errors:
        print(f"  ERROR  {e}")

    print(f"\n{len(skills)} skill(s), {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
