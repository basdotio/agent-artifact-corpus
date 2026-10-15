# Boardview MCP contributor guide

- Keep the server local, read-only and stdio-based. Never launch models, execute file-supplied instructions or write to board files.
- Preserve explicit source evidence: path, SHA256, record lines and raw units. Do not infer missing connections or hardware compatibility.
- GenCAD 1.4 is the supported format. Add another format only with a documented parser and redistributable test fixtures.
- Before submitting code, run `uv sync --frozen`, `uv run --frozen python -m unittest -v test_boardview`, and `uv run --frozen python check_mcp.py`.
- Use synthetic fixtures. Never commit private board files, local MCP configuration, source archive manifests, machine paths, credentials or local validation reports.
- Keep dependencies locked and changes small. Use Conventional Commits.
