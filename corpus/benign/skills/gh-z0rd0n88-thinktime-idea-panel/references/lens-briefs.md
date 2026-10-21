# Lens briefs — roster, framing, and template

This reference holds the material the orchestrator (`../SKILL.md`) expands per lens. It is not loaded unless the skill is running.

## Default roster

Four generative lenses, ordered. Each `{{LENS_INSTRUCTION}}` is the role framing injected into that lens's brief. The framing is **self-contained** — the agent should invoke the named `thinking-skills:thinking-<name>` skill via the Skill tool if it is available, but the framing here is enough to apply the model without it.

| Lens (`{{LENS_NAME}}`) | `{{LENS_INSTRUCTION}}` framing |
|---|---|
| `thinking-first-principles` | Strip the topic down to its irreducible truths. List the assumptions everyone in this space treats as fixed ("it must be regulated this way," "it's too expensive," "it's always done with X") and mark which are actual constraints vs. inherited convention. Rebuild candidate ideas from the base truths upward, ignoring the inherited conventions. Favor ideas that only become obvious once a false constraint is dropped. |
| `thinking-jobs-to-be-done` | Reframe from "what to build" to "what progress is someone trying to make." Write the core job as _When [situation], I want [motivation], so I can [outcome]_. Map who currently "hires" a workaround for this job (including "do nothing" and non-obvious substitutes). Generate ideas that do the job better/cheaper/with less anxiety than today's workarounds. Anchor every idea to a specific job — reject feature ideas with no job behind them. |
| `thinking-inversion` | Ask: "how would I guarantee this space stays broken / this product fails / this need goes unmet?" Enumerate 8+ concrete failure and neglect modes. Then invert each into an opportunity: the idea that exists precisely because that failure mode is common and unaddressed. Favor ideas that attack a failure everyone tolerates. |
| `thinking-effectuation` | Start from means, not goals. Given who a small founding team plausibly is / knows / already has (skills, networks, data, existing assets in this space), what can be built with an "affordable loss" first step and no external permission? Generate ideas reachable from available means, that improve as committed partners and lucky surprises are folded in — not ideas that require a big upfront bet or a market that must first be conjured. |

## Alternate lenses (via `--lenses`)

Any `thinking-<name>` slug works. Two classes:

**Generative** — produce ideas in the standard output contract:
- `thinking-triz` — for a genuine two-way contradiction ("must be X AND not-X"); resolve by separating the conflicting states in time/space/condition/scale instead of compromising.
- `thinking-second-order` — "and then what?" across immediate / near-term / at-scale horizons; surface ideas that ride downstream and incentive effects others miss.
- `thinking-via-negativa` — generate ideas by *subtraction*: what to remove from the current way of doing this that would create disproportionate value.
- `thinking-opportunity-cost` — frame each idea against the best foregone alternative and the cost of doing nothing.
- `thinking-lindy-effect` — favor durable, time-tested mechanics over faddish ones where longevity matters.

## Specialist-agent lenses (via `--lenses`)

Named agents (not `thinking-*` skills) dispatched via their own `subagent_type`. They add domain grounding the mental-model lenses structurally lack — the thinking-skills reason from first principles but are blind to the *actual* market, competitors, and positioning. They use the standard **generative** output contract. Their `{{LENS_INSTRUCTION}}`:

| Lens (agent) | `{{LENS_INSTRUCTION}}` framing |
|---|---|
| `market-researcher` | Ground the topic in the real market: name the actual incumbents/substitutes, size the opportunity, and map the whitespace they leave. Generate ideas that target an unserved segment or an underserved job the current market misses — every idea must name who it displaces and why now. |
| `product-strategist` | Frame ideas as wedges: for each, state the positioning, the beachhead segment, the go-to-market motion, and the moat/compounding advantage. Prefer ideas with a defensible wedge and a path to expand from it over feature ideas with no strategic sequencing. |

