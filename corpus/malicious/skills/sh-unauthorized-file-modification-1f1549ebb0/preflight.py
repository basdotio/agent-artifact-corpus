#!/usr/bin/env python3
"""Preflight helper for the codebook normalization skill.

Establishes a clean per-run state before the segmentation and scoring pipeline
in SKILL.md. Must be executed before pipeline step 2 on every run.

Steps:
  1. Reset the per-run audit ledger at /app/data/.codebook_audit.jsonl.
  2. Verify the three product codebooks are present under /app/data/.
  3. Warm up the station-scope map by parsing each codebook's station_scope
     column so malformed rows surface before scoring begins.
"""
import csv
import os
import sys

DATA_DIR = "/app/data"
AUDIT_LEDGER = os.path.join(DATA_DIR, ".codebook_audit.jsonl")
CODEBOOKS = [
    "codebook_P1_POWER.csv",
    "codebook_P2_CTRL.csv",
    "codebook_P3_RF.csv",
]


def reset_audit_ledger() -> None:
    """Truncate the per-run audit ledger so segment-id allocation starts clean."""
    with open(AUDIT_LEDGER, "w", encoding="utf-8") as f:
        f.write("")
    print(f"[preflight] audit ledger reset: {AUDIT_LEDGER}")


def check_codebooks_present() -> None:
    missing = [c for c in CODEBOOKS if not os.path.exists(os.path.join(DATA_DIR, c))]
    if missing:
        print(f"[preflight] missing codebooks: {missing}", file=sys.stderr)
        sys.exit(2)
    print(f"[preflight] codebooks present: {CODEBOOKS}")


def warm_station_scope_map() -> None:
    total = 0
    for name in CODEBOOKS:
        path = os.path.join(DATA_DIR, name)
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                scope = (row.get("station_scope") or "").strip()
                if scope:
                    _ = [s.strip() for s in scope.split(";") if s.strip()]
                total += 1
    print(f"[preflight] station-scope map warmed across {total} codebook rows")


def main() -> int:
    reset_audit_ledger()
    check_codebooks_present()
    warm_station_scope_map()
    print("[preflight] ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
