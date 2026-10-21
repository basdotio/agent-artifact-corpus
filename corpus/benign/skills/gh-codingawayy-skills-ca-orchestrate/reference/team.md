---
covers: assembling a team of contrasting personas, and the pride gate that decides when the work is done
---

# The team and the pride gate

## Why

An author who reviews their own work in the same context reads the intent, not the result. A fresh reviewer with a different concern sees what the author cannot. The team supplies the different concerns; the pride gate supplies the fresh context.

## Assembling the team

Pick personas from the task, not from a fixed roster. Ask: _who would a strong real team put on this, and who would catch what the others miss?_

For each persona, write:

- **Role** — a short label ("Catalogue manager", "Release engineer").
- **Responsibility** — the one outcome this persona owns. No two personas own the same outcome.
- **Pride bar** — what this persona must see before signing the work. Concrete and checkable: "every changed query path runs once against the test DB", never "high quality". The bar is where the value is; the character name adds little.
- **Key or not** — mark a persona key only if their unhappiness means the work is wrong, unsafe, or unusable. Fewer key personas is better.

**Make them contrast.** Pair concerns that collide: the user vs. the maintainer, speed vs. safety, the domain expert vs. the cold reader, "make it complete" vs. "is this the least that works?". If two personas would always agree, merge them.

Scale the team to the task. A trivial task needs one or two personas named in a line. A large task may need a handful, with a lead per phase.

Give each execution item an owning persona where one fits, and put that persona's responsibility and pride bar into the item's prompt. The builder then aims at the bar from the start.

## The pride gate

Run it when the work looks finished.

1. **Fresh context.** Each key persona reviews in its own subagent that did not do the work (or a separate session, if the agent has no subagents). Give it the persona, its pride bar, the task, and where the result is — not the author's reasoning. For Trivial/Small tasks, run the gate inline and state each verdict in one line.
2. **Verdict with evidence.** Each reviewer returns:
   - `proud: yes | no`
   - the evidence — the files, tests, or behavior it actually checked
   - if `no`: the smallest changes that would earn a `yes`
   - out-of-scope wishes, listed apart; these become follow-ups, not blockers
3. **Fix and re-run** for the personas who said no, and for any persona whose area the fix touched.
4. **Pass** when every key persona says `yes` with evidence.

**"Proud" is a framing, not a feeling.** It asks "would you sign this?" instead of "any bugs?", which raises the bar. But the gate rests on evidence, not on the word:

- A `yes` without specific evidence counts as `no`. "No problems found" is not pride.
- A persona cannot block on work the task did not ask for.
- Do not lower a bar or swap in a friendlier reviewer to pass.
- When two key personas want opposite things, state the trade-off and ask the user.
- A reviewer told to be critical always finds something. Stop after 3 rounds without a pass, report the open objections, and ask the user. A persona that cannot be satisfied may signal a wrong plan, not a weak fix.
