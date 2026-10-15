"""Log redaction: keep secrets, LAN addresses and MACs out of logs you might paste into an issue.

Shared by the sibling servers, byte for byte. Change it in mcp-server-shared,
not in a copy, then sync (`python scripts/sync_shared.py --update`).

Logs mention devices by name wherever we control the message, but libraries
log addresses freely, and tracebacks carry URLs and headers. So instead of
editing messages one by one, the stderr handler's *formatter* redacts the
final text, tracebacks included:

    192.168.1.60                     -> x.x.x.60      (last octet kept, to tell devices apart)
    AA:BB:CC:DD:EE:FF                -> xx:xx:xx:xx:EE:FF
    AABBCCDDEEFF                     -> xxxxxxxxEEFF  (bare uppercase hex, as in MQTT topics)
    mqtt://user:secret@host          -> mqtt://user:***@host
    eyJhbGciOi...(a JWT)             -> [jwt redacted]   (Cloudflare Access assertions)
    Authorization: Bearer abc123     -> Authorization: Bearer [redacted]
    -----BEGIN PRIVATE KEY----- ...  -> [pem redacted]   (certificates and keys)

Loopback and unspecified addresses (127.x, 0.0.0.0) are left alone: they say
nothing about your network and matter when debugging the simulator.

Each server's CLI turns redaction off with --no-redact or its
<NAME>_LOG_UNREDACTED=1, e.g. when you are the only reader. Secrets (JWTs,
bearer tokens, keys, URL passwords) are redacted even then.
"""

from __future__ import annotations

import logging
import re

_IPV4 = re.compile(r"(?<![\d.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\d.])")
_MAC = re.compile(r"(?<![0-9A-Fa-f:])((?:[0-9A-Fa-f]{2}[:-]){4})([0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2})(?![0-9A-Fa-f:])")
_BARE_MAC = re.compile(r"(?<![0-9A-Za-z])([0-9A-F]{8})([0-9A-F]{4})(?![0-9A-Za-z])")
_URL_PASSWORD = re.compile(r"(\w+://[^/\s:@]+):[^@/\s]+@")
# A JWT is three base64url parts; its header always starts with {" -> "eyJ".
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*")
_BEARER = re.compile(r"(?i)(\bbearer\s+)[A-Za-z0-9._~+/=-]{8,}")
_PEM = re.compile(r"-----BEGIN [A-Z0-9 ]+-----.*?-----END [A-Z0-9 ]+-----", re.S)


def _ip(m: re.Match[str]) -> str:
    first = m.group(1)
    if first in ("127", "0"):
        return m.group(0)
    return f"x.x.x.{m.group(4)}"


def redact_secrets(text: str) -> str:
    """Credentials only: always applied, even when addresses are shown."""
    text = _PEM.sub("[pem redacted]", text)
    text = _JWT.sub("[jwt redacted]", text)
    text = _BEARER.sub(r"\1[redacted]", text)
    return _URL_PASSWORD.sub(r"\1:***@", text)


def redact(text: str) -> str:
    text = redact_secrets(text)
    text = _IPV4.sub(_ip, text)
    text = _MAC.sub(lambda m: "xx:xx:xx:xx:" + m.group(2), text)
    return _BARE_MAC.sub(lambda m: "xxxxxxxx" + m.group(2), text)


class RedactingFormatter(logging.Formatter):
    def __init__(self, fmt: str | None = None, datefmt: str | None = None, *, addresses: bool = True) -> None:
        super().__init__(fmt, datefmt)
        self.addresses = addresses

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        return redact(text) if self.addresses else redact_secrets(text)


def setup_logging(level: int, *, redacted: bool = True, fmt: str = "%(levelname)s %(name)s: %(message)s") -> None:
    """Log to stderr (stdout belongs to the MCP stdio transport). Addresses are
    redacted unless asked not to; secrets always are."""
    import sys

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(RedactingFormatter(fmt, addresses=redacted))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
