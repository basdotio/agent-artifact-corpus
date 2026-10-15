# gba-matching-decomp (Claude Code skill)

A Claude Code skill for running a complete **matching decompilation of a Game Boy Advance ROM**: C that rebuilds byte-identically with agbcc, grouped by subsystem, named and commented, with extra game versions and decomp.dev progress reports. It is distilled from a full run on Medabots AX (Metabee and Rokusho).

## Install

```sh
git clone https://github.com/FacundoMainere/gba-matching-decomp-skill ~/.claude/skills/gba-matching-decomp
```

Claude Code loads skills from `~/.claude/skills/<name>/SKILL.md`, or from `.claude/skills/` inside a project. Then ask Claude to "decompile this GBA ROM", or invoke the skill by name.

## Contents

- `SKILL.md`: the playbook. Phases: scaffold, agent matching (bandit model selection, retries, permuter, endgame), header unification and subsystem grouping, naming and comments, extra versions, publishing.
- `workflows/`: the multi-agent Workflow scripts for each phase, parameterized by args.
- `templates/tools/`: every tool from the original project (splitter, check_func, integration, bandit, merge tools, rename, version alignment, objdiff report). Adapt them with `templates/PORTING.md`.
- `templates/ghidra/`: Ghidra headless scripts (memory map and Thumb seeding, function-list export, per-function C drafts for agents).
- `templates/`: the Makefile (multi-version, header dependencies), `aliases.s`, `global.h`, the CI progress workflow, and the tools LICENSE.
- `reference/STRATEGY.md`: the full log of what worked, gotchas and lessons. `reference/matching_tips.md` holds agbcc matching tricks.

This repository contains no ROM, game code or assets.

## License

MIT, see [LICENSE](LICENSE).
