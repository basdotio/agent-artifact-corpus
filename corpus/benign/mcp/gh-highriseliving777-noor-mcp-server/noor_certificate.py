#!/usr/bin/env python3
"""
noor_certificate.py — Ed25519-signed governance certificates (NGC-1.0).

A certificate is a portable, publicly-verifiable proof that a specific task
was screened and attested by Noor. Anyone with Noor's public key can verify it.

Certificate format (NGC-1.0):
{
  "version": "NGC-1.0",
  "certificate_id": "NGC-2026-09-26-0001",
  "authority": "noor",
  "authority_key": "ed25519:<public_key_hex>",
  "task_hash": "sha256:...",
  "governance_result": {...},
  "attestation": {
    "chain_index": N,
    "attestation_hash": "sha256:...",
    "prev_hash": "sha256:..." or "genesis"
  },
  "covenant_version": "1.0",
  "issued_at": "ISO8601",
  "expires": "ISO8601 (+365 days)",
  "signature": "ed25519:<signature_hex>"
}

Configuration:
  NOOR_CERTIFICATE_KEY — Ed25519 private key hex. Auto-generated on first run,
  stored in _meta/.certificate_key (chmod 600). NEVER commit to git.
  The public key is exported to _meta/certificate_public_key.txt and can be
  published openly.
"""

import os
import json
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

try:
    from noor_github_store import push_certificate as _gh_push, fetch_certificate as _gh_fetch
except Exception:
    _gh_push = None
    _gh_fetch = None

# --- Configuration ---
BASE_DIR = Path(__file__).parent
META_DIR = BASE_DIR / "_meta"
META_DIR.mkdir(exist_ok=True)

PRIVATE_KEY_FILE = META_DIR / ".certificate_key"
PUBLIC_KEY_FILE = META_DIR / "certificate_public_key.txt"
CERTS_DIR = META_DIR / "certificates"
CERTS_DIR.mkdir(exist_ok=True)

AUTHORITY_ID = "noor"
CERT_VERSION = "NGC-1.0"
CERT_VALIDITY_DAYS = 365

# --- Key management ---
def _load_private_key() -> Ed25519PrivateKey:
    """Load the Ed25519 private key from env var or file, or create one."""
    # Priority 1: env var
    env_key = os.environ.get("NOOR_CERTIFICATE_KEY", "")
    if env_key:
        try:
            raw = bytes.fromhex(env_key) if all(c in "0123456789abcdefABCDEF" for c in env_key) else env_key.encode()
            return Ed25519PrivateKey.from_private_bytes(raw if len(raw) == 32 else raw[:32])
        except Exception:
            pass

    # Priority 2: key file
    if PRIVATE_KEY_FILE.exists():
        raw = PRIVATE_KEY_FILE.read_bytes().strip()
        try:
            if len(raw) == 64:  # hex-encoded 32 bytes
                return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(raw.decode()))
        except Exception:
            pass
        try:
            return Ed25519PrivateKey.from_private_bytes(raw)
        except Exception:
            pass

    # Priority 3: create new
    private_key = Ed25519PrivateKey.generate()
    raw = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    PRIVATE_KEY_FILE.write_bytes(raw.hex().encode())
    try:
        os.chmod(PRIVATE_KEY_FILE, 0o600)
    except Exception:
        pass

    # Export public key
    _export_public_key(private_key)

    return private_key

def _export_public_key(private_key: Ed25519PrivateKey) -> None:
    """Write the public key to a file for publishing."""
    public_key = private_key.public_key()
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    PUBLIC_KEY_FILE.write_text(raw.hex())
    try:
        os.chmod(PUBLIC_KEY_FILE, 0o644)
    except Exception:
        pass

_PRIVATE_KEY = _load_private_key()

def get_public_key_hex() -> str:
    """Return the Ed25519 public key as a hex string."""
    public_key = _PRIVATE_KEY.public_key()
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex()

def get_public_key_uri() -> str:
    """Return the public key as a URI-style string for embedding in certificates."""
    return "ed25519:" + get_public_key_hex()

