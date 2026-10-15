# Section Selection Guide

The master template (`assets/master-template.md`) is a menu, not a checklist.
Most repos should use 40-60% of it. Including a section with nothing real to
put in it (placeholder text, invented numbers, a "Kubernetes Deployment"
section for a repo with no Kubernetes anywhere) is worse than leaving it out.

Always ask: is there a real file, config, or code path backing this section?
If not, drop the section. Don't shrink it to a stub — remove it entirely.
That one rule is the whole method — everything below is worked examples of
applying it to patterns that come up often, not a closed list of allowed
project types. A repo that doesn't match any row still gets the same
treatment: look at what's actually there and keep only what it supports.

## Detection signals

These are common patterns, useful for guessing what a repo's README
audience expects — not categories a repo needs to be sorted into.

| Project type | Signals to look for |
|---|---|
| Embedded / firmware / IoT | `platformio.ini`, `*.ino`, `sdkconfig`, `esp_*.h` / `Arduino.h` / `WiFi.h` includes, `CMakeLists.txt` targeting a chip toolchain, `boards.txt`, references to pins/I2C/OneWire/GPIO in code |
| Desktop app | Qt (`.pro`, `CMakeLists.txt` with `find_package(Qt...)`, `QApplication`), Electron (`main.js` + `package.json` with `electron`), `.NET`/WPF, GTK |
| Backend / web service | `Dockerfile`, `docker-compose.yml`, server framework imports (Express, FastAPI, Flask, Gin, Actix, Spring Boot), `k8s/` or `helm/` dirs, OpenAPI/Swagger spec |
| CLI tool | `bin` field in `package.json`, `argparse`/`click`/`cobra`/`clap` usage, single-purpose script with a `main()` entry point, no server code |
| Library / SDK | Published to a package registry (has a `publish` config, version badge target), public API surface is the point, no deployment artifacts |
| Automation workflow export | `.json` with n8n's `nodes`/`connections` schema, Power Automate `.flow` / ARM template export, Zapier/Make export |
| Data / ML project | Notebooks (`.ipynb`), `requirements.txt`/`environment.yml` heavy on pandas/numpy/torch/sklearn, `data/` dir, training scripts |

A repo can match more than one row (e.g. a backend service with a CLI
admin tool). Cover both; don't force a single label.

## What to keep / drop per type

### Embedded / firmware / IoT
**Keep:** About, Key Capabilities, Requirements (rewrite "Hardware Boundary
Profile" as the *actual* board + sensors + wiring, not a resource-limits
table — e.g. "ESP32-WROOM-32, MAX30102 via I2C, DS18B20 via OneWire" from the
real includes/pin defs), Toolchain & flashing (board package version,
upload command / port, not a Docker command), Usage (serial monitor output,
BLE/HTTP API only if the firmware actually exposes one), Architecture (task/
loop structure, interrupt or ISR notes if present), Testing (only if there's
an actual test harness — otherwise a short "Validation" note on how it was
bench-tested, grounded in comments/commit history if evidenced), Troubleshooting
(wiring/upload/port issues), License.
**Drop:** Kubernetes/Helm, Config Matrix (unless there are real build-time
`#define` flags worth tabulating), DB Migration Policy, Observability/health
endpoints, Rollback & Recovery, Scaling Model.

### Desktop app
**Keep:** About, Requirements (Host & OS compatibility, real toolchain
versions from the build files), Quickstart (per-OS build/packaging steps),
Usage (screenshots if present in repo, CLI flags), Architecture (module/class
breakdown for anything non-trivial, e.g. a Qt6 MVC split), Testing, License,
Contributing (only if a `CONTRIBUTING.md` or PR template exists).
**Drop:** Kubernetes, hardware boundary profile, DB migration policy /
observability (unless the app talks to a real backend — then keep a short
data-flow note, not the full production apparatus).

### Backend / web service
Closest to the full template. **Keep:** Config Matrix (from real env vars /
`.env.example`), Deployment, Health & Readiness (only if endpoints exist in
code), Observability (only if logging/metrics/tracing libs are actually
wired in), DB Migration Policy (only if a migration tool/folder exists),
Rollback & Recovery, Scaling Model — all grounded in what's in the repo, not
a generic SRE checklist.

### CLI tool / library / SDK
**Keep:** About, Installation (via the real package manager/registry),
Usage Patterns (real command examples / real function signatures),
API & Interface Documentation (for libraries — pull real exported
functions/classes, not invented ones), Versioning & Changelog (only if a
`CHANGELOG.md` or semver tags exist), License.
**Drop:** Deployment, observability, DB sections, hardware profile.

### Automation workflow export (n8n / Power Automate / Zapier)
This is the one category where the master template's shape barely applies —
write a different structure:
- What it does: trigger → steps → outcome, in plain language
- Required credentials/connections and where to configure them
- Import instructions (n8n: Import from File/URL; Power Automate: import
  package steps)
- Node-by-node or step-by-step summary of the meaningful nodes only
- Customization points (hardcoded URLs, sheet IDs, webhook paths to change)
- Error handling/retry behavior, only if actually configured on the nodes
- License/usage note
Skip deployment, hardware, DB migration, observability sections entirely.

### Data / ML project
**Keep:** About, Data sources (with real dataset names/links found in code
or docs), Environment setup (conda/pip, from the real lockfile), Reproducing
results (real script/notebook invocation order), Key outputs, License notes
for the dataset if stated. **Drop:** deployment/observability unless there's
a real served model API (then treat that part like a backend service).

## When nothing fits cleanly

If the repo is small (a script, a homework assignment, a rough prototype),
most of this guide's "keep" lists still overshoot. In that case use only:
About, Requirements, Quickstart, Usage, License. Don't pad a small project
with sections just because the template has them.
