# Contributing to init-rules

Thanks for helping improve `/init-rules`. Open an issue for a proposed behavior change so its scope can be discussed before you implement it. Small documentation fixes can go straight to a pull request.

## Before opening a pull request

1. Read [README.md](README.md) for the supported usage and [SKILL.md](SKILL.md) for the workflow and output rules.
2. Keep changes focused. Update the relevant file in `references/` when you change a phase's guidance, and keep README examples consistent with the skill.
3. For behavior changes, add a fixture or assertion that demonstrates the intended result. The regression harness lives in `tests/run.sh` and `tests/check.py`.
4. Run `tests/run.sh` if you have Claude Code, Git, Python 3, and PyYAML available. It runs headlessly and can take several minutes. Report the result in your pull request. If you cannot run it, say why and describe any checks you did run.

The fixture's `CLAUDE.md.fixture` name is intentional: it keeps those instructions from loading while you work on this repository.

## Reports and proposals

For a bug, include the `/init-rules` command, the relevant repository structure or a small reproduction, the expected output, and the actual output. Remove secrets and private repository content before sharing logs or generated rules.

For a feature, explain the repository evidence that would support the new behavior and how you would verify the generated rules. The skill should not turn guesses into repository rules.
