"""RSA-SHA256 signature verification for Manus webhooks.

See ManusAPIDocs/webhooks/security.md.

Signed content layout: `{timestamp}.{public_url}.{sha256_hex(body)}`
"""

from __future__ import annotations

import base64
import hashlib
import time
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

DEFAULT_MAX_AGE_SECONDS: int = 300


@dataclass(frozen=True)
class VerificationResult:
    valid: bool
    reason: str | None = None


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_public_key(pem: str) -> rsa.RSAPublicKey:
    key = serialization.load_pem_public_key(pem.encode("utf-8"))
    if not isinstance(key, rsa.RSAPublicKey):
        raise ValueError("Loaded key is not an RSA public key")
    return key


def build_signed_content(timestamp: str, public_url: str, body: bytes) -> bytes:
    return f"{timestamp}.{public_url}.{sha256_hex(body)}".encode()


def verify_signature(
    *,
    public_key: rsa.RSAPublicKey,
    signature_b64: str,
    timestamp: str,
    public_url: str,
    body: bytes,
    now: float | None = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> VerificationResult:
    """Verify a Manus webhook signature."""
    if not signature_b64 or not timestamp:
        return VerificationResult(False, "missing signature or timestamp")

    try:
        ts_int = int(timestamp)
    except ValueError:
        return VerificationResult(False, "timestamp is not an integer")

    current = now if now is not None else time.time()
    if abs(current - ts_int) > max_age_seconds:
        return VerificationResult(False, f"timestamp skew > {max_age_seconds}s")

    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception as e:
        return VerificationResult(False, f"signature is not valid base64: {e}")

    signed = build_signed_content(timestamp, public_url, body)
    try:
        public_key.verify(
            signature,
            signed,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except InvalidSignature:
        return VerificationResult(False, "signature does not match")
    return VerificationResult(True, None)
