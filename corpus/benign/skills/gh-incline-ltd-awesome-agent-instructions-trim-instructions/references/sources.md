# Primary sources

Checked on **2026-10-03**. A checked date records a documentation review, not a
host installation test. Recheck the relevant page before relying on changed
model or host behavior. Undated documentation below has no publication date
asserted here.

## O01

[OpenAI: Rethinking skills and prompts for GPT-6 Astra](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)
Published **2026-09-11**. Supports contextual reading, narrower workflows, and
clear completion conditions. Its model-specific advice requires evaluation
when shared instructions serve other models.

## O02

[OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)
Documents skill selection, progressive loading, and local directories.
Codex's initial listing can shorten descriptions or omit skills when its budget
is exceeded; installed metadata is not necessarily injected verbatim.

## A01

[Anthropic: Prompting Claude Opus 5.5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)
Scoped guidance for chat thinking prompts, former thinking-disabled integrations,
unattended work, and visual preferences. Preserve product requirements while
testing changes. API effort and harness changes are outside this skill's scope.

## A02

[Anthropic: Migrating to Claude Opus 5.5](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide)
The behavior-change section for older Opus migrations suggests trying removal
of fixed-count progress scaffolding. It does not require removing status updates.

## A03

[Anthropic: The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
Published **2026-07-24**; the official URL redirects to `claude.dev`.
Supports reviewing repetition, procedural constraints, and context placement.
Anthropic reports removing over 80% of its Claude Code system prompt without
measurable loss on its coding evaluations for Opus 5 and Fable 5. That result is
not a reduction target or a performance claim for this project.

## A04

[Anthropic: How Claude remembers your project](https://code.claude.com/docs/en/memory)
Distinguishes shared instructions from learned memory, recommends concrete
commands, and documents file loading. Imported files also consume context.
Its current prompt audit covers more than CLAUDE.md and skills.

## A05

[Anthropic: Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
The aggressive-language advice concerns unnecessary tool/skill invocation on
Opus 4.5 and 4.6. It is not evidence for rewriting every capitalized requirement.

## Host documentation

These are documented project skill locations, not a claim that this skill has
been exercised inside each host. Copying files proves only that copying worked.

| Host | Project skill location | Official reference |
| --- | --- | --- |
| Codex | `.agents/skills/<name>/SKILL.md` | [Skills](https://learn.chatgpt.com/docs/build-skills), [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) |
| Claude Code | `.claude/skills/<name>/SKILL.md` | [Skills](https://code.claude.com/docs/en/skills), [memory](https://code.claude.com/docs/en/memory) |
| Cursor | `.cursor/skills/<name>/SKILL.md` or `.agents/skills/<name>/SKILL.md` | [Skills](https://cursor.com/docs/skills), [rules](https://cursor.com/docs/rules) |
| GitHub Copilot | `.github/skills/<name>/SKILL.md`; also `.agents/skills/` and `.claude/skills/` | [Skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills), [surface support](https://docs.github.com/en/copilot/reference/customization-cheat-sheet) |
| Gemini CLI | `.gemini/skills/<name>/SKILL.md` or `.agents/skills/<name>/SKILL.md` | [Skills](https://geminicli.com/docs/cli/skills/), [GEMINI.md](https://geminicli.com/docs/cli/gemini-md/) |

Loading depends on host, version, settings, directory, and task. Codex selects
one instruction file per directory along its startup path. Claude Code's direct
AGENTS.md support starts at v2.1.277 and is conditional on its project-instruction
settings and competing CLAUDE files. Cursor rules have distinct activation modes.
Copilot support varies by surface. Gemini combines startup and later-discovered
context. The measurement helper does not resolve these behaviors.

GitHub documents [`gh skill`](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills#managing-skills-with-github-cli)
for GitHub CLI 2.90.0+, in public preview. Verify the installed version and inspect
the package before choosing that route. This reference is not an installation
receipt or a promise of compatibility with earlier CLI versions.
