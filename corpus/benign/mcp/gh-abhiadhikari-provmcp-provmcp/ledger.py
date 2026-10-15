"""Append-only, hash-chained, signed provenance ledger.

Every tool call the proxy observes becomes one entry. Entries are chained by hash
so that altering an old entry invalidates every entry after it, and signed so that
the chain itself cannot be silently rebuilt.

What this proves: no entry was altered or removed after it was written.
What this does NOT prove: who produced an entry, or that the downstream tool told
the truth. Say so in the README — see docs/provenance-design.md on the limits.

Design rules (do not relax):
  - APPEND ONLY. There is no update or delete path and there must never be one.
  - Hashes cover CANONICAL json (sorted keys, no whitespace, UTF-8). Byte-stability
    is the entire point; pretty-printing breaks verification.
  - Signing keys never enter the repo. Missing key = loud failure, not a warning.
  - Default to storing a hash of the result, not the result. A proxy over a
    clinical server will see PHI.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

GENESIS = "0" * 64


def canonical(obj: object) -> bytes:
    """Byte-stable JSON. Sorted keys, no whitespace, UTF-8, no NaN."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class Entry:
    """One observed tool call.

    `result_hash` is always present. `result` is present only when retention is
    explicitly enabled for this server — see RedactionPolicy in proxy.py.
    """

    seq: int
    timestamp: str                     # ISO 8601, UTC, contemporaneous
    server_id: str                     # downstream server the call went to
    tool: str
    arguments: dict
    result_hash: str                   # sha256 of canonical(result)
    source_release: str | None = None  # e.g. "GEO 2026-03-01", "OT 25.06"
    duration_ms: int = 0
    error: str | None = None
    client: str | None = None          # calling client, "name/version", if it identified itself
    result: object | None = None       # only if retention is on
    prev_hash: str = GENESIS
    entry_hash: str = ""
    signature: str = ""

    def hashable(self) -> dict:
        """Everything the hash covers. Excludes entry_hash and signature."""
        d = asdict(self)
        d.pop("entry_hash")
        d.pop("signature")
        return d

    def compute_hash(self) -> str:
        return sha256_hex(canonical(self.hashable()))


class Ledger:
    """JSONL on disk, one entry per line, append-only."""

    def __init__(self, path: Path, signing_key: ed25519.Ed25519PrivateKey | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._key = signing_key
        self._head: tuple[int, str] | None = None  # cached after first scan

    @property
    def signed(self) -> bool:
        return self._key is not None

    # ---------- reading ----------

    def entries(self) -> Iterator[Entry]:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield Entry(**json.loads(line))

    def head(self) -> tuple[int, str]:
        """(next sequence number, hash of last entry).

        Scans the file once, then tracks the head in memory. The chain links
        on the stored hash here, not the recomputed one — that's what makes a
        *later* tampered entry detectable by verify(); the append path is not
        the place to validate history.
        """
        if self._head is None:
            seq, prev = 0, GENESIS
            for e in self.entries():
                seq, prev = e.seq + 1, e.entry_hash
            self._head = (seq, prev)
        return self._head

    # ---------- writing ----------

    def append(
        self,
        *,
        server_id: str,
        tool: str,
        arguments: dict,
        result: object,
        source_release: str | None = None,
        duration_ms: int = 0,
        error: str | None = None,
        client: str | None = None,
        retain_result: bool = False,
    ) -> Entry:
        """Seal and persist one entry. Raises on any I/O failure — the caller
        must treat that as a failed call, never a dropped record."""
        seq, prev = self.head()
        entry = Entry(
            seq=seq,
            timestamp=datetime.now(UTC).isoformat(),
            server_id=server_id,
            tool=tool,
            arguments=arguments,
            result_hash=sha256_hex(canonical(result)),
            source_release=source_release,
            duration_ms=duration_ms,
            error=error,
            client=client,
            result=result if retain_result else None,
            prev_hash=prev,
        )
        entry_hash = entry.compute_hash()
        signature = ""
        if self._key is not None:
            signature = base64.b64encode(self._key.sign(entry_hash.encode())).decode()

        sealed = Entry(**{**asdict(entry), "entry_hash": entry_hash, "signature": signature})
        line = json.dumps(asdict(sealed), ensure_ascii=False) + "\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        self._head = (seq + 1, entry_hash)
        return sealed

    # ---------- verification ----------

    def verify(self, public_key: ed25519.Ed25519PublicKey | None = None) -> list[str]:
        """Return a list of problems. Empty list means the chain is intact."""
        problems: list[str] = []
        expected_seq, expected_prev = 0, GENESIS

        for entry in self.entries():
            # Link on the RECOMPUTED hash, never the stored one. If an earlier
            # entry's content was altered, its recomputed hash changes and every
            # later entry's prev_hash stops matching — which is the whole point
            # of a chain. Comparing against the stored entry_hash would let a
            # single-entry edit pass every downstream link.
            recomputed = entry.compute_hash()

            if entry.seq != expected_seq:
                problems.append(f"seq {entry.seq}: expected {expected_seq} (entry missing?)")
            if entry.prev_hash != expected_prev:
                problems.append(f"seq {entry.seq}: chain broken (prev_hash mismatch)")
            if recomputed != entry.entry_hash:
                problems.append(f"seq {entry.seq}: content altered (entry_hash mismatch)")
            if public_key is not None:
                if not entry.signature:
                    problems.append(f"seq {entry.seq}: unsigned")
                else:
                    try:
                        public_key.verify(
                            base64.b64decode(entry.signature), entry.entry_hash.encode()
                        )
                    except InvalidSignature:
                        problems.append(f"seq {entry.seq}: bad signature")

            expected_seq, expected_prev = entry.seq + 1, recomputed

        return problems
