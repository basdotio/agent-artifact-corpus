# open-computer-skills

![demo](demo.gif)

Give your AI agent hands on your computer: screenshot, click, type, and terminal skills that plug into Claude Code, Codex, OpenCode, and Gemini CLI via MCP.

[![CI](https://github.com/apsethicsbowl20026-collab/open-computer-skills/actions/workflows/ci.yml/badge.svg)](https://github.com/apsethicsbowl20026-collab/open-computer-skills/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![MCP](https://img.shields.io/badge/MCP-stdio%20%2B%20streamable--http-green.svg)

Companion to [Alphalogic](https://github.com/ishanxnagpal/computer-agent): this repo holds the skills, that repo provides the MCP server (`backend/mcp_server.py`) they run on.

## Quickstart

Prerequisites: Python 3.10+, an [Alphalogic](https://github.com/ishanxnagpal/computer-agent) checkout, and one of the supported AI apps.

```bash
# 1. Wire the MCP server into your AI app (backs up existing config to *.bak):
python scripts/install.py --server "C:\path\to\computer-agent\backend\mcp_server.py" --clients opencode,claude-code,codex,gemini-cli

# 2. Restart your AI app, then try a read-only first step:
# "Take a screenshot and tell me what's open. Don't click anything."
```

## Skills

Each folder under `skills/` is a standalone skill in the open Agent Skills format.

| Skill | Lets your agent… | Uses |
|---|---|---|
| [see-verify](skills/see-verify/SKILL.md) | Look first, describe, then act | `screenshot` |
| [click-ground](skills/click-ground/SKILL.md) | Click, drag, type, and scroll at 1280×800 | `computer_action` |
| [form-fill](skills/form-fill/SKILL.md) | Fill forms field-by-field with checks | `computer_action` + `screenshot` |
| [desktop-text](skills/desktop-text/SKILL.md) | Work text-only via element ids (`t_12`) — no vision needed | `desktop_snapshot` + `desktop_act` |
| [safe-bash](skills/safe-bash/SKILL.md) | Run shell commands (destructive ones blocked) | `bash_exec` |
| [stop-guard](skills/stop-guard/SKILL.md) | Stop immediately when you say so | all |

Worked example: [examples/coupon-form.md](examples/coupon-form.md).

## Verify the setup

No mouse moves, no clicks — just lists the tools and echoes:

```bash
python scripts/smoke.py --server "C:\path\to\computer-agent\backend\mcp_server.py"
# TOOLS: bash_exec, computer_action, desktop_act, desktop_snapshot, screenshot
# CALL-OK: mcp-ok
# SMOKE-PASS
```

## Safety

- The server blocks destructive shell commands (`rm -rf /`, `mkfs`, `shutdown`, …).
- Say `STOP` at any time: the agent must halt, screenshot, and report.
- Only grant OS accessibility permissions to software you trust, and only automate machines you own or administer.

## Layout

```
skills/<name>/SKILL.md              # the 6 skills
scripts/install.py                  # one-click client setup
scripts/smoke.py                    # connection check, no clicks
examples/coupon-form.md             # sample task
assets/social.png                   # social preview card
.github/workflows/ci.yml           # checks
```

## Contributing

Issues and PRs welcome — the easiest contribution is a new skill:

1. Open an issue with the [skill request template](.github/ISSUE_TEMPLATE/skill-request.md).
2. Copy an existing `skills/<name>/` folder, keep the same `SKILL.md` shape.
3. Run the repo checks (`python -m py_compile scripts/*.py`) and open a PR.

## License

MIT. See [LICENSE](LICENSE).
