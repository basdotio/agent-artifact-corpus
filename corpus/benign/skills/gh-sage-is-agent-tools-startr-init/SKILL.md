---
name: startr-init
description: Bootstrap or align a repo to Startr.Cloud conventions — standard Makefile (help, git-derived vars, git-flow-next release/hotfix, things_clean), canonical `.gitignore` and `.dockerignore`, optional Docker / Startr.sh-web / CapRover blocks. Use for new Startr projects or "startr-init" / "startr-makefile".
argument-hint: (no arguments)
---

# /startr-init — Startr.Cloud convention scaffolder

Bootstrap a repo with the conventions used across the Startr.Cloud project family. **Current scope is the Makefile, the universal `.gitignore`, and the canonical `.dockerignore`** — there's room here for git hooks, GitHub Actions, etc. as future modules, but each is opt-in and lives in its own section.

When invoked: detect what's in the target repo, confirm the slice to scaffold, merge into existing files (don't blindly overwrite), and verify the result.

---

## Pre-flight

Run all of these first:

1. **Confirm we're in a git repo.** Standard variables read from `git remote` and `git rev-parse`. If not in a repo, ask whether to `git init` first.
2. **Check existing Makefile inode count.** `stat -f "%l %N" Makefile` — if link count > 1, **do NOT use Write** (breaks hardlinks). Edit in place via `sed` or HEREDOC append. Warn the user.
3. **Read existing Makefile if any.** Identify which standard targets are already present (so the merge doesn't duplicate them) and which custom targets must be preserved verbatim.
4. **Check for an existing `.gitignore`.** The Startr `.gitignore` is **universal** — written for every repo, no detection gate (see Block 11). If one already exists and doesn't use the `.*` allowlist convention (no `.*` line in the first ~5 non-comment lines), offer to convert it (don't overwrite silently — follow the conversion gotchas in Block 11).
5. **Detect project type** — used to propose optional blocks. Check for:
   - `Dockerfile` or `compose.yaml` / `docker-compose.yaml` → propose **Docker block** AND scaffold `.dockerignore` if missing (or offer to refactor if present and not yet using the `.*` allowlist convention)
   - `package.json` with a `build` script *or* a `startr.json` / `.startr/` marker → propose **Startr.sh web block**
   - `captain-definition` → propose **CapRover deploy block**
   - None of the above → universal-only is fine
6. **Confirm with the user.** Show the detected layers, ask for approval or override before writing.

---

## What the skill writes

Every Startr Makefile has the same skeleton, in this order:

```
# 1. help (default target — must come first)
# 2. Dynamic variables (git-derived)
# 3. -include .env
# 4. Project-specific custom targets (preserved from existing Makefile)
# 5. Optional layer: Startr.sh web (it_run / it_build / it_build_n_run)
# 6. Optional layer: Docker lifecycle
# 7. Optional layer: CapRover deploy
# 8. show_vars + verify (debug / one-shot self-check)
# 9. Git-flow-next release/hotfix flow
# 10. things_clean (with warning if uploads/ or persistent gitignored data exists)
# 11. .PHONY declarations
#
# (Separate files, not Makefile content:)
# 12. .gitignore (universal — lenient `.*` allowlist convention; always written)
# 13. .dockerignore (lenient `.*` allowlist convention; paired with Dockerfile detection)
```

### Branch convention

Startr follows **git-flow**: `develop` is the active working branch, `master` is the release-ready / distributable branch. **Never `main`.** The framing is the recording-industry mastering analogy — a "master" is the finished, distributable cut of a work; "develop" is the session where that version is being shaped. Every branch-name reference in scaffolded output (Makefile fallbacks, .PHONY targets, push destinations, runbook text) must use this naming. The `release_finish` / `hotfix_finish` recipes below already push to `develop` + `master` correctly.

The blocks below are the canonical recipes. Copy them verbatim — don't paraphrase.

### Block 1 — `help` target (universal, must be first so it's the default)

```makefile
help:
	@echo "================================================"
	@echo "       $(OWNER)/$(PROJECT_NAME) by Startr.Cloud"
	@echo "================================================"
	@echo "This is the default make command."
	@echo "This command lists available make commands."
	@echo ""
	@echo "Usage example:"
	@echo "    make it_run"
	@echo ""
	@echo "Available make commands:"
	@echo ""
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | \
		awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ { \
		if ($$1 !~ "^[#.]") {print $$1}}' | \
		sort | \
		grep -E -v -e '^[^[:alnum:]]' -e '^$@$$'
	@echo ""
```

