---
name: gga
description: Simulate the pegRNA Golden Gate assembly in silico and write the product plasmids as annotated SnapGene .dna files — digest the destination vector with BsmBI, ligate the protospacer/scaffold/3'-extension duplexes by their 4-nt overhangs, verify the product, and annotate spacer, RTT, PBS and the junctions in color while carrying over the vector's own features. Different groups can go into different backbones in one run (e.g. CH into UPEC-tevo, AML into UPEmS-tevo). Use whenever asked to simulate or verify Golden Gate assembly, clone pegRNAs into a vector in silico, or produce .dna maps of the finished plasmids from an oligo order sheet.
---

# gga — in-silico Golden Gate → annotated product plasmids

Takes the oligo order sheet written by `pegrna_gga_oligo_order.ipynb` and writes
one **circular** `.dna` file per design: the finished plasmid, with the pegRNA
cassette annotated and the vector's own features preserved.

Related: the `anneal` skill writes the *annealed oligo duplexes* (the inputs to
this reaction). This skill writes the *products*.

## Usage

```bash
python ~/.claude/skills/gga/scripts/gga.py ORDER.csv -o OUTDIR \
    --report REPORT.csv --designs DESIGNS.csv \
    --vector CH=/path/UPEC_tevo.dna \
    --vector AML=/path/UPEmS_tevo.dna
```

| flag | meaning |
|---|---|
| `ORDER.csv` | the IDT sheet (positional; the spacer/extension come from `--report`) |
| `-o OUTDIR` | created if absent; one `<name_stem>.dna` per design |
| `--report` | **required** — supplies `Group`, `name_stem`, `spacer`, `extension` |
| `--designs` | annotates RTT and PBS separately instead of one merged block |
| `--vector G=PATH` | repeatable: maps a `Group` to its vector. A bare `--vector PATH` applies to every group |
| `--only REGEX` | assemble a subset |

`--vector CH=… --vector AML=…` is what routes CH into UPEC-tevo and AML into
UPEmS-tevo in a single run. A design whose group has no vector is reported, not
guessed.

## What it does

1. **Digest** — finds the vector's single `CGTCTC` and single `GAGACG` site,
   cuts 1/5, and keeps the backbone (the stuffer between the sites is discarded).
   Raises if the site count is not exactly one per strand.
2. **Ligate** — joins the protospacer, scaffold and 3' extension top strands.
   Product = `backbone + CACC-spacer-GTTTT | AGAG-scaffold | GTGC-extension`.
3. **Verify, then write** — a design is only written if the cassette reads
   exactly `CACC spacer GTTTTAGAG scaffold GTGC RTT PBS [tevopreQ1]`, **no BsmBI
   site survives** (scanned across the circular join, not just the linear
   sequence), and `len(product) == len(backbone) + len(insert)`. Failures are
   listed at the end and the exit status is non-zero.

## Output

Circular `.dna`, so SnapGene shows it as a plasmid. Insert colors match the
`anneal` skill; vector features keep their original colors.

| feature | color |
|---|---|
| pegRNA cassette (whole insert) | bisque `#ffe4c4` |
| spacer | cyan `#00ccff` |
| RTT | amber `#ffcc00` |
| PBS | green `#99cc00` |
| CACC / AGAG / GTGC junctions | **red** `#ff0000` |
| sgRNA scaffold | grey `#a6acb3` |
| vector's own features | as in the source map |

`sgRNA scaffold` spans the full `GTTTTAGAG + SCAFFOLD`, and the red `AGAG
junction` is drawn over part of it — same convention as `anneal`, because those
9 nt are scaffold nt 1–9, not a linker.

## Two things that are easy to get wrong

- **Vector features must be shifted, not copied.** The product begins at the
  downstream cut, so a feature at original position *p* moves to
  `(p - cut_offset) mod len(vector)`. Features landing in the excised stuffer are
  dropped; one straddling the new origin is emitted as two segments.
- **Reverse-strand joined features list their parts in descending order.**
  SnapGene writes UPEC-tevo's `lac promoter` as
  `join{5438..5444, 5420..5438, 5413..5420}`. Taking `parts[0].start` and
  `parts[-1].end` as the bounds yields `4324-4305` — start after end — and the
  write is rejected. Sort the shifted segments before taking the outer bounds.

## Verifying output

The notebook's own `assemble()` is an independent implementation of the same
reaction; comparing against it is the strongest check available:

```python
r = assemble(MAP, row['spacer'], row['extension'], epeg)   # from the notebook
seq, feats = read_dna(f'{stem}.dna')
assert seq.upper() == r['product'].upper()
```

Also worth asserting: `SeqIO.read(path, "snapgene")` parses; the DNA block's
flags byte is `1` (circular); `CGTCTC`/`GAGACG` absent from `seq + seq[:5]`; the
`spacer`/`RTT`/`PBS` features match the report and designs csv; and enough vector
features survived (UPEC-tevo yields ~61 of its 71).
