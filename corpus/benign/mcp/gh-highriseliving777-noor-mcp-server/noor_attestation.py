#!/usr/bin/env python3
"""
noor_attestation.py — Trust Chain attestation engine.

Produces a tamper-evident chain of cryptographic proofs. Each attestation:
- Is SHA-256 hashed over (task_hash + governance_result + timestamp + agent_id + covenant_version)
- Is HMAC-SHA256 signed with Noor's attestation key
- References the previous attestation's hash (chain link)
- Is stored in _meta/attestations.jsonl (append-only, immutable)

The chain is verified by recomputing each attestation's hash and ensuring
prev_hash points to the previous entry's hash.

Configuration:
  NOOR_ATTESTATION_KEY — HMAC secret. Auto-generated on first run, stored in
  _meta/.attestation_key (chmod 600). NEVER commit to git.
"""

import os
import json
import hmac
import hashlib
import secrets
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

try:
    from noor_github_store import push_attestation as _gh_push_att, fetch_all_attestations as _gh_fetch_att
except Exception:
    _gh_push_att = None
    _gh_fetch_att = None

# --- Configuration ---
BASE_DIR = Path(__file__).parent
META_DIR = BASE_DIR / "_meta"
META_DIR.mkdir(exist_ok=True)

CHAIN_FILE = META_DIR / "attestations.jsonl"
KEY_FILE = META_DIR / ".attestation_key"
COVENANT_VERSION = "1.0"

# --- Key management ---
def load_or_create_key() -> bytes:
    """Load the HMAC key, or create one if it doesn't exist.
    Priority: env var > key file > create new.
    """
    env_key = os.environ.get("NOOR_ATTESTATION_KEY", "")
    if env_key:
        return env_key.encode() if isinstance(env_key, str) else env_key

    if KEY_FILE.exists():
        raw = KEY_FILE.read_bytes()
        # If it's raw hex, decode; otherwise use as-is
        try:
            if len(raw) == 64 and all(c in b"0123456789abcdefABCDEF" for c in raw):
                return bytes.fromhex(raw.decode())
        except Exception:
            pass
        return raw

    # Create new key
    key = secrets.token_bytes(32)
    KEY_FILE.write_bytes(key.hex().encode())
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return key

_ATTESTATION_KEY = load_or_create_key()

