#!/usr/bin/env python3
"""
noor_verification.py — Public verification portal for Noor Governance Certificates.

Given a certificate ID, this module:
1. Loads the certificate
2. Checks the revocation list
3. Verifies the Ed25519 signature
4. Confirms the attestation reference is intact
5. Returns a public verification result

The verification is READ-ONLY. It never writes to the chain. It only
confirms what already exists. Anyone can run it. Anyone can verify.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional

from noor_certificate import (
    load_certificate,
    verify_certificate,
    get_public_key_hex,
)
from noor_revocation import is_revoked
from noor_attestation import load_chain

# --- Configuration ---
BASE_DIR = Path(__file__).parent

# --- Core: verify_certificate_by_id ---
def verify_certificate_by_id(certificate_id: str) -> Dict:
    """Public verification. Takes a certificate ID, returns full verification result.

    Returns a dict with:
        valid: bool — the certificate is signed, not revoked, not expired
        certificate_id: str
        authority: str
        chain_index: int
        governance_result: dict
        issued_at / expires: ISO8601
        checks: {signature, revocation, attestation, expiration}
        public_key: str (the key used for verification)
    """
    if not certificate_id:
        return {"valid": False, "reason": "certificate_id required"}

    # 1. Load the certificate
    cert = load_certificate(certificate_id)
    if cert is None:
        return {
            "valid": False,
            "certificate_id": certificate_id,
            "reason": "Certificate not found",
        }

    checks = {
        "signature": False,
        "revocation": "unknown",
        "attestation": "unknown",
        "expiration": "unknown",
    }

    # 2. Check revocation FIRST — if revoked, we stop here
    revocation = is_revoked(certificate_id)
    if revocation:
        checks["revocation"] = "REVOKED"
        return {
            "valid": False,
            "certificate_id": certificate_id,
            "reason": "Certificate has been revoked",
            "revocation": {
                "revoked_at": revocation.get("revoked_at"),
                "revoked_by": revocation.get("revoked_by"),
                "reason": revocation.get("reason"),
            },
            "checks": checks,
        }
    checks["revocation"] = "not_revoked"

    # 3. Verify signature
    sig_result = verify_certificate(cert)
    checks["signature"] = sig_result.get("valid", False)
    if not checks["signature"]:
        return {
            "valid": False,
            "certificate_id": certificate_id,
            "reason": "Signature verification failed: " + sig_result.get("reason", "unknown"),
            "checks": checks,
        }

    # 4. Check expiration explicitly (verify_certificate already does, but we want it in the report)
    try:
        expires = datetime.fromisoformat(cert.get("expires", "").replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            checks["expiration"] = "expired"
            return {
                "valid": False,
                "certificate_id": certificate_id,
                "reason": "Certificate expired",
                "expired_at": cert.get("expires"),
                "checks": checks,
            }
        checks["expiration"] = "valid"
    except Exception:
        checks["expiration"] = "invalid_format"

    # 5. Confirm attestation exists in the chain
    attestation_ref = cert.get("attestation", {})
    chain_index = attestation_ref.get("chain_index")
    attestation_hash = attestation_ref.get("attestation_hash")

    chain = load_chain()
    chain_entry = None
    for entry in chain:
        if entry.get("chain_index") == chain_index:
            chain_entry = entry
            break

    if chain_entry is None:
        checks["attestation"] = "not_in_chain"
        return {
            "valid": False,
            "certificate_id": certificate_id,
            "reason": "Attestation not found in chain (chain_index=" + str(chain_index) + ")",
            "checks": checks,
        }

    if chain_entry.get("attestation_hash") != attestation_hash:
        checks["attestation"] = "hash_mismatch"
        return {
            "valid": False,
            "certificate_id": certificate_id,
            "reason": "Attestation hash mismatch",
            "checks": checks,
        }
    checks["attestation"] = "confirmed"

    # 6. All checks passed — build the public report
    return {
        "valid": True,
        "certificate_id": certificate_id,
        "authority": cert.get("authority"),
        "authority_key": cert.get("authority_key"),
        "chain_index": chain_index,
        "covenant_version": cert.get("covenant_version"),
        "governance_result": cert.get("governance_result"),
        "issued_at": cert.get("issued_at"),
        "expires": cert.get("expires"),
        "checks": checks,
        "public_key": get_public_key_hex(),
        "verify_url": "https://jarvis-bridge-jtuc.onrender.com/api/verify/" + certificate_id,
    }

# --- Verify all certificates in the store ---
def verify_all_certificates() -> Dict:
    """Verify every certificate in the store. Returns a summary."""
    from noor_certificate import list_certificates
    cert_ids = list_certificates()
    results = []
    for cid in cert_ids:
        results.append(verify_certificate_by_id(cid))
    valid_count = sum(1 for r in results if r.get("valid"))
    return {
        "total": len(results),
        "valid": valid_count,
        "invalid": len(results) - valid_count,
        "results": results,
    }

# --- Status for health endpoints ---
def get_verification_status() -> Dict:
    """Return a status dict for health/monitoring endpoints."""
    from noor_certificate import list_certificates
    return {
        "status": "active",
        "public_key": get_public_key_hex(),
        "verify_endpoint": "/api/verify/{certificate_id}",
        "certificates_issued": len(list_certificates()),
        "note": "Verification is read-only. Anyone can verify a certificate ID.",
    }

# --- Testing ---
if __name__ == "__main__":
    print("Testing noor_verification.py")
    print("=" * 70)

    from noor_certificate import list_certificates
    certs = list_certificates()
    if not certs:
        print("⚠️ No certificates in store. Run noor_certificate.py first.")
    else:
        test_id = certs[0]
        print("\n[1] Verifying certificate: " + test_id)
        result = verify_certificate_by_id(test_id)
        print(json.dumps(result, indent=2, default=str))

    print("\n[2] Verifying a non-existent certificate...")
    result = verify_certificate_by_id("NGC-9999-99-99-9999")
    print(json.dumps(result, indent=2, default=str))

    print("\n[3] Verifying the revoked test certificate (NGC-2026-09-26-9999)...")
    result = verify_certificate_by_id("NGC-2026-09-26-9999")
    print(json.dumps(result, indent=2, default=str))

    print("\n" + "=" * 70)
    print("Verification status:")
    print(json.dumps(get_verification_status(), indent=2))
