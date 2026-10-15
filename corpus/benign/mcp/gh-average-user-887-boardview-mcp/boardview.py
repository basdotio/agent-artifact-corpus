"""GenCAD connectivity reader. No inferred connections or transformed pin geometry."""
from __future__ import annotations

import hashlib
import math
import shlex
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAX_BYTES = 32 * 1024 * 1024
EXTENSIONS = {'.cad', '.gcd', '.brd', '.bdv', '.bvr', '.fz', '.tvw'}


def tokens(line: str) -> list[str]:
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    lexer.escape = ''  # Preserve Windows source paths in quoted header attributes.
    return list(lexer)


def number(value: str) -> float:
    n = float(value)
    if not math.isfinite(n):
        raise ValueError('Non-finite coordinate')
    return n


def page(items: list, offset: int, limit: int) -> dict:
    if offset < 0 or not 1 <= limit <= 100:
        raise ValueError('offset must be >= 0; limit must be 1..100')
    end = offset + limit
    return {'total': len(items), 'offset': offset, 'items': items[offset:end],
            'next_offset': end if end < len(items) else None}


@dataclass
class Board:
    path: Path
    sha256: str
    header: dict = field(default_factory=dict)
    components: dict = field(default_factory=dict)
    shapes: dict = field(default_factory=dict)
    devices: dict = field(default_factory=dict)
    nets: dict = field(default_factory=dict)
    connections: dict = field(default_factory=dict)

    def evidence(self) -> dict:
        return {'path': str(self.path), 'sha256': self.sha256, 'format': 'GenCAD 1.4',
                'units': self.header.get('UNITS'),
                'coordinate_frame': 'Raw file coordinates; pin coordinates are shape-local. No bottom-side or rotation transform applied.',
                'compatibility': 'Board/revision and physical hardware compatibility are not certified.'}

    def component(self, ref: str) -> dict:
        if ref not in self.components:
            raise ValueError(f'Unknown exact component reference: {ref}')
        c = self.components[ref]
        return {**c, 'device_fields': self.devices.get(c.get('device'), {}),
                'pin_count': len(self.shapes[c['shape']])}

    def pins(self, ref: str) -> list[dict]:
        c = self.component(ref)
        return [{**p, 'component': ref,
                 'net': self.connections.get((ref, name), {}).get('net'),
                 'signal_line': self.connections.get((ref, name), {}).get('line'),
                 'connectivity_status': 'declared' if (ref, name) in self.connections else 'not_declared'}
                for name, p in self.shapes[c['shape']].items()]


