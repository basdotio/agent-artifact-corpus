# Trigger evals — revenantworks-localops-lmstudiorunner 1.1.0 **Re-anchored to v1.1.1, 2026-09-13 — provenance only, nothing executed here.** The 1.1.1 change lands the weekly review's doctrine edits (#0046, #0056); the `description` field is byte-identical, so the routing surface these judge did not move. **Re-anchored to v1.1.2, 2026-09-13 — provenance only, nothing executed here.** The 1.1.2 change (observations #0067, #0068) is body-only — a discovery-time RAM check and a new Failure shape; the `description` field is byte-identical, so the routing surface these judge did not move. **Re-anchored to v1.1.3, 2026-09-13 — provenance only, nothing executed here.** The 1.1.3 change (observation #0069) is body-only — task-cards.md rule 7 now requires pasting a named population's content, not just listing it; the `description` field is byte-identical, so the routing surface these judge did not move. **Re-anchored to v1.1.4, 2026-09-14 — provenance only, nothing executed here.** The 1.1.4 change (observations #0070, #0074, #0075) is body-only — the Discover-step existing-runner check and the `queue`/`run` CI-discovery and zero-baseline checks; the `description` field is byte-identical, so the routing surface these judge did not move. **Re-anchored to v1.1.5, 2026-09-14 — provenance only, nothing executed here.** The 1.1.5 change closes a local-path leak in `CHANGELOG.md`; the `description` field is byte-identical, so the routing surface these judge did not move.

Provenance: authored against SKILL.md at the 1.0.0 build (2026-09-09). **Re-anchored to v1.0.1, 2026-09-10 — provenance only, nothing executed here:** the 1.0.1 patch closed seven estate-audit findings (loaded-context field handling, eval preconditions, the check-command gate, a results ledger, the discovery probe list, a Load budget section, and the `capabilities`/`publisher`/`compatibility_type` field list) — all body and reference changes. The `description` is byte-identical, so the routing surface these rows judge did not move; no query, expectation, or count touched. **Re-anchored to v1.1.0, 2026-09-10 — provenance only, nothing executed here:** step 4 gained a reasoning-cost probe sentence and `references/api-surface.md` gained the `enable_thinking` caveat and the budget-sizing probe section (estate-audit unit W9). The `description` is byte-identical, so the routing surface these rows judge did not move; no query, expectation, or count touched. **Re-anchored to v1.1.6, 2026-09-22:** provenance only, nothing executed here: the 2026-09-20 task-observer batch was installed (doctrine and references only). The `description` is byte-identical, so no query, expected value, or count moved. **Re-anchored to v1.2.0, 2026-09-28:** U13 parity audit: GPU seam, pre-flight, v1 API, body slim. **Re-anchored to v1.0.0, 2026-10-01:** provenance only, nothing executed here: `gpu-seam.md` names comfyrunner where it said the planned media runner (D5); the description and body are unchanged.
Judged from **name + description only**, as a cold router would.

Balance: 20 should-fire · 12 should-not · 7 boundary pairs (14 more queries) — 46 queries in all. Unit: one query = one numbered row, or one side of a boundary pair.

**Extended at v1.2.0, 2026-09-28 (U13 P2-6):** the description gained "when LM Studio and an image tool share the GPU" and lost "so it never names a model that may not be installed" (now "never a remembered name"). Rows #31, #32 and pair B7 cover the new clause; the authoring unit re-read every row against the new description on 2026-09-28 (name + description only) and found none moved; #30 is the one row the new GPU word could pull, and B7 records that split. This was not a cold judge — the reader wrote the clause — so a cold re-judge of the 46 queries was owed. **Cold re-judge done 2026-10-01 (unit J1):** 32 rows judged, one tie (M8, row #31: the router named comfyrunner and this skill). **FX4, 2026-10-01:** the description gained "or to free LM Studio's hold before a render" and comfyrunner's lost "when ComfyUI and LM Studio share one GPU" and "unloads the local LLM" (J1 E9), so #31 now lands here alone; the closing surface clause now names LM Studio only (owner rule). Re-judged by hand from name + description: no other row moves.

**Re-anchored to the K6b description cut, 2026-10-08 (commit b338715):** every row re-read against the cut text; row wording only, no row added, removed or flipped; a row whose routing words left the description says so in its reason. A reader re-read, not a cold judge: the `tools/blind_queries.py` cold re-judge is still owed.

## Should fire

