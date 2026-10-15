#!/usr/bin/env python3
"""Measure explicitly selected instruction files without changing or printing them."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys
from typing import BinaryIO

MAX_FILES = 64
MAX_FILE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024

INSTRUCTION_NAMES = {
    "AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "CLAUDE.local.md",
    "GEMINI.md", "SKILL.md", "copilot-instructions.md", ".cursorrules",
}
PRIVATE_LOCATIONS = {".git", ".ssh", ".aws", ".gnupg", ".kube"}
PRIVATE_NAMES = {".envrc", ".netrc", ".npmrc", ".pypirc", "kubeconfig"}
PRIVATE_SUFFIXES = {".env", ".pem", ".key", ".p12", ".pfx", ".keystore"}
PRIVATE_PATTERN = re.compile(
    r"^(?:secrets?|credentials?|passwords?|private[-_]?keys?|"
    r"api[-_]?keys?|access[-_]?tokens?|auth[-_]?tokens?|id_rsa|id_ed25519)"
    r"(?:[._-]|$)", re.IGNORECASE,
)


class MeasurementError(ValueError):
    """A selected input cannot be measured under this helper's contract."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default error can repeat arbitrary values supplied by callers.
        raise MeasurementError("Invalid arguments; run measure.py --help for usage.")


def _private_component(part: str) -> bool:
    lowered = part.lower()
    return bool(
        lowered in PRIVATE_LOCATIONS or lowered in PRIVATE_NAMES
        or lowered == ".env" or lowered.startswith(".env.")
        or Path(lowered).suffix in PRIVATE_SUFFIXES or PRIVATE_PATTERN.match(lowered)
    )


def _relative_path(value: str) -> PurePosixPath:
    if (not value or "\\" in value or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or PurePosixPath(value).is_absolute() or PureWindowsPath(value).drive
            or ".." in value.split("/")):
        raise MeasurementError("Use root-relative paths with forward slashes and no traversal.")
    path = PurePosixPath(value)
    if not path.parts:
        raise MeasurementError("Select a file, not the root directory.")
    if any(_private_component(part) for part in path.parts):
        raise MeasurementError("Secret-like files and private configuration paths are excluded.")
    return path


def _is_instruction(root: Path, path: PurePosixPath) -> bool:
    if (path.name in INSTRUCTION_NAMES or path.name.endswith(".instructions.md")
            or path.suffix == ".mdc"):
        return True
    parts = root.parts + path.parts
    return path.suffix == ".md" and any(
        parts[index:index + 2] == (".claude", "rules")
        for index in range(len(parts) - 2)
    )


def _is_link(info: os.stat_result) -> bool:
    # Windows junctions are reparse points; reject those too.
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _checked_path(root: Path, path: PurePosixPath) -> Path:
    current = root
    for index, part in enumerate(path.parts):
        current = current / part
        info = current.lstat()
        if _is_link(info):
            raise MeasurementError(f"Symlinks are excluded: {path.as_posix()}")
        if index < len(path.parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise MeasurementError(f"A parent is not a directory: {path.as_posix()}")
    if not stat.S_ISREG(info.st_mode):
        raise MeasurementError(f"Select a regular file: {path.as_posix()}")
    if not current.resolve(strict=True).is_relative_to(root):
        raise MeasurementError("Selected files must stay inside the root.")
    return current


def _open_file(root: Path, path: PurePosixPath, checked: Path) -> BinaryIO:
    # On platforms with openat support, refuse symlinks during the directory walk
    # as well as during the earlier validation. No directory names are discovered.
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if os.open in os.supports_dir_fd and nofollow and directory:
        descriptor = os.open(root, os.O_RDONLY | directory | nofollow)
        try:
            for part in path.parts[:-1]:
                child = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            file_descriptor = os.open(
                path.name, os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0),
                dir_fd=descriptor,
            )
        finally:
            os.close(descriptor)
        return os.fdopen(file_descriptor, "rb")
    # Without descriptor-relative no-follow opens, before/after checks cannot
    # eliminate path replacement races. This fallback needs a stable, trusted tree.
    return checked.open("rb")


def _counts(text: str) -> dict[str, int]:
    return {
        "bytes": len(text.encode("utf-8")),
        "characters": len(text),
        "estimated_tokens": (len(text) + 3) // 4,
    }


def _frontmatter(text: str) -> dict:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n").lstrip("\ufeff") != "---":
        return {"status": "absent", "metadata": _counts(""), "body": _counts(text)}
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") in {"---", "..."}:
            return {
                "status": "delimited",
                "metadata": _counts("".join(lines[:index + 1])),
                "body": _counts("".join(lines[index + 1:])),
            }
    return {
        "status": "malformed",
        "diagnostic": "Opening frontmatter delimiter has no closing delimiter; sections not estimated.",
    }


