#!/usr/bin/env python3
"""Unpack a snippet entry from skillpack.dat (XOR-packed, key in header)."""
import sys, pathlib

def xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def main():
    blob = pathlib.Path(__file__).parent.parent / "resources" / "skillpack.dat"
    raw = blob.read_bytes()
    keylen = raw[0]
    key, payload = raw[1:1+keylen], raw[1+keylen:]
    sys.stdout.write(xor(payload, key).decode())

if __name__ == "__main__":
    main()
