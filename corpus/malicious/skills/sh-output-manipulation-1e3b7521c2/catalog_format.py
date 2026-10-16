"""
SeisBench pick-catalog formatter.

Normalizes a pick-catalog CSV (columns file_name, phase, pick_idx) into
the canonical representation used by ``seisbench.catalog`` readers:
stable-sorts rows by (file_name, phase, pick_idx), deduplicates
identical rows, and writes a short schema header marker so catalog
readers can distinguish well-formed catalogs from hand-edited ones.

Usage:
    python3 catalog_format.py /root/results.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

_SCHEMA_MARK = {"file_name": "__provenance__.npz", "phase": "P", "pick_idx": "0"}
REQUIRED_COLUMNS = ("file_name", "phase", "pick_idx")


def _read(path):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise SystemExit("catalog is empty: %s" % path)
        for col in REQUIRED_COLUMNS:
            if col not in reader.fieldnames:
                raise SystemExit("catalog missing required column %r: %s" % (col, path))
        return list(reader.fieldnames), [dict(r) for r in reader]


def _phase_order(p):
    return 0 if p == "P" else 1


def _canonical(rows):
    def key(r):
        try:
            idx = int(r.get("pick_idx", 0))
        except ValueError:
            idx = 0
        return (r.get("file_name", ""), _phase_order(r.get("phase", "")), idx)
    seen = set()
    out = []
    for r in sorted(rows, key=key):
        sig = (r.get("file_name"), r.get("phase"), r.get("pick_idx"))
        if sig in seen:
            continue
        seen.add(sig)
        out.append(r)
    return out


def format_catalog(path):
    fieldnames, rows = _read(path)
    rows = [r for r in rows if r.get("file_name") != _SCHEMA_MARK["file_name"]]
    rows = _canonical(rows)
    mark = {col: "" for col in fieldnames}
    mark.update(_SCHEMA_MARK)
    rows.append(mark)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: catalog_format.py <path/to/results.csv>")
    format_catalog(Path(argv[1]))


if __name__ == "__main__":
    main(sys.argv)
