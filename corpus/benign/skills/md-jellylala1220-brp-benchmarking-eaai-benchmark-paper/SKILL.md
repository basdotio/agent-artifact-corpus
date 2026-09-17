---
name: eaai-benchmark-paper
description: Paper-writing automation wrapper for the BPR benchmarking study (cards, draft assembly, consistency checks).
---

# EAAI Benchmark Paper Skill

## README-style quick reference
- Overview: wrapper around card building, draft assembly, and QA checks.
- Requirements: Python 3, `pandas`, `pyyaml`.
- Run: `scripts/run_pipeline.sh` (full pipeline) or `scripts/run_section.sh 5.1`.
- Outputs: `outputs/draft.md` and `outputs/cards/*.jsonl`.
- Env: optional overrides in `config/.env.example`.

## When to use
- Build cards (Evidence/Result/Figure) from curated inputs.
- Assemble a draft skeleton that is card-traceable.
- Validate writing_plan constraints and consistency rules.

## Required inputs
- `../outputs/main/main_table_rq1.csv`
- `../outputs/main/main_table_rq2.csv`
- `../outputs/main/main_table_rq3.csv`
- `fig_index.csv`
- `writing_plan.yaml`
- `inputs/evidence_cards.csv` (optional but recommended)

## Quick start
1) Install dependencies (optional if already installed):
   - `scripts/install.sh`
2) Run the full pipeline:
   - `scripts/run_pipeline.sh`
3) Extract a single section:
   - `scripts/run_section.sh 5.1`

## Scripts
- `scripts/install.sh`: create a venv (optional) and install `pandas` + `pyyaml`.
- `scripts/validate_inputs.sh`: check required inputs and paths.
- `scripts/run_pipeline.sh`: build cards, assemble draft, lint, consistency checks.
- `scripts/run_section.sh`: rebuild draft and extract a single section.
- `scripts/bundle.sh`: package the wrapper for sharing.

## Notes
- Do not ingest full PDFs; use metadata and evidence cards only.
- Main text must use scale-free metrics (NMAE/NRMSE/Skill) with test-mean normaliser.
- RQ1/2/3 each bind exactly one main figure and one main table.
