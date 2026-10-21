# Reddit draft (r/ClaudeCode — check sub rules before posting, no bots)

Title: I made 6 computer-use skills that work with Claude Code + Codex + OpenCode (one-click MCP setup)

Body:
After wiring Alphalogic's MCP server to 4 clients by hand one too many times,
I packaged the loop as skills:

- see-verify (screenshot, describe, only then act)
- click-ground (1280x800 clicks/drags/keys)
- form-fill, desktop-text (ids like t_12 for text-only models)
- safe-bash (destructive cmds blocked), stop-guard

`python scripts/install.py --server <path-to-mcp_server.py> --clients opencode,claude-code,codex,gemini-cli` backs up your configs and merges the entry. Smoke test does list-tools + echo with no mouse moves.

Repo: https://github.com/apsethicsbowl20026-collab/open-computer-skills (MIT)

Happy to add the skill you keep rewriting — what's missing?
