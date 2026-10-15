"""Local, read-only inventories and exclusive reports shared by artifact tools."""
import fnmatch
import hashlib
import json
import os
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def directory(path):
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"Not a real directory: {path}")
    return path.resolve()


def validate_output(path, sources=()):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise ValueError(f"Output exists: {path}")
    if not path.parent.is_dir():
        raise ValueError(f"Output parent must exist: {path.parent}")
    path = path.parent.resolve() / path.name
    for source in sources:
        source = Path(source).resolve()
        if path == source or (source.is_dir() and source in path.parents):
            raise ValueError("Output must be outside source evidence")
    return path


def write_report(report, output=None, sources=()):
    content = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if output:
        output = validate_output(output, sources)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(content)
    else:
        print(content, end="")


def inventory(root, exclude=()):
    root = directory(root)
    for pattern in exclude:
        if not pattern or pattern.startswith("/") or ".." in pattern.split("/"):
            raise ValueError("Exclusions must be nonempty relative glob patterns")
    files = {}
    for base, dirs, names in os.walk(root, followlinks=False):
        for name in sorted(dirs + names):
            path = Path(base) / name
            if path.is_symlink():
                raise ValueError(f"Symlink refused: {path}")
        for name in sorted(names):
            path = Path(base) / name
            rel = path.relative_to(root).as_posix()
            if any(fnmatch.fnmatchcase(rel, pattern) for pattern in exclude):
                continue
            if not path.is_file():
                raise ValueError(f"Nonregular file refused: {path}")
            stat = path.stat()
            checksum = digest(path)
            after = path.stat()
            if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError(f"Source changed during hashing: {path}")
            files[rel] = {"bytes": stat.st_size, "sha256": checksum}
    return dict(sorted(files.items()))


def compare(expected, actual):
    missing = sorted(expected.keys() - actual.keys())
    extra = sorted(actual.keys() - expected.keys())
    changed = sorted(k for k in expected.keys() & actual.keys() if expected[k] != actual[k])
    return {"equal": not (missing or extra or changed),
            "expected_files": len(expected), "actual_files": len(actual),
            "missing": missing, "extra": extra, "changed": changed}
