"""Copy selected static files without transforming them; no build or runtime validation.

Output must be new or empty and disjoint from source. All mappings are checked
before writing. This is a local copy helper, not a transactional filesystem or
an adversarial concurrent-writer sandbox. A copy-time failure retains partial output.
"""
import argparse
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import sys
from grea.safe_paths import overlaps as _overlap, relative_name, unique_paths


def _relative(value):
    return relative_name(value)


def _tree(path):
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise ValueError('Symlink: ' + str(path))
    if stat.S_ISDIR(mode):
        for child in path.iterdir():
            _tree(child)
    elif not stat.S_ISREG(mode):
        raise ValueError('Not a regular file: ' + str(path))


def _empty_output(path):
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError('Output must be new or empty')


def _copy(input_path, destination):
    mode = input_path.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise ValueError('Source became a symlink during copy')
    if stat.S_ISDIR(mode):
        destination.mkdir()  # Never merge with another writer's directory.
        for child in input_path.iterdir():
            _copy(child, destination / child.name)
        destination.chmod(stat.S_IMODE(mode))
    elif stat.S_ISREG(mode):
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(input_path, flags), 'rb') as incoming, destination.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing)
        destination.chmod(stat.S_IMODE(mode))
    else:
        raise ValueError('Not a regular file: ' + str(input_path))


def copy_assets(source, output, mappings):
    source = Path(source).resolve(strict=True)
    raw_output = Path(output).absolute()
    if any(p.is_symlink() and not p.exists() for p in (raw_output, *raw_output.parents)):
        raise ValueError('Dangling output symlink')
    output = raw_output.resolve()
    if not source.is_dir():
        raise ValueError('Source must be a directory')
    if _overlap(source, output):
        raise ValueError('Source and output must be disjoint')
    _empty_output(output)
    if not mappings:
        raise ValueError('At least one FROM=TO mapping is required')
    selected = []
    for mapping in mappings:
        if '=' not in mapping:
            raise ValueError('Expected FROM=TO: ' + mapping)
        original, target = mapping.split('=', 1)
        from_path, to_path = _relative(original), _relative(target)
        input_path, destination = source / from_path, output / to_path
        current = source
        for part in from_path.parts:
            current = current / part
            if stat.S_ISLNK(current.lstat().st_mode):
                raise ValueError('Symlink in source path: ' + str(current))
        _tree(input_path)
        if any(_overlap(destination, previous[1]) for previous in selected):
            raise ValueError('Overlapping destination mappings')
        selected.append((input_path, destination, original, target))
    unique_paths([item[3] for item in selected])
    # Recheck after preflight; do not overwrite intervening user output.
    _empty_output(output)
    output.mkdir(parents=True, exist_ok=True)
    for input_path, destination, _, _ in selected:
        destination.parent.mkdir(parents=True, exist_ok=True)
        _copy(input_path, destination)
    return {'output': str(output),
            'mappings': [{'from': original, 'to': target} for _, _, original, target in selected],
            'validation': 'copy-only; browser and original-game acceptance still required'}


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--map', action='append', required=True, dest='mappings', metavar='FROM=TO')
    try:
        args = parser.parse_args(argv)
        print(json.dumps(copy_assets(args.source, args.output, args.mappings), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
