#!/usr/bin/env python3
"""Decrypt a macOS WeChat V1MMWX package into a plain wxapkg.

Use only on packages you own or are authorized to inspect.  This implementation
is kept deliberately small so each transformation can be audited.
"""

from __future__ import annotations

import argparse
import hashlib
from grea.host.paths import Path
from grea.safe_paths import disjoint, write_bytes_new



HEADER = b"V1MMWX"
SALT = b"saltiest"
IV = b"the iv: 16 bytes"


def decrypt(appid: str, encrypted: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7
    if not encrypted.startswith(HEADER):
        raise ValueError("input does not start with V1MMWX")
    if len(appid) < 2:
        raise ValueError("AppID is too short")

    key = hashlib.pbkdf2_hmac(
        "sha1", appid.encode("utf-8"), SALT, 1000, dklen=32
    )
    encrypted_prefix = encrypted[len(HEADER) : len(HEADER) + 1024]
    encrypted_tail = encrypted[len(HEADER) + 1024 :]
    if len(encrypted_prefix) != 1024 or len(encrypted_prefix) % 16:
        raise ValueError("encrypted AES prefix must be exactly 1024 bytes")

    decryptor = Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor()
    padded_prefix = decryptor.update(encrypted_prefix) + decryptor.finalize()
    unpadder = PKCS7(128).unpadder()
    plain_prefix = unpadder.update(padded_prefix) + unpadder.finalize()

    # This is the macOS WeChat rule used by the captured V1MMWX packages.
    xor_key = 0x66 if appid.endswith("0a") else ord(appid[-2])
    plain_tail = bytes(value ^ xor_key for value in encrypted_tail)
    plain = plain_prefix + plain_tail
    if len(plain) < 14 or plain[0] != 0xBE or plain[13] != 0xED:
        raise ValueError("decrypted bytes do not have the expected wxapkg header")
    return plain


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("appid")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    args.output = disjoint(args.output, args.input)
    if args.output.exists():
        raise ValueError("Output already exists")
    source = args.input.read_bytes()
    clear = decrypt(args.appid, source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_bytes_new(args.output, clear)
    print(f"input_bytes={len(source)}")
    print(f"input_sha256={hashlib.sha256(source).hexdigest()}")
    print(f"output_bytes={len(clear)}")
    print(f"output_sha256={hashlib.sha256(clear).hexdigest()}")
    print(f"output_head={clear[:14].hex()}")


if __name__ == "__main__":
    main()
