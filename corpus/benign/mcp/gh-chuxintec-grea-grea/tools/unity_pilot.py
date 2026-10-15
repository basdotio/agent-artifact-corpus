#!/usr/bin/env python3
"""Freeze selected Unity authoring inputs and create verified, isolated pilot copies.

This tool never migrates or edits the source project. Snapshots contain local paths
and must remain private when their inputs are private.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
from grea.safe_paths import canonical_path, disjoint, relative_name


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def relative(value):
    return relative_name(value).as_posix()


def safe_root(value):
    return canonical_path(value)


def outside(output, source):
    output = disjoint(output, source)
    if output.exists():
        raise ValueError('Output already exists')
    return output


def inventory(root, includes):
    files = {}
    for name in includes:
        selected = root / relative(name)
        if any(p.is_symlink() for p in (selected, *selected.parents) if p != root and root in p.parents):
            raise ValueError('Symlink input is unsupported')
        top = safe_root(selected)
        if not top.exists():
            raise ValueError('Missing selected input: ' + name)
        # Reject links instead of following them into another project/cache.
        entries = [top, *sorted(top.rglob('*'))] if top.is_dir() else [top]
        for path in entries:
            if path.is_symlink():
                raise ValueError('Symlink input is unsupported')
            if path.is_file():
                rel = path.relative_to(root).as_posix()
                if any(part in {'.git', 'Library', 'Temp', 'Logs', 'Obj', '__pycache__', 'node_modules'} for part in Path(rel).parts):
                    raise ValueError('Do not select generated/cache directories')
                if path.name == '.DS_Store':
                    continue
                files[rel] = {'sha256': sha(path), 'bytes': path.stat().st_size,
                              'executable': bool(path.stat().st_mode & 0o111)}
                if len(files) > 100000:
                    raise ValueError('Snapshot file budget exceeded')
    return dict(sorted(files.items()))


def snapshot(source, unity_root, output, extras=()):
    source = safe_root(source)
    unity = '' if unity_root == '.' else relative(unity_root) + '/'
    includes = [unity + name for name in ('Assets', 'Packages', 'ProjectSettings')] + list(extras)
    output = outside(output, source)
    files = inventory(source, includes)
    result = {'schemaVersion': 1, 'source': str(source), 'unityRoot': unity_root,
              'includes': includes, 'files': files,
              'treeSha256': hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    return {'files': len(files), 'treeSha256': result['treeSha256'], 'sourceWritten': False}


def load(snapshot_path):
    data = json.loads(Path(snapshot_path).read_text())
    if data.get('schemaVersion') != 1 or not isinstance(data.get('files'), dict):
        raise ValueError('Unsupported snapshot')
    for name in data['files']:
        relative(name)
    identity = hashlib.sha256(json.dumps(data['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if identity != data.get('treeSha256'):
        raise ValueError('Snapshot manifest integrity mismatch')
    return data


def verify(snapshot_path, source=None):
    data = load(snapshot_path)
    root = safe_root(source or data['source'])
    actual = inventory(root, data['includes'])
    changed = [name for name in sorted(set(actual) | set(data['files'])) if actual.get(name) != data['files'].get(name)]
    return {'unchanged': not changed, 'files': len(actual), 'changes': changed, 'sourceWritten': False}


def clone(snapshot_path, output):
    data = load(snapshot_path); source = safe_root(data['source']); output = outside(output, source)
    if not verify(snapshot_path)['unchanged']:
        raise ValueError('Source changed since snapshot; no copy created')
    output.mkdir(parents=True)
    for name in data['includes']:
        if (source / name).is_dir():
            (output / name).mkdir(parents=True, exist_ok=True)
    for name, identity in data['files'].items():
        target = output / name; target.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
        with os.fdopen(os.open(source / name, flags), 'rb') as incoming, target.open('xb') as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
        target.chmod(0o755 if identity['executable'] else 0o644)
        if sha(target) != identity['sha256']:
            raise ValueError('Input changed while copying; partial output retained')
    if not verify(snapshot_path)['unchanged'] or not verify(snapshot_path, output)['unchanged']:
        raise ValueError('Copy or source changed; output retained for inspection')
    return {'copied': len(data['files']), 'sourceWritten': False, 'unityExecuted': False,
            'treeSha256': data['treeSha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('snapshot'); p.add_argument('--source', required=True); p.add_argument('--unity-root', default='.'); p.add_argument('--output', required=True); p.add_argument('--include', action='append', default=[])
    for command in ('clone', 'verify'):
        p = sub.add_parser(command); p.add_argument('--snapshot', required=True)
        p.add_argument('--output', required=True) if command == 'clone' else p.add_argument('--source')
    args = parser.parse_args()
    if args.command == 'snapshot': result = snapshot(args.source, args.unity_root, args.output, args.include)
    elif args.command == 'clone': result = clone(args.snapshot, args.output)
    else: result = verify(args.snapshot, args.source)
    print(json.dumps(result, indent=2))
    if result.get('unchanged') is False: raise SystemExit(1)


if __name__ == '__main__': main()
