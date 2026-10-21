# init-rules

A [Claude Code](https://claude.com/claude-code) skill that creates, audits, or improves a repository's Claude Code rules (`CLAUDE.md` and path-scoped `.claude/rules/*.md`) **from verified repository evidence** rather than from a generic template.

Run `/init-rules` inside any repository. It analyzes the code, manifests, lockfiles, CI, and existing agent config, then writes a compact `CLAUDE.md` plus focused rules that make future Claude sessions:

- use only commands that actually exist in the repo, and never invent APIs, flags, or files;
- write code for the repo's real language and library versions, with no newer syntax and no deprecated APIs;
- follow the project's architecture, conventions, coding standard, and existing code (reuse instead of duplicating);
- make surgical changes, validate them, investigate failures, and never claim checks that didn't run;
- keep docs, comments, and the rules themselves in sync with changes;
- respect security, data-integrity, and performance risks specific to the repo.

## How it differs from the built-in `/init`

The built-in `/init` writes a starting `CLAUDE.md`. `/init-rules` is a separate, deeper command and doesn't replace it:

- **Output:** a compact `CLAUDE.md` plus path-scoped `.claude/rules/*.md` that load only for matching files.
- **Existing config:** audited rule by rule (keep / rewrite / move / delete / enforce mechanically), with reasons.
- **Commands:** each one is backed by a script, a Makefile target, or a CI step.
- **Facts:** every fact is labeled VERIFIED / INFERRED / UNKNOWN, and only verified facts become rules.
- **Risks:** analysis specific to the repo, covering authN vs authZ, migrations, concurrency, generated files, secrets, and performance.
- **Guardrails:** it recommends permission rules and a lint feedback hook, or installs them with `enforce`.
- **Reruns:** idempotent, so an unchanged repo gives little or no diff.

## Requirements

- Claude Code with skills support. Developed and verified with **2.1.289**.
- A git repository works best (diff review, glob checks); non-git directories are supported.

## Install

```bash
git clone https://github.com/aleslanger/init-rules.git ~/.claude/skills/init-rules
```

Or keep the clone elsewhere and link it (safe to rerun):

```bash
git clone https://github.com/aleslanger/init-rules.git ~/src/init-rules
ln -sfn ~/src/init-rules ~/.claude/skills/init-rules
```

Start a new Claude Code session; `/init-rules` appears next to the built-in `/init`.

**Update:** `git -C ~/.claude/skills/init-rules pull` (or pull in your clone).
**Uninstall:** `rm -rf ~/.claude/skills/init-rules` (for the symlink setup this removes only the link).

## Usage

```text
/init-rules                  analyze the repo; create the rules or audit/update existing ones
/init-rules <focus area>     same, with extra attention to an area, e.g. /init-rules migrations
/init-rules enforce          also propose mechanical guardrails and install only the ones you confirm
/init-rules coordinator      also generate rules where the main agent only delegates, reviews, and merges
/init-rules herdr            also generate rules for Herdr (herdr.dev) agent panes
/init-rules help             show usage
```

Arguments can be combined, e.g. `/init-rules coordinator API`.

Claude Code asks for your approval before writing into `.claude/`. Approve it so path-scoped rules can be created.

### What it writes

- **Always:** `CLAUDE.md` and `.claude/rules/*.md` of the current repository only.
- **With `enforce`, per item you confirm:** entries merged into `.claude/settings.json` (permission `deny`/`ask` rules) and hook scripts in `.claude/hooks/`, for example a PostToolUse hook that runs the repo's own linter on each file Claude edits.
- **Never:** your global `~/.claude` config, application code, tests, CI, dependencies, commits, or pushes.

### What you get back

A report with the verified findings (versions, architecture, commands, conventions), each file changed and its scope, the highest-impact rules, the existing rules kept/rewritten/removed and why, unknowns and source conflicts, relevant risks, mechanical-enforcement candidates, proposed workflow recipes (project skills), and exactly which validation ran and what remains unverified.

## How it works

The skill runs fixed phases. `SKILL.md` holds the workflow; detail loads only when its phase needs it:

| File | Phase |
|---|---|
| `SKILL.md` | scope, principles, phases A–J, Definition of Done, report format |
| `references/discovery.md` | B–D: what to discover (structure, versions, architecture, performance, conventions, docs, security, operations) and the risk list |
| `references/rule-catalog.md` | F: rule families to generate (verification, security, architecture, performance, code quality, versions, docs, orchestration, …) |
| `references/self-review.md` | H: adversarial scenarios the generated rules must withstand |
| `references/enforcement.md` | `enforce`: verified settings/hook formats and the feedback-hook template |

## Limitations

- **Rules are guidance, not guarantees.** Claude can still ignore prose; that's why critical restrictions are flagged for mechanical enforcement.
- **Output quality follows the evidence.** A repo without CI, scripts, or lockfiles yields fewer, more cautious rules and more unknowns.
- **Headless runs** (`claude -p`) can't approve writes to `.claude/`, so each unwritten rule file is returned as complete, ready-to-save Markdown with its `paths` frontmatter.
- A full run reads a fair part of the repository and takes several minutes on larger projects.

## Development

`tests/run.sh` runs the skill headless on a fixture repo full of traps (a nonexistent `npm test`, a nonexistent `./deploy.sh`, generic filler, a valid rule that must survive, generated protobuf code, a secret placeholder that must not be copied) and checks the result with `tests/check.py`.

```bash
tests/run.sh          # several minutes; needs claude, git, python3 with PyYAML
tests/run.sh --keep   # keep the temp repo and report for inspection
```

`tests/compare.py` compares `/init-rules` with Anthropic's `claude-md-improver` on three isolated fixture repositories: a Python service, a Go CLI, and a browser app. It runs both skills on the same starting files, saves their outputs, and reports separate checks for commands, forbidden commands, preserved knowledge, paths, change scope, rule files, length, and runtime. It deliberately does not compute one overall score. Review the saved files for unsupported claims and useful detail; these automated checks are narrow. The command invokes Claude Code repeatedly and incurs API cost.

The first comparison and the follow-up regression result are recorded in [tests/BENCHMARK.md](tests/BENCHMARK.md).

```bash
python3 tests/compare.py run \
  --plugin-dir /path/to/claude-md-management \
  --output-dir /tmp/init-rules-benchmark
python3 tests/compare.py score --output-dir /tmp/init-rules-benchmark
```

The official plugin directory must contain `.claude-plugin/plugin.json`. The `score` command can re-evaluate saved outputs without another Claude run. Use `--case demo`, `--case go_cli`, or `--case web_app` to limit a run.

The fixture's `CLAUDE.md` is stored as `CLAUDE.md.fixture` so it never loads while you work on this repo.

## License

[MIT](LICENSE)