| # | Request | Why it lands here |
|---|---|---|
| 1 | "offload this to my local model" | `offload` + local model, the core claim |
| 2 | "can Gemma do this instead of you?" | Delegation to a named local model |
| 3 | "run this on LM Studio" | Names the server the skill drives |
| 4 | "hand this batch to the local LLM overnight" | Batch + unattended, both claimed |
| 5 | "which of my installed models should do this?" | Model-fit question, claimed by name |
| 6 | "is there a better model installed for this?" | The switch question |
| 7 | "should I switch models for this job?" | Same, phrased as the user would |
| 8 | "queue this up for the local model tonight" | Queue + unattended |
| 9 | "is this task worth delegating?" | `size a task before delegating` |
| 10 | "score this before I hand it over" | The size entry |
| 11 | "my local model returned nothing" | Returns nothing — a named failure symptom |
| 12 | "the local model keeps repeating itself" | Repetition — named symptom |
| 13 | "it drifts after about fifty items" | Drift on a long list — named symptom |
| 14 | "lmstudiorunner audit" | Named subcommand |
| 15 | "lmstudiorunner status" | Named subcommand |
| 16 | "set up an unattended run that keeps only what passes" | The gate claim |
| 17 | "delegate this to an on-device model" | `on-device`, a phrasing users reach for |
| 18 | "run this offline, nothing to the cloud" | `offline` + the privacy motive |
| 31 | "free the GPU from LM Studio before I render in ComfyUI" | "or to free its hold" (J1 M8, E9); comfyrunner only checks the card before its own render |
| 32 | "is my local model still holding VRAM?" | Same clause, asked as an occupancy question |

## Should not fire

| # | Request | Where it belongs | Why not here |
|---|---|---|---|
| 19 | "which Claude model should I use?" | promptwright | Cloud tier pick, ceded by name |
| 20 | "should this run on Opus or Sonnet?" | promptwright | Same |
| 21 | "write the prompt for this agent" | promptwright | Prompt text, ceded by name |
| 22 | "improve this system prompt" | promptwright | Prompt quality |
| 23 | "add a kill switch to my scheduled job" | agentwright | Guardrails around a scheduled run, ceded |
| 24 | "how often should this cron run?" | agentwright | A schedule, ceded ("a schedule's guardrails"); cadence is no longer named |
| 25 | "build me a skill for X" | skillwright | Skill package |
| 26 | "audit this skill" | skillwright | Skill package |
| 27 | "make my README read better" | commscribe | Docs prose (owner Q20: not skill-package files) |
| 28 | "write the release announcement" | commscribe | A message to an audience |
| 29 | "compare Llama and Mistral as products" | researchscribe | Sourced product comparison, not a run-target pick |
| 30 | "my GPU is running hot" | none | Hardware support, not delegation |

## Boundary pairs

Each pair shares vocabulary and splits on the deciding key.

| # | A (fires) | B (does not) | The key |
|---|---|---|---|
| B1 | "which installed model fits this job?" | "which Claude model fits this job?" | Local vs cloud. The description claims installed/local and cedes cloud tiers to promptwright by name |
| B2 | "the local model returns empty output" | "Claude returned an empty response" | Whose model. Only local failure shapes are claimed |
| B3 | "queue this for an unattended local run" | "schedule this job to run nightly with retries" | Delegating work vs designing the schedule around it. Cadence and retries are ceded to agentwright |
| B4 | "score this task before delegating" | "score this prompt" | The object. A task's fit for a local model here; prompt quality is promptwright's |
| B5 | "hand this to the local model" | "hand this to a subagent" | Local model vs in-session agent fan-out. Nothing here claims subagents |
| B6 | "is a better model installed for this?" | "is a better model available to buy?" | Installed vs market. The skill reads what is installed; a product comparison is researchscribe's |
| B7 | "LM Studio and ComfyUI both want the GPU — which goes first?" | "my GPU is running hot" | Sharing the card between two GPU consumers vs hardware health. Only sharing is claimed (#30 stays none) |

## Known soft edges

- **#29 vs B6-A** — "compare Llama and Mistral" against "is a better model
  installed". Both mention models by capability. The split is whether anything
  is installed and in play; a cold router seeing only vocabulary could go
  either way, and researchscribe's description claims comparisons generally. This
  is the pair most likely to misroute and is recorded rather than claimed
  closed.
- **#25 vs the whole skill** — a request to *build a skill that delegates to a
  local model* is skillwright's build, not this skill's job. The description
  does not claim skill-building, but both sets of vocabulary appear in the same
  sentence when a user asks for it.
