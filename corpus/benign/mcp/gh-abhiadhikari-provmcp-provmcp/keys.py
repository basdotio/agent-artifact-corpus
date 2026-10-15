"""Ed25519 key handling. Keys live outside the repo; a missing key is an error."""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

KEY_ENV = "PROVMCP_SIGNING_KEY"
PRIVATE_NAME = "signing.pem"
PUBLIC_NAME = "pub.pem"


class MissingKeyError(RuntimeError):
    pass


def generate(out_dir: Path) -> tuple[Path, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    priv_path, pub_path = out_dir / PRIVATE_NAME, out_dir / PUBLIC_NAME
    if priv_path.exists():
        raise FileExistsError(f"{priv_path} exists; refusing to overwrite a signing key")

    key = ed25519.Ed25519PrivateKey.generate()
    priv_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    os.chmod(priv_path, 0o600)
    pub_path.write_bytes(public_pem(key.public_key()))
    return priv_path, pub_path


def public_pem(pub: ed25519.Ed25519PublicKey) -> bytes:
    return pub.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )


def load_private(path: Path | str | None) -> ed25519.Ed25519PrivateKey:
    """Load from an explicit path or $PROVMCP_SIGNING_KEY. Loud on absence."""
    candidate = path or os.environ.get(KEY_ENV)
    if not candidate:
        raise MissingKeyError(
            f"no signing key: pass --key or set {KEY_ENV}. "
            "Run `provmcp keygen --out <dir>` to create one. "
            "Use --unsigned to run without signatures (chain only)."
        )
    p = Path(candidate).expanduser()
    if not p.exists():
        raise MissingKeyError(f"signing key not found at {p}")
    key = serialization.load_pem_private_key(p.read_bytes(), password=None)
    if not isinstance(key, ed25519.Ed25519PrivateKey):
        raise MissingKeyError(f"{p} is not an Ed25519 private key")
    return key


def load_public(path: Path | str) -> ed25519.Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).expanduser().read_bytes())
    if not isinstance(key, ed25519.Ed25519PublicKey):
        raise ValueError(f"{path} is not an Ed25519 public key")
    return key
