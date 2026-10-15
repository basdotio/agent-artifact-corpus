---
name: jev-anything
license: MIT
description: >
  Use when the user wants to add Jev (TypeSafe's System One decision model) to
  anything: a classifier, router, scorer, guardrail, extractor, or any "smart
  if-statement" in their code or workflow. Triggers include "add jev", "jev
  classifier", "route/score/classify/grade/guardrail with jev", "put a decision
  layer in", or "jev-anything". Works even when the user does not understand Jev
  yet: this skill makes you interrogate, educate, and plan with them first, then
  scaffold a working Jev layer through TypeSafe's direct API or OpenRouter.
---

# jev-anything

You are helping a user put a Jev decision layer into their software, even if they
do not understand Jev well. Your job is NOT to immediately write code. Your job is
to first understand Jev correctly, then work out with the user what they actually
need, then scaffold it through TypeSafe's direct API or OpenRouter.

## Step 0: Read the references before you say anything technical

Do not describe Jev, quote its cost, or write a call from memory. Read these first:

- `references/01-what-jev-is.md` - what Jev is and is not, the three decision
  primitives, how it actually works.
- `references/02-openrouter-decisions-api.md` - current TypeSafe direct access,
  the included OpenRouter client's exact request and response, auth, model slugs,
  verified field names, and two patterns that matter in practice (the escape
  option, and per-input-variable criteria).
- `references/03-fit-limits-cost-time.md` - what Jev can and cannot do, hard
  limits, how to estimate cost and latency, threshold anchors, the real-time
  pattern, error handling, and the flagged high-stakes categories.
- `references/04-measure-and-optimize.md` - after it runs, how to measure accuracy
  on labeled data and tune it (read this before Step 6).

If you skip these you will hallucinate Jev's API or its abilities. Read them.

## Step 1: Interrogate (understand what they actually want)

Most users arrive with a vague wish ("make my app smart", "classify my leads").
Pull it into a concrete decision. Ask, in plain language, only what you still need.
Do not infer answers to these when the honest move is to ask; a wrong guess here
becomes a wrong system:

1. What is the ONE decision you want made, in a sentence?
2. What is the input (the "state")? Where does it come from? (text, JSON, a row, a
   message)
3. What shape is the answer? Confirm the primitive with the user, do not silently
   pick it:
   - yes/no with a probability  -> Jev `noul`
   - pick one of a fixed list   -> Jev `choice` (max 255 options)
   - a graded level on a rubric  -> Jev `score` (2 to 10 ordered levels)
   Watch for phrases that fit more than one shape. "How urgent is it?" could be a
   yes/no (is_urgent) OR a graded score. When the wording is compatible with both,
   ask the user which they mean and why (a score if they want to rank/prioritize, a
   noul if they just want a gate). Naming the tradeoff out loud is the point.
   If they need free text, an explanation, code, or reasoning: Jev cannot do that.
   Say so now (see Step 2).
4. Where in their workflow does this plug in? What happens with EACH answer? (this
   is the branch/if-statement Jev replaces)
5. What happens to the cases the system does NOT act on - the not-shortlisted, the
   not-flagged, the escalated? Does anyone ever see them, or do they vanish? Users
   often forget the silent pile; surface it.
6. How wrong is too wrong? Ask for their tolerance for false positives vs false
   negatives in plain terms ("is it worse to auto-hide a real comment, or to let
   some spam through?"). Their answer sets the thresholds later; without it you are
   guessing the most important numbers in the build.
7. Volume and speed: how many decisions per day, and does it need to be real-time?
   (drives cost and latency, Step 2.)

Do not move on until you can state the decision back to them in one sentence, with
the primitive, and they agree.

## Step 2: Educate (be honest about fit, cost, and time)

Tell the user the truth about their specific case, grounded in the references:

- Can Jev even do this? If they need generation/reasoning/writing/code, Jev is the
  wrong tool alone; it pairs with an LLM. Offer the realistic split (Jev decides,
  the LLM writes) or tell them Jev is not what they need.
- Cost: compute it from their volume using the formula in reference 03 (input
  tokens x the current price, output is free). Give a real monthly number, not a
  hand-wave. OpenRouter responses return `usage.cost`; for direct TypeSafe access,
  use documented token usage and current billing rather than assuming that field.
- Time: quote the real latency range from the references and what it means for
  their UX (inline vs background, and the real-time pattern if they are latency-
  sensitive - reference 03).
- The one caveat that matters: Jev's "no type errors" guarantee is about the answer
  matching the schema, NOT about the answer being correct. Jev can be confidently
  wrong (in testing it returned confidence 1.0 on inputs a human found ambiguous).
  So the layer must be non-authoritative by default (Step 4).
- DATA LEAVES THEIR NETWORK: the `state` goes to TypeSafe, either directly or via
  the selected gateway (a cloud call, not local). If it can contain personal or sensitive data (customer
  messages, resumes, financials, health), tell the user plainly and flag a privacy
  and data-processing-agreement review before production. Send only the fields the
  decision needs.
- HIGH-STAKES CHECK: if the decision affects people's money, safety, legal
  standing, or opportunities - especially hiring, credit, housing, insurance,
  moderation that can ban/mute, or anything a regulator might call an "automated
  decision" - say so plainly, tell them it needs human oversight and possibly legal
  review (you are not their lawyer), and design it to never take the irreversible
  action alone. See reference 03's flagged categories.

If Jev is a bad fit, say so plainly and stop. A wrong-tool build helps nobody.

## Step 3: Plan (agree the exact question set before coding)

Turn the decision into a concrete Jev `questions` spec and confirm it with the
user. Use `PLAN-TEMPLATE.md` - fill it in with them:

- the `state` (what text/JSON you will send)
- each question: name, type (noul/choice/score), instructions, and criteria
  (options or rubric levels)
- READ THE EXACT CRITERIA WORDING BACK to the user and get their sign-off. You are
  often authoring the option descriptions and rubric levels yourself; those words
  are what Jev classifies against, so a non-technical user must confirm they match
  their real categories before you call the plan final.
- for a `choice` whose option list might not cover every real input, add an
  explicit escape option ("none of these / needs a human") rather than trusting the
  confidence threshold to catch mismatches - see reference 02. Otherwise Jev
  force-fits an out-of-scope input into a real option, confidently.
- for each possible answer, what their code should DO
- the confidence threshold below which you escalate to a human or an LLM rather
  than act automatically. Anchor the starting number to the stakes using reference
  03; do not invent it. Tie it back to their false-positive/false-negative answer
  from Step 1.

Show them the filled plan and get a yes before writing code.

## Step 4: Implement (drop the layer in)

- Choose the access path with the user. For TypeSafe direct, use the current
  first-party SDK/API docs linked in reference 02 and `TYPESAFE_API_KEY`. For the
  included dependency-free OpenRouter path, copy `scaffolding/jev_client.py` or
  `jev_client.ts` and set `OPENROUTER_API_KEY` (see `scaffolding/.env.example`).
- Write ONE small function that builds the `state` from their input, calls the
  client with the agreed questions, and returns the typed answer plus confidence.
- Wire it in exactly where their current if-statement / manual label / routing
  decision lives. Do not move authority into Jev: it returns a decision and a
  confidence; the threshold and the action stay in the user's code.
- Handle the call FAILING, not just low confidence. Networks time out and APIs
  error. Decide with the user which way to fail per action: fail-open (let it
  through / escalate to a human) when blocking is worse, fail-closed (hold / queue)
  when a wrong auto-action is worse. Never let an exception silently drop the item.
- If the input requirement varies per call (e.g. each job posting needs a different
  number of years), keep the question `instructions` generic and put the variable
  requirement in the `state`, so the classifier does not hardcode one case and
  break on reuse - see reference 02.
- The `scaffolding/examples/` folder has a worked version of each primitive
  (email triage = choice, PR risk = score, guardrail = noul). Adapt the closest.

## Step 5: Verify (prove it before trusting it)

- If a key is available: run it on 5 to 10 real inputs the user provides. Print the
  answer, confidence, and full probability distribution. Check the low-confidence
  and the error paths actually escalate. On OpenRouter, show `usage.cost`; on the
  direct TypeSafe API, show documented token usage and calculate cost from current
  billing so the estimate is grounded.
- If NO key is available yet (common): still finish the build. Write the integration
  plus a runnable test with an injectable fake decision function so the action logic
  is proven offline, and leave a clear note that live verification is pending a key.
  Do not fake live results or claim it was verified against the API when it was not.
- Only after this, remove any scaffolding TODOs and hand it over.

## Step 6: Measure and optimize (do not skip this once it runs)

A classifier that runs is not yet a classifier that is right. Once the user has run
it on real inputs, measure its accuracy and tune it. Read
`references/04-measure-and-optimize.md`, then:

1. Get ground truth the human-reasonable, unbiased way. Take a random sample of the
   user's real inputs and export a BLIND rating sheet with
   `scaffolding/make_rating_sheet.py` (a CSV with the answer column blank and the
   model's guess NOT shown, so the user does not just rubber-stamp it). The user
   fills the answer column in a spreadsheet from the fixed category list - about 10
   to 20 minutes for 50 short items, done once and reused. Load it with
   `evaluate.load_labeled_csv`. Detail and the reasoning are in reference 04.
2. Split it (`evaluate.split`) into a tuning set and a held-out test set, then
   measure with `scaffolding/evaluate.py`: per-question accuracy with a 95%
   confidence interval, a confusion breakdown, confidence calibration, and cost,
   stored as a timestamped run. Tune against the tuning set and report the held-out
   number, so you are not grading your own homework. Respect the interval - a 40 to
   50 item sample is "about 85 percent," not "85.0."
3. Read WHICH cases are wrong and WHY, then pull the highest-leverage fix. The
   biggest by far is the CRITERIA wording (published experiments moved a classifier
   70% -> 96% by rewriting only the criteria; the question text barely matters).
   Define what passes as well as what fails, define the underlying axis rather than
   surface features, and keep the state focused. Full priced-ordered lever list and
   the evidence are in reference 04. Tune the confidence threshold LAST.
4. Re-run evaluate.py (it prints the change per question vs the last run), keep what
   helped, and repeat until the user's target accuracy or until rounds stop helping.
5. Set expectations honestly: Jev has a ceiling, some tasks need an LLM or more
   information in the state, and you never raise the auto-act threshold just to make
   a number look better.

Hand over the labeled set, the results history, and the final tuned criteria so the
user can re-measure later when their data drifts.

## Guardrail default (carry this into every build)

Jev decides, it does not act. Return `{answer, confidence, probabilities}` and keep
thresholds, side effects, and escalation in the user's own code. For any decision
that gates money, security, deletion, sending, or a person's standing, start below
a high confidence threshold and escalate to a human until measured. This is the
single most important design rule and it is also the best thing to teach the user.
