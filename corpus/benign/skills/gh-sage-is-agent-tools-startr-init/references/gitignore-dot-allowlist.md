# `.gitignore` hidden-artifact allowlist

For any `.gitignore` in Startr repos, prefer the **hidden-artifact allowlist** pattern over the conventional verbose template that lists each tool's dotfolder by name (`.next`, `.cache`, `.parcel-cache`, `.eslintcache`, etc.).

**Why:** One line (`.*`) collapses dozens of tool-specific entries and silently catches new ones (next year's `.foocache`) without a template update. Conventional templates rot — they list ignores for tools the project no longer uses and miss ignores for tools it just adopted. The allowlist inverts the default: hidden = secret by default, opt in only what's intentionally shared. Aligns with the DRY/KISS instinct behind the other Startr conventions.

**How to apply:** When creating or rewriting a `.gitignore`, lead with this block, then the non-dot junk (`node_modules/`, `dist/`, `*.log`, build outputs, etc.).

```gitignore
# Hidden-artifact allowlist: deny dotfiles and dotfolders everywhere in the
# repo unless they are intentionally shared and explicitly included below.
.*
!/.gitignore
!/.gitattributes
!/.dockerignore
!/.editorconfig
# .env.example anywhere (no leading slash = any depth). Keep this note on its
# OWN line — gitignore has no inline comments (see nuances below).
!.*.example
# Tool configs the team checks in — add as needed per repo:
!/.bandit.yaml
!/.gitleaks.toml
!/.pre-commit-config.yaml
!.todoscope-exclude.csv
# Folders need both the folder and its contents re-included:
!.semgrep/
!.semgrep/**
!.obsidian/
!.obsidian/**
# Nested dotfiles need their full path:
!/app/.eslintrc.cjs
!/app/.prettierrc
!/app/backend/.dockerignore
```

**Path-prefix nuances** (important — easy to get wrong):

- `!/.gitignore` — leading `/` anchors to repo root only (won't re-include nested copies).
- `!.*.example` — no leading `/` matches at any depth (e.g. `.env.example`, `app/.env.example`).
- **No inline/trailing comments.** `#` only starts a comment at the START of a line; a trailing `# note` after a pattern becomes PART of the pattern, so `!.*.example   # foo` silently fails to re-include `.env.example`. Keep every comment on its own line. (Caught the hard way; verify with `git check-ignore -v <path>`.)
- Folders need **both** `!folder/` and `!folder/**` to recurse into contents — re-including just the folder doesn't re-include the files inside.
- For selective tracking inside an otherwise-ignored folder: `docs/outreach/*` then `!docs/outreach/README.md`.

**Conversion gotchas:**

1. **Discover tracked dotfiles exhaustively** — don't truncate with `head` during discovery. Use `git ls-files | grep -E '(^|/)\.[^/]+' | wc -l` first to size the list, then read the full thing. Missed `.prettierignore`, `.prettierrc.mjs`, `.stylelintrc.json`, `.vscode/extensions.json`, `static/.nojekyll` in one docs repo because `head -30` cut off after Obsidian content.
2. **Anchor `dist/` to root with `/dist/`** when sub-repos / vendored projects have their own tracked `dist/`. Unanchored `dist/` matches at any depth and silently hides 16 tracked CSS files in a vendored `src/style-core/dist/`. Same caution for `build/`, `coverage/`, etc.
3. **Check for git submodules** before adding `dist/`-style ignores — submodule entries (mode 160000 in `git ls-tree`) shouldn't be added to gitignore; they're tracked as gitlinks. One repo had `dist/` as a submodule.
4. **Verify with `git ls-files -i -c --exclude-standard`** after writing — this catches any tracked file that the new rules would hide. Authoritative; don't trust hand-rolled `check-ignore` spot checks alone.
