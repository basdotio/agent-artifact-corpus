# Synthesizer brief

The orchestrator (`../SKILL.md` §5.5) expands this template and passes it verbatim as the `prompt` of a single `Agent` call (`subagent_type: general-purpose`).

## Building `{{LENS_OUTPUTS}}`

Concatenate each lens's verbatim output as plain text (no template engine — the synthesizer LLM cannot expand Handlebars). For each lens in roster order, append:

```
---
### Lens: <lens-name>
<lens's verbatim output>
---
```

A lens that failed renders as `<lens-name>: [FAILED — no output]`. The final concatenated string replaces `{{LENS_OUTPUTS}}`.

## Template

```
You are synthesizing an idea-generation panel. You have no prior conversation context. {{N_LENSES}} lenses each attacked the same topic from a different frame; your job is to merge their ideas into one prioritized shortlist — NOT to generate new ideas of your own and NOT to discard the sharp edges by averaging.

## TOPIC
{{TOPIC}}

## CONTEXT
{{CONTEXT_BLOCK}}
# Verbatim --context material the lenses received. Strip this whole block when --context was absent.

## LENS OUTPUTS (verbatim)
{{LENS_OUTPUTS}}

## MERGE INSTRUCTIONS

One lens may be `critical-thinking`, which returns assumptions/questions instead of ideas. Route its output to the "Assumptions & Open Questions" section ONLY — never rank its items as ideas. If no `critical-thinking` lens is present, omit that section entirely.

Produce a single markdown report with EXACTLY this structure and these headings:

# Idea Panel: {{TOPIC}}

## Executive Summary
2–4 sentences: how many lenses ran, the shape of the idea space they surfaced, and the single most promising direction.

## Ranked Idea Shortlist
The strongest 5–8 ideas across all lenses, ranked. Deduplicate: when two lenses produced the same idea, merge them into one entry and note both lenses (convergence = stronger signal, rank it higher). For each: **Title** — pitch — which lens(es) produced it — one-line why-it-ranks-here (novelty × plausibility) — biggest risk. Rank by novelty × plausibility: a safe obvious idea and a brilliant impossible idea both rank low; the top of the list is novel AND plausibly reachable.

## Wildcards
The 2–4 highest-novelty / highest-risk ideas (including the lenses' own wildcard entries) worth keeping on the table precisely because they're non-obvious. One line each; be explicit that these are high-variance bets.

## Cross-Lens Convergence
Ideas or themes that ≥2 lenses arrived at independently, and — separately — any productive *disagreement* between lenses (e.g. first-principles wants to remove a constraint that effectuation treats as a given asset). This cross-frame view is the unique value of a panel over a single pass; surface it explicitly.

## Assumptions & Open Questions
Only if a `critical-thinking` lens ran: its assumptions/questions, integrated here. Omit this section entirely otherwise.

## Recommended Next Idea to Develop
Name the single idea most worth taking forward and one sentence on why. Then point to the next step: sharpen it with `idea-autopsy:iterate-to-v2`, formalize with `product-management:write-spec` or `to-prd`, then pressure-test with `idea-autopsy:evaluate-proposal-harsh`.

Do not include preamble. Start with `# Idea Panel: ...`.
```