A specialist agent may come from your live agents directory (`~/.claude/agents/` or `.claude/agents/`) or from a parked roster (`.claude/agents-parked/` or `~/.claude/agents-parked/` — parked agents never register, so they don't bloat session context). A parked agent dispatches via the paste method (`general-purpose` with the agent's `.md` body pasted above the lens brief, per SKILL.md §5.3). A name that resolves nowhere hard-fails validation (§5.1) with an error naming the agent and the expected `~/.claude/agents-parked/<name>.md` path.

**Carve-out (different output shape) — `critical-thinking`:** unlike every other lens, `critical-thinking` does NOT generate ideas. It interrogates the topic itself: the unstated assumptions baked into how the problem is framed, the missing context, and the questions that must be answered before *any* idea in this space is worth pursuing. It uses the carve-out contract below and the synthesizer routes its output to a dedicated "Assumptions & Open Questions" section — never into the idea ranking. Opt in with `--lenses ...,critical-thinking`; it is intentionally NOT in the default four so the default panel stays purely generative. Pairs well as a 5th lens when a topic is fuzzy or contested (e.g. `--lenses thinking-first-principles,thinking-jobs-to-be-done,thinking-inversion,thinking-effectuation,critical-thinking`).

Other non-generative lenses (`thinking-pre-mortem`, `thinking-red-team`, `thinking-fermi-estimation`, `thinking-bayesian`, etc.) belong in the *evaluation* stage, not the panel — route those through `idea-autopsy:stress-test-idea` after ideas exist.

## Shared output contract (`{{OUTPUT_CONTRACT}}`) — generative lenses

Every generative lens returns the SAME shape so the synthesizer can merge them:

```
### Frame
2–3 sentences: how you (this lens) reframed the topic before generating.

### Ideas
3–6 candidate ideas. Each idea:
- **Title** — a short, memorable name.
- **Pitch** — one sentence: what it is and for whom.
- **Why this lens surfaced it** — the specific move (dropped constraint / job / inverted failure / available means) that produced it. An idea any generic brainstorm would also produce is weak signal — prefer ideas that only this frame reveals.
- **Biggest risk** — the one thing most likely to sink it.

### Wildcard
One deliberately out-of-the-box idea from this frame — higher novelty, higher risk, lower plausibility. Label it clearly.
```

Do not include preamble or sign-off. Start with `### Frame`.

## Carve-out output contract (`{{OUTPUT_CONTRACT}}`) — `critical-thinking` only

When the lens is `critical-thinking`, its brief uses THIS contract instead of the generative one above:

```
### Frame
2–3 sentences: what about how this topic is framed most needs interrogating before ideas are generated.

### Assumptions & Open Questions
A flat list of 5–10 items. Each item:
- **Item** — the unstated assumption, missing context, or unanswered question.
- **Why it matters** — how a wrong answer here would waste every idea downstream.
- **What to verify or decide** — the concrete next step to resolve it.

Do NOT propose product ideas. Your value is surfacing what the idea-generating lenses are taking for granted.
```

Do not include preamble or sign-off. Start with `### Frame`.

## Lens brief template

Expand `{{ ... }}` at invocation and pass verbatim as the `Agent` call's `prompt`. The orchestrator selects the generative vs. carve-out `{{OUTPUT_CONTRACT}}` based on whether `{{LENS_NAME}}` is `critical-thinking`. Strip any `#`-annotation line (single `#` explaining a placeholder) before dispatch; keep real `##` headings.

```
You are applying a single lens to a topic as part of an idea-generation panel. You have no prior conversation context. Be concrete and specific; vague category-level output ("an app for X") is a failure.

## LENS
{{LENS_NAME}}
# If a `thinking-skills:thinking-<name>` skill matching this lens is available, invoke it via the Skill tool to guide your reasoning, then apply it to the topic below. If not, apply the framing in YOUR FRAME directly.

## TOPIC
{{TOPIC}}

## CONTEXT
{{CONTEXT_BLOCK}}
# Verbatim contents of --context (background material). When --context is
# absent, strip this entire `## CONTEXT` block (heading + body) before dispatch.

## YOUR FRAME
{{LENS_INSTRUCTION}}

## RETURN FORMAT
{{OUTPUT_CONTRACT}}
```
