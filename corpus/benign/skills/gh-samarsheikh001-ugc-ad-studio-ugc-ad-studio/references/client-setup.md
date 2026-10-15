# Claude + NinjaChat client setup

This package supports two installation routes. In Claude.ai, upload `ugc-ad-studio.zip` from **Customize → Skills → + Create skill → Upload a skill**, then enable it. In Claude Code, place the skill folder at `.claude/skills/ugc-ad-studio/SKILL.md`.

Before production, check these independently in the intended Claude client:

1. Choose **Claude Opus 5.5** in the model selector or current Claude Code model setting. Anthropic's current announcement lists Opus 5.5 on Claude and its cloud platforms, but account entitlements can differ.
2. Connect/enable **NinjaChat MCP** using its current client-specific setup guide.
3. Confirm the client lists the NinjaChat media tools needed for the planned output.
4. Use a free capability/catalog query before quoting media. Do not put an API key, bearer token, signed asset URL or other secret in this repository.

NinjaChat access in another app does not prove your Claude session is configured. This package does not add `.mcp.json` credentials/configuration or enable a connector automatically.

## Official references

- [Claude Opus 5.5 announcement](https://www.anthropic.com/claude-opus-5-5)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [NinjaChat MCP client setup](https://docs.ninjachat.ai/mcp/clients.md)
