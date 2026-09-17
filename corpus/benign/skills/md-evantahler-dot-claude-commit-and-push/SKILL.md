---
name: commit-and-push
description: Commit all changes and push to the current remote branch.
disable-model-invocation: true
argument-hint: "[commit message]"
allowed-tools: Bash(git *), Bash(bun lint*), Bash(bun format*), Bash(bun check*), Bash(bun fix*), Bash(bun run lint*), Bash(bun run format*), Bash(bun run check*), Bash(bun run fix*), Bash(bun x *), Bash(npm run lint*), Bash(npm run format*), Bash(npm run check*), Bash(npm run fix*), Bash(pnpm lint*), Bash(pnpm format*), Bash(pnpm check*), Bash(pnpm fix*), Bash(pnpm run lint*), Bash(pnpm run format*), Bash(pnpm run check*), Bash(pnpm run fix*), Bash(yarn lint*), Bash(yarn format*), Bash(yarn check*), Bash(yarn fix*), Bash(yarn run lint*), Bash(yarn run format*), Bash(yarn run check*), Bash(yarn run fix*), Bash(make lint*), Bash(make format*), Bash(make check*), Bash(make fix*), Bash(cd * && make *), Bash(cd * && bun *), Bash(cd * && npm *), Bash(cd * && pnpm *), Bash(cd * && yarn *), Bash(cd * && cargo *), Bash(cd * && go *), Bash(cargo clippy*), Bash(cargo fmt*), Bash(go vet*), Bash(cat package.json*), Bash(cat Makefile*), Bash(cat Cargo.toml*), Bash(gh pr *)
---

# Commit and Push

1. **Lint check**: Look for lint/check commands in the repo by inspecting project configs (e.g., `package.json` scripts, `Makefile` targets, etc.) at the repo root and in any subdirectories that have changed files. Common commands include `bun run check`, `bun lint`, `pnpm lint`, `npm run lint`, `yarn lint`, `make lint`, `cargo clippy`, `go vet ./...`, etc. Run whatever lint/format checks are available — if it's a monorepo, run checks at the root AND in affected subdirectories (e.g., `cd apps/engine && make lint`). If a check fails with auto-fixable issues, run the corresponding fix command (e.g., `bun run fix`, `bun format`, `make format`), then re-run the check to confirm. If no linter is found, skip this step.
2. Run `git status` to see what's changed
3. Run `git diff` and `git diff --staged` to understand the changes
4. Run `git log --oneline -5` to see recent commit style
5. Stage all relevant changed files by name (do NOT use `git add -A` or `git add .`)
6. If `$ARGUMENTS` is provided, use it as the commit message. Otherwise, write a concise commit message based on the diff. Always append the co-author trailer:

   ```text
   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   ```

7. Commit using a HEREDOC:

   ```bash
   git commit -m "$(cat <<'EOF'
   message here

   Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
   EOF
   )"
   ```

8. Push to the current branch with `git push`
9. If the current branch is not `main`, check if a PR already exists with `gh pr view --json url 2>&1`. If no PR exists, create a draft PR:

   ```bash
   gh pr create --draft --title "PR title" --body "$(cat <<'EOF'
   ## Summary
   <description>

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```

   Use the commit message as the PR title (first line) and expand on the changes in the body. If the PR closes a GitHub issue, include `Closes <issue URL>` (e.g., `Closes https://github.com/owner/repo/issues/123`) in the body so GitHub automatically links and closes the issue on merge.

   If a PR already exists, review the current title and description with `gh pr view --json title,body`. If they no longer accurately reflect the full set of changes on the branch (e.g., new commits added since the PR was created), update them with `gh pr edit --title "..." --body "..."`. Use `git log origin/main..HEAD` to understand all changes on the branch.

10. **Always update the PR description if anything important changed.** This is not optional — every push should leave the PR description accurate and up-to-date. Even if a PR already existed before this run, re-check the description against the full set of branch changes and update it if the new commit introduces meaningful differences.

11. Report the result, including the PR URL if one was created
