"""Explicit owner connection settings; no host/profile discovery."""
from dataclasses import dataclass, field
import math
import os
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    base_url: str
    token: str = field(repr=False)
    evidence_dir: Path
    ca_file: Path | None = None
    request_timeout: float = 30.0
    namespace: str | None = None
    source_root: Path | None = None

    def __post_init__(self):
        parsed = urlsplit(self.base_url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.path not in ('', '/')
                or parsed.query or parsed.fragment or any(c.isspace() for c in self.base_url)):
            raise ValueError('SOAR_URL must be an HTTPS origin without user info, path, query or fragment')
        _ = parsed.port  # validate port range before any HTTP request
        if not self.token or any(ord(c) < 32 or ord(c) > 126 for c in self.token):
            raise ValueError('SOAR_API_TOKEN must be nonempty printable ASCII without control characters')
        if not math.isfinite(self.request_timeout) or self.request_timeout <= 0:
            raise ValueError('request timeout must be positive and finite')
        if not self.evidence_dir.is_absolute():
            raise ValueError('SOAR_EVIDENCE_DIR must be an absolute owner-selected directory')
        if self.ca_file is not None and (not self.ca_file.is_absolute() or not self.ca_file.is_file()):
            raise ValueError('SOAR_CA_FILE must name an existing absolute CA file')
        if (self.namespace is None) != (self.source_root is None):
            raise ValueError('SOAR_NAMESPACE and SOAR_PLAYBOOK_SOURCE_ROOT must be selected together')

    @classmethod
    def from_env(cls, environ=None):
        env = os.environ if environ is None else environ
        required = ('SOAR_URL', 'SOAR_API_TOKEN', 'SOAR_EVIDENCE_DIR')
        if any(not env.get(name) for name in required):
            raise ValueError('required configuration: ' + ', '.join(required))
        return cls(base_url=env['SOAR_URL'], token=env['SOAR_API_TOKEN'],
                   evidence_dir=Path(env['SOAR_EVIDENCE_DIR']),
                   ca_file=Path(env['SOAR_CA_FILE']) if env.get('SOAR_CA_FILE') else None,
                   request_timeout=float(env.get('SOAR_REQUEST_TIMEOUT_SECONDS', '30')),
                   namespace=env.get('SOAR_NAMESPACE') or None,
                   source_root=Path(env['SOAR_PLAYBOOK_SOURCE_ROOT']) if env.get('SOAR_PLAYBOOK_SOURCE_ROOT') else None)
