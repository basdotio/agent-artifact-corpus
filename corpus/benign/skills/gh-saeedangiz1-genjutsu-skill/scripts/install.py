#!/usr/bin/env python3
"""Install this self-contained skill without copying private runtime state."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

SKILL_NAME = "genjutsu-video-workflow"
MANIFEST = ".genjutsu-install.json"
SKIP_DIRS = {".git", ".venv", ".venv-face", "venv", "node_modules", "__pycache__",
             ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache", "runs", "outputs",
             "private", "secrets", "downloads", "models", "dist", "build", ".idea", ".vscode"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".log", ".mp4", ".mov", ".webm", ".mkv", ".mp3", ".wav",
                 ".zip", ".pem", ".key", ".p12", ".pfx", ".download", ".part"}
REQUIRED = ("SKILL.md", "scripts/install.py", "scripts/runtime.py", "scripts/check.py",
            "assets/workflow/workflow.py", "assets/workflow/requirements.txt")


def excluded(path: Path) -> bool:
    """Publication filter shared with the local integrity checker."""
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return (bool(parts & SKIP_DIRS) or path.suffix.lower() in SKIP_SUFFIXES
            or (name.startswith(".env") and name != ".env.example")
            or name.startswith((".runtime", "credential", "token", "secret", "capture-"))
            or name in {MANIFEST, ".ds_store", "thumbs.db"})


def skill_identity(root: Path) -> str:
    path = root / "SKILL.md"
    if not path.is_file() or path.is_symlink():
        raise ValueError("Source/target must contain a regular SKILL.md file.")
    text = path.read_text(encoding="utf-8-sig")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md needs YAML frontmatter.")
    frontmatter = text.split("---", 2)[1]
    name = re.search(r"^name:\s*['\"]?([a-z0-9-]+)['\"]?\s*$", frontmatter, re.MULTILINE)
    description = re.search(r"^description:\s*\S", frontmatter, re.MULTILINE)
    if not name or not description:
        raise ValueError("SKILL.md requires name and description frontmatter fields.")
    return name.group(1)


def source_files(root: Path) -> list[Path]:
    if skill_identity(root) != SKILL_NAME:
        raise ValueError(f"Expected skill name {SKILL_NAME}.")
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in list(dirs):
            rel = (base / name).relative_to(root)
            if excluded(rel):
                dirs.remove(name)
            elif (base / name).is_symlink() or getattr(base / name, "is_junction", lambda: False)():
                raise ValueError(f"Published resources cannot be symbolic links/junctions: {rel}")
        for name in names:
            path = base / name
            rel = path.relative_to(root)
            if excluded(rel):
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Published resource must be a regular file: {rel}")
            files.append(rel)
    missing = set(REQUIRED) - {p.as_posix() for p in files}
    if missing:
        raise ValueError("Incomplete skill; missing: " + ", ".join(sorted(missing)))
    return sorted(files, key=lambda p: p.as_posix())


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def checked_target(source: Path, target: Path) -> Path:
    raw = target.expanduser().absolute()
    if raw.is_symlink() or getattr(raw, "is_junction", lambda: False)():
        raise ValueError("Target cannot be a symbolic link or junction.")
    target = raw.resolve()
    source = source.resolve()
    home = Path.home().resolve()
    if target == Path(target.anchor) or target == home or target in home.parents:
        raise ValueError("Target must be a dedicated skill directory, never a filesystem/home root.")
    if target == source or target in source.parents or source in target.parents:
        raise ValueError("Source and target must be separate, non-nested directories.")
    if target.name.lower() in SKIP_DIRS or target.name.lower() == "skills":
        raise ValueError("Target must identify one skill, not a discovery root or private state directory.")
    if target.exists() and not target.is_dir():
        raise ValueError("Target exists and is not a directory.")
    return target


def read_manifest(target: Path) -> dict[str, str]:
    path = target / MANIFEST
    if path.is_symlink():
        raise ValueError("Install manifest cannot be a symbolic link.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("Existing nonempty target is unmanaged; choose an empty/new skill directory.") from None
    if data.get("skill") != SKILL_NAME or not isinstance(data.get("files"), dict):
        raise ValueError("Existing target does not have a matching installer manifest.")
    result = data["files"]
    for name, value in result.items():
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or ":" in name or "\\" in name or excluded(rel):
            raise ValueError("Unsafe path in existing install manifest.")
        if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("Invalid checksum in existing install manifest.")
    return result


def install(source: Path, target: Path, replace: bool = False) -> tuple[Path, int]:
    source = source.expanduser().resolve()
    target = checked_target(source, target)
    files = source_files(source)
    hashes = {rel.as_posix(): digest(source / rel) for rel in files}
    previous = {}
    existing = target.exists() and any(target.iterdir())
    if existing:
        if skill_identity(target) != SKILL_NAME:
            raise ValueError("Target belongs to another skill; unrelated files will not be overwritten.")
        previous = read_manifest(target)
        for name in previous:
            previous_path = target / name
            if target not in previous_path.resolve().parents or previous_path.is_symlink():
                raise ValueError('Existing managed resource escapes the skill directory: ' + name)
        for rel in files:
            destination = target / rel
            if target not in destination.resolve().parents:
                raise ValueError(f"Target resource escapes the skill directory: {rel}")
            if destination.is_symlink() or (destination.exists() and not destination.is_file()):
                raise ValueError(f"Target resource is not a regular file: {rel}")
            if destination.exists() and rel.as_posix() not in previous:
                raise ValueError(f"Unmanaged target resource will not be overwritten: {rel}")
        changed = hashes != previous or any(
            not (target / name).is_file() or digest(target / name) != value
            for name, value in hashes.items())
        if changed and not replace:
            raise ValueError("Existing skill differs. Use --replace to update installer-owned resources.")
        if not changed:
            return target, 0
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".genjutsu-stage-", dir=target.parent) as temporary:
        stage = Path(temporary) / "skill"
        stage.mkdir()
        for rel in files:
            (stage / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / rel, stage / rel)
        (stage / MANIFEST).write_text(json.dumps({"skill": SKILL_NAME, "files": hashes}, indent=2) + "\n", encoding="utf-8")
        if not existing:
            if target.exists():
                target.rmdir()  # Verified empty above; fails safely if another process added anything.
            stage.replace(target)
        else:
            # Update only tracked resources. Keep local .env, runs, caches, and unrelated files intact.
            for rel in files:
                destination = target / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                (stage / rel).replace(destination)
            for name in previous.keys() - hashes.keys():
                old = target / name
                if old.is_file() and not old.is_symlink() and digest(old) == previous[name]:
                    old.unlink()  # Remove only unchanged, obsolete installer-owned resources.
            (stage / MANIFEST).replace(target / MANIFEST)
    return target, len(files)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("claude", "codex"), default="claude", help="Discovery directory for the default target (default: claude).")
    parser.add_argument("--target", type=Path, help="Dedicated destination skill directory; supports spaces.")
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1], help=argparse.SUPPRESS)
    parser.add_argument("--replace", action="store_true", help="Update an existing managed installation; preserve secrets and local runs.")
    args = parser.parse_args(argv)
    target = args.target or Path.home() / (".claude" if args.agent == "claude" else ".codex") / "skills" / SKILL_NAME
    try:
        destination, count = install(args.source, target, args.replace)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Install failed: {exc}\n")
    print(f"{'Installed ' + str(count) + ' resources' if count else 'Already up to date'}: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
