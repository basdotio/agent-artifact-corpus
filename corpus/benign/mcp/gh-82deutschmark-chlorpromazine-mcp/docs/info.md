https://github.com/modelcontextprotocol/typescript-sdk?tab=readme-ov-file#overview

---

**TypeScript Safety & Handler Robustness (2025-05-18, Claude 3.5 Sonnet)**

- All request handlers enforce correct parameter shapes (`(request, extra)`), always using `request.params`.
- Defensive type guards for all Zod-inferred values (e.g., `params.model`, `userContent.text`).
- Fallback logic ensures the `model` field is always a string (defaults to `DEFAULT_ASSISTANT_MODEL`).
- Code is robust for novice coders and follows MCP SDK v1.11.4 best practices.

"mcpServers": {
    "chlorpromazine_mcp": {
      "command": "npm",
      "args": [
        "--prefix",
        "D:/1Projects/chlorpromazine-mcp",
        "run",
        "dev"
      ],
      "env": {
        "SERPAPI_KEY": "<your-serpapi-key>",
        "SITE_FILTER": "stackoverflow.com,github.com,docs.python.org,…",
        "API_KEY": "<optional-bearer-token>"
        