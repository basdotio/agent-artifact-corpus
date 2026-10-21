---
name: feature-triage
description: Use when a new planning cycle (quarter, program increment, release train) starts and the cycle's feature requests need triaging for relevance to your specialty - "which of these features are analytics/security/accessibility/performance relevant", "run the triage for this quarter", "classify the backlog", "the prioritization outcome is in, update the results", or "run the retro on the triage". Covers pre-decision classification, post-decision updates, and the learning retro. This is a TEMPLATE - fill in references/classification-template.md with your own relevance rules before it can classify anything. Do NOT use for one-off questions about a single work item, or for general backlog grooming that has no relevance dimension to judge.
---

# Feature Triage (template)

> This skill was seeded from a real, production quarterly feature-triage skill (an analytics
> specialist classifying ~700 feature requests per quarter) and generalized into a template. The
> METHOD ships complete - the tiered subagent pipeline, the canary gate, the arbitration ladder,
> the verification gates, the feedback loop. The RULES do not: relevance is defined by your
> domain, so `references/classification-template.md` is a fill-in skeleton. The skill cannot
> classify anything until you write your own rules, examples, and canaries into it.

## The problem this solves

Every planning cycle, hundreds of feature requests land in your work tracker, and only a small
fraction matter to your specialty - analytics, security, accessibility, localization,
performance, privacy, whatever "relevant to me" means for you. Reading them all yourself takes
days; skimming misses the ones that matter. This skill runs that triage end to end with a fleet
of classifier subagents, at recall the skim can't match, with every uncertain call surfaced to a
human instead of silently dropped - and it gets measurably better every cycle by learning from
your corrections.

## Safety rules (non-negotiable)

1. The work tracker (Azure DevOps, Jira, Linear, GitHub...) is READ-ONLY. Never call a write tool.
2. Never delete anything in the docs destination (Notion, Confluence, a wiki...). Add and edit
   only; re-runs are add-only, diffed on the work-item ID. A human's manual edits are sacred.
3. NEVER put secrets (tokens, API keys, connection strings) into docs, chat, or run files.
4. Recall-first: uncertainty = `No` + `Confidence: Low` (which surfaces in the human miss-scan
   queue), never a silent drop. Errors become `No / Low / "review manually"` rows.
5. Echo the resolved cycle name + phase and get the user's confirmation BEFORE querying anything.
6. **Do the mode's whole job, and nothing outside it - without asking either way.** Two failures,
   opposite directions, same root:
   - *Too much*: re-pulling or re-classifying items nobody asked about. Anything outside the
     current mode's step list is OUT OF SCOPE, not an offer - do not do it and do not ask about it.
   - *Too little*: finishing part of a mode's checklist (e.g. updating a table but leaving a
     summary figure or chart stale) and stopping to ask whether to finish. Every step in the
     mode's list is mandatory and runs unprompted; a half-updated result is a defect, not a
     checkpoint.
   The test before reporting done: is every line of the mode's definition-of-done ticked, and did
   anything happen that is not in the list? Both answers must be clean.
   **Corollary: the fix for "too much" is a narrower mode, never a blind spot.** A scope-limiting
   rule must name the exact dimension that caused the waste. Narrowing along the wrong dimension -
   a date instead of a decision, a folder instead of an owner - can turn a spend problem into a
   silent recall hole while looking like the same fix. See the Phase B cutoff rule below for a
   worked example of exactly that mistake and its correction.

## Files

| File | Who loads it | When |
|---|---|---|
| `references/classification-template.md` | classifier subagents (+ orchestrator for spot checks) | classification |

Classifier subagents read ONLY that file. The orchestrator never loads full feature descriptions
into its own context - subagents fetch their own data.

## Cycle and phase detection

- Resolve which cycle is being triaged (e.g. "next quarter") and echo it in your tracker's exact
  format before querying.
- **Phase A** = pre-decision: the requests are in, the prioritization decision has not happened.
  **Phase B** = post-decision: the outcome is visible; update results and build handoffs.
  If today is near the decision boundary, or phase-A artifacts already exist for this cycle, ASK
  which phase applies - the user's answer is authoritative.
- Keep run state in a per-cycle folder (`runs/<cycle>/`) outside the docs tool: the pulled IDs,
  the classified JSONL, the reports. Re-runs reconcile against it instead of reclassifying.

## Phase A workflow

