---
name: readme-writer
description: Writes a production-quality README.md for any code repository, grounded entirely in the repo's real contents. Give it a repo link to clone, or paste/upload the repo's files, and it inventories manifests, CI config, build files, and code, works out what kind of project it actually is, and drafts a README using only the sections that project needs — no placeholder text, no invented badges or benchmarks, no boilerplate sections that don't apply. Works the same way regardless of language, stack, or project category. Use whenever asked to write, generate, or improve a README for a repo, or for a specific named project, in whatever wording that request takes.
---

# README Writer

Produces one README.md, grounded in what the repository actually contains.
Two failure modes to avoid equally: a generic template with brackets left
in, and a confident README that states things the repo doesn't back up.

## Workflow

### 1. Get the repo

Auto-detect how it's being handed to you:

- **GitHub URL in the request** — shallow clone it:
  `git clone --depth 1 <url> /home/claude/repo-work/<name>`
  This works because `github.com` and `codeload.github.com` are reachable.
  Other hosts (GitLab, Bitbucket, private GitHub) generally aren't — if the
  clone fails, say so plainly and ask for a zip upload or pasted files
  instead of retrying silently.
- **Uploaded zip/files** (`/mnt/user-data/uploads/`) — unzip to a working
  directory.
- **Pasted file contents / directory listing in chat** — work from that text
  directly; ask for the specific files you need if the paste is too partial
  to inventory (e.g. only a tree with no manifest contents).

### 2. Inventory

Before drafting anything, build a picture of what's real:

- Directory structure (`find . -not -path '*/.git/*' | sort`, or similar)
- Manifests: `package.json`, `requirements.txt`/`pyproject.toml`,
  `Cargo.toml`, `go.mod`, `CMakeLists.txt`, `platformio.ini`, `*.pro`
- CI: `.github/workflows/*`, `.gitlab-ci.yml`
- Containers/infra: `Dockerfile`, `docker-compose.yml`, `k8s/`, `helm/`
- `LICENSE`, existing `README*`, `CHANGELOG.md`, `.env.example`
- Entry points and any obviously central source files — open enough of
  them to know what the thing actually does, not just what it's named
- Anything else specific to the stack you find — hardware/pin/protocol
  references, notebook files, workflow-export JSON schemas, and so on

Read this list of evidence like a checklist you'll need in step 5 — every
line you write later has to trace back to something found here.

### 3. Work out what kind of project it is

Use `references/section-selection.md`'s detection signals and keep/drop
guidance. The categories it lists (embedded, desktop app, backend service,
CLI/library, automation export, data/ML) are common patterns, not an
exhaustive or restrictive list — a repo can span more than one, or match
none cleanly. Either way, the same rule underneath applies regardless of
category: a section earns its place only if the inventory actually backs
it up. If a repo doesn't fit any listed pattern, apply that rule directly
from what step 2 found instead of forcing it into one of the examples.

### 4. Choose sections

Open `assets/master-template.md` — it's the full menu of sections this
template family supports (badges, About, Requirements, Quickstart, Usage,
Architecture, Config Matrix, Deployment, Observability, DB Migration
Policy, Rollback, Testing, Troubleshooting, Versioning, Contributing,
License, etc.). Per `references/section-selection.md`'s mapping for this
project's type, keep only the sections with real evidence behind them from
step 2. State your section choice to yourself before drafting — if you
can't name the evidence for a section, it's out.

### 5. Draft

Follow the master template's heading style and ordering for the sections
you kept. Fill every value from the inventory — real commands, real env
var names, real version numbers, real board/sensor names, real function
signatures. Where the template implies something you have no evidence for
(a badge, a benchmark, a support policy), omit that line or row rather than
guessing or leaving a placeholder.

If an existing README is present, read it for facts worth keeping (real
gotchas, real usage notes) — don't reuse its wording, and don't carry over
a claim you can't verify from the current repo state.

### 6. Style pass

Apply `references/writing-style.md`: no marketing filler, no unearned
superlatives, badges only with evidence, sentences that use the project's
own names and numbers. Read the draft once specifically hunting for lines
that could apply to any repo — cut or make them specific.

### 7. Save and hand it over

Write the file to `/mnt/user-data/outputs/README.md` and present it. This
skill only produces the file — it doesn't commit anything back into the
repo. If something notable from the old README couldn't be verified and
was dropped, say so in one line so the user can decide whether to restore
it by hand.

## Reference files

- `references/section-selection.md` — project-type detection signals and
  which sections to keep/drop for each
- `references/writing-style.md` — the anti-filler, anti-fabrication rules
  for the actual prose
- `assets/master-template.md` — the full section menu and heading structure
  to draw from
