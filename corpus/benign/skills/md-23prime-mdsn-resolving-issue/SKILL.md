---
name: resolving-issue
description: Implement a GitHub Issue end-to-end: branch, implement, test, fix, review, commit, PR, and reflect learnings into docs/. Use when the user asks to work on, implement, fix, or resolve a GitHub Issue.
---

# Implementing Issue

Read `AGENTS.md` for architecture conventions and `docs/CONTRIBUTING.md` for branch/commit/PR rules.
Also read `docs/PATTERNS.md`, `docs/TESTING.md`, and `docs/VALIDATION.md` before implementing.

## Step 0 — Read the Issue

Determine the issue number from the user's message or context. Fetch the Issue:

```bash
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
gh issue view <N> -R "$REPO"
```

Read the title, body, and comments to understand the task fully before proceeding.

The Issue body follows `.github/ISSUE_TEMPLATE/default.md`. Extract the **Type** field
from the `## Type` section if present.

## Step 1 — Clarify task type

Use the Type extracted from the Issue body. If the `## Type` section is missing or unclear,
determine the type from context:

| Type | Branch prefix | Commit type |
| ---- | ------------- | ----------- |
| `feat` | `feature/` | `feat` |
| `fix` | `feature/` | `fix` |
| `refactor` | `feature/` | `refactor` |
| `perf` | `feature/` | `perf` |
| `docs` | `feature/` | `docs` |
| `ai` | `feature/` | `ai` |
| `chore` | `feature/` | `chore` |

Confirm the task and type with the user before proceeding.

## Step 2 — Create branch

Include the Issue number in the branch name:

```bash
git switch -c feature/<N>-<short-description>
```

## Step 3 — Implement

Follow `AGENTS.md` conventions. Consult the docs before writing code:

- `docs/PATTERNS.md` — source layout, how to add a rule, clap and output patterns
- `docs/TESTING.md` — test structure, helper patterns, DirGuard
- `docs/VALIDATION.md` — layer boundaries and what each layer validates

## Step 4 — Update `docs/SPEC.md` if needed

If the implementation changes user-visible behavior (new flags, new error codes, output format
changes, new validation rules), update `docs/SPEC.md` accordingly.

## Step 5 — Test against real files

```bash
mise run rs-run -- -- 'examples/*.md'
```

## Step 6 — Auto-fix and check

```bash
mise run fix
```

If any errors remain that cannot be auto-fixed, resolve them manually, then verify:

```bash
mise run check
```

Repeat until clean.

## Step 7 — CodeRabbit review

Invoke the `coderabbit` skill. Fix each actionable finding and re-review until clean.

## Step 8 — Commit

Follow `docs/CONTRIBUTING.md`:

- Conventional Commits, English only
- **No `Co-Authored-By:` line**

```bash
git add <files>
git commit -m "<type>: <description>"
```

## Step 9 — Push and open PR

```bash
git push -u origin feature/<N>-<short-description>
```

Create a PR following `.github/PULL_REQUEST_TEMPLATE.md`. PR body must be in English and include `Closes #<N>`.

```bash
gh pr create --title "<type>: ..." --body "$(cat <<'EOF'
## Checklist

- [ ] Target branch is `main`
- [ ] Status checks are passing

## Summary

## Reason for change

## Changes

## Notes

Closes #<N>
EOF
)"
```

## Step 10 — Address PR review comments

After opening the PR, GitHub Copilot and CodeRabbit will post review comments automatically. Check whether reviews have arrived:

```bash
gh pr view <PR_NUMBER> --json reviews | jq '[.reviews[].author.login]'
```

- If the array is empty, reviews have not arrived yet. Wait ~2–3 minutes and check again.
- If still empty after ~5 minutes, automated reviews are likely disabled — skip this step.
- If `copilot-pull-request-reviewer` or `coderabbitai` appear, invoke the `implementing-pr-review` skill to evaluate and apply valid suggestions.

## Step 11 — Reflect learnings into `docs/`

After the PR is merged, review what was encountered during implementation and PR review.
If anything is **generalizable** — useful for future implementations in this project — add it to the appropriate file under `docs/`.

Sources to review:

- **Accepted review comments**: patterns or pitfalls that reviewers pointed out
- **User corrections**: when the user said "no, not that — do X instead", consider whether X is a project-wide rule worth documenting
- **Compilation/check failures**: if `mise run check` failed for a non-obvious reason, note the fix

Choose the target file based on the nature of the learning:

| Learning type | Target file |
| --- | --- |
| Code patterns, clap/serde conventions, output formatting | `docs/PATTERNS.md` |
| Test structure, helper patterns, working directory gotchas | `docs/TESTING.md` |
| Validation boundary decisions, `try_new` vs `new` | `docs/VALIDATION.md` |

Criteria for adding:

- Would a future implementer likely make the same mistake?
- Is it specific to this codebase (not just "read the Rust docs")?
- Is it concrete enough to be actionable?

If any of the above apply, open a separate PR for the docs updates:

```bash
git switch main && git pull
git switch -c docs/patterns-from-issue-<N>
git add docs/
git commit -m "docs: add patterns from issue-<N> implementation"
git push -u origin docs/patterns-from-issue-<N>
gh pr create --title "docs: add patterns from issue-<N> implementation" --body "$(cat <<'EOF'
## Checklist

- [ ] Target branch is `main`
- [ ] Status checks are passing

## Summary

Add generalizable patterns learned during issue-<N> implementation.

## Notes

Related: #<PR_NUMBER>
EOF
)"
```

If nothing generalizable was found, skip this step.
