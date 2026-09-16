---
name: openrouter-model-catalog
description: Generate or update a Codex model_catalog_json from OpenRouter.
---

# OpenRouter Model Catalog

Use the bundled generator as the single source of truth for conversion. Set
`skill_dir` to the directory containing this file.

## 1. Resolve the target

Honor a user-supplied catalog or config path. Otherwise let the generator inspect
`${CODEX_HOME:-$HOME/.codex}/openrouter.config.toml`, then `config.toml`, and fall
back to `openrouter.model.json` in the same Codex home.

Complete this step when the intended `model_catalog_json` path is unambiguous.

## 2. Generate and install

Run:

```bash
python3 "$skill_dir/scripts/generate_catalog.py"
```

Pass `--config PATH` when the user named a config file or `--output PATH` when
they named the catalog directly. Use `--check` for a read-only freshness check.

The generator fetches OpenRouter's models, derives the catalog schema and base
instructions from `codex debug models --bundled`, validates the candidate with
the installed Codex binary, and atomically replaces changed output. Preserve its
failure boundary: a fetch, conversion, or Codex validation error leaves the old
catalog intact.

Complete this step only when the command reports `updated` or `up to date` and
accounts for every unique model returned by OpenRouter.

## 3. Report activation state

Report the absolute catalog path, model count, and whether bytes changed. State
that already-running Codex app-server or Desktop processes load a catalog at
startup and need a restart before the new list is active.

Complete the skill when the on-disk catalog passed the installed Codex parser and
the activation state is explicit.
