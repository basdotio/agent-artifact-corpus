---
name: new-domain
description: "Creates a new domain skill pack (3-7 skills, agents, reference files) for a field the existing packs (coding, marketing, sales, design) do not cover."
when_to_use: "The user says 'I need a skill for', 'create a pack for', 'set up for [domain]', names a new field such as finance, legal, HR or ops, or keeps doing the same kind of task without a matching skill. Not for setting up a project (use /new-project)."
---

# New Domain Skill Pack Generator

You are creating a complete, installable skill pack for a new domain. The output must match the quality and structure of the existing coding, marketing, and sales packs.

## Step 1: DOMAIN DISCOVERY
Ask the user:
1. What domain is this for? (e.g., finance, legal, HR, operations, research)
2. What are the 3-5 most common tasks you do in this domain?
3. What does "good output" look like? How do you judge quality?
4. Are there specific tools, platforms, or data sources you use?
5. What mistakes or bad patterns should be avoided?

Continue once you have clear answers to at least questions 1-3.

## Step 2: SEARCH EXISTING SKILLS
Before building from scratch, search for existing skills that might cover this domain:
1. Check installed skills: use Glob to scan `~/.claude/skills/*/SKILL.md` and `.claude/skills/*/SKILL.md`
2. Search community repos if web access available:
   - https://github.com/VoltAgent/awesome-agent-skills
   - https://github.com/ComposioHQ/awesome-claude-skills
   - https://github.com/softaworks/agent-toolkit
   - https://github.com/Kamalnrf/claude-plugins
   - https://github.com/hesreallyhim/awesome-claude-code
3. Report what you found. Ask user if any existing skills should be incorporated or adapted.

## Step 3: DESIGN THE PACK
Based on discovery, propose:
- **Pack name** (kebab-case)
- **Skills list** (3-7 skills, each with one-line description and negative triggers for overlap prevention)
- **Persona** (domain personality — 4-6 lines embedded in each SKILL.md, not a separate file)
- **Agents** (1-3 specialists — what roles, what tools, what model) → `.md` files in the pack's top-level directory
- **Hooks** (any domain-specific automation) → merge into `.claude/settings.json`
- **Reference files** (scoring rubrics, checklists, glossaries) → real copies in each skill's `reference/` directory (not symlinks, not inlined)

Present this plan and get user approval before building. If available, read `~/ailoopwise-blueprint/blueprint/skill-writing-guide.md` for full formatting rules.

## Step 4: BUILD FROM TEMPLATE
Copy the template structure and populate:

```
skills/[domain-name]/
├── [each-skill]/                    # Each skill independently installable
│   ├── SKILL.md                     # YAML frontmatter + instructions (under 500 lines)
│   ├── reference/                   # Optional — checklists, rubrics loaded on demand
│   ├── scripts/                     # Optional — deterministic validation code
│   └── assets/                      # Optional — templates, output files
└── README.md                        # Optional — pack documentation
```

### Quality rules for every generated file:
- **SKILL.md**: YAML frontmatter (name matching folder, description with WHAT + WHEN + triggers + negative triggers, metadata). Body: Persona section (4-6 lines), imperative voice, numbered steps, at least 1 input/output example, 3-6 hybrid evals (binary for structural checks + model-graded for semantic quality, target 85%+ combined score). Under 500 lines.
- **Agents**: Least-privilege tools, identity + core behaviors + quality standard + handoff protocol
- **Reference files**: Real, actionable content — not placeholders. Copy into each skill's `reference/` directory as real files. SKILL.md references them via `reference/filename.md` paths. Claude reads them on demand (progressive disclosure).
- **Forbidden inside skill folders**: README.md, plugin.json, CHANGELOG.md

## Step 5: VALIDATE
After building:
1. Check every SKILL.md `name` field matches its folder name
2. Check every description says what the skill does and when to use it (or puts the when in `when_to_use`), including when not to; description plus when_to_use stay under 1,536 characters
3. Check every non-coding SKILL.md has a Persona section
4. Check agents have appropriate tool restrictions
5. Check each skill's `reference/` directory contains real files (not symlinks) that the SKILL.md references
6. Check every SKILL.md is under 500 lines
7. Check every SKILL.md has 3-6 evals, each labeled as `(binary)` or `(model-graded)`
8. Test one skill by running it with a sample task

## Step 6: INSTALL
Guide the user through installation:
1. Copy skill folders to `~/.claude/skills/` (global) or `.claude/skills/` (project)
2. Copy agent `.md` files to `~/.claude/agents/` (global) or `.claude/agents/` (project)
3. Test with a real task

## Step 7: SUGGEST AUTORESEARCH (optional)
After the pack is installed and the user has tested it 2-3 times manually:
- Suggest: "Autoresearch available — want to optimize this skill now?"
- If user accepts: define 3-6 eval criteria per skill, run autoresearch until 95%+ pass rate for 3 consecutive experiments
- If user declines or says "skip": move on without autoresearch
- Rationale: A brand-new skill often lacks enough test inputs for meaningful evals. Manual testing first, then optimize.

## OUTPUT
When complete, provide:
- Summary of what was created (file count, skill names, agent names)
- How to invoke each skill (`/skill-name`) and when Claude picks it up on its own
- Suggested first task to test the pack