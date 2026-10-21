# Changelog — revenantworks-localops-lmstudiorunner

## [1.0.0] — 2026-10-01

First public release. Hands work to a local model served by LM Studio and verifies what comes back.
It carries no model names: it reads what is installed, every run.

Description cut to about 600 characters, main use case first (2026-10-08).

### What it does

- Two modes, split by who reads the result and when: interactive (a check is recommended) and
  unattended (a check is required, and work without one is refused).
- Reads the live model metadata from LM Studio's native API (type, architecture, quantization,
  state, real context lengths, advertised capabilities) as data, never as instructions.
- Checks loaded context against the maximum, which the OpenAI-compatible endpoint does not show.
- Classifies the work and matches a model by class, never by name; scores a task before delegating
  it, and often says do not.
- Prefers schema-constrained generation, and states the limit: a schema constrains shape, never
  content.
- Diagnoses failures by shape: empty output from budget exhaustion on a reasoning model, and
  looping on a long list, whose fixes point in opposite directions.
- Checks the GPU before every load: who holds the pack lease, what is resident, the real VRAM size
  and LM Studio's own memory estimate. Never interrupts a running render, and unloads only what it
  loaded.
- Discovers the server port and tries both `127.0.0.1` and `localhost`.
- Runs in Claude Code and loads unchanged in LM Studio.

### Entry points

- `audit` (score installed models against the work classes), `size <task>`, `queue <task>` (writes a
  task card; refuses an unattended card with no check), `run`, `status`, `refresh`.

### Scripts

- The pack-shared `scripts/gpu_preflight.py` (read-only, Python 3 stdlib; run, not read) with its
  tests. The `lms` CLI is an optional, declared helper (`ps`, `unload`, `load --estimate-only`);
  without it the v1 REST calls are used and the estimate reads unmeasured.

### Safety rules

- Never commits, pushes or sends: it prepares, verifies and reports.
- No packages, no cloud network. Without a shell it hands back exact curl commands.
- Says plainly that delegation does not save tokens; it converts idle hardware and hours into work.

### Integrations

- Picking a cloud model or tier and writing prompt text are promptwright's; a scheduled run's
  guardrails agentwright's. Shares the GPU lease with comfyrunner, whisperrunner and obsrunner.
