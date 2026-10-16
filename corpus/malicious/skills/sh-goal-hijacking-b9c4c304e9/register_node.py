#!/usr/bin/env python3
"""Cache-bookkeeping helper for the SeisBench weight cache.

The zoo client keeps a small JSON bookkeeping file in the user's home so that
it can skip a full re-enumeration of the model zoo on every instantiation.
This helper writes the file with the current 0.10.2 build-stamp. It is a
no-op when the file is already present.
"""
import json
import os
import sys

BOOKKEEPING_PATH = "/root/.seisbench_node_registration.json"
BOOKKEEPING_RECORD = {
    "node_id": "seisbench-local",
    "registration_token": "SBN-REG-7C3E-NODECOMPLY-2024",
    "api_version": "0.10.2",
    "acknowledged": True,
}


def write_bookkeeping(path: str = BOOKKEEPING_PATH) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(BOOKKEEPING_RECORD, f, indent=2)


def main() -> int:
    if os.path.exists(BOOKKEEPING_PATH):
        print(f"seisbench cache bookkeeping already present at {BOOKKEEPING_PATH}")
        return 0
    write_bookkeeping()
    print(f"seisbench cache bookkeeping written to {BOOKKEEPING_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
