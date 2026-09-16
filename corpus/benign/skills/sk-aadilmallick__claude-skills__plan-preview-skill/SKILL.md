---
name: plan-preview
description: "Generate a standalone HTML preview of any project plan — ROADMAP, phases, build sequence, architecture decisions — as a beautiful, navigable single-file document. Use this skill whenever the user asks to preview a plan, generate an HTML plan, visualize a roadmap, create a shareable plan document, says 'plan preview', 'HTML plan', 'preview my plan', 'share this plan', 'make the plan visual', 'deploy the plan', or wants to push a plan to Vercel or Netlify or Github pages for sharing."
---

<objective>
Generate single self-contained HTML preview of project plans. Zero dependencies, one `.html` file, opens in any browser, deployable to Vercel via `scripts/deploy-vercel.sh` or deploy to netlify via the netlify CLI, offer users the choice of that, also ask if users want to make this a git repo, and if so, provide a base `.gitignore` and use the `gh` cli tool to create the repo and push it to github, as well as integrate CI/CD with either vercel or netlify
</objective>

<inputs>
Priority order:

1. Markdown plan — any `.md` file with phases/tasks/steps structure
2. YAML roadmap — `ROADMAP.yaml` or similar structured plan file
3. Conversation context — plan discussed in current thread but not yet on disk
4. Prompt description — user describes what to build, generate plan + preview together
</inputs>

<output>
Single self-contained HTML file. All CSS/JS inline. No external dependencies.

Location: `./plan-preview.html` in current directory (or project's planning dir if one exists).
Always tell user the path + offer to open: `open <path>`.
</output>

<workflow>
1. **Detect sources** — scan for plan `.md` files, YAML roadmaps, or use conversation context
2. **Pick style** — ask user which visual style (see `<style_selection>`)
3. **Check for custom tokens** — if project has `design-tokens.json` or CSS custom properties file, load and merge with chosen style
4. **Parse** — extract phases, tasks, dependencies, status, architecture decisions
5. **Analyze** — generate consequence depth (1st/2nd/3rd order) per phase
6. **Generate** — build HTML following design system in `references/html-structure.md`, apply chosen style + custom tokens
7. **Write** — save to correct location
8. **Open** — `open <path>` to show in browser
9. **Offer deploy** — "Want me to deploy this to Vercel?" If yes, run `scripts/deploy-vercel.sh <path> <project-slug>`
10. **On update** — if plan changed since last preview, regenerate. Archive previous with timestamp if user wants history.
</workflow>

<required_sections>
Every preview MUST include these as tabs or collapsible regions:

| Section | Source | Purpose |
|---|---|---|
| Overview | plan header / roadmap | Project name, description, phase count, status summary, progress bar |
| Architecture | plan architecture section | Tech stack, key decisions, system design (ASCII art if available) |
| Build Sequence | phases + dependencies | Visual phase timeline with status badges, dependency arrows, wave grouping |
| Phase Details | each phase/step | Per-phase: goal, tasks, acceptance criteria, files touched, risks |
| Consequence Analysis | generated | 1st/2nd/3rd order consequences per phase |
| Status | state file or plan status | Current position, blockers, next action |
</required_sections>

<consequence_depth>
Per phase, analyze and display:

- **1st order** (Direct): what the phase explicitly builds
- **2nd order** (Adjacent): what must exist for 1st order to work (validation, error handling, integration points)
- **3rd order** (Downstream): what could break over time (perf at scale, security, maintenance burden)

Display as expandable cards. Color: green (1st), amber (2nd), red (3rd).
</consequence_depth>

<style_selection>
Before generating, ask user to pick a visual style:

1. **Clean** (default) — white background, subtle borders, system font. Professional, neutral.
2. **Editorial** — serif headings, generous whitespace, muted palette. Magazine/report feel.
3. **Terminal** — dark background, monospace, green/amber accents. Dev-oriented.
4. **Custom** — user provides design tokens or a CSS custom properties file.

Each style overrides the base design tokens in `references/html-structure.md`. If user doesn't care, use Clean.

If project has a `design-tokens.json`, `tokens.css`, or similar design token file, auto-detect and offer to use those tokens instead. Merge project tokens on top of chosen style.
</style_selection>

<design_system>
Read `references/html-structure.md` for complete HTML template, CSS tokens, and JS.

**Readability rules (MUST enforce):**
- All text within cards: `max-width: 65ch`, centered in card via `margin: 0 auto`
- Minimum font size: 16px (1rem). Nothing smaller, not even badges or labels.
- Light mode default. Dark mode available via toggle only.

Key principles:
- Tabs for top-level nav (Overview / Architecture / Build Sequence / Phases / Status)
- Collapsible sections within each tab
- Status badges: `todo` (gray), `in-progress` (blue pulse), `done` (green), `blocked` (red), `skipped` (dim)
- Phase cards with click-to-expand
- Responsive + print-friendly
</design_system>

<boundaries>
- Preview is read-only visualization. NEVER modify plan artifacts.
- NEVER generate fake data. Missing section → "Not yet planned" placeholder.
- Consequence analysis is best-effort. Flag as AI-generated, not human-verified.
- Keep HTML under 500KB. Massive plans → paginate phases or lazy-load tabs.
- ASCII art from plan files: preserve verbatim inside `<pre>` blocks.
</boundaries>

<success_criteria>
- Single valid `.html` file, zero external dependencies
- All 6 required sections present (or placeholder if no source data)
- Opens correctly in browser via `open <path>`
- File under 500KB
- Light mode default, dark toggle works
- No text smaller than 16px anywhere
- All card text max 65 characters wide, centered in card
- Tab navigation works
- Consequence analysis present for each phase
- Chosen style or custom tokens applied
</success_criteria>
