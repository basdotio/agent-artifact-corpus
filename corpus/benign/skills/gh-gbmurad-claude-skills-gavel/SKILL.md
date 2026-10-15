---
name: gavel
description: Puts a decision on trial. A defense and a prosecution argue it, 3 to 8 specialist jurors vote alone without seeing each other, and a judge who commits to his own view first rules on the evidence. Setup picks the opposition's harshness, the jury, and each role's model. Use when the user says use gavel, gavel this, put it on trial, should we do X.
argument-hint: "<the decision> [--last] [--quick] [--deliberate] [--research]"
allowed-tools: Read, Write, Agent, AskUserQuestion, Bash(python3 *gavel/scripts/gavel.py *)
metadata:
  status: active
  version: "1.1.0"
  owner: george
  band: index
---

# gavel: put a decision on trial, get a ruling you can act on

**Done =** `ruling.md` exists in the case folder, `gavel.py close` accepted it, and the user has the verdict, the
dissent, and the one fact that would flip it.

You are the **clerk**. You run the setup, file the case, call each role as a fresh subagent on the model the
setup names, run the script between stages, and report the ruling. You never argue, vote, judge, or edit
anything a role wrote. Role briefs: `references/roles.md`. Juror bench: `references/bench.md`. Why each rule
exists: `references/research.md`. `<skill>` below is this skill's folder (printed when the skill loads).

## Procedure
1. **Is this a trial?** If the question has a checkable answer (a fact, a bug, a sum, a test that would settle
   it), say so and answer it directly; a vote does as well as a debate there. Otherwise tell the user the cost
   once (2 judge runs, 2 to 4 speeches, one run per juror) and go to setup.
2. **Setup.** If the user says "use my last settings" or passes `--last`, run `gavel.py settings`, show the line,
   and skip to step 3 with `--last`. Otherwise:
   - **The question.** If they have not given it, ask them to type it in one sentence.
   - **First menu** (one AskUserQuestion call, four questions):
     - "How hard should the prosecution push?" Fair (concedes what is true) · Tough (Recommended) · Ruthless
       (attacks every claim, concedes nothing unproven)
     - "Who sits on the jury?" The judge picks 5 for this case (Recommended) · I'll choose the seats · Quick
       trial: 3 seats, no rebuttals
     - "Model for the judge?" Opus (Recommended) · Fable · Sonnet · Same as this chat
     - "Default model for the jury?" Sonnet (Recommended) · Haiku (cheapest) · Opus · Fable
   - **Second menu** (one call): "Model for the defense?" and "Model for the prosecution?" (Sonnet
     (Recommended) · Opus · Fable · Haiku). If they chose to pick seats, add two multiSelect questions from the
     bench: "Build and money seats" (engineer, finance, operations, security and privacy) and "People and market
     seats" (designer, customer, competitor, legal and compliance). Tell them they can type anyone under Other,
     such as "a retired airline pilot", and give one seat its own model as "designer: opus". The premortem
     seat always sits. 3 to 8 seats in all.
   - "Same as this chat" is `inherit`: spawn that role without a model.
3. **File the case.** Run `python3 <skill>/scripts/gavel.py new "<question>"` with the choices as flags:
   `--opposition`, `--judge`, `--defense`, `--prosecution`, `--jury`, `--seats "a, b: opus"` or `--quick`, plus
   `--deliberate`, `--research`, `--last` when asked. It prints the case folder and the plan; show the plan line.
   A FIX line means a choice was invalid: ask again. Fill `case.md`: facts with sources, constraints, what has
   been tried, stakes. Ask at most two questions, only for a fact the case turns on. Never invent facts.
4. **Pretrial.** Spawn the judge with brief 1 on the judge's model. `{N}` is the setup's `jurors`. Run
   `gavel.py pretrial <case>`; it prints each seat's ballot file and model. On a FIX line, send it to the judge
   once and rerun.
5. **Openings.** In one message, spawn the defense (brief 2) and the prosecution (brief 3, with the level
   paragraph for the setup's `opposition` in place of `{LEVEL}`) in parallel, each on its model.
6. **Rebuttals** (not in a quick trial). In one message, spawn both rebuttals (brief 4) in parallel.
7. **Record.** `gavel.py record <case>`. A speech over its word limit goes back to its side once.
8. **Jury.** In one message, spawn every seat with brief 5, in parallel, each on the model `gavel.py pretrial`
   printed for it. Add the premortem paragraph only to the premortem seat. Then `gavel.py tally <case>`; send
   any FIX line to that juror once.
9. **Deliberation** (only with `--deliberate`, or offered when the tally says `split` and the stakes are high).
   Spawn every juror again with brief 6, then rerun the tally. Round 2 counts only if the jurors who moved name
   a new point; otherwise the script falls back to the blind vote.
10. **Ruling.** Spawn a fresh judge with brief 7 on the judge's model. Run `gavel.py close <case>`; a FIX line
    goes back to the judge once.
11. **Report** in at most eight lines: the VERDICT line, the ruling in plain words, the vote (counts, median,
    spread), the strongest dissent, what would flip it, and the path to `ruling.md`. Quote; never soften.

## Guardrails
- Each role reads only the files its brief names and writes only its own file. Roles return one line.
- The sealed prior is read by the judge alone. The clerk never paraphrases a speech to another role.
- Never more than two rounds of argument. Never show jurors each other's ballots before their blind vote.
- The prosecution's level changes how hard it pushes, never its duty to name a rival and support every claim.
- The ruling stands as written. To challenge it, file a new case with the new facts.
- Case files can hold private facts. Keep `.gavel/` out of version control.
- Jurors on one model share blind spots. The tally says how varied the jury was; repeat that when it matters.

## Related
`references/roles.md` · `references/bench.md` · `references/research.md` · `scripts/gavel.py` ·
`scripts/test_gavel.py`