def measure_files(root: Path | str, selections: list[str], *, allow_reference: bool = False) -> dict:
    """Measure each normalized path once; distinct hardlink paths retain their roles."""
    if not selections or len(selections) > MAX_FILES:
        raise MeasurementError(f"Select between 1 and {MAX_FILES} input paths.")
    try:
        supplied_root = Path(root)
        if _is_link(supplied_root.lstat()) or not supplied_root.is_dir():
            raise MeasurementError("Root must be a real directory, not a symlink.")
        real_root = supplied_root.resolve(strict=True)
        if any(_private_component(part) for part in real_root.parts):
            raise MeasurementError("Secret-like and private configuration locations cannot be used as the root.")
    except OSError:
        raise MeasurementError("Root is unavailable or is not a readable directory.") from None

    paths = sorted({_relative_path(value) for value in selections}, key=str)
    duplicates_skipped = len(selections) - len(paths)
    results = []
    total_bytes = 0
    for path in paths:
        if not _is_instruction(real_root, path) and not (allow_reference and path.suffix == ".md"):
            raise MeasurementError(
                f"Unrecognized instruction filename: {path.as_posix()}; "
                "use --allow-reference for an explicitly selected Markdown reference."
            )
        try:
            checked = _checked_path(real_root, path)
            with _open_file(real_root, path, checked) as stream:
                before = os.fstat(stream.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise MeasurementError(f"Select a regular file: {path.as_posix()}")
                identity = (before.st_dev, before.st_ino)
                if before.st_size > MAX_FILE_BYTES:
                    raise MeasurementError(f"File exceeds {MAX_FILE_BYTES} bytes: {path.as_posix()}")
                raw = stream.read(MAX_FILE_BYTES + 1)
                after = os.fstat(stream.fileno())
                current = _checked_path(real_root, path).stat()
                if (before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
                        or identity != (current.st_dev, current.st_ino)):
                    raise MeasurementError(f"File changed while being read: {path.as_posix()}")
        except OSError:
            raise MeasurementError(f"File or parent is unavailable: {path.as_posix()}") from None
        if len(raw) > MAX_FILE_BYTES:
            raise MeasurementError(f"File exceeds {MAX_FILE_BYTES} bytes: {path.as_posix()}")
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_BYTES:
            raise MeasurementError(f"Selected files exceed {MAX_TOTAL_BYTES} total bytes.")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise MeasurementError(f"File is not valid UTF-8: {path.as_posix()}") from None
        item = {"path": path.as_posix(), **_counts(text), "sha256": hashlib.sha256(raw).hexdigest()}
        if path.name == "SKILL.md":
            item["frontmatter"] = _frontmatter(text)
        results.append(item)
    totals = {key: sum(item[key] for item in results) for key in ("bytes", "characters", "estimated_tokens")}
    return {
        "schema_version": 1,
        "scope": "selected_files_only",
        "deduplication": "normalized_paths_only",
        "token_estimate_method": "ceil(characters / 4) per file; total sums file estimates",
        "caveat": "Estimates are not live session token usage. Frontmatter delimiters do not validate YAML.",
        "files": results,
        "totals": {"files": len(results), **totals},
        "duplicates_skipped": duplicates_skipped,
    }


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser(prog="measure.py", description=__doc__)
    parser.add_argument("--root", required=True, type=Path, help="Directory containing every selected file")
    parser.add_argument("--allow-reference", action="store_true", help="Also accept explicitly selected .md references")
    parser.add_argument("--json", action="store_true", help="Print stable JSON with root-relative paths")
    parser.add_argument("files", nargs="+", help="Explicit root-relative file paths; no glob expansion or discovery")
    try:
        args = parser.parse_args(argv)
        report = measure_files(args.root, args.files, allow_reference=args.allow_reference)
    except MeasurementError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print("Selected-file estimates: ceil(characters / 4) per file, summed for the total.")
        print(report["caveat"])
        for item in report["files"]:
            print(f"{item['path']}: {item['characters']} characters, {item['bytes']} bytes, ~{item['estimated_tokens']} tokens")
            print(f"  SHA256: {item['sha256']}")
            if "frontmatter" in item:
                sections = item["frontmatter"]
                if sections["status"] == "malformed":
                    print(f"  Frontmatter: {sections['diagnostic']}")
                else:
                    print(f"  Frontmatter ({sections['status']}): ~{sections['metadata']['estimated_tokens']} tokens; "
                          f"body: ~{sections['body']['estimated_tokens']} tokens")
        total = report["totals"]
        print(f"Total: {total['files']} files, {total['characters']} characters, "
              f"{total['bytes']} bytes, ~{total['estimated_tokens']} tokens")
        print(f"Repeated normalized paths skipped: {report['duplicates_skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