1. **Confirm** the cycle string + phase with the user. Create `runs/<cycle>/`. If phase-A
   artifacts already exist, this is a re-run: reconcile (add-only), don't reclassify what the
   JSONL already holds.
2. **Pull IDs** from the tracker with a deliberate over-fetch cap, then assert `count < cap` (a
   result that exactly hits the cap is truncated, not complete) and a plausibility floor (a
   quarter that "only" has 30 requests when history says hundreds means the query is wrong).
   Save the ID list with the count on line 1. Report the count.
3. **Scope-family check - ASK BEFORE SPENDING THE FLEET.** Group the pulled titles by their
   tag/prefix families and list any family with more than ~10 tickets. For each family your rules
   don't already cover, ask the user ONE question: *"<family> is <n> tickets this cycle - is that
   work shipping in one of our products, or is someone else building it elsewhere?"* Ownership is
   invisible inside a ticket: a feature built by an external team in a separate product can read
   as a textbook Yes for pages and still be irrelevant, because it never lands in anything you
   measure. One question up front is cheaper than a family of wrong verdicts plus a re-run.
4. **Canary gate**: dispatch ONE classifier subagent on the locked canaries in the template
   (digests included there - no tracker fetch). Pass: at most one miss, and zero Yes-canaries
   flipped to No. Fail: STOP, report which flipped, and fix the rules before any fleet spend.
5. **Classify - TIERED, two passes:**
   - **Pass 1, title triage.** Split IDs into batches of ~100; dispatch triage subagents that
     fetch ONLY the light fields (id, title, tags, area/team). `Confidence` is redefined for this
     pass: `Low` = "the title is not enough, escalate me".
   - **Pass 2, escalation.** Every feature pass 1 marked `Yes` **or** `Low` goes into full-detail
     batches of ~25. Expect roughly half to escalate.
   - **Final verdict** = the pass-2 verdict where a feature escalated, the pass-1 verdict
     otherwise. Never skip pass 2 for a `Yes` - a cheap Yes is not a Yes.
   Validate each batch on return (JSON parses; ID set == assignment; vocabulary ok). One
   re-dispatch per failed batch, then error rows.
6. **Assemble**: concatenate to `classified.jsonl`; assert the ID set matches the pull exactly.
   **Consistency pass**: review the Yes and Low-confidence-No rows (compact) for cross-batch
   contradictions - two tickets in THIS cycle with the same subject and opposite verdicts - and
   rule violations visible from title+reason; re-classify contested rows individually with full
   detail. A title that repeats an EARLIER cycle's ticket is a continuation chunk of a multi-cycle
   effort, not a contradiction and not a duplicate - never drop one for that.
   **Spot check**: pick ~5 random Yes + ~5 random No, fetch full detail, re-derive the verdict.
7. **Arbitration pass**: every row the consistency pass or spot check leaves CONTESTED goes here
   before anything is shown to the user. Climb the **progressive context ladder** in the template
   one rung at a time - full acceptance criteria and its named sections, then the parent epic,
   then sibling tickets in the same family, then the item's comment thread - and stop at the
   first rung that settles it. Record the rung and the evidence in the row's `reason`. Only rows
   still 50/50 after the ladder go to the user as an open question. Budget: a handful of rows per
   run, never the whole list.
8. **Insights pass**: with the assembled Yes list (titles + reasons), produce a bounded advisory -
   a handful of questions worth asking, opportunities worth raising, documentation gaps - every
   item anchored to a concrete feature in this cycle. Propose, never assume.
9. **Write the results** to your docs destination: the Yes rows as a database/table, the
   Low-confidence-No list as a "miss-scan" section for human review, a funnel summary
   (requested -> relevant -> decided), and the advisory.
10. **Report + handoff**: write `report.md` (counts, funnel, anomalies, changed rows). Tell the
    user: the counts, the links, and their actions - review the Yes rows, scan the miss-scan
    list, then say "review done" (retro) now and "the decision happened" (phase B) later.

## Phase B workflow (post-decision)

