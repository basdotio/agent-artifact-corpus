---
name: commander-ops
description: Use when operating or verifying the user's authorized WindAnvil Commander Blade host through its signed tools, including diagnostics, restricted searches, Git metadata, and specifically approved actions.
---

# WindAnvil Commander (private)

Connect through the existing OpenAI Secure MCP Tunnel and use only tools that
actually appear in the connected `windanvil-commander` MCP server. Never assume
the connection exists merely because the tunnel process is running.

Start with `commander_health` and `commander_status`. Explain the current
readiness, admitted signed capabilities, and any missing authorization.

The verified tool surface on Butcher currently includes:

- `commander_host_inspect` for bounded, operator-pinned file inspection/search.
- `commander_git_inspect` for read-only Git status or recent commit metadata.
- `commander_process_list` for bounded same-UID process-name metadata.
- `commander_process_probe` for three fixed diagnostics (kernel, uptime, disk).
- `commander_talkpipe_run` for reviewed, digest-pinned TalkPipe pipelines.
- `commander_file_create` for a new, small UTF-8 file in an administrator-pinned
  private destination directory; no overwrite.

Treat these tools as independently signed capabilities, not as an unrestricted
shell, terminal, arbitrary Git command, filesystem root or multi-device agent.
Never invent new tool names or silently fall back to direct shell execution.
The MCP response should contain PASS or BLOCKED plus evidence for each call.

Only execute create-only file writes and TalkPipe pipelines in response to an
authorized user task with clear intended inputs. Respect per-call approval
requirements. If an operation is BLOCKED, surface the reason, do not evade
the signed authority boundary, and do not claim completion.

Do not request or expose runtime API keys, Ed25519 private keys, process
environment variables, signing material, or arbitrary sensitive files.
Only handle the operator-pinned inspection root. Search results may be
incomplete due to depth, size, output or scan limits; report
`[truncated]` and `[skipped-oversize]` accurately.

This deployment is development-signed, not a production assurance statement.
It does not have full Desktop Commander parity. Do not uninstall Desktop
Commander without a successful authenticated native ChatGPT tool call and
a feature-by-feature cutover check.