If the project doesn't have `it_run`, replace the `Usage example` line with a target that *does* exist (e.g. `make run` or `make build`).

### Block 2 — Dynamic variables (universal)

```makefile
# Dynamic variable extraction (mirrors startr.sh)
PROJECTPATH := $(shell git rev-parse --show-toplevel)
PROJECT     := $(shell echo $$(basename $(PROJECTPATH)) | tr '[:upper:]' '[:lower:]')
# Use symbolic-ref (clean failure on empty repos) → short SHA (detached HEAD) → develop fallback.
# Do NOT use `git rev-parse --abbrev-ref HEAD` — it prints "HEAD" to stdout AND fails on a
# no-commits repo, producing a corrupted "HEAD develop" value.
FULL_BRANCH := $(shell git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo "develop")
BRANCH      := $(shell echo $(FULL_BRANCH) | sed 's/.*\///' | tr '[:upper:]' '[:lower:]')
TAG         := $(shell git describe --always --tag 2>/dev/null || echo "v0.0.0")

# Owner and project name extracted from git remote URL
REMOTE_URL   := $(shell git config --get remote.origin.url 2>/dev/null || echo "unknown/unknown")
OWNER        := $(shell echo $(REMOTE_URL) | sed -E 's|.*[:/]([^/]+)/[^/]+(.git)?$$|\1|')
PROJECT_NAME := $(shell echo $(REMOTE_URL) | sed -E 's|.*[:/][^/]+/([^/]+)(.git)?$$|\1|' | sed 's/\.git$$//')

# Container name (used by Docker block if present)
CONTAINER := $(PROJECT)-$(BRANCH)

# Load environment overrides from .env if present
-include .env
```

### Block 3 — `show_vars` + `verify` debug helpers (universal)

`show_vars` dumps resolved variables; `verify` is the one-shot self-check — it depends on `show_vars` and `require_gitflow_next` so they all run inside a single `make` process rather than N separate invocations. Always pair these together.

```makefile
show_vars:
	@echo "=== Dynamic Variables ==="
	@echo "PROJECTPATH=$(PROJECTPATH)"
	@echo "PROJECT=$(PROJECT)"
	@echo "OWNER=$(OWNER)"
	@echo "PROJECT_NAME=$(PROJECT_NAME)"
	@echo "FULL_BRANCH=$(FULL_BRANCH)"
	@echo "BRANCH=$(BRANCH)"
	@echo "TAG=$(TAG)"
	@echo "CONTAINER=$(CONTAINER)"
	@echo "REMOTE_URL=$(REMOTE_URL)"
	@echo ""

# One-shot scaffold self-check. Bundles every read-only verification into a
# single make invocation so post-scaffold testing isn't N separate processes.
verify: show_vars require_gitflow_next
	@echo "=== Targets defined in this Makefile ==="
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | \
		awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ { \
		if ($$1 !~ "^[#.]") {print "  " $$1}}' | \
		sort -u | \
		grep -E -v -e '^  [^[:alnum:]]'
	@echo ""
	@echo "OK: Makefile scaffold verified."
```

### Block 4 — Git-flow-next release/hotfix (universal)

Uses `git-flow-next` (the Go rewrite — `brew install git-flow-next`), **not** `git-flow-avh`. The version-bumping recipes assume tags follow `vX.Y.Z` (or `vX.Y.Z.W` for hotfixes).

```makefile
require_gitflow_next:
	@if ! git flow version 2>/dev/null | grep -q 'git-flow-next'; then \
		echo "Error: git-flow-next required (Go rewrite). Install: brew install git-flow-next"; \
		exit 1; \
	fi

minor_release: require_gitflow_next
	# Start a minor release with incremented minor version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2+1".0"}') && echo "or use 'make release_finish' to finish the release"

patch_release: require_gitflow_next
	# Start a patch release with incremented patch version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3+1}') && echo "or use 'make release_finish' to finish the release"

major_release: require_gitflow_next
	# Start a major release with incremented major version
	git flow release start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1+1".0.0"}') && echo "or use 'make release_finish' to finish the release"

hotfix: require_gitflow_next
	# Start a hotfix with incremented n.n.n.n version (incrementing the fourth number)
	git flow hotfix start $$(git tag --sort=-v:refname | sed 's/^v//' | head -n 1 | awk -F'.' '{print $$1"."$$2"."$$3"."$$4+1}') && echo "or use 'make hotfix_finish' to finish the hotfix"

release_finish: require_gitflow_next
	git flow release finish && git push origin develop && git push origin master && git push --tags && git checkout develop

hotfix_finish: require_gitflow_next
	git flow hotfix finish && git push origin develop && git push origin master && git push --tags && git checkout master
```

