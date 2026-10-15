---
name: layer-generation
description: Interviews and diagnoses the Generation layer, the fastest pace layer, where people and AI agents write code (tools, context files, prompts, local tests, the inner loop). Use when a change involves adopting or scaling coding agents or assistants, developer experience in the inner loop, shadow AI tools, or claims that engineers should be "faster", or when a pace-layers session identifies Generation as the goal or lever layer.
---

# Layer 1: Generation

**Natural clock:** seconds to hours. **Reform horizon:** weeks. **Changes by:** explore and discard. **Typical steward:** engineering leadership.

Generation is where code gets written, now by people and agents together. It is the fastest layer and the one with the least power. Its job, in pace-layer terms, is to be prolific, cheap, and mostly thrown away: to propose. It remembers almost nothing, and that is healthy as long as the layers below filter what it produces.

AI acts on this layer more directly than on any other. Output becomes abundant. The risk is rarely that this layer is too fast; the risk is that its output leaks into slower layers unfiltered, or that the organization tries to make experimentation here safe by making it slow.

Coding is typically 11–16% of developer time. Before accepting any goal that targets this layer, check the ceiling (Amdahl's law): what share of end-to-end lead time does writing code actually take here?

## If you arrived here directly

If no brief or goal exists yet, ask three questions first:

1. What is happening that made you want to change something here?
2. In one sentence, what do you want to be true that isn't now?
3. What is your role, and what can you decide on your own?

If the answers point to a slower layer (for example, the real complaint is review time), say so and suggest the right layer skill, but continue if the user wants to.

## Interview

Four passes. Ask 2–4 questions per turn. Skip anything the brief or your own inspection already answers. The short question set for quick mode is marked ★.

### Pass 1: What exists

- ★ Which coding assistants and agents are in use, by whom, and which are sanctioned versus used anyway?
- ★ What context do agents get: repository instruction files, conventions docs, skills, access to issue trackers or docs?
- How do people decide what to hand to an agent versus do themselves?
- What does the local feedback loop look like: time from edit to running tests?
- How big is a typical change now compared with a year ago?

### Pass 2: Topology

- ★ Who chooses tools: individuals, teams, or a central group? Who can block a tool?
- Where does generated work go next: a pull request, a direct commit, a review queue, a pairing session?
- Which teams or repositories are heavy users and which are not, and why?
- Which codebases do agents handle well, and which do they fail on? (Agent-legibility is a property of the code: tests, types, docs, clear module boundaries.)

### Pass 3: Under the hood

- ★ What happens to agent output that turns out wrong? How much is thrown away, and is that seen as waste or as normal?
- Who understands the code that agents wrote last month? If its author left, could anyone explain why it works?
- Where does a developer's day actually go? Ask for a rough split if no data exists.
- Are batches getting bigger? Larger changes are harder to review and riskier to release.
- What does the team believe AI has done for them, and what evidence is that belief based on? (Perceived speedups and measured speedups often diverge.)

### Pass 4: Forces

- **From the frontier:** How often do the tools change, and what breaks when they do?
- **From slower layers:** What policies, platform limits, data restrictions, or norms constrain which tools can be used and on what code?
- **What this layer pushes inward:** Which patterns invented here (prompts, harnesses, context files) should become shared standards? Is there any route for that to happen?

## Look before you ask

If you have read access to a repository, check these and ask the user to confirm what you find:

- Agent context files: `CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, `.github/copilot-instructions.md`, skills folders.
- Change size over time: `git log --since="6 months ago" --no-merges --shortstat --format="%ad" --date=short` and compare months.
- Test presence and speed: test directories, the test command, how long it takes.
- Signals of agent-legibility: type coverage, module structure, README and architecture docs.

Run read-only commands only.

## Reading the answers

| If you hear | It usually means | Ask or check next |
|---|---|---|
| "Adoption is high but lead time hasn't moved" | The bottleneck is downstream (shear S1) | Run `layer-verification` or `shear-check` S1 |
| "Changes are getting bigger" | Batch size is growing; review and release risk rise | Cap change size; check review time trend |
| "People use tools we haven't approved" | Governance or platform is too slow for this layer; stance is unclear | Shear S3; ask whether a clear AI stance exists |
| "Agents are useless on our core codebase" | A legibility problem in Domain or Platform, not an agent problem | Ask about tests, docs, boundaries in that codebase |
| "Nobody throws anything away" | The fast layer is being treated as if it must be reliable | Lower the cost of trying; raise the bar for promotion |
| "We measure adoption" or "lines accepted" | Proxy metrics that reward volume | Pair with stability and rework metrics (H10) |
| "Seniors love it, juniors struggle" or the reverse | A Nature-layer effect: skill formation and review load | Run `layer-nature` short set |

## Moves that work here

- **Explore and discard.** Make trying cheap: sandboxes, low-risk repositories, time-boxed experiments, explicit permission to throw work away.
- **Small batches.** Cap change size so downstream review stays possible.
- **Context as a shared asset.** Treat repository instruction files, skills, and conventions as code: reviewed, versioned, improved.
- **Evaluation on your own work.** Measure agent success on a set of real tasks from your codebase, not on vendor benchmarks.
- **A sifting route.** Give successful patterns a defined path into Platform as paved-road defaults (heuristic H3).

## Moves that fail here

- Making every experiment go through approval. It drives the work into shadow tools and slows learning to the pace of the slowest gate.
- Mandating adoption with a quota. It rewards volume and pushes unreviewable output downstream.
- Treating the agent as the problem when the codebase is illegible.

## Failure modes

- **Held too slow:** shadow AI, talent loss, and a learning gap against competitors.
- **Pushed without filters:** fast output hardening into slow layers (generated code in core systems with no theory holder), rising change failures, comprehension debt.
- **Forced to be reliable:** exploration dies; the layer stops proposing anything.

## Leading indicators

- Change size distribution (median and 90th percentile lines changed).
- Agent task success rate on an internal evaluation set.
- Share of work in small batches.
- Discard rate of agent attempts (a healthy fast layer discards a lot).
- Time from edit to first test feedback.

## Who belongs in the room

- **Steward:** the engineering leader accountable for how code is written here.
- **A heavy user and a skeptic:** two engineers with opposite experiences. Their disagreement is the evidence.
- **Shear S1 owner:** whoever owns the harness or verification capacity downstream. If no one does, that gap is a finding.
- **Theory holder:** for any codebase the change touches, someone who knows why it works.

## Write to the brief

Append under "3. Layer briefs" in `brief.md`, or print it:

```markdown
### Generation
- Exists: tools, sanctioned vs. shadow; context provided to agents; inner-loop speed
- Topology: who chooses and blocks tools; where output goes next; heavy vs. light users; legible vs. illegible codebases
- Under the hood: discard handling; theory holders; time split; batch size trend; belief vs. evidence
- Forces: frontier churn; slow-layer constraints; patterns ready to sift inward
- Diagnosis: (2–4 lines, citing the user's answers)
- Ceiling check: coding share of lead time ≈ ...% → max gain ≈ ...%
- Unknowns → who would know
- Candidate room seats: ...
```
