# Skill template

Copy this folder to `skills/<your-skill-name>/` and edit.

- Folder name and `name:` in `SKILL.md` must match: lowercase, hyphens.
- `name` and `description` are the only required frontmatter fields.
- Keep `SKILL.md` short. Put bulk in `references/` and say when to read each file.
- Set `metadata.internal: true` in the frontmatter to keep a draft out of normal discovery.
- Optional dirs: `scripts/` (self-contained, helpful errors, referenced relative to the skill root), `references/` (loaded on demand), `assets/` (templates, data).
- Limits (agentskills.io spec; Claude adds: no `anthropic`/`claude` in the name, no XML tags in `name` or `description`):
  - `name`: 1-64 chars, `a-z 0-9 -`, no leading, trailing or double hyphens, must equal the folder name.
  - `description`: 1-1024 chars. `SKILL.md` body: under 500 lines (about 5k tokens). Keep file references one level deep from `SKILL.md`.
  - Optional: `license` (a name like `MIT`, or a bundled file), `compatibility` (max 500 chars, only if there are real environment needs), `metadata` (string-to-string map), `allowed-tools` (experimental).
- Validate with `skills-ref validate ./skills/<name>` (https://github.com/agentskills/agentskills/tree/main/skills-ref).
- Portable frontmatter: stick to `name`, `description`, `metadata`. Agent-specific extras are ignored where unsupported:
  - Cursor: `paths` (glob list scoping the skill to matching files; replaces legacy `globs`), `disable-model-invocation: true` (slash-command only), `icon`, `color`.
  - Claude Code: `allowed-tools`, `context: fork`.
- Write the `description` in third person, saying what the skill does and when to use it ("Processes X. Use when ..."), not "I can" or "you can".
- Name style: gerund (`processing-pdfs`) or noun phrase (`pdf-processing`); avoid vague names like `helper` or `utils`. Stay consistent across the repo.
- Avoid dated guidance in the body; put legacy material in an "old patterns" section. Use one term per concept.
- Before sharing: write at least three evals, and test on Haiku, Sonnet and Opus.
- Write the `description` for triggering: it is what the agent reads to decide relevance.
- Test with `npx skills add ./ --list` from the repo root.

The template's frontmatter sets `metadata.internal: true` so the CLI doesn't list it as an installable skill (it finds `SKILL.md` files outside `skills/` too). Delete that `metadata` block in your copy.
