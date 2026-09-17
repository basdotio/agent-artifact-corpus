---
name: loop
description: Use when user has a hypothesis and a repo and wants to run experiments. Triggered by "start experiments", "run the loop", "test this hypothesis".
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to run a specific experiment or annotate a result, skip this skill. Execute the task and return structured results immediately.
</SUBAGENT-STOP>

<HARD-GATE>
Design ALL conditions upfront. Rank them. Run ONE at a time. Never propose the next experiment before logging what you learned from the last one.
</HARD-GATE>

# Loop Skill

You are running a scientific iteration loop. Each experiment is a question. The answer shapes the next question. The ledger accumulates evidence.

## Phase 1 — Design all conditions, rank by information value

Ask:
> "What's the core hypothesis we're testing? One sentence."

Then list ALL planned conditions — you already know them from the discovery phase. Show them ranked by **what teaches you the most first**:

```
HYPOTHESIS: [one sentence]
FALSIFICATION: [what result kills it]

CONDITIONS (ranked by information value):
  1. [highest priority] — tests [what], teaches [what] if it fails/passes
  2. [second] — only run this if condition 1 passes/fails in [way]
  3. [third] — ...
  N. [memory transplant / killer test] — run last, most definitive

RANKING LOGIC: [one sentence explaining why this order]
```

Ask:
> "Does this ranking make sense? Any condition you want to move up or down?"

Wait. Adjust if needed. Then create TodoWrite tasks — one per condition, in ranked order.

Write `hypothesis.md`:
```markdown
# Hypothesis
[one sentence]

# Prediction
[what you expect to observe if hypothesis is correct]

# Falsification
[what result proves it wrong]

# Conditions (ranked)
1. [name]: [what changes] — Priority: [why first]
2. [name]: [what changes] — Priority: [why second]
...
```

## Phase 2 — Run one experiment at a time

For each condition, in ranked order:

**BEFORE running — state the question:**
> "Condition [N]: [name]. The question this answers: [one sentence]. Expected result if hypothesis holds: [specific]. Expected result if hypothesis fails: [specific]. Running now."

**AFTER running — ask for the insight:**
> "Result: [metric]. Expected? What does this tell you — one sentence."

Wait for their answer. Then add your own causal read:
> "My read: [mechanistic explanation]. This [confirms / challenges / is neutral toward] the hypothesis because [why]."

**Log the insight immediately** — append to `insights.md`:
```markdown
## Insight [N] — [date]
Condition: [name]
Result: [metric]
Researcher interpretation: [their words]
Causal annotation: [mechanistic explanation]
Hypothesis status: [strengthened / weakened / unchanged / killed]
Next question this raises: [what you now want to know]
```

Mark the TodoWrite task complete. Then ask:
> "Given this result, does the ranking still make sense? Or do you want to reprioritize?"

**Only then propose the next condition.**

## Phase 3 — After each insight, update the ledger

After every experiment, run:
```bash
# Append to insights ledger
echo "---" >> .research-loop/sessions/<slug>/insights.md
```

Then update `knowledge_graph.md` — change the condition status from `pending` to `done: [result]`.

## Phase 4 — Kill or continue decision

After each run:
```
Does the result change what we think?
├── CONFIRMS hypothesis → continue ranked list
├── WEAKENS hypothesis → reprioritize — move falsification test up
├── KILLS hypothesis → stop, log finding, load execution skill
└── SURPRISING (neither confirms nor kills) → this is the most interesting result
    → pause, ask "what does this mean?", update hypothesis if needed
```

Surprising results are never failures. They are the most valuable signal.

## Phase 5 — When all conditions are run

Before looking at the full picture, ask:
> "Write the conclusion in one sentence — what does the evidence say about the hypothesis?"

Then show the full ledger. Compare their conclusion to the original prediction. If they differ — that gap is often the real finding.

Load `execution` skill to formalize the decision: continue, pivot, or write the paper.
