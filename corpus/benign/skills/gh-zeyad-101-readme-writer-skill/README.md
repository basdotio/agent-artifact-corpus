# readme-writer

A Claude Skill that writes a production-quality `README.md` for any code
repository — grounded entirely in what the repo actually contains. No
placeholder text, no invented badges or benchmarks, no boilerplate sections
that don't apply.

## What it does

Give it a repo link, or paste/upload the repo's files, and it:

1. Clones or reads the repo
2. Inventories manifests, CI config, build files, and source
3. Works out what kind of project it is from the evidence — not a fixed
   category list, the same logic applies to whatever it finds
4. Drafts a README using only the sections that project actually needs
5. Runs a style pass to strip AI-sounding filler and unearned superlatives

Every line in the output has to trace back to something found in the repo.
If the evidence isn't there, the section is dropped, not stubbed out.

## Structure

- `SKILL.md` — the workflow Claude follows
- `assets/master-template.md` — the full menu of possible README sections
- `references/section-selection.md` — evidence-based rules for which
  sections apply to a given repo
- `references/writing-style.md` — rules against filler and fabrication in
  the generated prose

## Installing

- **claude.ai**: Settings → Capabilities → Skills → upload a packaged
  `.skill` file. Build one from this folder with:
  ```sh
  python package_skill.py path/to/readme-writer
  ```
  (from Anthropic's `skill-creator` skill, or any equivalent packager —
  it just validates the frontmatter and zips the folder).
- **Claude Code**: drop this folder into your skills directory, e.g.
  `~/.claude/skills/readme-writer` or a project's `.claude/skills/`.

## Usage

Ask Claude to write, generate, or improve a README for a repo — paste a
repo link or upload the project's files.

## License

MIT — see `LICENSE`.
