---
name: mcp-builder
description: Plan and build MCP servers with agent-friendly tools, schemas, error handling, and evaluation. Use when creating or refactoring MCP integrations.
---

# MCP Builder

Build MCP servers around user workflows, not raw API endpoints.

## Workflow

1. Read the target API docs and identify the workflows an agent must complete end to end.
2. Design a small tool surface with high-signal outputs, clear identifiers, and actionable errors.
3. Implement shared infrastructure first: auth, request helpers, pagination, truncation, and formatting.
4. Add tool schemas and docstrings that make correct usage obvious.
5. Evaluate the server with realistic tasks before expanding scope.

## Principles

- Prefer workflow tools over thin endpoint wrappers.
- Return concise, high-signal responses by default.
- Use human-readable identifiers whenever possible.
- Make error messages corrective: tell the agent what to try next.
- Design for limited context and large datasets.

## Resources

- `references/mcp_best_practices.md` for design principles that apply to every server.
- `references/python_mcp_server.md` for Python implementation patterns.
- `references/node_mcp_server.md` for TypeScript implementation patterns.
- `scripts/connections.py` and `scripts/evaluation.py` as repo-local helpers.

## Deliverables

- A concrete tool inventory tied to user workflows.
- Strict input/output schemas.
- Evaluation prompts or scripts that confirm the server is usable by an agent.
