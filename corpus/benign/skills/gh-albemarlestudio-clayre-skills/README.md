# Clayre connector skill

The public mirror of [`skills/clayre-connector/SKILL.md`](SKILL.md) — the file an
agent reads to learn when and how to call [Clayre](https://www.clayre.app), the
strategy and brand layer around an operator's content operation.

**Connect:**

- **MCP** — `https://www.clayre.app/mcp` (OAuth sign-in, or a scoped `clyr_…`
  bearer key minted in the cockpit at Settings → Connections → Assistants).
- **REST** — OpenAPI at `https://www.clayre.app/api/v1/openapi.json`, same key.

Not a posting tool — Clayre decides what's worth posting; scheduling and
publishing stay with the human's own channel.

Canonical source lives in the private product repo; this mirror is refreshed on
each connector change.