### Block 5 — `things_clean` (universal, **with** the .env-family preservation)

The standard across all sampled Makefiles uses `--exclude=!.env`, but that only preserves the literal file `.env` — split env files like `.env.local`, `.env.production` get wiped silently. We widen the pattern to `!.env*` to match intent.

```makefile
things_clean:
	git clean --exclude='!.env*' -Xdf
```

**Auto-detect persistent gitignored dirs and warn about them.** If the project has gitignored entries that look like *user data* (not build artifacts), prepend a `WARNING` comment listing them so future-you sees the blast radius.

Detection algorithm: read `.gitignore`, strip comments and blank lines, drop entries matching the **build/cache denylist** below, drop entries that don't currently exist on disk. What remains is the candidate list — present it to the user for confirmation, then write the comment.

```bash
# Build/cache patterns to IGNORE (these are reproducible — no warning needed):
__pycache__   *.pyc   *.pyo   .pytest_cache   .mypy_cache   .ruff_cache
.venv   venv   env   *.egg-info   dist   build   .eggs
node_modules   .next   .nuxt   .svelte-kit   .turbo   .parcel-cache
target   out   bin   obj   .gradle   .idea   .vscode
.cache   .tmp   tmp   .DS_Store   Thumbs.db   *.log   logs
.env*           # already preserved
.coverage   coverage   htmlcov   .nyc_output
```

Anything in `.gitignore` that doesn't match one of those patterns AND exists on disk is a candidate. Common true-positives: `uploads/`, `data/`, `media/`, `db.sqlite3`, `storage/`, `var/`. Common false-positives the denylist avoids: `*.pyc`, `__pycache__/`, `node_modules/`.

Comment template (only emit if the candidate list is non-empty):

```makefile
# WARNING: things_clean wipes ALL gitignored files including:
#   uploads/   - rendered comics + source videos
#   data/      - <user description>
# It preserves any file matching .env* (e.g. .env, .env.local, .env.production).
# Use a narrower target (like `make clean`) for routine wipes.
```

When proposing the candidates to the user, also ask for a one-line description of each — it goes after the dash in the comment so the warning is human-meaningful, not just a path list.

If the candidate list is empty, emit only the bare target (no warning comment).

### Block 6 — Startr.sh web (optional)

Only include if the project uses the Startr.sh web bootstrap (detected by `package.json` build script + Startr marker, or user override).

```makefile
it_run:
	@bash -c 'bash <(curl -sL startr.sh) run'

it_build:
	@bash -c 'bash <(curl -sL startr.sh) build'

it_build_n_run:
	@bash -c 'bash <(curl -sL startr.sh) build && bash <(curl -sL startr.sh) run'
```

### Block 7 — Docker lifecycle (optional)

Only if `Dockerfile` or `compose.yaml` is present.

```makefile
it_stop:
	-docker stop $(CONTAINER)
	-docker rm $(CONTAINER)

it_clean:
	docker image prune -f
	docker builder prune -f

it_gone: it_stop
	-docker rmi $(CONTAINER):$(BRANCH)
```

For projects pushing to GHCR (detected by existing `IMAGE_NAME` references or user opt-in), also include:

```makefile
ghcr_login:
	@gh auth token | docker login ghcr.io -u $(OWNER) --password-stdin

it_build_multi_arch_push_GHCR: ghcr_login
	docker buildx build --platform linux/amd64,linux/arm64 \
		-t ghcr.io/$(shell echo $(OWNER) | tr '[:upper:]' '[:lower:]')/$(PROJECT):$(BRANCH) \
		-t ghcr.io/$(shell echo $(OWNER) | tr '[:upper:]' '[:lower:]')/$(PROJECT):$(TAG) \
		--push .
```

### Block 8 — CapRover deploy (optional)

Only if `captain-definition` is present.

```makefile
HAS_SUBMODULE := $(shell [ -f .gitmodules ] && echo 1)
HAS_CAPROVER  := $(shell which caprover 2>/dev/null && echo 1)

deploy:
	@if [ "$(HAS_CAPROVER)" = "" ]; then \
		echo "CapRover CLI not installed. Run: npm install -g caprover"; exit 1; \
	fi
	@if [ "$(HAS_SUBMODULE)" = "1" ]; then \
		echo "Submodules detected — deploying via tar"; \
		git ls-files --recurse-submodules | tar -czf deploy.tar -T -; \
		npx caprover deploy -t ./deploy.tar; \
		rm ./deploy.tar; \
	else \
		npx caprover deploy; \
	fi
```

