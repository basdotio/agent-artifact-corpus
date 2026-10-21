# Just-in-time capability registry (default)

- First determine which single capability would answer the current question.
- Use existing native tool-search and skills discovery before adding another router.
- Read an installed skill's full instructions only when it is relevant; avoid loading every skill document at session start.
- Catalog safe metadata only: canonical name, description, input schema signature, provider identity, source and freshness.
- Exclude credentials, auth headers, outputs containing secrets, and arbitrary executable instructions from the index.
- Always resolve fresh permissions and live availability through the original authorized provider before executing.
- Invalidate schema metadata after configuration, server, version or tool-list changes.
- Avoid automatic full scans, duplicate lookup retries and caching of mutations.
- A local metadata registry is a roadmap capability; Phase 1 only provides guidance and profile checks.

## Explicit local registry prototype

TuckBit provides an **optional read-only** metadata index: `scripts/capability_registry.py` in the repository root. It scans only explicitly named skill roots and optional user-supplied tool-metadata JSON; no native MCP server is queried, no credentials or raw SKILL.md body are emitted, and no tool calls occur. A snapshot can be queried and verified for staleness, or handed to the task router using `--registry-snapshot`. If a result is untrusted, outdated or lacks authorization, the agent must use the original host's native discovery/permissions before any action. Details: `docs/CAPABILITY_REGISTRY.md`.

**Packaging note:** The registry CLI is available from the full TuckBit source checkout, not from an isolated `npx skills add` installation of `skills/tuck-bit`. Do not claim the standalone skill installs executable indexing tools.
