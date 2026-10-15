# Reference 03: Fit, limits, cost, and time

Use this to give the user honest numbers in Step 2 (Educate).

## Is Jev the right tool? A 20-second test

Jev fits if the answer is one of: yes/no, one-of-a-fixed-list, or a graded level.
Jev does NOT fit if the user needs any of: written text, an explanation, a summary,
code, a plan, multi-step reasoning, or image understanding. If they need those,
either pair Jev with an LLM (Jev decides, the LLM writes) or use an LLM alone.

Good fits: lead/email/ticket classification, support routing, moderation and spam,
jailbreak/guardrail checks, diff-risk or code-smell scoring, relevance ranking,
extraction of a known label, cheap first-pass verification of another model's work,
routing a request to a cheap vs expensive model.

## Hard limits

- `choice` supports at most 255 options.
- `score` requires 2 to 10 ordered levels.
- No images (text/JSON state only).
- Confidence is calibrated but not perfect. A correct TYPE is not a correct ANSWER.
- It is one decision call: no memory between calls, no tools, no browsing.

## Cost (get a real number, do not hand-wave)

- Price: input tokens only, output is free. TypeSafe's stated rate is
  $0.042 per million input tokens (~$0.0004 per average decision on their
  benchmarks). Confirm the live price on the OpenRouter model page.
- OpenRouter responses return `usage.cost` and `usage.input_tokens`, so you can
  measure real cost instead of estimating. The direct TypeSafe API documents token
  usage; check current billing docs rather than assuming it returns a cost field.

Estimation formula for the user's workload:

```
monthly_cost = decisions_per_month
             * avg_input_tokens_per_decision   (state + questions; count them, do not guess)
             * price_per_input_token            (e.g. 0.042 / 1_000_000)
# output tokens are free
```

Worked example: 1,000,000 decisions/month, ~400 input tokens each, at $0.042/M:
1,000,000 * 400 * (0.042 / 1,000,000) = $16.80/month. Say the real number to the
user and note it excludes any OpenRouter margin (check the live model page).

Cost-saving tip to teach: batch several questions about the same state into ONE
request (they share the input tokens) instead of one request per question.

## Time / latency

- TypeSafe claims 70ms to 500ms end-to-end per decision (creators report ~100 to
  150ms typical). These are vendor/creator claims; treat as approximate.
- Implication: fast enough to run inline in most flows, but for very high volume or
  strict real-time UX, run it in the background or in parallel and design for the
  upper end of the range. Network latency to OpenRouter is on top of model latency.

## The non-authoritative rule (design requirement, not a suggestion)

Because Jev can be confidently wrong, the layer must not take irreversible action
on its own for anything that matters. Pattern:
- Return `{answer, confidence, probabilities}` from the Jev call.
- Keep the threshold and the action in the user's code.
- For decisions that gate money, security, deletion, sending, or publishing: act
  automatically only above a high confidence threshold you have measured; below it,
  escalate to a human or to an LLM. Start conservative and loosen only after you
  measure false positives and false negatives on real data.

## Threshold anchors (so you are not inventing the number blind)

The confidence threshold for acting automatically is the highest-stakes number in
the build, and Jev can be confidently wrong, so anchor the STARTING point to the
cost of a mistake, then measure and adjust on real data. These are starting points,
not laws:

- Reversible, low-cost mistake (tag an email, pick a queue): ~0.6-0.7 to auto-act,
  below that route to a fallback.
- Costs someone time or annoyance (auto-answer a chat, auto-hide a comment):
  ~0.8-0.85 to auto-act, below that send to a human/queue.
- Irreversible or affects a person (mute/ban, auto-reject, anything touching money,
  security, or standing): >=0.9 to auto-act on the SEVERE end only, and even then
  prefer a reversible action (warn, hold, flag) over the irreversible one until you
  have measured false positives on real traffic.

Always tie the number to the user's own false-positive vs false-negative answer
from the interrogate step. If they never gave one, get it before you set thresholds.

## Real-time surfaces (post-now, moderate-async)

Jev is fast but not free of latency (tens to hundreds of ms plus network). For a
surface where a human is waiting (live chat, in-game messages, a chatbot reply), do
NOT block the user-visible action on the Jev call. Show/post the content
immediately, run Jev in parallel or just after, and apply the consequence
(warn/mute/hide/route) asynchronously when the answer comes back. This keeps the UX
instant while still getting the decision. Reserve inline/blocking Jev calls for
flows where a short wait is acceptable (batch jobs, form submissions).

## Handle the call failing, not just low confidence

The Jev call can time out or error. Decide the failure direction per action, with
the user:
- fail-open (let it through, or escalate to a human) when blocking a legitimate item
  is the worse outcome, e.g. a support router: on error, just send to a human.
- fail-closed (hold or queue) when taking a wrong automatic action is the worse
  outcome, e.g. auto-publish: on error, hold for review.
Never let an exception silently drop the item or default to the risky action.

## Flagged high-stakes categories (name these to the user)

Beyond money/security/deletion/sending, explicitly flag decisions that affect a
person's rights or opportunities, because they carry legal and ethical weight the
user may not have considered:
- hiring / resume screening, credit and lending, housing, insurance, education
  admissions, and government benefits. Several jurisdictions regulate "automated
  employment/decision tools" (e.g. NYC Local Law 144, the EU AI Act). You are not
  the user's lawyer; tell them to get counsel, and design so a human reviews every
  consequential outcome and the system never auto-rejects a person.
- moderation that can mute, ban, or remove: bias toward reversible actions (warn,
  temporary hold) and human review of the severe end.

## When there is no API key yet

It is common to build before a key exists. That is fine: write the integration plus
a test that uses an injectable fake decision function, prove the ACTION LOGIC
offline (right buckets, right escalation, right failure behavior), and clearly mark
live verification as pending. Do not claim it was verified against the live API when
it was not.

## Data privacy (Jev is a cloud call)

The `state` leaves the user's systems and goes to TypeSafe, either directly or
through the selected gateway. With OpenRouter, it passes through OpenRouter too.
For anything with personal or sensitive data (customer chat, resumes, financials,
health, minors), name this to the user, recommend a privacy / data-processing
review before production, and minimize what you send: put only the fields the
decision actually needs in the state, not whole records. If data residency or "must
stay on our network" is a hard requirement, Jev via a cloud gateway may be the wrong
fit and a local model should be considered instead.
