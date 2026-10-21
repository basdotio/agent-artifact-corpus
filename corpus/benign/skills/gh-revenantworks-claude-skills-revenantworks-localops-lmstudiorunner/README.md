# revenantworks-localops-lmstudiorunner

Hands work to a local model served by LM Studio, and answers the two questions
that decide whether that was a good idea: **is this task the right shape for a
local model**, and **is the right model installed to do it**.

It carries no model names. It reads what is actually installed, every run.

## Why another one of these

Three skills already delegate to LM Studio. Two of them hardcode their
recommended models, which is exactly the guidance that rots. The best of them,
[`delegate-local`](https://github.com/IsmaelMartinez/delegate-local), routes by
capability tier and audits against hardware — and says plainly that its
verification is lightweight and its use is in-session.

This one claims the part none of them do: **the unattended path, where nobody
reads the output before it is used.** That is a different problem, and it needs
a different rule.

## The two modes

**Interactive** — you are present and will read the result. A check is
recommended, not required. Your eyes are the check.

**Unattended** — nobody is watching, and the result gets committed or acted on
before anyone reads it. A check is required, and work without one is refused.

The line is **who reads the result and when** — never how big or important the
task is. The reason is a failure that actually happened: a local model produced
a test file that could not parse, the runner dropped the whole script, and the
suite still printed `11/11 passed`. A person reading the output would have
caught it instantly. Nobody was reading.

## What it does that the others don't

- **Reads the live model metadata** (data, not instructions) — `type`, `arch`, `quantization`, `state`,
  real context lengths, advertised `capabilities` — from LM Studio's native
  API. It can never recommend a model you don't have, and it never carries a
  list that goes stale.
- **Checks loaded context against maximum.** A model loaded at a fraction of
  its ceiling silently truncates long input, and the OpenAI-compatible endpoint
  doesn't show it. On the machine this was built against, the gap was 12,288
  against 262,144.
- **Prefers schema-constrained generation** to validating afterwards — and
  states the limit: a schema constrains shape, never content.
- **Diagnoses failures by shape.** Empty output from budget exhaustion on a
  reasoning model is a different problem from looping on a long list, and the
  fixes point in opposite directions — one wants a bigger budget, the other
  gets worse with one.
- **Scores tasks before delegating**, and often says don't.
- **Checks the GPU before every load.** When LM Studio shares the card with
  ComfyUI, a read-only pre-flight reads who holds the GPU, what is resident,
  the real VRAM size (from the registry, never the WMI field that caps at
  4 GB), and LM Studio's own memory estimate. It never interrupts a running
  render, and at the end it unloads only what it loaded.

## Entry points

| Command | What it does |
|---|---|
| `lmstudiorunner audit` | Score installed models against the work classes; report gaps and the context check |
| `lmstudiorunner size <task>` | Score one task — class, fit, mode, the check it needs |
| `lmstudiorunner queue <task>` | Write a task card; refuse an unattended card with no check |
| `lmstudiorunner run` | Work the queue, verify each unit, report |
| `lmstudiorunner status` | What is queued, running, done, set aside |
| `lmstudiorunner refresh` | Re-verify the API surface notes and restamp them |

## Requirements

A running LM Studio server on this machine. The skill discovers the port rather
than assuming 1234, and tries `127.0.0.1` as well as `localhost` — on Windows
the name can resolve to IPv6 while the server binds IPv4.

Optional: the `lms` CLI (for `ps`, `unload` and the memory estimate) and
Python 3 to run `scripts/gpu_preflight.py`, the read-only GPU pre-flight.
Without them the skill uses the REST API and reports the estimate as
unmeasured. No packages. No cloud network at runtime. Where the surface has no
shell, it hands back the exact commands instead of running them.

## Running it inside LM Studio

LM Studio loads SKILL.md files directly and needs only `name` and
`description`. This skill uses no Claude Code-only frontmatter key, so it
works in both places unchanged.

One caution if you run it there: LM Studio's own local model would be both the
executor and the judge of its own output. Keep the check external — a test
command, a schema, a count — which is what the skill asks for anyway.

## What it is not

It doesn't pick cloud models or tiers (promptwright), write prompt text
(promptwright), or design the cadence, guardrails and kill switch around a
scheduled run (agentwright). It never commits, pushes, or sends — it prepares,
verifies, and reports.

## Honest economics

This does not save tokens. Writing a good task card costs more than doing a
small task yourself. What it converts is **idle hardware and idle hours** into
work, and it pays off on volume and on cards that get re-run — never on a
single small unit. The skill says so rather than selling the saving.