### Block 9 — `.dockerignore` (separate file, paired with Dockerfile presence)

This block writes a **separate file** (`.dockerignore` at repo root), not Makefile content. Trigger: same `Dockerfile`/`compose.yaml` detection as the Docker Makefile block.

The convention mirrors the Startr `.gitignore` allowlist — deny dotfiles/folders with `.*` then enumerate non-dot project junk. Two files (`.gitignore` and `.dockerignore`) feel like siblings, which makes future-you's diffing easier and means a developer who internalized the gitignore shape doesn't have to learn a second one.

**If `.dockerignore` is missing — write this template:**

```dockerignore
# Hidden-artifact allowlist: deny dotfiles and dotfolders everywhere in the
# build context unless they are intentionally needed inside the image.
.*

# Build & runtime junk (per-stack — keep only what applies)
node_modules/
dist/
*.log
*.tgz

# Project-specific runtime data (never bake into the image)
# pb_data/         # PocketBase
# db.sqlite3       # Django
# uploads/         # user-uploaded files

# Repo metadata not needed inside the image
README.md
LICENSE
Dockerfile
Makefile
```

**If `.dockerignore` already exists** but doesn't use the convention (no `.*` line in the first ~5 non-comment lines):

1. Read the existing file. List every entry.
2. Drop dot-prefixed entries (covered by `.*`); preserve non-dot entries.
3. Cross-check against the Dockerfile's `COPY` directives: anything the Dockerfile explicitly copies must NOT be in the deny list.
4. Propose the refactor diff to the user before writing.

**Refactor verification gates:**

1. **[WE]** Read every `COPY` line in the `Dockerfile` (`grep '^COPY' Dockerfile`). For each one, confirm the source path is not matched by the new `.dockerignore` patterns.
2. **[MANUALLY]** Run `docker build --no-cache .` and confirm success — image-leak check is `docker run --rm <img> find / \( -name ".env*" -o -name "*.pem" \) 2>/dev/null` returning empty.
3. **[WE]** Compare image sizes before/after with `docker image ls` — should not grow.

Reference: `references/dockerignore-allowlist.md` documents the lenient-vs-strict trade-off and conversion gotchas.

### Block 10 — `.PHONY` (universal, last)

Build the list from whichever blocks were included. Wrap at ~80 chars with backslash-continuation:

```makefile
.PHONY: help show_vars verify require_gitflow_next \
	minor_release patch_release major_release hotfix \
	release_finish hotfix_finish things_clean \
	it_run it_build it_build_n_run \
	it_stop it_clean it_gone ghcr_login it_build_multi_arch_push_GHCR \
	deploy \
	<custom targets preserved from existing Makefile>
```

### Block 11 — `.gitignore` (universal, separate file — always written)

This block writes a **separate file** (`.gitignore` at repo root), not Makefile content. **No detection gate** — every Startr repo gets it, same as the Makefile. It's the sibling of the `.dockerignore` allowlist (Block 9): deny all dotfiles/dotfolders with `.*`, then explicitly re-include the ones the team checks in, then the non-dot junk. Per the `feedback-gitignore-dot-allowlist` memory — one `.*` line collapses dozens of tool-specific entries and silently catches next year's `.foocache` without a template update.

**If `.gitignore` is missing — write this template** (trim the re-includes to what the repo actually tracks; `!/.dockerignore` only if the Docker layer was scaffolded):

```gitignore
# Hidden-artifact allowlist: deny dotfiles and dotfolders everywhere in the
# repo unless they are intentionally shared and explicitly included below.
.*
!/.gitignore
!/.gitattributes
!/.dockerignore
!/.editorconfig
# .env.example at any depth (no leading slash). Keep this note on its OWN line —
# gitignore has no inline comments; a trailing comment becomes part of the pattern.
!.*.example
# Tool configs the team checks in — uncomment/add per repo as adopted:
#!/.pre-commit-config.yaml
#!/.gitleaks.toml
#!.todoscope-exclude.csv

# Non-dot build & runtime junk (root-anchored so vendored sub-repos keep their own)
node_modules/
/dist/
/build/
*.log
*.tgz

# Project-specific runtime data (never commit)
# uploads/
# data/
# db.sqlite3
```

