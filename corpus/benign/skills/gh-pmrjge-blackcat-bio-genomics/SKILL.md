---
name: bio-genomics
description: Use for sequencing data — QC, alignment, BAM/CRAM, variant calling, VCF, RNA-seq.
---
# Genomics: reads to variants and counts

Data rules (human data stays put) and baseline: `bio-chem-computing`. Running at scale: `bio-pipelines`.

## Versions
- samtools 1.24 and bcftools 1.24 — Verified 2026-10-02 https://github.com/samtools/samtools/releases/latest https://github.com/samtools/bcftools/releases/latest
- GATK 4.7.0.0 — Verified 2026-10-02 https://github.com/broadinstitute/gatk/releases/latest
- Other tools (fastp, BWA-MEM2, minimap2, STAR, salmon, DeepVariant, Clair3, VEP) — check the installed version (`<tool> --version`) and record it; unverified here.

## Standard paths
| data | path |
|---|---|
| short-read DNA (WGS/WES) | fastp/FastQC → BWA-MEM2 → sort + mark duplicates → (BQSR) → DeepVariant or GATK HaplotypeCaller (gVCF) → joint genotyping → filtering → annotation (VEP/snpEff) |
| long reads (ONT/PacBio HiFi) | minimap2 (preset per platform) → Clair3/DeepVariant (HiFi) and Sniffles2 for SVs |
| bulk RNA-seq | fastp → salmon (quasi-mapping, with decoys) or STAR → counts → DESeq2/edgeR (`data-analysis` for statistics) |
| somatic variants | tumor/normal with Mutect2 + panel of normals + contamination estimates; never germline callers |
For production, prefer the nf-core pipeline (sarek, rnaseq) over hand-built chains.

## Rules
- Same reference FASTA (with `.fai` and `.dict`) for alignment, calling and annotation; contig names checked (`samtools view -H | rg '^@SQ' | head`).
- Read groups set at alignment (`-R '@RG\tID:…\tSM:…\tPL:ILLUMINA\tLB:…'`); sample names consistent with the samplesheet.
- Coordinate-sorted, indexed BAM/CRAM; CRAM needs the exact reference to decode — archive it with the data.
- Duplicate marking for PCR-based libraries; not for amplicon data without UMIs (use UMI-aware dedup when UMIs exist).
- Coordinates: VCF/SAM are 1-based, BED is 0-based half-open — convert deliberately.
- VCF hygiene: `bcftools norm -m -any -f ref.fa` (split multiallelics, left-align) before comparing or annotating; `bcftools view -i 'QUAL>30 && INFO/DP>10'` style filters documented with reasons; `bcftools stats` for summaries.
- Benchmark callers against truth sets (GIAB HG002 with hap.py/vcfeval in stratified regions) before trusting a new pipeline.
- RNA-seq: library strandedness checked (salmon `lib_format_counts.json` or RSeQC); gene/transcript IDs from the same annotation release as the index.

## Quick checks (cheap, read-only)
`samtools flagstat` / `samtools stats` (mapping rate, properly paired, duplicates), `samtools idxstats` (per-contig counts, sex check by chrY), `mosdepth` (coverage), `bcftools stats` + `plot-vcfstats`, Ti/Tv ratio (~2.0–2.1 WGS, ~2.8–3.0 exome) and het/hom ratio as sanity checks, MultiQC across samples.

## Pitfalls
Mixed genome builds (hg19 vs GRCh38 vs T2T) between inputs; `chr` prefix mismatches; BED off-by-one; calling on unsorted or unindexed BAMs; joint-genotyping samples aligned to different references; treating no-calls as reference; annotating with a different transcript set than the clinic uses; filtering by hard thresholds copied from another platform.

## Verify
Mapping rate, duplication and coverage within expectations per sample · variant counts, Ti/Tv and het/hom plausible · truth-set F1 reported when validating a pipeline · reference build, annotation release and tool versions recorded.
