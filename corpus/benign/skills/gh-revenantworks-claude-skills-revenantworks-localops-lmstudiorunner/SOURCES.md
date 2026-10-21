# Sources — revenantworks-localops-lmstudiorunner

> **Last verified: 2026-09-26** — the parity register below (calendar surface,
> 90 days, declared in `volatile.json`). Primary sources verified
> 2026-09-09 unless noted.

## Primary — the API this skill drives

- **LM Studio developer documentation** — `lmstudio.ai/docs`: API changelog
  (TTL from 0.3.9, speculative decoding from 0.3.10, native `/api/v0` and the
  later `/api/v1`), structured response with JSON schema, model parameters.
- **A live `GET /api/v0/models` response**, 2026-09-09. The field table in
  `references/api-surface.md` is transcribed from an actual response, not from
  documentation — the docs do not enumerate every field the endpoint returns.
- **Three live chat-completion probes against `gemma-4-12b-it` (Q4_K_M,
  `tool_use`, loaded at full 262144 context), 2026-09-10** — the basis for
  `references/api-surface.md`'s `enable_thinking` caveat and the "Sizing the
  budget" section. `chat_template_kwargs.enable_thinking: false` did not
  suppress reasoning (~168-200 tokens on all three requests, `max_tokens` 200
  and 600). `response_format.json_schema` (`strict: true`) did not add
  reasoning cost by itself — the difference between a 200-token budget failing
  and a 600-token budget succeeding on the same schema was `max_tokens`, not
  the schema. Cross-checked against `lmstudio.ai/docs/app/api/structured-output`
  and `lmstudio.ai/docs/app/api/endpoints/openai`, fetched 2026-09-10: neither
  page documents `chat_template_kwargs`, `reasoning_content`, `reasoning_effort`,
  `enable_thinking`, or `reasoning_tokens` — the switch is a llama.cpp/vLLM
  chat-template convention LM Studio passes through, not a first-party
  documented field, treated here as best-effort per model, never guaranteed.

## Parity register *(dated 2026-09-26; re-check every 90 days)*

Incumbents doing the same core job, each fetched on the date shown. Page text
was read as data.

| Code | Incumbent | Kind | Fetched | What it does |
|---|---|---|---|---|
| DL | `github.com/IsmaelMartinez/delegate-local` | skill, MIT | 2026-09-26 | Delegates summarisation, log triage and bulk text; capability tiers resolved against installed models through preference lists; Ollama, MLX and Docker backends (not LM Studio); a hit/miss feedback ledger; `llmfit` hardware audit. In-session only |
| HL | `github.com/houtini-ai/houtini-lm` (v3.3.3, 2026-09-24; renamed from `houtini-ai/lm`) | MCP server, Apache-2.0 | 2026-09-26 | `chat`, `code_task`, `code_task_files` (the server reads files), `discover`, `list_models`, `stats`; task scoring with family profiles; strips think blocks; truncation flags. No load or unload |
| LM | `github.com/seajhawk/lmstudio-mcp`, plus the `lms` CLI | MCP server, MIT | 2026-09-26 | List, details, load with TTL, unload, draft-model config. Lifecycle only: no routing, no verification |

| # | Core-job capability | DL | HL | LM | This skill |
|---|---|---|---|---|---|
| 1 | Live discovery of server and installed models | met | met | met | met (v1 with v0 fallback, since 1.2.0) |
| 2 | Route by capability, never by name | met | met | out of scope | beaten — no names anywhere |
| 3 | "Should I delegate this at all" scoring | partial | partial | out of scope | beaten — four-question pass, work classes, claim types |
| 4 | Reasoning budget and think handling | not stated | met | out of scope | beaten on diagnosis |
| 5 | Output verification | met | partial | out of scope | beaten — per-card check, required unattended, confirmation rate per claim type |
| 6 | Unattended queue that keeps only checked work | missing | missing | missing | beaten (sole holder) |
| 7 | Model lifecycle: load, unload, TTL | not stated | missing | met | met since 1.2.0 — unload by instance id at hand-back |
| 8 | Hardware and memory fit before load | met | missing | missing | met since 1.2.0 — the GPU pre-flight |
| 9 | Offload accounting | partial | met | out of scope | met — local calls, local tokens and Claude tokens avoided in every report, plus the class ledger (SKILL step 7; work-classes.md, "Report flags and the class ledger") |
| 10 | Keep source text out of the orchestrator's context | missing | met | out of scope | met — a script builds the request from the file (api-surface.md, "File input") |
| 11 | GPU co-tenancy with another GPU consumer | missing | missing | missing | beaten since 1.2.0 — a pack-wide lease; artokun/comfyui-mcp's panel also frees LM Studio VRAM during a render (re-scan 2026-10-01), so not sole holder |
| 12 | Portable across surfaces, with a no-shell fallback | Claude Code | MCP clients | MCP clients | beaten |

**Margin** (capabilities no incumbent has, as of 2026-09-26), each mapped to a
claim case in `evals/SUITE.md`, section K:

1. An unattended queue with a required, owner-authored check and set-aside with evidence (K1).
2. Pre-delegation fit scoring with claim-type doctrine and a confirmation rate per claim type (K2).
3. The loaded-versus-maximum context divergence, reported unprompted (K3).
4. Named failure-shape diagnostics, including reasoning share on a passing call (K4).
5. The GPU hand-off seam through a pack-wide lease with every other GPU consumer (K5). Narrowed 2026-10-01: artokun/comfyui-mcp unloads LM Studio during its own renders, so the margin is the pack-wide lease (the pack-shared `references/gpu-seam.md` and `scripts/gpu_preflight.py`), not a sole-holder claim.

**Retire condition.** Retire a single margin when an incumbent matches it with
a case its own evals prove. Retire the whole skill when one incumbent ships
both an unattended queue with a required, owner-authored check (margin 1) and a
GPU pre-flight that shares the card with a second consumer (margin 5). Re-check
at the next refresh.

Also reviewed at build (2026-09-09), not in the register because neither runs
a verified queue: `TerminalSkills/skills` → `lm-studio-subagents` and
OpenClaw's `lm-studio-subagents` — both name specific models, the staleness
this skill avoids.

Re-scanned 2026-10-01 (unit PR). Also seen: rysk-tanaka/skills lms-review and lms-rescue (2026-09-29), delegation only.

## GPU seam sources

- ComfyUI server routes (`docs.comfy.org`, and `server.py` on Comfy-Org/ComfyUI
  master), fetched 2026-09-26: `GET /system_stats` (`vram_total`, `vram_free`),
  `GET /queue`, `POST /free` (`unload_models`, `free_memory`), `POST /interrupt`.
- Task-observer observation #0064 (update 2026-09-23): WMI `AdapterRAM` reports
  4 GB on a 16 GB card; the registry `HardwareInformation.qwMemorySize` is right.
  Re-confirmed live 2026-09-28 by the pre-flight script.
- `lms load --estimate-only`, LM Studio CLI docs fetched 2026-09-26, run live
  2026-09-28.

## Ecosystem context

- **LM Studio** runs SKILL.md skills natively and reads Claude
  Code skill directories without conversion, which is why this skill
  depends on no Claude Code-only frontmatter key.
- **The Agent Skills open standard** (`agentskills.io`) — the SKILL.md format
  this file conforms to.

## Measured, not sourced

The failure numbers in `references/work-classes.md` and
`references/task-cards.md` are observations from real runs against a local
model on one machine, recorded with their conditions. They are evidence for the
shape of the failure, not published benchmarks, and they are labelled as
measurements in the text so nobody mistakes them for vendor claims.
