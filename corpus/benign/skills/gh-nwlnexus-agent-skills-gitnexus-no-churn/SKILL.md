---
name: gitnexus-no-churn
description: Set up or repair GitNexus in a repository so it never causes churn — no "index is N commits behind" after every commit and no CLAUDE.md/AGENTS.md rewrites from `gitnexus analyze`. Use when adding GitNexus to a repo, when the index reports itself stale/behind, when `gitnexus analyze` dirties CLAUDE.md/AGENTS.md/.claude/skills, or when asked to "apply the gitnexus no-churn pattern". Works with husky, lefthook, pre-commit or plain git hooks, any language.
---

# GitNexus without churn

GitNexus causes two kinds of recurring noise when used naively:

1. **Stale index.** The index records the commit it was built at; every commit makes it "N commits behind" and the Claude hook nags to re-run `analyze`.
2. **Doc rewrites.** A bare `gitnexus analyze` injects volatile symbol counts into the managed `<!-- gitnexus:start -->…<!-- gitnexus:end -->` section of `CLAUDE.md`/`AGENTS.md` and reinstalls skills, so each re-index produces a diff that wants a commit.

The fix is the same in every repo: **git hooks keep the index at HEAD with `--index-only`**, and **the docs are generated once with `--no-stats`** and only regenerated after a gitnexus upgrade. Apply it as one `chore(gitnexus): …` PR.

## Step 0 — preconditions (read-only)

```sh
command -v gitnexus && gitnexus --version          # must be installed (mise/npm global); never rely on npx
test -f .gitnexus/gitnexus.json && gitnexus status # indexed? if not: gitnexus analyze --index-only
git config core.hooksPath; ls .husky lefthook.yml .lefthook.yml .pre-commit-config.yaml 2>/dev/null
ls CLAUDE.md AGENTS.md; grep -c 'gitnexus:start' CLAUDE.md AGENTS.md 2>/dev/null
ls package.json Makefile justfile 2>/dev/null
```

Decide: **hook manager** (husky → lefthook → pre-commit → plain), **where repo-local scripts live** (`scripts/`, `tools/`, `bin/`… match the repo), **how the repo exposes commands** (`package.json` scripts, `Makefile`, `justfile`, or none → document the raw command).

## Step 1 — install the refresh script

Copy `scripts/gitnexus-refresh.sh` from this skill directory to the repo's scripts location (e.g. `scripts/git-hooks/gitnexus-refresh.sh`), `chmod 755`. It is repo-agnostic: resolves the git root, exits silently if gitnexus is missing or the clone isn't indexed, skips when the index already matches HEAD, otherwise runs `gitnexus analyze --index-only` detached (log in `.gitnexus/refresh.log`). Don't fork it per repo unless the repo's conventions demand (e.g. a different scripts dir).

## Step 2 — wire post-commit, post-merge, post-checkout, post-rewrite

Hook bodies are one line: `sh <path>/gitnexus-refresh.sh`. `post-checkout` must run only for branch checkouts that move HEAD: `[ "$3" = "1" ] && [ "$1" != "$2" ] || exit 0` first.

- **husky** (`.husky/` exists): add `.husky/post-commit`, `post-merge`, `post-checkout`, `post-rewrite` (same shebang/mode as the existing hooks; husky 9 runs them with `sh -e`).
- **lefthook**: add `post-commit`, `post-merge`, `post-checkout`, `post-rewrite` sections with a single `gitnexus-refresh` command; `run: sh <path>/gitnexus-refresh.sh {1} {2} {3}` for post-checkout.
- **pre-commit framework**: add a `repo: local` hook with `stages: [post-commit, post-merge, post-checkout, post-rewrite]`, `always_run: true`, `pass_filenames: false`; remind the user to `pre-commit install --hook-type post-commit --hook-type post-merge --hook-type post-checkout --hook-type post-rewrite`.
- **none**: create a committed `.githooks/` with the four files and set `git config core.hooksPath .githooks` in the repo's setup script/Makefile target (never rely on an uncommitted `.git/hooks`).

Never put the hook under `pre-commit`/`pre-push`: those must stay fast and the index should follow the *resulting* HEAD.

## Step 3 — make the docs stable

1. Regenerate the managed section once without counts: `gitnexus analyze --force --no-stats --skip-skills`. Expect a diff that only removes the `(N symbols, …)` header counts and the per-area count table. If the repo never had a managed section and doesn't want one, use `--index-only` everywhere and skip this.
2. Expose two commands using the repo's convention:
   - routine refresh → `gitnexus analyze --index-only` (e.g. `pnpm gitnexus:index` / `make gitnexus-index`)
   - docs refresh → `gitnexus analyze --force --no-stats --skip-skills` (e.g. `gitnexus:refresh-docs`), *only* after a gitnexus upgrade changes its template.
3. Add a short **"GitNexus index hygiene"** section to `CLAUDE.md` (and `AGENTS.md` if present) **outside** the markers, adapted to the repo:

   > The index (`.gitnexus/`, untracked) is refreshed automatically by the `post-commit`/`post-merge`/`post-checkout`/`post-rewrite` hooks (`<path>/gitnexus-refresh.sh`): index-only, background, log in `.gitnexus/refresh.log`. If it still reports itself behind, run `<index command>`.
   > - Do NOT run a bare `gitnexus analyze` (or `node .gitnexus/run.cjs analyze`): it rewrites `CLAUDE.md`, `AGENTS.md` and `.claude/skills/gitnexus-*`. Use `<index command>`.
   > - `<docs command>` regenerates the managed `gitnexus:start`…`gitnexus:end` section without volatile counts; run it only after a gitnexus upgrade, commit the result. Never hand-edit between the markers.

4. If the repo still has the obsolete nested `.claude/skills/gitnexus/<skill>/` layout or committed `.claude/skills/generated/**`, replace them with the flat `.claude/skills/gitnexus-*` layout GitNexus ≥1.6 writes (`gitnexus analyze --skills --skip-agents-md` regenerates `gitnexus-area-*`; `git rm` the old dirs). The area skills carry counts in their *bodies* only, which is fine — they are not re-generated by the hooks.

## Step 4 — verify before opening the PR

```sh
git commit …                      # fires post-commit
sleep 10; tail -3 .gitnexus/refresh.log; gitnexus status   # Indexed == Current, ✅ up-to-date
git status --short                # must be clean: no CLAUDE.md/AGENTS.md/skills diff
```

Then push, PR, merge (if authorised), pull `main` — the pull fires `post-merge`; confirm `gitnexus status` again.

## Rules of thumb

- `--index-only` for anything automated; `--no-stats` for anything that touches the docs; never bare `analyze`.
- Index refresh is cheap (seconds, incremental) but rapid rebases queue several runs; gitnexus's own lock serialises them — do not add locking in the hook.
- Multiple worktrees each have their own `.gitnexus/`; the hooks handle each one independently.
- Running gitnexus through `npx` is slow (registry round-trip, TLS-sensitive) and can exceed MCP's 30 s connect timeout — install it (mise/npm global) and reference the binary.
- Don't change the per-user GitNexus MCP/hook setup from inside a repo; that lives in the user's Claude config (nix-managed for Nigel).