> **Phase B is a lookup, not a re-run.** Items were already classified in phase A and reviewed by
> a human. Phase B reads the one extra field that records the decision outcome for rows that
> already exist, and finishes the result. No classification runs in phase B - ever. No canary
> gate, no subagents, no triage.
>
> **The cutoff closes the list - for undecided late arrivals only.** A scope-limiting rule must
> name the dimension it actually limits, not a proxy for it. The intuitive version - "anything that
> joins the cycle after the phase-A pull is out of scope, full stop" - uses the wrong dimension
> (the calendar date) and can silently hide items that matter: a late arrival that gets DECIDED
> (prioritized, approved, funded - whatever your decision field is) is committed work someone is
> about to build, and an undetected decided item is exactly the silent miss the recall-first rule
> exists to prevent. The line runs along the DECISION, not the calendar:
>
> - A late arrival that is **NOT decided** is out of scope for the cycle, full stop - it returns on
>   its own in next cycle's phase-A pull. Never bulk-classify these, never offer to.
> - A late arrival that **IS decided** must be evaluated. That is the **Delta check** below, and it
>   runs on its own, unprompted.
>
> What stays banned is what the cutoff rule was actually protecting against: re-classifying
> anything already recorded, and dragging the whole late-arrival pool through the fleet. Phase B
> itself still classifies nothing - the Delta check that runs ahead of it does, on the decided gap
> only.

1. Confirm the cycle + that the decision outcome is visible. Locate phase-A state.
2. Pull both sets: all items, and the prioritized/committed subset.
3. **Decision flags**: for every existing row, set prioritized True/False by ID membership. Touch
   nothing else. Verify the flagged count equals the intersection, and diff every other column
   against a pre-run snapshot to prove nothing else moved. An item with no recorded decision
   counts as NOT prioritized - don't leave it blank.
4. **Filter the working view** down to relevant-and-prioritized (keep an unfiltered view too, as
   the safety net).
5. **Watch list**: relevant-but-not-prioritized rows -> a "watch next cycle" list, grouped by why
   (decided No / no decision recorded / moved to a later cycle).
6. **Finish the result completely, without asking**: the funnel with updated counts and ratio, any
   chart or figure that visualizes it (regenerated, not left stale), the advisory re-scoped to the
   prioritized set, and `report_b.md`. Any per-owner follow-up messages are DRAFTS only - never
   send anything. A result that updates the numbers but leaves a stale chart or an empty summary
   row is an unfinished job, not a checkpoint to ask permission at.

## Delta check (step 0 of every mode, and whenever asked "what changed since...")

Item lists keep growing after the phase-A pull - new requests don't stop arriving just because the
deadline passed. A mode that assumes the phase-A pull is still current is working from a stale
list, and if a newcomer gets decided before anyone notices, that is a silent recall miss.

1. **Snapshot.** Pull both sets again (all items; decided/committed items) and save dated snapshot
   files (`runs/<cycle>/snapshots/<date>_all.txt`, `..._decided.txt`).
2. **Diff** against a running register of everything ever judged this cycle, and report before
   spending anything: `new` (never seen before), `gap` (decided but never judged - the only set
   that gets classified), `left` (was in the register, no longer in the pull), and `kept_but_gone`
   (`left` intersected with your relevant list - name these individually; an item the user is
   actively working on must never vanish silently).
3. **Canary gate** - this mode classifies, so the gate applies (unlike phase B, which classifies
   nothing).
4. **Classify the `gap` at full detail - no title-triage pass.** The set is small (tens, not
   hundreds); triage exists to save reading at scale and buys nothing here, while recall-first says
   read the description.
5. **Gates**, same as phase A: batch ID diff (read the written JSONL, never trust a summary line),
   consistency pass, arbitration pass on contested rows, spot check.
6. **Register.** Append every classified row (`source: delta-<date>`). Append undecided newcomers
   with a null verdict and a "seen, not evaluated" source so they don't resurface every day.
7. **Write results**: new relevant rows join the SAME table as phase-A rows, tagged with when they
   were added (not when the ticket was created); funnel counts and any chart updated; `kept_but_gone`
   named on the page.
8. **Report** and reconcile project state.

A permanent per-cycle register (`{id, verdict, confidence, evaluated_on, source}`) plus dated
snapshot files from every pull are what make "today vs. yesterday" answerable at all - build them
once in phase A, append to them here, and never reconstruct either from your docs destination.

## Drafting a follow-up message

Phase A's advisory and phase B's per-owner follow-ups both end in a message a human has to send.
Four rules, each learned by breaking it:

