"""Complete response bodies and mechanical metadata in a private local store."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import uuid


class EvidenceStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        if self.root.is_symlink():
            raise ValueError('evidence root must not be a symlink')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == 'posix' and self.root.stat().st_mode & 0o077:
            raise ValueError('evidence root must be private (mode 0700)')

    def _path(self, identity, suffix):
        if not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{32}', identity):
            raise ValueError('invalid evidence id')
        return self.root / (identity + suffix)

    def save(self, body: bytes, metadata: dict) -> dict:
        identity = uuid.uuid4().hex
        receipt = dict(id=identity, bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                       uri=f'soar-evidence://{identity}/body')
        for suffix, content in (('.body', body), ('.json', json.dumps(
                dict(metadata=metadata, evidence=receipt), ensure_ascii=False, allow_nan=False).encode())):
            fd = os.open(self._path(identity, suffix), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        return receipt

    def raw(self, identity: str) -> bytes:
        path = self._path(identity, '.body')
        if path.is_symlink():
            raise ValueError('evidence must not be a symlink')
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('evidence must be a private regular file')
            return stream.read()

    def read(self, identity: str, *, offset: int = 0, limit: int = 16000) -> dict:
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 16000:
            raise ValueError('offset must be nonnegative; limit must be 1..16000')
        raw = self.raw(identity)
        try:
            content = raw.decode('utf-8')
            encoding, units = 'utf-8', 'unicode_characters'
        except UnicodeDecodeError:
            content = raw
            encoding, units = 'base64', 'bytes'
        if offset > len(content):
            raise ValueError('offset exceeds evidence length')
        end = min(offset + limit, len(content))
        piece = content[offset:end]
        text = base64.b64encode(piece).decode('ascii') if isinstance(piece, bytes) else piece
        return dict(evidence_id=identity, encoding=encoding, offset_units=units,
                    offset=offset, end=end, total=len(content), bytes=len(raw),
                    sha256=hashlib.sha256(raw).hexdigest(), text=text,
                    next_offset=end if end < len(content) else None)
