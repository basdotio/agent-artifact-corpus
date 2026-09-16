# plan-preview

Generate a standalone HTML preview of any project plan as a beautiful, navigable single-file document. Zero dependencies, one `.html` file, opens in any browser.

## Why

Project plans live in markdown or YAML files that are hard to scan, share with stakeholders, or present visually. This skill turns them into polished, interactive HTML documents with tabs, collapsible sections, status badges, and consequence analysis.

## Features

| Feature | Description |
|---|---|
| Single file output | Self-contained HTML with all CSS/JS inline |
| Multiple input formats | Markdown plans, YAML roadmaps, conversation context |
| 4 visual styles | Clean, Editorial, Terminal, or Custom (design tokens) |
| Consequence analysis | 1st/2nd/3rd order impact per phase |
| Vercel deploy | One-command deploy via included script |
| Dark mode | Toggle between light and dark themes |

## Required sections

Every preview includes these as tabs or collapsible regions:

- **Overview**: project name, description, phase count, status summary, progress bar
- **Architecture**: tech stack, key decisions, system design
- **Build Sequence**: visual phase timeline with status badges and dependency arrows
- **Phase Details**: per-phase goal, tasks, acceptance criteria, files touched, risks
- **Consequence Analysis**: 1st/2nd/3rd order consequences per phase
- **Status**: current position, blockers, next action

## Install

Clone and symlink into your Claude Code skills directory:

```bash
git clone https://github.com/alexadark/plan-preview-skill.git
ln -s "$(pwd)/plan-preview-skill" ~/.claude/skills/plan-preview
```

## Usage

In Claude Code:

```
/plan-preview
```

Or describe what you need:

- "preview my plan"
- "generate an HTML plan"
- "make the plan visual"
- "deploy the plan to Vercel"

The skill detects plan files in your project, asks you to pick a visual style, then generates a single `.html` file you can open locally or deploy.

## Deploy to Vercel

After generating a preview:

```bash
./scripts/deploy-vercel.sh plan-preview.html my-project-plan
```

## File structure

```
plan-preview/
  SKILL.md              # Skill definition and workflow
  README.md             # This file
  LICENSE               # MIT
  references/
    html-structure.md   # HTML template, CSS tokens, JS
  scripts/
    deploy-vercel.sh    # One-command Vercel deployment
```

## Prerequisites

- Claude Code CLI
- Vercel CLI (optional, for deployment only)

## License

MIT