- **Match message altitude to what the recipient already knows.** A first-round message to an owner
  who has not seen the analysis yet earns real per-item questions: what is genuinely unknown, where
  the data will live and whether you get access, what ships this cycle versus what is only a
  foundation. Implementation detail (exact toggles, counting semantics, audit-log location) stays in
  the tracker, not the message - cut it even from an otherwise-good draft. Once you have personally
  reviewed the item with that owner (a call, a prior round), the message drops an altitude level
  again: one plain status line per item ("already planned", "on/off setting, tracked like the rest",
  "spec coming"), at most one or two real open questions, no proposal, no ownership question. Group
  identical statuses under one line instead of repeating the same sentence per item.
- **Never ask what your own analysis already settled.** The easy version is "don't ask what the
  ticket already answers" - it wastes the recipient's time and signals the ticket was not read. The
  hard version is the same test turned on YOUR OWN findings: if the run already proved the answer,
  that finding becomes the PREMISE of a sharper question, never the question itself. State what you
  worked out, then ask the one thing only they know.
- **A link must already answer what the message claims it answers.** Before citing a documentation
  page, open it and confirm it contains the thing being cited. Write the documentation FIRST, then
  send the message that links it. A link to a page that does not hold the answer costs the
  recipient's time and your credibility at once.
- **Show the draft as plain text, not a blockquote.** A draft exists to be copied out of the
  terminal and pasted somewhere else; blockquote markers render as a bar down the left of every
  line and get selected along with the text. Use plain paragraphs between horizontal rules - no
  `>`, no bullet markers, no leading spaces, no code fence - in chat AND in the run file. Quoting a
  message already SENT, as a historical record, is fine; a draft someone still has to copy is not.
- **When the gap is wider than a message, hand over a questionnaire instead.** One or two questions
  per item stay a message. When an owner holds a whole block of facts you cannot settle alone, or
  will answer async or in a booked meeting, write a discovery questionnaire per
  `references/questionnaire-template.md`, on the requester's explicit ask: interview them only about
  the send (who it goes to, what must come back), then most-important-first questions with an answer
  stub under each, one idea per question, held to the same "never ask what the ticket or your own
  analysis already answers" test. Sync the tracker to the SENT version and keep working on labeled
  assumptions until the answers land.

All of these run on the OUTGOING message, not only on the human's draft of it. The observed failure
mode was stating these rules while critiquing someone's draft and then breaking them in the
replacement.

## Classifier subagent contract (dispatch prompt template)

> You classify <cycle> feature requests for <your specialty> relevance. Read
> `<absolute path to references/classification-template.md>` FIRST and follow it exactly.
> Your assigned work-item IDs: [<~25 ids>].
> Fetch them read-only with <your tracker tool + field list>.
> Classify EVERY assigned ID (fetch failure -> the error-row format in the template).
> Write your JSONL to `<runs path>/batches/batch_<NN>.jsonl` (one JSON object per line) AND
> return the same lines as your final message plus one summary line
> "<n>/<assigned> classified, <y> Yes, <l> Low-No".

Canary batch: same contract but "classify these locked canaries using ONLY their digests - no
tracker access". Paste the digests INTO the dispatch prompt and tell the subagent not to read the
canary table's Expected column - it is the answer key, and it lives in the same file.

Title-triage contract (pass 1): same first paragraph, then: fetch ONLY id/title/tags/team, judge
from those alone, `Low` confidence means "this one needs its description", emit a best Yes/No for
every ID anyway - never omit one, never flip to Yes to be safe.

## Verification gates

| Gate | Pass | On fail |
|---|---|---|
| fetch cap | count < cap | raise cap, re-run |
| cycle sanity | count plausible vs history | re-confirm the cycle string |
| canary | at most 1 miss, no Yes->No flip | stop, fix the rules |
| batch | schema + ID set ok - **read the written JSONL and diff its IDs against the assignment; NEVER trust the subagent's own "n classified" summary line** | one re-dispatch of the missing IDs, then error rows |
| escalation rate | pass-1 Yes+Low is a sane share of the pull (calibrate on your first run) | inspect the triage output before spending pass 2 |
| assembly | pull IDs == JSONL IDs | classify stragglers individually |
| Yes-rate plausibility | final Yes % sits in the band your history predicts | far above: the fleet is rescuing borderline items - inspect before writing. Far below: first check whether one large out-of-scope family explains it, then inspect the Low-No queue |
| spot check | at most 1 in 10 disagrees | send every disagreement through the arbitration pass first; show the user only what the ladder cannot settle |
| output counts | destination rows == Yes; miss-scan == Low-No | insert the missing rows by ID |
| register completeness | the running register has no duplicate IDs, and its row count == phase-A count + every delta appended since | rebuild the register from the classified JSONL files; never from the docs destination |

