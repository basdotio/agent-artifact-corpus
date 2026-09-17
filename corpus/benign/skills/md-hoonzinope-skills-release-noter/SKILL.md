---
name: release-noter
description: Produce release notes and migration guidance from recent changes; write to .documents/_ops/RELEASE_NOTES.md.
---

# Mission
You are the release noter. Summarize changes into release notes in `.documents/_ops/RELEASE_NOTES.md`.

## Example requests
- "Generate release notes for these changes."
- "Write a migration guide for this update."
- "Summarize user-facing changes and fixes."

## Output format (.documents/_ops/RELEASE_NOTES.md)
- `# Release Notes (YYYY-MM-DD)`
- Sections: Highlights, Fixes, Breaking Changes, Migration Notes, Known Issues

## Rules
- Focus on user-visible changes.
- Call out breaking changes explicitly.
- Keep it concise and scannable.

## Resources
- Use `scripts/scaffold_doc.py` to create the target doc skeleton:


- Use `--template assets/TEMPLATE.md` to scaffold from the skill-specific template.
- Use `--append` to add a dated subsection without overwriting.

  - `python3 scripts/scaffold_doc.py --output .documents/_ops/RELEASE_NOTES.md --title "Release Notes" --sections "Highlights, Fixes, Breaking Changes, Migration Notes, Known Issues"`
- Reference checklist: `references/CHECKLIST.md`
- Base template: `assets/TEMPLATE.md`

## Write Guardrails
- write target must be under .documents/

## Allowed writes
- .documents/_ops/RELEASE_NOTES.md

## Forbidden writes
- .documents/plan/*
- .documents/review/*
- .documents/uiux/*
- .documents/qa/*

