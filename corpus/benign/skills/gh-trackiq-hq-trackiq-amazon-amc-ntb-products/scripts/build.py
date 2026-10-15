#!/usr/bin/env python3
"""Package every skill for the manual-install path and write the registry.

Produces, in dist/:
    <skill>-<version>.zip   one zip per skill, the thing users upload
    <skill>.zip             a stable "latest" alias for the website button
    registry.json           the catalog the website renders and installed
                            skills check themselves against

The zip contains a single top-level folder named exactly the skill name —
both Claude and ChatGPT reject flat zips and mismatched folder names.

    python scripts/build.py [--base-url https://trackiq.com/skills]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGINS = REPO / "plugins"
DIST = REPO / "dist"

DEFAULT_BASE_URL = "https://trackiq.com/skills"
# Claude's skill upload rejects oversized zips; ChatGPT's limit is 50MB.
# 25MB keeps one artifact valid on both, with room for the email templates.
SIZE_WARN_BYTES = 25 * 1024 * 1024
# Files that are ours, not the user's — excluded from what gets shipped.
EXCLUDE_NAMES = {".DS_Store", "skill.json", "Thumbs.db"}
EXCLUDE_DIRS = {"__pycache__", ".git"}
# When the skill IS the repo root, also strip the plugin manifest, dev
# scripts, CI config and git metadata so the shipped zip is claude.ai-upload
# clean (same files that .gitattributes export-ignores from Download ZIP).
ROOT_EXCLUDE_NAMES = {".gitignore", ".gitattributes", "README.md", "LICENSE"}
ROOT_EXCLUDE_DIRS = {".claude-plugin", ".github", "scripts", "dist"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def files_in(skill_dir: Path) -> list[Path]:
    at_root = skill_dir == REPO
    exclude_names = EXCLUDE_NAMES | ROOT_EXCLUDE_NAMES if at_root else EXCLUDE_NAMES
    exclude_dirs = EXCLUDE_DIRS | ROOT_EXCLUDE_DIRS if at_root else EXCLUDE_DIRS
    out = []
    for p in sorted(skill_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name in exclude_names:
            continue
        if any(part in exclude_dirs for part in p.relative_to(skill_dir).parts):
            continue
        out.append(p)
    return out


def package(skill_dir: Path, name: str, version: str) -> Path:
    zip_path = DIST / f"{name}-{version}.zip"
    # Deterministic: a rebuild of an unchanged skill produces the same hash,
    # so the registry only churns when content actually changed.
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files_in(skill_dir):
            arc = Path(name) / f.relative_to(skill_dir)
            info = zipfile.ZipInfo(arc.as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, f.read_bytes())

    size = zip_path.stat().st_size
    if size > SIZE_WARN_BYTES:
        print(f"  warn   {name}: zip is {size / 1e6:.1f}MB — trim assets/ before publishing")

    shutil.copyfile(zip_path, DIST / f"{name}.zip")
    return zip_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help="public URL that dist/ is served from")
    args = ap.parse_args()
    base = args.base_url.rstrip("/")

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    skill_dirs = sorted(p for p in sorted(set(REPO.glob("plugins/*/skills/*")) | set(REPO.glob("skills/*")))
                        if p.is_dir() and not p.name.startswith("_"))
    # Repo-root skill (SKILL.md at the top) — the repo IS the plugin and
    # the skill, named after itself.
    if (REPO / "SKILL.md").exists():
        skill_dirs = [REPO] + skill_dirs

    entries = []
    for skill_dir in skill_dirs:
        meta_path = skill_dir / "skill.json"
        if not meta_path.exists():
            print(f"  ERROR  {skill_dir.name}: no skill.json — run validate.py")
            return 1
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        # Repo-root skill: the directory name is whatever the checkout
        # happens to be called — trust skill.json for the real name.
        name = meta["name"] if skill_dir == REPO else skill_dir.name
        version = meta["version"]

        zip_path = package(skill_dir, name, version)
        plugin = name if skill_dir == REPO else skill_dir.parent.parent.name

        entries.append({
            "name": name,
            "title": meta.get("title", name),
            "category": meta.get("category", ""),
            "version": version,
            "updated": meta.get("updated", ""),
            "summary": meta.get("summary", ""),
            "changelog": meta.get("changelog", ""),
            "requires": meta.get("requires", {}),
            "fallback": meta.get("fallback", ""),
            "homepage": meta.get("homepage", ""),
            "license": meta.get("license", "MIT"),
            "plugin": plugin,
            "install": {
                # Auto-updating path: git-backed, no user action to stay current.
                "claude_code": f"/plugin marketplace add TrackIQ-HQ/amazon-seller-skills\n/plugin install {plugin}@trackiq",
                # Manual path: identical zip for Claude and ChatGPT uploads.
                "zip": f"{base}/{name}.zip",
                "zip_pinned": f"{base}/{zip_path.name}",
            },
            "sha256": sha256(zip_path),
            "bytes": zip_path.stat().st_size,
        })
        print(f"  built  {name} v{version}  ({zip_path.stat().st_size / 1024:.0f}KB)")

    registry = {
        "$schema": f"{base}/registry.schema.json",
        "generated": date.today().isoformat(),
        "marketplace": "TrackIQ-HQ/amazon-seller-skills",
        "skills": entries,
    }
    (DIST / "registry.json").write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\n{len(entries)} skill(s) -> dist/  (registry.json served at {base}/registry.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
