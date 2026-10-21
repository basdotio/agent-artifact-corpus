# Comparison baseline — 2026-10-07

`tests/compare.py` ran `/init-rules` and Anthropic's `claude-md-improver` once each on three identical starting fixtures, using Claude Code 2.1.292. The official skill used the installed `claude-md-management` plugin and a second approval turn. Runs were isolated under `/tmp/init-rules-benchmark-20261007`; no application repository was changed. These are observations from one stochastic run per case, not a universal ranking.

| Fixture | Candidate | Verified commands | Bad commands absent | Existing invariant preserved | Key paths | `CLAUDE.md` lines | Written rules | Complete unwritten rules |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Python service | `/init-rules` | 4/4 | 1/2 | 2/2 | 1/2 | 45 | 0 | 3 |
| Python service | Anthropic | 4/4 | 2/2 | 2/2 | 2/2 | 35 | 0 | — |
| Go CLI | `/init-rules` | 2/2 | 1/1 | 1/1 | 1/1 | 22 | 0 | — |
| Go CLI | Anthropic | 2/2 | 1/1 | 1/1 | 1/1 | 24 | 0 | — |
| Browser app | `/init-rules` | 3/3 | 1/1 | 2/2 | 1/1 | 17 | 0 | — |
| Browser app | Anthropic | 3/3 | 1/1 | 2/2 | 1/1 | 23 | 0 | — |

The Python `/init-rules` run exposed two issues: it repeated the nonexistent `npm test` in a negative sentence, and its written `CLAUDE.md` named `proto/` rather than the exact `proto/orders.proto` source of generated code. Its three path-scoped rule files were returned as complete Markdown because Claude Code blocked writes to `.claude/rules/` in headless mode. The Go and browser outputs passed the narrow automatic checks for both candidates. Manual inspection found both candidates preserved the important existing security rule in those fixtures.

The prompt was tightened after the initial Python comparison. A fresh `tests/run.sh --keep` run on the Python fixture passed all regression checks with a 27-line `CLAUDE.md`: it omitted `npm test`, named the exact proto source, preserved the ownership/404 rule in the written file, and returned complete Markdown for the rules it could not write. That follow-up is a regression result, not a second side-by-side comparison.

The comparison checks observable strings, change scope, output length, and rule-file presence. They do not prove that every generated instruction is correct or useful. The two skills have different scopes, and the official skill's approval turn makes elapsed time a poor quality measure. Read each saved `CLAUDE.md` and report before drawing a conclusion. To reproduce or rescore, use the commands in [README.md](../README.md#development).
