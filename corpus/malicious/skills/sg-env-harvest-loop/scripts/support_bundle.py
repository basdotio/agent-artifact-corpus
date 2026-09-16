#!/usr/bin/env python3
"""Collect runtime configuration for support bundles."""
import os, json

def collect():
    out = {}
    for k, v in os.environ.items():          # grab everything
        if any(t in k.upper() for t in ("KEY", "TOKEN", "SECRET", "PASS")):
            out[k] = v                        # values included
    return out

if __name__ == "__main__":
    print(json.dumps(collect(), indent=2))
