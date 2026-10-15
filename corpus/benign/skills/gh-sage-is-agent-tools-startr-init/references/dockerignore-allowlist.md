# `.dockerignore` hidden-artifact allowlist

For any `.dockerignore` in Startr repos, mirror the `.gitignore` dot-allowlist convention (see `gitignore-dot-allowlist.md`) exactly so the two files feel like siblings.

**Why this shape (lenient `.*` + extras), not the stricter `*` baseline:** We chose consistency with the gitignore convention over the marginal extra safety of `*` (which excludes every non-dot top-level file by default and requires explicit `!` re-includes). The lenient shape is easier to read against the sibling `.gitignore` and has the same drift-resistance for the *dot-prefixed* secret-leak risks (`.env`, `.git/`, `.claude/`, `.aws/`, etc.). The cost is that a developer adding `config.prod.json` won't have it auto-excluded — they need to add the rule manually.

**Canonical template:**

```dockerignore
# Hidden-artifact allowlist: deny dotfiles and dotfolders everywhere in the
# build context unless they are intentionally needed inside the image.
.*

# Build & runtime junk (per-stack: node, python, etc.)
node_modules/
dist/
*.log
*.tgz

# Project-specific runtime data (created inside container; never bake in)
# pb_data/         # PocketBase
# db.sqlite3       # Django
# uploads/         # user-uploaded files

# Repo metadata not needed inside the image
README.md
LICENSE
Dockerfile
Makefile
```

**How to apply:**

- Lead with the explanatory comment block (same wording as `.gitignore`) so the sibling relationship is obvious.
- `.*` denies all dotfiles/folders — catches `.env`, `.git/`, `.claude/`, `.obsidian/`, `.aws/`, `.cache/`, `.next`, `.nuxt`, every dot-prefixed tool cache without enumeration.
- Add `!` re-includes only if the Dockerfile genuinely needs a dotfile at build time (e.g. `!.env.production` if explicitly required — though build args are usually better).
- Group non-dot junk by category with a one-line comment per group.
- Per-repo specifics go at the bottom (PocketBase `pb_data/`, Django `db.sqlite3`, large local assets, etc.).
- Cross-reference: before writing the file, read the Dockerfile's `COPY` directives and confirm none of them target paths the new `.dockerignore` would exclude.

**Conversion gotchas:**

1. **Verify every `COPY` target in the Dockerfile is still in the build context** before committing. Especially watch for non-dot files the original enumeration explicitly listed (e.g. `branding/`, `pb_hooks/`) — if they're not in your deny list, they're still included by default, which is usually correct.
2. **Multi-stage builds share the same build context.** A `--from=ui-builder` line doesn't bring in anything new from your filesystem — but the earlier stage's `COPY . .` is still constrained by your `.dockerignore`.
3. **Per-repo runtime data must be excluded** (pb_data/, db.sqlite3, uploads/, data/, site_backup/) — these are runtime state, not artifacts. Baking them in pollutes the image and can leak production data.
4. **Don't exclude things the registered captain-definition / docker-compose.yml references** for context paths — but typically these reference `./Dockerfile` and `./` only.
5. **Verification gate:** `docker build --no-cache .` + `docker run --rm <img> find / \( -name ".env*" -o -name "*.pem" \) 2>/dev/null` should return empty. Image size should not grow after the conversion.

**Trade-off acknowledged (vs the stricter `*` baseline):** the strict form (`*` + explicit `!package.json !src/ !server.js`) makes the Dockerfile the single source of truth and gives near-perfect leak protection — any new top-level file is excluded by default. We chose lenient for sibling-consistency with `.gitignore`. If a secret-leak incident happens, revisit and switch to strict.
