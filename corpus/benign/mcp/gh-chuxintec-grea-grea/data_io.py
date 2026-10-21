"""Engine-independent bounded JSON and byte identities for offline tools."""
import hashlib
import json
import math
from grea.host.paths import Path


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def budget(value, max_depth=32, max_nodes=100000):
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if depth > max_depth or count > max_nodes:
            raise ValueError('JSON depth or node budget exceeded')
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('Non-finite JSON number')
        if isinstance(item, str):
            item.encode('utf-8')  # Reject unpaired surrogates before generating files.
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, dict):
            pending.extend((child, depth + 1) for pair in item.items() for child in pair)


def decode(raw, max_nodes=100000, max_depth=32):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError('Non-finite JSON constant: ' + value)

    value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=invalid_constant)
    budget(value, max_depth=max_depth, max_nodes=max_nodes)
    return value


def read_bytes(path, max_bytes=8 * 1024 * 1024):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('Expected a regular input without links')
    before = path.stat()
    if before.st_size > max_bytes:
        raise ValueError('JSON input byte budget exceeded')
    with path.open('rb') as stream:
        raw = stream.read(max_bytes + 1)
    after = path.stat()
    if len(raw) > max_bytes or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('Input changed or exceeded budget during read')
    return raw


def load(path, max_bytes=8 * 1024 * 1024, max_nodes=100000):
    raw = read_bytes(path, max_bytes)
    return decode(raw, max_nodes), sha(raw)
