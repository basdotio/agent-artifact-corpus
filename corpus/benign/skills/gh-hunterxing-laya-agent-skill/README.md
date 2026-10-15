# laya-agent-skill

A provider-agnostic, agent-agnostic sidecar for making fast, structured **typed decisions** through any [Laya](https://github.com/NandhaKishorM/laya)-compatible decision API. It works with a local service, a self-hosted gateway adapter, or any OpenAI-compatible deployment.

## What it does

Laya-compatible decision backends answer `choice` / `score` / `noul` questions with probabilities instead of generating prose. The skill provides bounded workflows and safe integration paths for coding and tool-using agents:

- request, ticket, email, log and evidence classification;
- model, domain, workflow and skill routing suggestions;
- failure triage and evidence verification;
- change-risk floors and minimum test-scope hints;
- prompt-injection, jailbreak, phishing, spam and toxicity pre-screening;
- tool-call pre-screening before execution, with deterministic policy still in charge.

It explicitly does **not** let a decision model authorize destructive operations. Hard rules and user confirmation always win.

## Agent-agnostic by design

The host only needs one of these capabilities:

- **local command execution** — use `scripts/laya.sh` or `scripts/laya.py`;
- **MCP stdio** — register `scripts/laya_mcp.py`;
- **HTTP tool access** — call the configured OpenAI-compatible endpoint;
- **project rules / skill loading** — use the contract in `references/integration.md`.

No hostname, token, model name or vendor is hardcoded. The backend is resolved at runtime:

| Variable | Purpose | Default |
|---|---|---|
| `LAYA_BASE_URL` | OpenAI-compatible API root | required |
| `LAYA_API_KEY` | Bearer token, if required | — |
| `LAYA_MODEL` | Default checkpoint or preset | `laya-latest` |
| `LAYA_DECISION_PATH` | Native `state + questions` path | `/decisions` |
| `LAYA_CHAT_PATH` | OpenAI-compatible path | `/chat/completions` |
| `LAYA_TIMEOUT_SECONDS` | Request timeout | `15` |
| `LAYA_NATIVE_DECISIONS` | Prefer native endpoint when `true` | `false` |

## Quick start

```bash
# Shell-capable agent
printf '%s' '{"request":"fix the login crash","candidates":[{"id":"debug","description":"locate the stack trace and fix the source"},{"id":"docs","description":"write documentation"}]}' \
  | sh scripts/laya.sh select

# Self-check
sh scripts/laya.sh selftest

# MCP-capable agent
python3 scripts/laya_mcp.py
```

For Codex, OpenCode, Claude Code, other MCP clients, HTTP-only agents, Windows hosts and generic project-rule agents, see `references/integration.md`. This repository does not require Hermes; Hermes users can still copy it into `~/.hermes/skills/mlops/laya-agent-skill/`.

## Safety model

```text
hard rules + tool metadata + Laya signal + user confirmation
```

- S0 ordinary conversation → skip the decision backend;
- S1 read-only → explicit read-only tool allowlist only;
- S2 reversible/service-affecting → show plan and rollback, then ask first;
- S3 destructive/security-sensitive → explicit confirmation; the model cannot lower this level.

`status: unknown`, exit code 2, malformed output, timeout or `needs_review: true` never means “no” and never authorizes an action. Continue with the host agent's normal review path.

## Files

```text
SKILL.md                         skill behavior and safety rules
references/development-workflows.md  input/output schemas
references/env-setup.md          provider-neutral configuration
references/integration.md        shell, MCP, HTTP and rule-file integration
scripts/laya.py                  stdlib JSON CLI
scripts/laya.sh                  POSIX wrapper
scripts/laya_mcp.py              stdio MCP server
scripts/laya_protocol.py         request/response validation
scripts/dev_workflows.py          bounded coding-agent workflows
LICENSE                          Apache-2.0
```

## License

Apache-2.0. Laya itself is by [Convai Innovations](https://github.com/convaiinnovations/laya) (Apache-2.0); this skill is an independent integration and is not affiliated with or endorsed by them.