# --- Chain helpers ---
def load_chain() -> List[Dict]:
    """Load all attestations. Local first, then GitHub fallback."""
    entries = []
    if CHAIN_FILE.exists():
        with open(CHAIN_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

    # If local is empty, fall back to GitHub
    if not entries and _gh_fetch_att:
        entries = _gh_fetch_att()
        # Cache locally
        if entries and not CHAIN_FILE.exists():
            try:
                with open(CHAIN_FILE, "w") as f:
                    for e in entries:
                        f.write(json.dumps(e, sort_keys=True) + "\n")
            except Exception:
                pass

    return entries

def get_last_hash() -> Optional[str]:
    """Get the hash of the last attestation in the chain."""
    chain = load_chain()
    if not chain:
        return None
    return chain[-1].get("attestation_hash")

def get_next_index() -> int:
    """Get the next chain index."""
    chain = load_chain()
    if not chain:
        return 1
    return chain[-1].get("chain_index", 0) + 1

# --- Core: Generate attestation ---
def compute_hash(payload: Dict) -> str:
    """Deterministic SHA-256 hash of a dict."""
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(serialized).hexdigest()

def sign(payload_hash: str) -> str:
    """HMAC-SHA256 sign a payload hash."""
    mac = hmac.new(_ATTESTATION_KEY, payload_hash.encode(), hashlib.sha256)
    return "hmac:" + mac.hexdigest()

def verify_signature(payload_hash: str, signature: str) -> bool:
    """Verify an HMAC signature."""
    expected = sign(payload_hash)
    return hmac.compare_digest(expected, signature)

def attest(
    task_hash: str,
    governance_result: Dict,
    agent_id: str,
    covenant_version: str = COVENANT_VERSION,
) -> Dict:
    """Generate a new attestation and append it to the chain.

    Args:
        task_hash: The SHA-256 hash of the task description (from screener).
        governance_result: The output from screen_task or HITL gate.
        agent_id: ID of the agent whose task is being attested.
        covenant_version: Version of the covenant (default "1.0").

    Returns:
        The full attestation dict with hash and signature.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    chain_index = get_next_index()
    prev_hash = get_last_hash() or "genesis"

    # Build the payload to hash
    payload = {
        "chain_index": chain_index,
        "task_hash": task_hash,
        "governance_result": governance_result,
        "agent_id": agent_id,
        "covenant_version": covenant_version,
        "timestamp": timestamp,
        "prev_hash": prev_hash,
    }

    attestation_hash = compute_hash(payload)
    signature = sign(attestation_hash)

    attestation = {
        **payload,
        "attestation_hash": attestation_hash,
        "signature": signature,
    }

    # Append to chain file locally
    with open(CHAIN_FILE, "a") as f:
        f.write(json.dumps(attestation, sort_keys=True) + "\n")

    # Push to GitHub (survives Render restarts)
    if _gh_push_att:
        gh_result = _gh_push_att(attestation)
        if gh_result.get("ok"):
            attestation["_github_url"] = gh_result.get("url")
        else:
            attestation["_github_error"] = gh_result.get("error")

    return attestation

# --- Verification ---
def verify_attestation(attestation: Dict) -> Dict:
    """Verify a single attestation: hash and signature."""
    # Recompute hash without the signature and hash fields
    payload = {k: v for k, v in attestation.items() if k not in ("attestation_hash", "signature")}
    expected_hash = compute_hash(payload)
    hash_ok = hmac.compare_digest(expected_hash, attestation.get("attestation_hash", ""))
    sig_ok = verify_signature(attestation.get("attestation_hash", ""), attestation.get("signature", ""))
    return {
        "valid": hash_ok and sig_ok,
        "hash_valid": hash_ok,
        "signature_valid": sig_ok,
        "chain_index": attestation.get("chain_index"),
        "attestation_hash": attestation.get("attestation_hash"),
    }

def verify_chain() -> Dict:
    """Verify the entire chain: each entry's prev_hash matches the previous entry's hash."""
    chain = load_chain()
    if not chain:
        return {"valid": True, "length": 0, "message": "Chain is empty (genesis state)."}

    issues = []
    for i, entry in enumerate(chain):
        # Verify this entry's hash and signature
        result = verify_attestation(entry)
        if not result["valid"]:
            issues.append({
                "chain_index": entry.get("chain_index"),
                "issue": "invalid hash or signature",
            })
            continue

        # Verify prev_hash link
        if i == 0:
            if entry.get("prev_hash") != "genesis":
                issues.append({"chain_index": entry.get("chain_index"), "issue": "first entry prev_hash is not 'genesis'"})
        else:
            prev_entry = chain[i - 1]
            if entry.get("prev_hash") != prev_entry.get("attestation_hash"):
                issues.append({
                    "chain_index": entry.get("chain_index"),
                    "issue": "prev_hash does not match previous entry's attestation_hash",
                })

    return {
        "valid": len(issues) == 0,
        "length": len(chain),
        "last_hash": chain[-1].get("attestation_hash"),
        "issues": issues,
    }

def get_chain_summary() -> Dict:
    """Return a summary of the chain."""
    chain = load_chain()
    if not chain:
        return {
            "length": 0,
            "first_index": None,
            "last_index": None,
            "last_hash": None,
            "genesis_time": None,
        }
    return {
        "length": len(chain),
        "first_index": chain[0].get("chain_index"),
        "last_index": chain[-1].get("chain_index"),
        "last_hash": chain[-1].get("attestation_hash"),
        "genesis_time": chain[0].get("timestamp"),
        "last_time": chain[-1].get("timestamp"),
    }

# --- Testing ---
if __name__ == "__main__":
    print("Testing noor_attestation.py")
    print("=" * 70)

    # Generate a test attestation
    test_result = {
        "tier": "CLEAR",
        "categories": [],
        "reasoning": "No unlawful-adjacent elements detected.",
    }
    att = attest(
        task_hash="sha256:test1234567890ab",
        governance_result=test_result,
        agent_id="test-agent",
    )
    print("\nGenerated attestation:")
    print(json.dumps(att, indent=2)[:600])

    print("\n" + "=" * 70)
    print("Verifying the attestation...")
    result = verify_attestation(att)
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 70)
    print("Verifying the entire chain...")
    chain_result = verify_chain()
    print(json.dumps(chain_result, indent=2))

    print("\n" + "=" * 70)
    print("Chain summary:")
    print(json.dumps(get_chain_summary(), indent=2))
