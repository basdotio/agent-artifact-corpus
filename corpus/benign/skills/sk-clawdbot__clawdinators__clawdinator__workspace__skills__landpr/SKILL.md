---
name: landpr
description: Land an OpenClaw PR end-to-end using the repo landpr checklist. Use when someone requests “/landpr” or asks to merge/land a PR.
user-invocable: true
---

# Land PR (OpenClaw)

Use this skill to land **openclaw/openclaw** PRs only.

## Safety + Scope

- **Repo restriction:** only `openclaw/openclaw`. If the PR is in any other repo, stop and ask.
- **Single approval gate:** do all read‑only prep, then summarize the plan and ask for explicit approval **once** before any rebase/force‑push/merge.
- **Never close PRs.** PR must end in GitHub state **MERGED**.
- **No GitHub comments** unless the user explicitly approves (global policy).

## Instructions

Use this as a **playbook** — do **not** paste the full checklist into chat:
- `/var/lib/clawd/repos/clawdinators/scripts/landpr.md`

If the user did not specify a PR, use the most recent PR mentioned in the conversation. If ambiguous, ask.

Default merge strategy: **rebase** unless the user explicitly requests squash.

After completion, verify PR state == MERGED.
