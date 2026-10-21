# Show HN draft (post manually — do NOT automate HN submissions)

Title: Show HN: Open computer-use skills for any AI agent (6 skills, one-click MCP setup)

Body:
I built the companion I wanted for computer-use agents: 6 copy-paste skills
(see-verify, click-ground, form-fill, desktop-text, safe-bash, stop-guard)
that work with Claude Code, Codex, OpenCode, Gemini CLI, Pi, Cursor, Antigravity
via MCP (stdio + streamable-http).

- One command wires all four clients (backs up configs to *.bak)
- Text-mode for cheap text-only models (snapshot ids like t_12)
- Destructive shell commands blocked, STOP means stop
- Smoke test with zero mouse moves: `python scripts/smoke.py`

Live: https://github.com/apsethicsbowl20026-collab/open-computer-skills
Built with screenshot-act-verify loops. Roast the grounding coordinates — what's brittle?
