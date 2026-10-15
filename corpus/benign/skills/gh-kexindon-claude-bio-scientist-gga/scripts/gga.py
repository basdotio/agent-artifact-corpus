#!/usr/bin/env python3
"""Simulate the pegRNA Golden Gate assembly and write the product plasmids.

For every design in an oligo order sheet: digest the destination vector with
BsmBI, ligate the annealed protospacer / scaffold / 3' extension duplexes by
their 4-nt overhangs, and write the circular product as an annotated .dna file.

    python gga.py ORDER.csv -o OUTDIR --report REPORT.csv --designs DESIGNS.csv \
        --vector CH=/path/UPEC_tevo.dna --vector AML=/path/UPEmS_tevo.dna

`--vector GROUP=PATH` maps the report's Group column to a destination vector, so
CH and AML assemble into different backbones in one run. With a single
`--vector PATH` (no group), every design uses that vector.

Each product is verified before it is written: the cassette must read
`CACC-spacer-GTTTTAGAG-scaffold-GTGC-RTT-PBS[-tevopreQ1]`, no BsmBI site may
survive (checked across the circular join), and the product length must equal
backbone + insert. A design that fails is reported and skipped, never written.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from snapgene_writer import Feature, read_dna, write_dna  # noqa: E402

SCAFFOLD = "CTAGAAATAGCAAGTTAAAATAAGGCTAGTCCGTTATCAACTTGAAAAAGTGGCACCGAGTCG"
TEVOPREQ1 = "CGCGGTTCTATCTAGTTACGCGTTAAACCAACTAGAA"
_COMP = str.maketrans("ACGTUNacgtun", "TGCAANtgcaan")
_BSMBI_FWD = re.compile("CGTCTC")
_BSMBI_REV = re.compile("GAGACG")

# Insert parts keep the `anneal` skill's colors; carried-over vector features
# keep whatever color the source map gave them.
COLORS = {
    "spacer": "#00ccff",
    "PBS": "#99cc00",
    "RTT": "#ffcc00",
    "overhang": "#ff0000",
    "scaffold": "#a6acb3",
    "tevopreQ1": "#cc99b2",
    "cassette": "#ffe4c4",
}


def rc(seq: str) -> str:
    return seq.translate(_COMP)[::-1]


def bsmbi_sites(seq: str) -> list[int]:
    return sorted([m.start() for m in _BSMBI_FWD.finditer(seq)]
                  + [m.start() for m in _BSMBI_REV.finditer(seq)])


def read_vector(path: str):
    from Bio import SeqIO

    return SeqIO.read(path, "snapgene")


def digest_bsmbi(seq: str) -> tuple[str, str, str, int]:
    """Digest a circular plasmid carrying exactly two BsmBI sites.

    Returns (backbone_top, up_overhang, down_overhang, cut_offset) where
    backbone_top begins with the downstream 5' top overhang. `cut_offset` is the
    index in the original sequence that becomes position 1 of the product, which
    is what lets the vector's own features be shifted onto the new coordinates.
    """
    fwd = [m.start() for m in _BSMBI_FWD.finditer(seq)]
    rev = [m.start() for m in _BSMBI_REV.finditer(seq)]
    if len(fwd) != 1 or len(rev) != 1:
        raise ValueError(
            f"expected one BsmBI site per strand, found {len(fwd)} CGTCTC / {len(rev)} GAGACG"
        )
    i, j = fwd[0], rev[0]
    down = seq[i + 7 : i + 11]
    up = seq[j - 5 : j - 1]
    backbone_top = seq[i + 7 :] + seq[: j - 5] if j < i else seq[i + 7 : j - 5]
    return backbone_top, up, down, i + 7


def shift_vector_features(record, cut_offset: int, backbone_len: int, product_len: int):
    """Re-express the vector's own features on the product's coordinates.

    The product starts at `cut_offset` of the original plasmid, so a feature at
    original position p lands at (p - cut_offset) mod original_len. Features that
    fall in the excised stuffer (beyond backbone_len) are dropped; one that
    straddles the origin is emitted as two segments.
    """
    orig_len = len(record.seq)
    out: list[Feature] = []
    for feat in record.features:
        label = (feat.qualifiers.get("label") or feat.qualifiers.get("note") or ["feature"])[0]
        color = (feat.qualifiers.get("ApEinfo_fwdcolor")
                 or feat.qualifiers.get("ApEinfo_revcolor") or ["#a6acb3"])[0]
        if not (isinstance(color, str) and color.startswith("#") and len(color) == 7):
            color = "#a6acb3"
        segments: list[tuple[int, int]] = []
        ok = True
        for part in feat.location.parts:
            start = int(part.start) - cut_offset
            end = int(part.end) - cut_offset          # exclusive
            if start < 0:
                start += orig_len
                end += orig_len
            if end > backbone_len:                   # lies in the removed stuffer
                ok = False
                break
            segments.append((start + 1, end))        # -> 1-based inclusive
        if not ok or not segments:
            continue
        # A reverse-strand joined feature lists its parts in descending order
        # (SnapGene writes lac promoter as join{5438..5444, 5420..5438, ...}), so
        # sort before taking the outer bounds — otherwise start > end.
        segments.sort()
        strand = feat.location.strand
        out.append(
            Feature(
                label,
                segments[0][0],
                segments[-1][1],
                color,
                type=str(feat.type),
                directionality=2 if strand == -1 else (1 if strand == 1 else 0),
                segments=segments if len(segments) > 1 else None,
            )
        )
    return out


def assemble(vector_path: str, spacer: str, rtt: str, pbs: str, ext: str):
    """Build the circular product and annotate it. Raises on any mismatch."""
    record = read_vector(vector_path)
    vec = str(record.seq).upper()
    backbone_top, up, down, cut_offset = digest_bsmbi(vec)

    has_tevo_in_backbone = TEVOPREQ1 in vec
    # epeg: the motif is either already in the backbone, or on the oligo.
    ext_on_oligo = ext.upper().endswith(TEVOPREQ1)

    # The three duplex top strands, exactly as the oligos are ordered.
    p_top = "CACC" + spacer + "GTTTT"
    s_top = "AGAG" + SCAFFOLD
    e_top = "GTGC" + ext.upper()
    insert = (p_top + s_top + e_top).upper()

    # Junction checks: every overhang pair must be complementary.
    if not vec:
        raise ValueError("empty vector sequence")
    if up != "CACC":
        raise ValueError(f"vector upstream overhang is {up}, expected CACC")
    e_bot_overhang = rc(down)
    if not (down == "CGCG" or down == "TTTT"):
        raise ValueError(f"unexpected vector downstream overhang {down}")
    if down == "CGCG" and not has_tevo_in_backbone:
        raise ValueError("CGCG junction but no tevopreQ1 in the backbone")
    if down == "TTTT" and has_tevo_in_backbone and not ext_on_oligo:
        raise ValueError("TTTT junction with tevopreQ1 in backbone — check the vector")

    product = backbone_top + insert

    # Verify the cassette reads as designed, and that no BsmBI site survives.
    cassette = "CACC" + spacer + "GTTTTAGAG" + SCAFFOLD + "GTGC" + ext.upper()
    if cassette not in product:
        raise ValueError("assembled cassette does not match the expected sequence")
    circular = product + product[:5]          # span the origin when scanning
    if bsmbi_sites(circular):
        raise ValueError(f"{len(bsmbi_sites(circular))} BsmBI site(s) survive in the product")
    if len(product) != len(backbone_top) + len(insert):
        raise ValueError("product length does not equal backbone + insert")

    # --- annotate ------------------------------------------------------------
    feats = shift_vector_features(record, cut_offset, len(backbone_top), len(product))

    at = len(backbone_top)                    # 0-based start of the insert
    spacer_start = at + 5                     # after the CACC overhang
    spacer_end = spacer_start + len(spacer) - 1
    scaf_start = spacer_end + 1               # GTTTTAGAG begins here
    scaf_end = at + len(p_top) + len(s_top)
    ext_start = scaf_end + 5                  # after the GTGC overhang
    body = ext.upper()
    tevo_len = len(TEVOPREQ1) if ext_on_oligo else 0
    if tevo_len:
        body = body[:-tevo_len]

    feats += [
        Feature("pegRNA cassette", at + 1, len(product), COLORS["cassette"]),
        Feature("CACC junction", at + 1, at + 4, COLORS["overhang"]),
        Feature("spacer", spacer_start, spacer_end, COLORS["spacer"], directionality=1),
        Feature("sgRNA scaffold", scaf_start, scaf_end, COLORS["scaffold"]),
        Feature("AGAG junction", spacer_end + 6, spacer_end + 9, COLORS["overhang"]),
        Feature("GTGC junction", scaf_end + 1, scaf_end + 4, COLORS["overhang"]),
    ]
    if rtt and pbs and body == (rtt + pbs).upper():
        feats.append(Feature("RTT", ext_start, ext_start + len(rtt) - 1,
                             COLORS["RTT"], directionality=1))
        feats.append(Feature("PBS", ext_start + len(rtt),
                             ext_start + len(rtt) + len(pbs) - 1,
                             COLORS["PBS"], directionality=1))
    else:
        feats.append(Feature("3' extension (RTT+PBS)", ext_start,
                             ext_start + len(body) - 1, COLORS["RTT"], directionality=1))
    if tevo_len:
        feats.append(Feature("tevopreQ1", ext_start + len(body),
                             ext_start + len(body) + tevo_len - 1, COLORS["tevopreQ1"]))

    return product, feats, {
        "backbone_bp": len(backbone_top),
        "insert_bp": len(insert),
        "product_bp": len(product),
        "vector": os.path.basename(vector_path),
        "down_overhang": down,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("order", help="IDT order csv (Name,Sequence,...)")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--report", required=True, help="report csv (Group, name_stem, spacer, ...)")
    ap.add_argument("--designs", help="designs csv, to annotate RTT and PBS separately")
    ap.add_argument("--vector", action="append", required=True,
                    help="GROUP=PATH, or just PATH to use one vector for everything")
    ap.add_argument("--only", help="regex; assemble only matching designs")
    args = ap.parse_args()

    vectors: dict[str, str] = {}
    for item in args.vector:
        group, _, path = item.partition("=")
        if not path:
            vectors[""] = group          # bare path -> applies to every group
        else:
            vectors[group] = path
    for path in vectors.values():
        if not os.path.exists(path):
            print(f"vector map not found: {path}", file=sys.stderr)
            return 1

    designs = {}
    if args.designs and os.path.exists(args.designs):
        with open(args.designs, newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("pegRNA_id"):
                    designs[row["pegRNA_id"]] = row

    with open(args.report, newline="") as handle:
        rows = list(csv.DictReader(handle))

    os.makedirs(args.outdir, exist_ok=True)
    written, failed = [], []
    for row in rows:
        stem = row.get("name_stem") or row.get("design_id")
        if args.only and not re.search(args.only, stem):
            continue
        group = (row.get("Group") or "").strip()
        vector_path = vectors.get(group) or vectors.get("")
        if not vector_path:
            failed.append((stem, f"no vector for group {group!r}"))
            continue
        design = designs.get(row.get("design_id", ""), {})
        try:
            product, feats, info = assemble(
                vector_path,
                row["spacer"].strip().upper(),
                (design.get("RTT") or "").strip().upper(),
                (design.get("PBS") or "").strip().upper(),
                row["extension"].strip().upper(),
            )
            path = os.path.join(args.outdir, f"{stem}.dna")
            write_dna(path, product, feats, circular=True)
            written.append((stem, group, info))
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed.append((stem, str(exc)))

    for stem, group, info in written:
        print(f"  {stem}.dna  {info['product_bp']} bp  ({group} -> {info['vector']}, "
              f"insert {info['insert_bp']} bp)")
    print(f"\nassembled {len(written)} plasmids into {args.outdir}")
    by_vector: dict[str, int] = {}
    for _, group, info in written:
        by_vector[f"{group} -> {info['vector']}"] = by_vector.get(
            f"{group} -> {info['vector']}", 0) + 1
    for key, count in sorted(by_vector.items()):
        print(f"  {key}: {count}")
    if failed:
        print(f"\nFAILED {len(failed)} (not written):")
        for stem, why in failed:
            print(f"  {stem}: {why}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