def parse(path: Path, data: bytes) -> Board:
    if len(data) > MAX_BYTES:
        raise ValueError('Board exceeds 32 MiB limit')
    if not data.lstrip(b'\xef\xbb\xbf \r\n').startswith(b'$HEADER') or b'GENCAD 1.4' not in data[:4096]:
        raise ValueError('Unsupported format: only text GenCAD 1.4 is implemented; FZ/TVW/other BRD/BDV/BVR and PDF are not parsed')
    try:
        text = data.decode('utf-8-sig')
        encoding = 'utf-8-sig'
    except UnicodeDecodeError:
        text = data.decode('cp1252')
        encoding = 'cp1252'
    if '\x00' in text:
        raise ValueError('Binary content in GenCAD input')
    board = Board(path, hashlib.sha256(data).hexdigest())
    board.header['encoding'] = encoding
    section = None
    seen: set[str] = set()
    current: Any = None
    selected = {'HEADER', 'SHAPES', 'COMPONENTS', 'DEVICES', 'SIGNALS'}
    relevant = {'GENCAD', 'DRAWING', 'REVISION', 'UNITS', 'ORIGIN', 'ATTRIBUTE',
                'SHAPE', 'PIN', 'COMPONENT', 'PLACE', 'LAYER', 'ROTATION',
                'DEVICE', 'PART', 'VALUE', 'PACKAGE', 'SIGNAL', 'NODE'}
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if len(line) > 16384:
            raise ValueError(f'Line {lineno} exceeds 16 KiB limit')
        if not line or line.startswith('#'):
            continue
        if line.startswith('$'):
            marker = line[1:]
            if marker.startswith('END'):
                if section != marker[3:]:
                    raise ValueError(f'Mismatched section at line {lineno}')
                seen.add(section)
                section = None
            else:
                if section is not None or marker in seen:
                    raise ValueError(f'Nested or duplicate section at line {lineno}')
                section = marker
            current = None
            continue
        if section not in selected:
            continue
        key = line.split(None, 1)[0]
        if key not in relevant or (key == 'ATTRIBUTE' and section != 'HEADER'):
            continue
        try:
            t = tokens(line)
            if any(len(v) > 2048 for v in t):
                raise ValueError('Field exceeds 2048 characters')
            if section == 'HEADER':
                if key == 'ATTRIBUTE':
                    board.header.setdefault('attributes', []).append(t[1:])
                else:
                    board.header[key] = t[1:]
            elif section == 'SHAPES':
                if key == 'SHAPE':
                    if t[1] in board.shapes:
                        raise ValueError('Duplicate shape')
                    current = board.shapes[t[1]] = {}
                elif key == 'PIN':
                    if current is None or t[1] in current:
                        raise ValueError('Orphan or duplicate shape pin')
                    current[t[1]] = {'pin': t[1], 'padstack': t[2],
                                     'local_x': number(t[3]), 'local_y': number(t[4]),
                                     'shape_layer': t[5], 'line': lineno}
            elif section == 'COMPONENTS':
                if key == 'COMPONENT':
                    if t[1] in board.components:
                        raise ValueError('Duplicate component')
                    current = board.components[t[1]] = {'reference': t[1], 'line': lineno}
                else:
                    if current is None:
                        raise ValueError('Orphan component field')
                    if key == 'PLACE':
                        current.update(x=number(t[1]), y=number(t[2]))
                    elif key == 'LAYER':
                        current['side'] = t[1]
                    elif key == 'ROTATION':
                        current['rotation_degrees'] = number(t[1])
                    elif key == 'SHAPE':
                        current.update(shape=t[1], shape_flags=t[2:])
                    elif key == 'DEVICE':
                        current['device'] = t[1]
            elif section == 'DEVICES':
                if key == 'DEVICE':
                    if t[1] in board.devices:
                        raise ValueError('Duplicate device')
                    current = board.devices[t[1]] = {}
                elif key in {'PART', 'VALUE', 'PACKAGE'}:
                    if current is None:
                        raise ValueError('Orphan device field')
                    current[key.lower()] = ' '.join(t[1:])
            elif section == 'SIGNALS':
                if key == 'SIGNAL':
                    current = t[1]
                    if current in board.nets:
                        raise ValueError('Duplicate signal')
                    board.nets[current] = []
                elif key == 'NODE':
                    if current is None or (t[1], t[2]) in board.connections:
                        raise ValueError('Orphan or multiply assigned signal node')
                    node = {'component': t[1], 'pin': t[2], 'line': lineno}
                    board.nets[current].append(node)
                    board.connections[(t[1], t[2])] = {'net': current, 'line': lineno}
        except (IndexError, ValueError) as exc:
            raise ValueError(f'Invalid GenCAD record at line {lineno}: {exc}') from exc
    if section is not None or not selected.issubset(seen):
        raise ValueError('Truncated GenCAD or missing required sections')
    if board.header.get('GENCAD') != ['1.4'] or not board.header.get('UNITS'):
        raise ValueError('Unsupported GenCAD version or missing units')
    if not board.components or not board.nets:
        raise ValueError('No components or signals found')
    for ref, c in board.components.items():
        if not {'x', 'y', 'shape', 'side', 'rotation_degrees'}.issubset(c) or c['shape'] not in board.shapes:
            raise ValueError(f'Incomplete component or undefined shape: {ref}')
    for ref, pin in board.connections:
        if ref not in board.components or pin not in board.shapes[board.components[ref]['shape']]:
            raise ValueError(f'Signal references undefined component/pin: {ref}.{pin}')
    return board


class Library:
    def __init__(self, roots: list[Path]):
        self.roots = [p.resolve(strict=True) for p in roots]
        if not self.roots or any(not p.is_dir() for p in self.roots):
            raise ValueError('At least one existing directory root is required')
        self.cache: OrderedDict[tuple[str, str], Board] = OrderedDict()

    def resolve(self, name: str) -> Path:
        p = Path(name)
        if not p.is_absolute():
            if len(self.roots) != 1:
                raise ValueError('Use an absolute path when multiple roots are configured')
            p = self.roots[0] / p
        p = p.resolve(strict=True)
        if not any(p.is_relative_to(root) for root in self.roots):
            raise ValueError('Path is outside configured boardview roots')
        if not p.is_file() or p.suffix.lower() not in EXTENSIONS:
            raise ValueError('Path must be a boardview file with an allowed extension')
        return p

    def load(self, name: str) -> Board:
        p = self.resolve(name)
        # Re-read and hash on every query so external edits cannot reuse stale evidence.
        with p.open('rb') as f:
            data = f.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('Board exceeds 32 MiB limit')
        key = (str(p), hashlib.sha256(data).hexdigest())
        if key not in self.cache:
            self.cache[key] = parse(p, data)
        self.cache.move_to_end(key)
        while len(self.cache) > 2:
            self.cache.popitem(last=False)
        return self.cache[key]

    def catalog(self, query: str = '', offset: int = 0, limit: int = 50) -> dict:
        rows = []
        for root in self.roots:
            for p in sorted(root.rglob('*')):
                if p.suffix.lower() not in EXTENSIONS or query.casefold() not in p.name.casefold():
                    continue
                try:
                    p = self.resolve(str(p))
                    with p.open('rb') as f:
                        head = f.read(4096)
                    rows.append({'path': str(p), 'bytes': p.stat().st_size,
                                 'format_candidate': 'GenCAD 1.4' if b'GENCAD 1.4' in head else 'unsupported',
                                 'validation': 'header inspected only; call board_info to validate'})
                except (ValueError, OSError):
                    continue
        return page(list({r['path']: r for r in rows}.values()), offset, limit)
