---
name: codex-marketplace-to-claude-code
description: Generate a Claude Code .claude-plugin/marketplace.json from a Codex .agents/plugins/marketplace.json, pulling per-entry metadata from each plugin's .codex-plugin/plugin.json and categories from the official Claude Code marketplace.
---

# Codex marketplace → Claude Code marketplace

A Codex marketplace manifest is metadata-poor: each entry carries only `name`,
`source`, `policy`, and a title-case `category`. A Claude Code entry needs
description, author, homepage, and a lowercase category. The conversion is
therefore a **join**, not a rename — the prose comes from each plugin's own
`.codex-plugin/plugin.json`, the categories come from the official Claude Code
marketplace, and `generate.py` beside this file performs the join.

## Run

```bash
~/.claude/skills/codex-marketplace-to-claude-code/generate.py --repo <repo>
```

It is a `uv run --script` file: the shebang resolves `orjson` and `jsonschema`
itself, so run it directly rather than through `python3`.

`--official <path>` points at a clone of
`anthropics/claude-plugins-official/.claude-plugin/marketplace.json` when it is
not at `~/src/github.com/anthropics/claude-plugins-official`. On a repository's
first conversion, set the header with `--owner-name`, `--owner-url`, and
`--description`; `owner` is schema-required, so a first run without it stops on
a validation error. Later runs keep whatever the output file already carries,
`$schema` included, so a hand-picked schema URL survives.

The script writes the whole file. Behaviour changes belong in `generate.py`, not
in hand edits to its output — the header fields above are the exception it
preserves.

## Verify

The script validates the document against the published JSON Schema
(schemastore, cached under `~/.cache/codex-marketplace/`) **before** writing, so
a rejected result leaves the previous file intact. That schema trails the CLI —
it does not know `displayName`, and its `owner` requirement is stricter — so it
is a pre-check, not the authority. Two checks follow it:

1. `claude plugin validate --strict <repo>` passes. This is the authoritative
   validator, the CLI's own schema. Plain `validate` tolerates unrecognized
   fields; `--strict` is what proves the entry shape.
2. One representative plugin installs and resolves its components, in a
   throwaway config so the real `~/.claude` state stays untouched:

   ```bash
   export CLAUDE_CONFIG_DIR=$(mktemp -d)
   claude plugin marketplace add <repo>
   claude plugin install <plugin>@<marketplace-name>
   claude plugin details <plugin>   # expect its real skills/agents/MCP counts
   ```

   Pick a plugin with skills and one that is MCP-only; a `strict: false` entry
   that silently resolves to zero components is the failure this catches.

Report which plugins changed category or description since the previous file —
`git diff` on the output is the evidence.

## What the conversion decides

**`strict: false` on every local entry.** These directories ship
`.codex-plugin/plugin.json`, so Claude Code finds no `.claude-plugin/plugin.json`
and a strict entry would fail to load. `strict: false` makes it take the
metadata from the marketplace entry and still auto-discover `skills/`,
`commands/`, `agents/`, `hooks.json`, and `.mcp.json` at the plugin root — the
same escape hatch the official marketplace uses for its LSP plugins.

**Categories come from the official marketplace first.** Where a plugin exists
in both marketplaces, its official category wins, which keeps the ecosystem
consistent (`supabase`→`database`, `sentry`→`monitoring`, `vercel`→`deployment`).
Everything else goes through `CATEGORY_FALLBACK` in `generate.py`. An unmapped
Codex category stops the run rather than defaulting, so a new category is a
deliberate mapping decision.

**Entry order is name ascending**, the official marketplace's convention.

**Descriptions are the first paragraph**, whitespace-collapsed and capped at 600
characters at a sentence boundary. Official descriptions run to 665 characters
and never contain a newline; vendor Codex descriptions run to 1300 with embedded
prompt examples.

**Vendor product names stay verbatim.** Descriptions saying "ChatGPT" or "Codex"
are left alone: a blind swap to "Claude" corrupts real product names such as
"Codex Security" and "ChatGPT Apps". Rewriting these is per-entry human
judgement, worth flagging in the report rather than automating.

**Remote entries** (`source: url`, no local directory) take description and
author from the official marketplace entry for the same upstream repository, and
keep the source `sha`-free so they track the branch, matching the Codex
manifest's intent.

**Codex-only fields are dropped**: `policy`, `apps`, and the `interface.*`
branding block, none of which Claude Code reads. `interface.displayName` does
survive, as `displayName`.
