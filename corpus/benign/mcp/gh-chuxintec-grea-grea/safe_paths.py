"""Portable names and filesystem-identity guards for cooperative local writers.

These checks reject aliases and accidental overwrites; they are not a sandbox
against concurrent hostile changes to parent directories.
"""
import os
from pathlib import Path, PureWindowsPath
import re
import unicodedata


def canonical_path(value):
    path = Path(value).expanduser().absolute()
    if any(p.is_symlink() and not p.exists() for p in (path, *path.parents)):
        raise ValueError('Dangling path symlink')
    if path.is_symlink():
        raise ValueError('Output/root may not itself be a symlink')
    # Resolve caller-selected existing ancestors (including macOS /tmp and /var).
    return path.resolve()


def overlaps(first, second):
    first, second = Path(first).resolve(), Path(second).resolve()
    if first == second or first in second.parents or second in first.parents:
        return True
    for root, other in ((first, second), (second, first)):
        if root.exists():
            for ancestor in (other, *other.parents):
                if ancestor.exists() and os.path.samefile(root, ancestor):
                    return True
    return False


def disjoint(output, *sources):
    output = canonical_path(output)
    if any(overlaps(output, source) for source in sources):
        raise ValueError('Output must be disjoint from source inputs')
    return output


def relative_name(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Expected a portable relative path')
    path = PureWindowsPath(value)
    parts = value.split('/')
    if path.drive or path.root or any(
        p in ('', '.', '..') or p.endswith((' ', '.'))
        or re.search(r'[<>:"|?*\x00-\x1f\x7f]', p)
        or re.fullmatch(r'(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?', p, re.I)
        for p in parts
    ):
        raise ValueError('Unsafe portable path: ' + repr(value))
    return Path(*parts)


def collision_key(path):
    return unicodedata.normalize('NFC', Path(path).as_posix()).casefold()


def unique_paths(paths):
    """Reject duplicate files, portable aliases and file/directory conflicts."""
    keys = set()
    spellings = {}
    for path in paths:
        path = relative_name(Path(path).as_posix())
        key = collision_key(path)
        if key in keys or any(parent in keys for parent in [collision_key(p) for p in path.parents if str(p) != '.']):
            raise ValueError('Duplicate or overlapping output path: ' + str(path))
        if any(other.startswith(key + '/') for other in keys):
            raise ValueError('File/directory output conflict: ' + str(path))
        for part in (path, *path.parents):
            if str(part) == '.':
                continue
            normalized = collision_key(part)
            if normalized in spellings and spellings[normalized] != part.as_posix():
                raise ValueError('Case/Unicode path alias: ' + str(part))
            spellings[normalized] = part.as_posix()
        keys.add(key)


def write_bytes_new(path, data):
    with Path(path).open('xb') as stream:
        stream.write(data)
