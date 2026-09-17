---
name: governance-worker
description: Implement repo governance, maintainer guidance, and Factory operational artifact alignment for the readiness mission.
---

# Governance Worker

NOTE: Startup and cleanup are handled by `worker-base`. This skill defines the work procedure.

## When to Use This Skill

Use this skill for features that add or modify:

- `README.md`, `.env.example`, `.gitignore`, and maintainer-facing setup guidance
- `CODEOWNERS`, Dependabot, issue templates, and PR templates
- Factory operational artifacts under `.factory/`
- cross-file alignment between docs, templates, hooks, workflows, and canonical validation command names

## Required Skills

None

## Work Procedure

1. Read the assigned feature, mission `AGENTS.md`, repo `AGENTS.md`, `.factory/services.yaml`, and any existing governance files before making changes.
2. Confirm the current canonical command names from `package.json` and any committed workflow or hook files; governance artifacts must reference only real commands.
3. Add or update the minimum set of files needed for the feature using GitHub-recognized paths and repo-specific wording. Avoid placeholder boilerplate that does not describe this repo.
4. For ownership files such as `CODEOWNERS`, use only real maintainer usernames or teams that can be inferred safely from repo context. Never use placeholder bot owners; if no safe maintainer owner can be inferred, return to orchestrator.
5. When editing docs, prefer concise authoritative instructions over exhaustive prose. The goal is maintainer usability and readiness signal, not marketing copy.
6. When editing `.factory/` artifacts, keep them aligned with mission boundaries, the approved `127.0.0.1:3001` browser path, and the actual repo structure.
7. Verify every changed path exists where GitHub or Factory expects it, and cross-check that file references, command names, and port numbers are consistent across the edited files.
8. Run the relevant validators after edits. At minimum preserve `pnpm lint`, `pnpm typecheck`, and any changed scripts or doc-linked commands that can be exercised locally.
9. In the handoff, call out any remaining repo-admin items that are intentionally out of scope rather than leaving them implicit.

## Example Handoff

```json
{
  "salientSummary": "Replaced the starter README with repo-specific setup and validation guidance, added .env.example and hardened .gitignore, then added CODEOWNERS, Dependabot, and GitHub templates that reference the real validation flow. Also aligned the Factory artifact docs so maintainers can discover the 3001 browser-smoke path from committed guidance.",
  "whatWasImplemented": "Created repo-governance files for onboarding, review ownership, dependency updates, issue intake, PR review, and Factory operations. Updated maintainer-facing docs so they consistently reference pnpm commands, the local web validation path on 127.0.0.1:3001, and the approved repo-only readiness scope.",
  "whatWasLeftUndone": "",
  "verification": {
    "commandsRun": [
      {
        "command": "pnpm lint",
        "exitCode": 0,
        "observation": "Lint still passes after the governance and documentation edits."
      },
      {
        "command": "pnpm typecheck",
        "exitCode": 0,
        "observation": "TypeScript still passes; doc/config files did not introduce code regressions."
      },
      {
        "command": "git status --short",
        "exitCode": 0,
        "observation": "Verified the expected governance files are staged in GitHub-recognized paths."
      }
    ],
    "interactiveChecks": []
  },
  "tests": {
    "added": []
  },
  "discoveredIssues": [
    {
      "severity": "low",
      "description": "Branch protection and secret-scanning settings remain unconfigured because they require GitHub admin access outside the approved repo-files-only scope."
    }
  ]
}
```

## When to Return to Orchestrator

- The feature depends on choosing an owner handle, team, or policy text that cannot be inferred safely from repo context
- A governance file would need a GitHub admin/runtime capability to be validated and repo-file validation is insufficient
- The requested alignment would require changing product/application behavior outside the approved readiness scope
