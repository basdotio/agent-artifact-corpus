# Jev inside agents, games and control loops

How to put Jev in a loop that acts: a browser agent, a coding-agent guard, a game
player, a robot or a drone. Read `question-design.md` ("Bounded action selector") first;
this file covers what the loop around the call needs. Every finding cites the project
that measured it; where a project is a demo with no measurements, it says so.

## Contents
- Rules first, Jev as reviewer
- Rebuild the menu every turn
- Never block the loop on Jev
- Put the answer in the state
- Verify "done" yourself
- Budgets that survive restarts
- Jev decides, an LLM only writes text
- Memory lives in the harness
- Guarding a coding agent's own decisions
- Context pruning: a caveat

## Rules first, Jev as reviewer

When code can decide most cases, let it, and use Jev only where judgment helps. On 11
robot-arm fixtures ([robo-harness](https://github.com/grmkris/robo-harness),
`docs/decider-comparison-2026-09-21.md`), with results and cost identical across three reruns:

| Strategy | Correct | Cost | Jev called |
| --- | --- | --- | --- |
| Rules only | 11/11 | $0 | never |
| Rules first, Jev as critic | 11/11 | $0.000139 | 4 of 11 |
| One Jev `choice` per step | 10/11 | $0.000442 | every step |
| Decomposed parallel questions (terminate / act / joint / direction) | 8/11 | $0.000455 | every step |

Every miss was a case where the right move was *not* to move: Jev re-picked a step that had
just failed to move the arm, and the parallel version chose `stop` on stale data. The
critic scored 11/11 because "the model never gets a vote on the cases it fails". The
repo's fix for the repeated failure was structural — drop a step that just failed from the
next candidate list — not a prompt change. Splitting one action into parallel
sub-questions did worst; keep one decision as one question unless you've measured otherwise.

## Rebuild the menu every turn

Offer only what exists and is possible right now; a stale menu gets a stale answer.

- [jev-ultrafast](https://github.com/browser-use/jev-ultrafast) (`jev_ultrafast/model.py`,
  `docs/design.md`) rebuilds an indexed table of visible elements after every observation
  and asks, in **one request**, a `choice` for the operation (click, type, scroll, done, …)
  plus one target question *per operation*, each listing only compatible elements and
  stating the operation it assumes; only the target question for the chosen operation is
  validated and used. Operations that aren't currently possible aren't offered; at most 250
  candidates are kept, and truncated ones can't be chosen. Measured: median task time
  9.45 s → 7.09 s, 17 Jev requests at a 178 ms median — three alternating runs of one
  task, with the clock starting after the first observation and setup and verification
  excluded (`docs/performance.md`; the README says it is not a general benchmark).
- It acts on the top pick with **no confidence bar and no fit noul**. Safety comes from
  elsewhere: the id must be one it offered, the page is checked for freshness right before
  input, three actions in a row that don't change the page end the run as BLOCKED, and the
  outcome is verified independently afterwards. A confidence bar is one way to be safe,
  not the only one.
- robo-harness (`apps/server/src/decision/candidates.ts`) offers movement candidates only
  when the observation is usable (fresh, no fault, nothing in progress), and keeps a 0.2
  margin under the step cap and plans at 90% of the speed cap, because sensor jitter got
  real steps refused.

## Never block the loop on Jev

A control loop can't wait on the network. Three patterns:

- **Stale-tagged cache.** [jev-drone](https://github.com/RomanSlack/jev-drone)
  (`tactics.py`, `run.py`) runs Jev in a background worker behind a queue of size 1; the
  loop uses the latest judgment tagged with its age and ignores it after `stale_after_s`
  (1.5 s for tactics, 0.3 s in the fast tunnel run).
- **Hold the last action** while a request is in flight
  ([typesafe-mario](https://github.com/fhshaik/typesafe-mario), `runner.py`; a demo, no
  measurements).
- **Hard deadline.** robo-harness (`jev.ts`) aborts a request at its deadline, so a late
  answer can never be applied.

More from the drone, which is measured:

- **Pipelining needs sequence numbers.** 6 parallel workers sustained 21 decisions/s at
  0.118 s median / 0.164 s p90, with zero errors in about 2,000 calls; a response is used
  only if its sequence number is newer than the current one (`tunnel_tactics.py`, README).
  Jev was 13% of the reaction budget; the airframe was 80%.
- **Code decides when to ask.** No call when the path is clear; a coarse scene fingerprint
  reuses the last judgment; a failed call resets the fingerprint so a static scene is asked
  again. With a 160-call cap per episode, one flight used about 80 calls in 65 s.
- **Map graded answers straight to control.** Re-picking a 6-way `choice` every 70 ms
  produced bang-bang steering; 5 descriptive steer and height levels mapped directly to the
  command, a committed maneuver held for about 1.4 s unless risk reached 1.7, and code kept
  the veto (a `climb` pick is refused unless the measured top edge is below the climb
  ceiling).
- **Test at real time.** At 10× simulation speed, 152 of 182 requests hit a full queue and
  Jev influenced nothing.
- **Feed the delay back in.** typesafe-mario puts the measured request delay into the next
  state and precomputes timing facts (`jump_must_start_this_decision`) in code.

## Put the answer in the state

Jev can't choose an action the state doesn't justify. The drone never chose `climb` until
the state included the obstruction's height, whether its top edge was visible, and the
climb ceiling; then `climb` came back at p = 0.93. When the `choice` was unsure (p = 0.24),
a dedicated noul answered cleanly (0.12), so behaviour was gated on the noul.
[jev-claude](https://github.com/Panebianco00/jev-claude) (`docs/DESIGN.md`) saw the same on
a coding agent: `git reset --hard HEAD~3` scored 0.46 from the command alone and 0.16 once
git facts (never pushed? gitignored?) were attached.

## Verify "done" yourself

A "done" answer is a judgment, never evidence. jev-ultrafast verifies route, date and
results independently after the run (`examples/flights.py`); robo-harness vetoes `done`
unless the piece is actually held and lifted, and ends the run on an unknown outcome
(`skill-loop.ts`). After an interruption, check the last action's real outcome before
repeating anything.

## Budgets that survive restarts

robo-harness (`spend.ts`) stores spend in SQLite and reserves a worst-case cost (4,000
input tokens × price) before each call, with a $10 default cap; a full day of real-arm runs
cost about $0.003. Protective stops were reclassified as pauses (retried up to 6 times)
after two runs were thrown away (`docs/acceptance-2026-09-18-overnight.md`). An in-memory
budget resets on every crash; persist it.

## Jev decides, an LLM only writes text

jev-ultrafast calls a small LLM only when the chosen operation is "type text". The LLM must
return exactly `{"text": ...}`; its value is reused only for byte-identical input, and the
executor never pulls quoted strings out of the goal. Earlier probes rejected an LLM that
swapped origin and destination and one that returned commentary instead of JSON. Measured:
346–581 ms per text call, $0.00006 for two calls (`model.py field_text`,
`docs/performance.md`).

## Memory lives in the harness

Jev has no history; each request stands alone. [jev-plays-pokemon](https://github.com/milanboers/jev-plays-pokemon)
re-sends the last 8 dialog pages, the last 12 actions with their outcomes, and how much of
the current room has been explored, oldest first — about 1,600–2,100 input tokens per
decision (a demo: token and cost estimates, no success rates). It also *samples* its goal
from a flattened distribution (temperature 2.0, floor 0.1 per option) so a confidently
wrong goal doesn't repeat every turn — an unmeasured idea worth trying when an agent loops.

## Guarding a coding agent's own decisions

[jev-claude](https://github.com/Panebianco00/jev-claude) routes Claude Code's plan approval,
clarifying questions and risky commands through Jev (PreToolUse hooks on `ExitPlanMode`
with a 20 s timeout, `AskUserQuestion` 15 s, `Bash`, `Edit|Write`, plus `Stop` and
`UserPromptSubmit`; `hooks/hooks.json`, `docs/DESIGN.md`). Measured lessons:

- **One band for meaning; stakes decide the action.** A 0.90 "yes" bar for high stakes
  left a `DROP TABLE` over 1.2M rows at 0.79, recorded as "uncertain". It now uses one noul
  band everywhere (yes ≥ 0.65, no ≤ 0.35), and stakes only choose what to do with a yes.
  When the band depended on stakes, raising stakes widened the uncertain zone: 0.72 blocked
  at medium stakes but not at high.
- **Wording, measured on the same `DROP TABLE`:** compound question 0.89; the same plus
  boilerplate criteria restating the question 0.81; "Does the command in `command` destroy
  stored data?" **0.98**.
- **Polarity.** "Is there a way to put things back?" answers "no" for `git status` and
  blocked read-only commands. Reframed as "unrestorable change", read-only commands scored
  0.02–0.11 and an unbacked `DROP` 0.94. Phrase the question so irrelevant or safe cases
  land on the non-blocking answer.
- **Scores never reach the top level.** A score is an expected value: complete plans scored
  1.85–1.99 on a 0–2 scale, so a 1.95 bar refused complete plans; it moved to 1.5.
- **Silent truncation corrupts answers.** A 4,000-character state cap showed Jev a third of
  a 13 KB plan: coverage 1.6, and settled decisions read as contradicted (0.11, 0.24). A
  24k cap gave coverage 1.99 and consistency 0.94.
- **Guard questions:** an injection noul scored 0.97–0.98 on real injections vs 0.05–0.12
  clean (bar 0.85); a `delegated_to_assistant` noul (0.98 vs 0.04–0.33) stopped false
  "ask the user" escalations after 3 of 4 delegated choices had been handed back; an
  `options_are_neutral` noul downgrades a pick when option wording is lopsided.
- **Near-ties:** two real options within 0.15 holding ≥ 0.7 of the mass → proceed and flag,
  don't escalate.
- **Cap refusals** so a hook can't trap the session: 2 per plan, 1 per question set, 1 per
  command. A per-question calibration harness (`npm run calibrate`, 37 fixtures, about
  $0.004 a run) is re-run and diffed whenever the model changes.

LangChain's official middleware
(`langchain_typesafe.experimental.middleware.AutoModeMiddleware`, `langchain-typesafe`
0.0.1a3) makes different choices from recipe 17 in `recipes.md`: its state is the last 30
messages *including tool output* plus the tool call, the threshold is fixed at 0.5, and a
failed classification blocks the tool (fail closed). As of 0.0.1a3, constructing it
without `criteria` sends none — the built-in risky/safe criteria are skipped. Decide those
defaults deliberately rather than inheriting them.

## Context pruning: a caveat

[fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) replaces Claude
Code's compaction summary with two nouls per tool call ("should this call stay?", "is its
full output needed verbatim, where re-running wouldn't do?"), both kept at ≥ 0.5, with a
missing answer defaulting to keep and a fallback to the built-in summary when the cut is
under 25% or anything errors. It publishes **no quality or regression measurement** (its
tests use a fake Jev), and Jev judges each result from a one-line stub (`ok, 4213 chars
(omitted)`), never the result itself. The widely shared "1M → 86K tokens in a second"
figure isn't in the repo. Measure task success after pruning before relying on it.