**Path-prefix nuances** (easy to get wrong — get them right):

- `!/.gitignore` — leading `/` anchors to repo root only (won't re-include nested copies).
- `!.*.example` — no leading `/` matches at any depth (e.g. `.env.example`, `app/.env.example`).
- **No inline/trailing comments.** `#` only starts a comment at the START of a line; a trailing `# note` after a pattern becomes PART of the pattern, so `!.*.example   # foo` silently fails to re-include `.env.example`. Every comment on its own line.
- Folders need **both** `!folder/` and `!folder/**` to recurse into contents.
- Anchor `/dist/`, `/build/`, `/coverage/` to root when vendored sub-repos have their own tracked copies — unanchored matches at any depth and silently hides tracked files.

**If `.gitignore` already exists** but doesn't use the convention (no `.*` line in the first ~5 non-comment lines), offer to convert (don't overwrite silently):

1. **Size the tracked-dotfile list first, don't truncate:** `git ls-files | grep -E '(^|/)\.[^/]+' | wc -l`, then read the full list — a `head` cut-off misses files like `.prettierrc`, `.vscode/extensions.json`, `static/.nojekyll` that then need explicit `!` re-includes.
2. **Check for submodules** (`git ls-tree` mode 160000) before adding `dist/`-style ignores — gitlinks shouldn't be added to gitignore.
3. Preserve non-dot entries; drop dot-prefixed ones covered by `.*`; add a `!` re-include for every tracked dotfile from step 1.
4. Propose the diff to the user before writing.

**Verification gate (authoritative):**

1. **[WE]** After writing, confirm no tracked file is now hidden: `git ls-files -i -c --exclude-standard` (should print nothing). Don't trust hand-rolled `check-ignore` spot checks alone.
2. **[WE]** Confirm the re-includes actually track: `git add --dry-run .gitignore .dockerignore Makefile .env.example` lists them; `.env` is reported ignored. (`git check-ignore -v` is misleading on negations — it prints the matching `!` line and exits 0.)

Reference: `references/gitignore-dot-allowlist.md` documents the convention and conversion gotchas.

---

## Merge strategy (when an existing Makefile is present)

Don't blindly overwrite. The merge rules:

1. **Preserve all custom (non-standard) targets and their recipes verbatim.** A target is "custom" if it's not in the standard list above.
2. **Replace any standard target that already exists** with the canonical recipe (the standard wins; older drift is fixed).
3. **Preserve the user's variable overrides** if they've customized a standard variable (e.g. forced `BRANCH := develop`). Show what was kept and ask whether to keep or replace with the standard derivation.
4. **Move `help` to the top** so it's the default.
5. **Move `.PHONY` to the bottom** and rebuild it from the actual final target list.
6. **Group sections** with the comment dividers shown above (`# 1. help`, `# 4. Custom targets`, etc.) so future merges are easier.

After the merge, run `make verify` to confirm the scaffold.

---

## Verification

After writing the Makefile:

1. **[WE]** `make verify` — single invocation that resolves all dynamic variables (via the `show_vars` dependency), runs the git-flow-next preflight (via the `require_gitflow_next` dependency), enumerates every target defined in the Makefile, and prints `OK` on success. This is the canonical post-scaffold check — do NOT run `make help` / `make show_vars` / `make require_gitflow_next` as three separate invocations; that pattern is wasteful and was explicitly flagged by the user.
2. **[WE]** If a Makefile already existed and was merged: re-run any preserved custom targets (e.g. `make run`, `make vendor`) to confirm the merge didn't break them.
3. **[WE]** `.gitignore` sanity (per Block 11): `git ls-files -i -c --exclude-standard` prints nothing (no tracked file newly hidden), and `git add --dry-run` shows the intended re-includes track while `.env` stays ignored.
4. **[MANUALLY]** Don't actually run `make minor_release` / `release_finish` etc. as part of verification — those mutate state and push to remotes. Just confirm the recipe text.

Report what was added, what was preserved, and any user-customized variables that were kept.

---

## Notes for future modules

This skill is named `/startr-init` (not `/startr-makefile`) so additional Startr conventions can be folded in without renaming. Plausible future modules:

- `.editorconfig` standard
- GitHub Actions: lint + release workflow templates
- Pre-commit hooks for the Sage.is identity / no-emoji rules
- `scripts/release.sh` interactive flow

When adding a new module: add a section above named `What the skill writes — <module>`, gate it on detection or explicit opt-in, and update the Pre-flight detection list.
