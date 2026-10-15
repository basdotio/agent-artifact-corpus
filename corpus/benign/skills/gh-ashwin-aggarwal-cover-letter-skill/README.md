# cover-letter-builder

A Claude Skill that writes cover letters as ATS-parsable LaTeX for Overleaf.

## What it does

Paste a job description and get back a complete .tex file ready to paste into Overleaf. The skill picks the two experiences from your own notes that best match the role, frames them for that role type, and writes against a strict style guide that strips out common AI-writing tells: em dashes, "not X but Y" constructions, stock openers, and filler vocabulary.

## How it works

Each run follows the same pipeline:

1. **Company research.** Finds one concrete, recent fact about the company (a launch, a blog post, a paper) and notes its domain. If nothing concrete turns up, the letter skips the hook instead of inventing one.
2. **Requirement extraction.** Pulls the 5 to 7 hard requirements from the posting and ranks them by prominence.
3. **Routing matrix filter.** Keeps only the experiences you have marked as valid evidence for this role type.
4. **Scoring.** Scores each remaining experience on requirement overlap, domain fit, and stack overlap, then takes the top two.
5. **Drafting.** Writes the hook, two evidence paragraphs, and a closing, applying every rule in `references/style.md`.
6. **Template fill.** Drops those values into the editable region of your template. Nothing else in the file changes.
7. **Self-check.** Verifies style rules, traces every claim back to your context file, reports word count and any requirements you had no evidence for.

**The routing matrix.** One project can be good evidence for several kinds of roles, and it should read differently for each. A retrieval system you built might be an evaluation story for an Applied AI role, a shipped-product story for a SWE role, and a pipeline story for a Data Engineering role. In `context.md` you mark which archetypes each experience supports and write one framing line per archetype. The skill uses only checked experiences and uses the framing line that matches the role.

## Setup

```bash
git clone <this repo's URL> cover-letter-builder
cd cover-letter-builder
cp references/context.example.md references/context.md
cp assets/template.example.tex assets/template.tex
```

Then fill in both copies:

- `references/context.md`: your background, archetypes, routing matrix, and experience entries. Anything left as `[FILL]` or `[CONFIRM]` is ignored, so you can fill it in gradually.
- `assets/template.tex`: your name, contact details, links, and opening sentence in the USER CONFIG region.

Both files are gitignored. They stay on your machine.

## Install

**Claude.ai.** Skills must be enabled for your account. Build the zip, then upload `dist/cover-letter-builder.zip` in Claude's skills settings:

```bash
./package.sh
```

The zip contains only `SKILL.md`, `references/style.md`, your `references/context.md`, and your `assets/template.tex`. Rerun it whenever you edit those files.

**Claude Code.** Copy or symlink the repo folder into your skills directory:

```bash
ln -s "$(pwd)" ~/.claude/skills/cover-letter-builder
```

## Usage

The job description is the only required input. Everything else is optional.

```
Write a cover letter for this role.

Date: October 3, 2026
Archetype: Applied AI
Recipient: Jane Smith, 123 Main St, New York, NY
Company fact: They open-sourced their evaluation harness last month.

<paste the full job description here>
```

The skill drafts immediately without asking questions first. It shows a short scoring summary, the full .tex file, and a self-check report. Reply with feedback ("swap the second project", "shorter closing") and it revises only the affected paragraphs and returns the full file again. In Claude Code it also saves each letter to `letters/<company>-<role>.tex`.

## Overleaf

Set the compiler to XeLaTeX (Menu > Settings > Compiler). pdfLaTeX fails on `fontspec`.

The template uses the Source Sans Pro font and the `fontawesome` package for header icons. Both are available on Overleaf by default.

## Customizing

- **Voice:** edit `references/style.md`. Add or remove banned words and constructions to match how you write.
- **Archetypes:** edit `references/context.md`. Rename, add, or remove role types. Keep the archetype list, the routing matrix columns, and the Archetype voice section in sync.
- **Situational mentions:** add one-sentence facts under "Situational mentions" in `references/context.md`, each with a trigger. The skill adds at most one per letter, and only when the posting explicitly emphasizes that trigger (for example, learning quickly or implementing research papers).
- **Layout:** edit `assets/template.tex`. Change fonts, colors, spacing, or the header freely, but keep the USER CONFIG and SKILL-EDITABLE banner comments and the macro names intact. The skill relies on them to know what it may change.

## Privacy

Never commit `references/context.md` or `assets/template.tex`. Both are in `.gitignore`, but check before every push:

```bash
git status
```

Neither file should appear in the output.

## License

MIT. See [LICENSE](LICENSE).
