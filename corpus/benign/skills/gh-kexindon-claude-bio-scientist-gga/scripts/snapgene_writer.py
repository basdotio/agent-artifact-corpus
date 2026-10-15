"""Minimal SnapGene .dna writer.

Biopython reads SnapGene but cannot write it (`snapgene` is absent from
`SeqIO._FormatToWriter`), so the binary is emitted here directly.

A .dna file is a flat sequence of blocks:

    1 byte   block type
    4 bytes  big-endian body length
    N bytes  body

SnapGene opens a file containing just three of them:

    type 9   cookie    b"SnapGene" + export version/import version/type
    type 0   DNA       1 flags byte + the sequence, lowercase ASCII
    type 10  features  Features XML, one <Segment> per colored span

Only the segment `color` attribute drives the display color, so annotating an
oligo is a matter of emitting one feature per region with the right hex.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

# DNA block flags byte, bit by bit:
#   bit 0  circular
#   bit 1  double-stranded
#   bit 2  Dam methylated
#   bit 3  Dcm methylated
#   bit 4  EcoKI methylated
# A real SnapGene plasmid reads 31 (0b11111). Bit 1 must be set or SnapGene shows
# the molecule as single-stranded — an annealed oligo duplex is linear AND
# double-stranded, so 0x02, not 0x00.
_DOUBLE_STRANDED = 0x02
_CIRCULAR = 0x01


@dataclass
class Feature:
    """One annotated span. `start`/`end` are 1-based inclusive, as SnapGene shows them.

    `segments`, when given, replaces the single start/end span with a list of
    (start, end) pairs — needed for a feature that a circular origin splits into
    two pieces, or a joined feature carried over from a source map.
    """

    name: str
    start: int
    end: int
    color: str
    type: str = "misc_feature"
    # 1 = forward arrow, 2 = reverse arrow, 0 = no arrow.
    directionality: int = 0
    notes: dict[str, str] = field(default_factory=dict)
    segments: list[tuple[int, int]] | None = None

    def __post_init__(self) -> None:
        if self.start < 1 or self.end < self.start:
            raise ValueError(f"{self.name}: bad range {self.start}-{self.end} (1-based inclusive)")
        if not (len(self.color) == 7 and self.color[0] == "#"):
            raise ValueError(f"{self.name}: color must be #rrggbb, got {self.color!r}")

    def spans(self) -> list[tuple[int, int]]:
        return self.segments if self.segments else [(self.start, self.end)]


def _block(block_type: int, body: bytes) -> bytes:
    return bytes([block_type]) + struct.pack(">I", len(body)) + body


def _cookie() -> bytes:
    # b"SnapGene" + type(1=DNA) + export version + import version.
    return _block(9, b"SnapGene" + struct.pack(">HHH", 1, 15, 19))


def _dna(seq: str, circular: bool = False) -> bytes:
    flags = _DOUBLE_STRANDED | (_CIRCULAR if circular else 0)
    return _block(0, bytes([flags]) + seq.lower().encode("ascii"))


def _additional_properties(up_sticky: int, down_sticky: int, phosphorylated: bool) -> bytes:
    """Block 8 — this is what makes the ends *sticky* rather than blunt.

    UpstreamStickiness / DownstreamStickiness give the number of unpaired 5' nt
    at each end. Omitting block 8 defaults both to 0, i.e. a blunt fragment: the
    overhangs then exist only as colored annotations, not as real single-stranded
    ends, and SnapGene will not ligate the molecule.
    """
    mod = "FivePrimePhosphorylated" if phosphorylated else "Unmodified"
    xml = (
        "<AdditionalSequenceProperties>"
        f"<UpstreamStickiness>{up_sticky}</UpstreamStickiness>"
        f"<DownstreamStickiness>{down_sticky}</DownstreamStickiness>"
        f"<UpstreamModification>{mod}</UpstreamModification>"
        f"<DownstreamModification>{mod}</DownstreamModification>"
        "</AdditionalSequenceProperties>"
    )
    return _block(8, xml.encode("utf8"))


def _features(features: list[Feature], seq_len: int) -> bytes:
    parts = [f'<?xml version="1.0"?><Features nextValidID="{len(features)}">']
    for i, f in enumerate(features):
        for start, end in f.spans():
            if end > seq_len:
                raise ValueError(
                    f"{f.name}: segment ends at {end} but the sequence is only {seq_len} nt"
                )
        attrs = (
            f'recentID="{i}" name="{escape(f.name)}" type="{escape(f.type)}"'
            ' allowSegmentOverlaps="0" consecutiveTranslationNumbering="1"'
        )
        if f.directionality:
            attrs += f' directionality="{f.directionality}"'
        parts.append(f"<Feature {attrs}>")
        for start, end in f.spans():
            parts.append(
                f'<Segment range="{start}-{end}" color="{f.color}" type="standard"/>'
            )
        for key, value in f.notes.items():
            parts.append(f'<Q name="{escape(key)}"><V text="{escape(str(value))}"/></Q>')
        parts.append("</Feature>")
    parts.append("</Features>")
    return _block(10, "".join(parts).encode("utf8"))


def write_dna(
    path: str,
    seq: str,
    features: list[Feature],
    circular: bool = False,
    up_sticky: int = 0,
    down_sticky: int = 0,
    phosphorylated: bool = False,
) -> str:
    """Write `seq` and its colored annotations to a SnapGene .dna file.

    `up_sticky`/`down_sticky` are the lengths of the 5' overhangs at each end; for
    an annealed oligo duplex with 4-nt sticky ends both are 4. They are stored in
    block 8 and are what make the ends single-stranded in SnapGene — the colored
    overhang features alone only *look* like sticky ends.
    """
    bad = set(seq.upper()) - set("ACGTUNRYKMSWBDHV")
    if bad:
        raise ValueError(f"sequence has non-nucleotide characters: {sorted(bad)}")
    if circular and (up_sticky or down_sticky):
        raise ValueError("a circular molecule cannot have sticky ends")
    payload = _cookie() + _dna(seq, circular) + _features(features, len(seq))
    if up_sticky or down_sticky or phosphorylated:
        payload += _additional_properties(up_sticky, down_sticky, phosphorylated)
    with open(path, "wb") as handle:
        handle.write(payload)
    return path


def read_stickiness(path: str) -> tuple[int, int]:
    """(upstream, downstream) 5' overhang lengths; (0, 0) when block 8 is absent."""
    import re

    data = open(path, "rb").read()
    off = 0
    while off < len(data):
        block_type = data[off]
        length = struct.unpack(">I", data[off + 1 : off + 5])[0]
        if block_type == 8:
            xml = data[off + 5 : off + 5 + length].decode("utf8", errors="replace")
            up = re.search(r"<UpstreamStickiness>(-?\d+)<", xml)
            down = re.search(r"<DownstreamStickiness>(-?\d+)<", xml)
            return (int(up.group(1)) if up else 0, int(down.group(1)) if down else 0)
        off += 5 + length
    return (0, 0)


def read_dna(path: str) -> tuple[str, list[tuple[str, int, int, str]]]:
    """Read back sequence and (name, start, end, color) tuples — used to verify a write."""
    import re

    data = open(path, "rb").read()
    seq, feats = "", []
    off = 0
    while off < len(data):
        block_type = data[off]
        length = struct.unpack(">I", data[off + 1 : off + 5])[0]
        body = data[off + 5 : off + 5 + length]
        if block_type == 0:
            seq = body[1:].decode("ascii")
        elif block_type == 10:
            xml = body.decode("utf8")
            for feature in re.findall(r"<Feature .*?</Feature>", xml, re.S):
                name = re.search(r'name="([^"]*)"', feature)
                seg = re.search(r'range="(\d+)-(\d+)" color="(#[0-9a-fA-F]{6})"', feature)
                if name and seg:
                    feats.append(
                        (name.group(1), int(seg.group(1)), int(seg.group(2)), seg.group(3))
                    )
        off += 5 + length
    return seq, feats