**The three-stage funnel** (keep the magnitudes in mind all run long): requested (everything in
the cycle) -> relevant to you (a small fraction) -> decided/committed (a fraction of that). Each
stage is a different number; never conflate them.

**A gate that a known-bad output can pass is not a gate.** Write each one so it can actually FAIL
on the defect it exists to catch, and prove that by running it against a known-bad case once. A
presence or substring check ("the new text appears exactly once") is the classic trap: a mangled,
misplaced, or wrongly-encoded value satisfies it perfectly. Prefer assertions with teeth - the
prior value survives intact as a prefix, the markup or structure count moves by EXACTLY what the
change should add and nothing is removed, the new text starts where it should, the declared format
is unchanged. And when a defect does get through, fix the ASSERTION, not just the instance;
otherwise the next run reproduces it.

**The mirror-image failure: a gate a CORRECT output cannot pass is just as broken.** Assert a
DELTA, not sameness. "The markup count is unchanged" sounds strict and is wrong the moment the
right fix legitimately adds markup - it then blocks the correct answer, and a check that blocks the
correct answer teaches whoever hits it to switch it off. Give every assertion a pass band that the
intended change fits and the known defect does not.

**A declared format is a CLAIM; the content is the EVIDENCE.** Metadata about what a field holds -
a format flag, a content type, a column type - can disagree with the bytes actually in it, and when
they disagree the content wins. Read the flag, then LOOK at the value and mirror what is really
there. Writing markdown into a field that reports "markdown" but contains a wall of markup produces
a correctly-declared, visibly-broken result.

## Feedback loop - how this gets smarter every cycle

Run this after the user's human review ("review done"), at least once per cycle:

1. **Diff AI vs human**: false positives (AI Yes the human removed), false negatives (rows the
   human added). Cross-reference the miss-scan list - a false negative that was listed there was
   "caught by miss-scan" (working as designed); track it separately from a true silent miss.
2. **Present the diff** as a table and ask the user to mark each row: a GENERALIZABLE lesson, or
   a situational one-off. One-offs are logged in `runs/<cycle>/retro_diff.md` but never become
   rules or examples - that is the anti-bloat valve.
3. **Apply confirmed lessons** to the template with replace-not-append curation: a new verdict
   that contradicts an existing example REPLACES that example (with a dated curation-log line),
   a pattern already covered is skipped, a genuinely new pattern adds ONE generalizable row. Hold
   a hard cap on example rows (~120); when exceeded, prune the most redundant row in the same
   group - never a canary. Locked canaries are IMMUTABLE unless the user explicitly unlocks one.
4. **Prefer rule edits over example piles** when the lesson is systematic. Every edit gets a
   dated changelog line in the file it touched.
5. **Append one row to the performance log** (cycle, total, AI Yes, false pos, silent false neg,
   caught-by-miss-scan, precision, recall). Rising precision at recall ~1.0 means the loop is
   working. Falling recall means STOP trimming and revisit last cycle's changes first.

The append-only failure mode is why this protocol exists: an example store that accumulates
corrections without removing what they contradict ends up asserting both verdicts for the same
feature, and the classifier obeys whichever it read last. Replace, never stack. And never shrink
the miss-scan queue to look tidy - in production it is where the real misses get caught.

### Observed is not handled

When a run surfaces an anomaly - "a few items behaved differently", "this one needed a workaround",
"the output looked slightly off" - that observation is closed ONLY by one of:

1. fixing it in the same session, or
2. putting it to the user as an explicit open decision.

A line in `retro_diff.md` does not close it. A reassuring footnote in a handoff document definitely
does not close it. When a defect surfaces days later, the information needed to prevent it was
usually in the room the whole time; what failed was the routing, not the analysis.

Two rules fall out of that:

- **Never state how something behaves or renders without having looked at it.** An inference
  written in the voice of a verification ("it still renders correctly") is how a real defect
  survives review.
- **When a defect gets through, fix the gate, not just the instance** - see Verification gates.

## Adapting this template

See `README.md` in this folder for the step-by-step. The short version: write your own
`references/classification-template.md` (rules, examples, canaries), wire your tracker's
read-only tool and field names into the subagent contract, set your own plausibility bands after
the first run, and run one cycle in shadow mode against your manual triage before trusting it.
