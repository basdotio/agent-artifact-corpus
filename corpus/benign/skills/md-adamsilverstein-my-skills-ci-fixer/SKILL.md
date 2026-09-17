---
name: ci-fixer
description: "Fix failing CI tests on a PR and ensure all checks pass. Use when the user wants to fix CI failures, resolve failing tests, fix linting errors on a PR, or ensure all GitHub Actions/CI checks pass. Triggers include requests like 'fix the CI', 'fix failing tests on this PR', 'make the CI pass', 'fix linting errors', 'resolve CI failures', or any CI/test fixing task."
---

# CI Fixer Skill

Diagnose, fix, and monitor CI failures on GitHub PRs. Persistent until all required checks pass.

## Workflow

1. **Analyze PR** - Get PR number, run `gh pr checks` to identify failures
2. **Diagnose** - Use `gh run view [RUN_ID] --log-failed` to get error details
3. **Fix** - Apply targeted fixes based on failure type (see below)
4. **Verify locally** - Run tests/linters locally before pushing
5. **Commit & Push** - Stage changes, commit with clear message, push
6. **Monitor** - Wait 3 minutes, check `gh pr checks`, repeat until all pass

## Essential Commands

```bash
# Check CI status
gh pr checks [PR_NUMBER]
gh pr checks [PR_NUMBER] --json name,state,conclusion

# Get failure logs
gh run view [RUN_ID] --log-failed

# Check for failing jobs (returns empty if all pass/skip)
gh pr checks [PR_NUMBER] --json name,state,conclusion | jq '.[] | select(.state == "completed" and .conclusion != "success" and .conclusion != "skipped")'
```

**Status meanings:**
- `conclusion: "success"` or `"skipped"` = OK
- `conclusion: "failure"` = Needs fix
- `state: "pending"/"queued"/"in_progress"` = Still running, wait

## Fix Strategies

**Linting:** Run auto-fix first (`npx eslint --fix`, `npx prettier --write`, `./vendor/bin/phpcbf`)

**Tests:** Read test + implementation, determine which is wrong, fix appropriately, verify locally

**Types:** Check TypeScript (`npx tsc --noEmit`) or PHPStan output, fix annotations/mismatches

**Builds:** Check logs for missing deps, syntax errors, import issues

## Important Rules

- Always verify fixes locally before pushing
- Make atomic commits with clear messages
- Don't blindly auto-fix; review changes
- Ask user if fix is ambiguous or could break functionality
- Be persistent: continue monitor/fix loop until all checks pass or user cancels
