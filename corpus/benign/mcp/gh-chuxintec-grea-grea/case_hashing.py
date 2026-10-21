"""Bounded file identity checks shared by legacy and revisioned case readers."""
from contextlib import contextmanager
from contextvars import ContextVar
from grea.host.paths import Path

from .common import GreaError, hash_file as raw_hash_file


_ACTIVE_AUDIT = ContextVar('case_hash_audit', default=None)


def hash_file(path):
    audit = _ACTIVE_AUDIT.get()
    if audit is None:
        return raw_hash_file(path, max_bytes=8 * 1024**3)
    path = Path(path).absolute()
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns, stat.st_ino)
    if key in audit['cache']:
        audit['reused'] += 1
        return audit['cache'][key]
    value = raw_hash_file(path, max_bytes=audit['limit'] - audit['bytes'])
    audit['bytes'] += value['bytes']
    audit['cache'][key] = value
    return value


@contextmanager
def audit_hashes(max_bytes):
    if type(max_bytes) is not int or not 1 <= max_bytes <= 64 * 1024**3:
        raise GreaError('INVALID_BUDGET', 'Hash budget must be 1 byte through 64 GiB.')
    audit = {'limit': max_bytes, 'bytes': 0, 'cache': {}, 'reused': 0}
    token = _ACTIVE_AUDIT.set(audit)
    try:
        yield audit
    finally:
        _ACTIVE_AUDIT.reset(token)


def audit_report(audit):
    return {
        'budget_bytes': audit['limit'], 'hashed_bytes': audit['bytes'],
        'hashed_files': len(audit['cache']), 'reused_within_call': audit['reused'],
        'persistent_cache': False, 'complete': True,
    }
