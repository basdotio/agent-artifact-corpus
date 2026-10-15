#!/usr/bin/env python3
"""
noor_revocation.py — Certificate revocation list (CRL) for the Noor Trust Chain.

Append-only log of revoked certificate IDs. Verification checks this list
before declaring a certificate valid. Admin-only revocation requires a secret
that only Sam holds.

Configuration:
  NOOR_ADMIN_KEY — Admin secret for revocation. Auto-generated on first run,
  stored in _meta/.admin_key (chmod 600). NEVER commit to git.
"""

import os
import json
import hmac
import secrets
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# --- Configuration ---
BASE_DIR = Path(__file__).parent
META_DIR = BASE_DIR / "_meta"
META_DIR.mkdir(exist_ok=True)

REVOCATIONS_FILE = META_DIR / "revocations.jsonl"
ADMIN_KEY_FILE = META_DIR / ".admin_key"

# --- Admin key management ---
def _load_or_create_admin_key() -> str:
    env_key = os.environ.get("NOOR_ADMIN_KEY", "")
    if env_key:
        return env_key

    if ADMIN_KEY_FILE.exists():
        return ADMIN_KEY_FILE.read_text().strip()

    key = secrets.token_urlsafe(32)
    ADMIN_KEY_FILE.write_text(key)
    try:
        os.chmod(ADMIN_KEY_FILE, 0o600)
    except Exception:
        pass
    return key

_ADMIN_KEY = _load_or_create_admin_key()

def verify_admin_key(provided_key: str) -> bool:
    """Constant-time comparison of admin key."""
    if not provided_key:
        return False
    return hmac.compare_digest(_ADMIN_KEY, provided_key)

# --- Revocation store ---
def load_revocations() -> List[Dict]:
    """Load all revocations from the append-only file."""
    if not REVOCATIONS_FILE.exists():
        return []
    entries = []
    with open(REVOCATIONS_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries

def is_revoked(certificate_id: str) -> Optional[Dict]:
    """Check if a certificate is revoked. Returns the revocation record or None."""
    for entry in load_revocations():
        if entry.get("certificate_id") == certificate_id:
            return entry
    return None

def revoke(
    certificate_id: str,
    admin_key: str,
    reason: str,
    revoked_by: str = "admin",
) -> Dict:
    """Revoke a certificate. Requires valid admin key.

    Args:
        certificate_id: The NGC-XXXX-XX-XX-XXXX ID to revoke.
        admin_key: The admin secret (must match NOOR_ADMIN_KEY).
        reason: Why the certificate is being revoked.
        revoked_by: Who revoked it (default: "admin").

    Returns:
        The revocation record, or an error dict.
    """
    if not verify_admin_key(admin_key):
        return {"ok": False, "error": "Invalid admin key"}

    if not certificate_id:
        return {"ok": False, "error": "certificate_id is required"}

    if not reason or not reason.strip():
        return {"ok": False, "error": "reason is required"}

    # Check if already revoked
    existing = is_revoked(certificate_id)
    if existing:
        return {"ok": False, "error": "Already revoked", "existing": existing}

    entry = {
        "certificate_id": certificate_id,
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "revoked_by": revoked_by,
        "reason": reason.strip(),
    }

    with open(REVOCATIONS_FILE, "a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")

    return {"ok": True, "revocation": entry}

def list_revocations() -> Dict:
    """Return the full revocation list (public read)."""
    entries = load_revocations()
    return {
        "count": len(entries),
        "revocations": entries,
    }

def get_revocation_summary() -> Dict:
    """Summary for status endpoints."""
    entries = load_revocations()
    return {
        "total_revoked": len(entries),
        "last_revoked_at": entries[-1]["revoked_at"] if entries else None,
        "last_revoked_id": entries[-1]["certificate_id"] if entries else None,
    }

# --- Testing ---
if __name__ == "__main__":
    print("Testing noor_revocation.py")
    print("=" * 70)

    # Use a test certificate ID
    test_cert_id = "NGC-2026-09-26-9999"

    # 1. Check it's not revoked
    print("\n[1] Is NGC-2026-09-26-9999 revoked?")
    print("Result: " + str(is_revoked(test_cert_id)))

    # 2. Try to revoke with wrong admin key
    print("\n[2] Revoke with wrong admin key (should fail)...")
    result = revoke(test_cert_id, admin_key="wrong_key", reason="Testing")
    print(json.dumps(result, indent=2))

    # 3. Revoke with correct admin key
    print("\n[3] Revoke with correct admin key...")
    result = revoke(
        test_cert_id,
        admin_key=_ADMIN_KEY,
        reason="Test revocation — do not use in production",
        revoked_by="test_runner",
    )
    print(json.dumps(result, indent=2))

    # 4. Verify it's now revoked
    print("\n[4] Is it revoked now?")
    revoked = is_revoked(test_cert_id)
    print("Result: " + str(revoked is not None))
    if revoked:
        print("Reason: " + revoked["reason"])

    # 5. Try to revoke the same one again (should fail)
    print("\n[5] Try to revoke again (should fail)...")
    result = revoke(test_cert_id, admin_key=_ADMIN_KEY, reason="Double revoke")
    print(json.dumps(result, indent=2))

    # 6. List all revocations
    print("\n[6] Revocation summary:")
    print(json.dumps(get_revocation_summary(), indent=2))

    print("\n" + "=" * 70)
    print("Admin key stored in _meta/.admin_key — DO NOT COMMIT")
