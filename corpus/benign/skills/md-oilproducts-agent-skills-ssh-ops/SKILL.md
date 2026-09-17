---
name: ssh-ops
description: Use for SSH and remote shell tasks through the shell-only ssh-ops wrappers (`scripts/ssh_ops.sh`). Supports ad-hoc host/user/auth, command execution, guarded PTY workflows, scp copy, credentials, and transcript-aware troubleshooting.
---

# SSH Ops

Use shell wrappers only.

## Preflight
1. Confirm wrapper exists: `/Users/chris/projects/ssh-ops/scripts/ssh_ops.sh`.
2. Confirm system SSH exists: `/usr/bin/ssh`.
3. Decide state-dir strategy:
   - default: wrapper auto-uses `/tmp/ssh-ops-$USER/<cwd-hash>`
   - explicit: pass `--state-dir /tmp/ssh-ops-<name>` (recommended for long sessions and scripts)

## Policy
- Use `scripts/ssh_ops.sh` commands only.
- Keep the same state dir across session-open/exec/pty/scp/session-close for continuity.
- Default to non-PTY command execution.
- PTY only when needed, with strict guardrails and override flag.
- Report exit codes, stderr summary, and transcript offsets.

## Core Workflow
1. Open or reuse session: `session-open` / `session-list`.
2. Execute remote work with `exec` (default) or guarded `pty-*`.
3. Use `scp-copy` when file transfer is needed.
4. Close session with `session-close`.

See `references/workflows.md` and `references/policies.md`.

## Credentials
1. Save credential: `credential-save`.
2. List credentials: `credential-list`.
3. Delete credentials: `credential-delete`.

## Error Handling
Use `references/errors.md`.