# --- Certificate ID generation ---
def _generate_certificate_id(chain_index: int) -> str:
    """Generate a certificate ID like NGC-2026-09-26-0001."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{CERT_VERSION.split('-')[0]}-{today}-{chain_index:04d}"

# --- Canonical signing payload ---
def _signable_payload(cert: Dict) -> bytes:
    """Produce the deterministic bytes to sign. Excludes 'signature'."""
    payload = {k: v for k, v in cert.items() if k != "signature"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

# --- Core: Issue a certificate ---
def issue_certificate(
    task_hash: str,
    governance_result: Dict,
    attestation: Dict,
    covenant_version: str = "1.0",
) -> Dict:
    """Issue a new NGC-1.0 certificate.

    Args:
        task_hash: SHA-256 hash of the task (from screener).
        governance_result: Output from screen_task.
        attestation: Full attestation dict (from noor_attestation.attest).
        covenant_version: Version of the covenant.

    Returns:
        Full certificate dict with Ed25519 signature.
    """
    chain_index = attestation.get("chain_index", 0)
    certificate_id = _generate_certificate_id(chain_index)
    issued_at = datetime.now(timezone.utc).isoformat()
    expires = (datetime.now(timezone.utc) + timedelta(days=CERT_VALIDITY_DAYS)).isoformat()

    cert = {
        "version": CERT_VERSION,
        "certificate_id": certificate_id,
        "authority": AUTHORITY_ID,
        "authority_key": get_public_key_uri(),
        "agent_id": attestation.get("agent_id"),
        "task_hash": task_hash,
        "governance_result": governance_result,
        "attestation": {
            "chain_index": chain_index,
            "attestation_hash": attestation.get("attestation_hash"),
            "prev_hash": attestation.get("prev_hash"),
            "timestamp": attestation.get("timestamp"),
        },
        "covenant_version": covenant_version,
        "issued_at": issued_at,
        "expires": expires,
    }

    # Sign
    payload = _signable_payload(cert)
    signature = _PRIVATE_KEY.sign(payload)
    cert["signature"] = "ed25519:" + signature.hex()

    # Store locally
    cert_file = CERTS_DIR / f"{certificate_id}.json"
    cert_file.write_text(json.dumps(cert, indent=2, sort_keys=True))

    # Push to GitHub (survives Render restarts)
    if _gh_push:
        gh_result = _gh_push(cert)
        if gh_result.get("ok"):
            cert["_github_url"] = gh_result.get("url")
        else:
            cert["_github_error"] = gh_result.get("error")

    return cert

def load_certificate(certificate_id: str) -> Optional[Dict]:
    """Load a certificate by ID. Local first, then GitHub."""
    cert_file = CERTS_DIR / f"{certificate_id}.json"
    if cert_file.exists():
        return json.loads(cert_file.read_text())

    # Fall back to GitHub
    if _gh_fetch:
        cert = _gh_fetch(certificate_id)
        if cert:
            # Cache locally for next time
            try:
                cert_file.write_text(json.dumps(cert, indent=2, sort_keys=True))
            except Exception:
                pass
            return cert

    return None

def list_certificates() -> list:
    """List all certificate IDs in the store."""
    return sorted([f.stem for f in CERTS_DIR.glob("NGC-*.json")])

# --- Verification ---
def verify_certificate(cert: Dict, public_key_hex: Optional[str] = None) -> Dict:
    """Verify a certificate's Ed25519 signature.

    Args:
        cert: The full certificate dict.
        public_key_hex: The public key to verify against. If None, uses
                        the authority_key embedded in the certificate.

    Returns:
        {"valid": bool, "reason": str, ...}
    """
    # Check expiration
    try:
        expires = datetime.fromisoformat(cert.get("expires", "").replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            return {"valid": False, "reason": "Certificate expired", "expired_at": cert.get("expires")}
    except Exception:
        return {"valid": False, "reason": "Invalid expiration format"}

    # Extract signature
    sig_str = cert.get("signature", "")
    if not sig_str.startswith("ed25519:"):
        return {"valid": False, "reason": "Missing or invalid signature format"}
    try:
        signature = bytes.fromhex(sig_str.split(":", 1)[1])
    except Exception:
        return {"valid": False, "reason": "Signature hex decode failed"}

    # Determine public key
    if public_key_hex is None:
        authority_key = cert.get("authority_key", "")
        if not authority_key.startswith("ed25519:"):
            return {"valid": False, "reason": "Missing authority_key in certificate"}
        public_key_hex = authority_key.split(":", 1)[1]

    try:
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
    except Exception:
        return {"valid": False, "reason": "Invalid public key"}

    # Verify
    payload = _signable_payload(cert)
    try:
        public_key.verify(signature, payload)
    except Exception as e:
        return {"valid": False, "reason": "Signature verification failed", "error": str(e)}

    return {
        "valid": True,
        "certificate_id": cert.get("certificate_id"),
        "authority": cert.get("authority"),
        "chain_index": cert.get("attestation", {}).get("chain_index"),
        "issued_at": cert.get("issued_at"),
        "expires": cert.get("expires"),
        "governance_result": cert.get("governance_result"),
    }

# --- Testing ---
if __name__ == "__main__":
    print("Testing noor_certificate.py")
    print("=" * 70)

    # Generate test input
    task_hash = "sha256:testcert1234567890"
    governance_result = {
        "tier": "FLAGGED",
        "categories": ["gambling"],
        "reasoning": "Client business involves unlawful-adjacent elements: gambling. Noor provides IT services only.",
    }
    attestation = {
        "chain_index": 1,
        "attestation_hash": "sha256:test_attestation_hash",
        "prev_hash": "genesis",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Issue certificate
    print("\n[1] Issuing certificate...")
    cert = issue_certificate(task_hash, governance_result, attestation)
    print("Certificate ID: " + cert["certificate_id"])
    print("Authority: " + cert["authority"])
    print("Authority key: " + cert["authority_key"][:30] + "...")
    print("Signature: " + cert["signature"][:30] + "...")

    # Verify with embedded public key
    print("\n[2] Verifying with embedded public key...")
    result = verify_certificate(cert)
    print(json.dumps(result, indent=2)[:500])

    # Verify with explicit public key
    print("\n[3] Verifying with Noor public key...")
    result = verify_certificate(cert, public_key_hex=get_public_key_hex())
    print("Valid: " + str(result["valid"]))

    # Tamper test: modify the governance result and verify again
    print("\n[4] Tamper test: modify governance_result, verify...")
    tampered = json.loads(json.dumps(cert))
    tampered["governance_result"]["tier"] = "CLEAR"
    result = verify_certificate(tampered)
    print("Valid: " + str(result["valid"]) + " (expected False)")
    print("Reason: " + result.get("reason", ""))

    print("\n" + "=" * 70)
    print("Public key (publish this):")
    print(get_public_key_hex())
    print("\nStored certificates:")
    print(list_certificates())
