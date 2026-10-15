# Jev Layer Plan (fill this in WITH the user before writing code)

Copy this, fill it in during Step 3, and get the user's yes before implementing.

## 1. The decision, in one sentence
> (e.g. "Decide which of 4 teams should own an incoming support ticket.")

## 2. The input (state)
- Source: (where the text/JSON comes from)
- What you will send as `state`: (describe exactly)

## 3. The question(s)
For each, pick a primitive and define it.

| name | type (noul/choice/score) | instructions (the question) | criteria (options or rubric levels) |
|------|--------------------------|-----------------------------|-------------------------------------|
|      |                          |                             |                                     |

(choice: <=255 options as key->description. score: 2..10 ordered levels, lowest first.)

- [ ] Read the exact criteria wording (option descriptions / rubric levels) back to
      the user and got sign-off. Those words are what Jev classifies against.
- [ ] If the option list may not cover every real input, added an escape option
      ("none of these / needs a human") - see reference 02.

## 4. What happens with each answer
- If answer = X and confidence >= T: (action)
- ...
- Below threshold T = ____ : escalate to (human / LLM / queue)
- If the Jev call ERRORS or times out: fail-open -> ____ or fail-closed -> ____
  (pick per the cost of a wrong auto-action vs blocking a legit item)
- What happens to items the system does NOT act on (the escalated / not-selected
  pile) and who reviews them: ____

## 5. Where it plugs in
> (the exact function / if-statement / route this replaces)

## 6. Cost and latency check
- Decisions per month: ____
- Avg input tokens per decision: ____  (count state + questions)
- Estimated monthly cost: ____  (tokens x price; output is free)
- Latency budget: inline / background? Acceptable ms: ____

## 7. Confidence threshold and escalation
- User's false-positive vs false-negative tolerance (from interrogate): ____
  (which mistake is worse, and roughly how much)
- Auto-act above confidence: ____  (anchor to stakes, reference 03; tie to the line above)
- Below: ____
- High-stakes / regulated decision (hiring, credit, housing, insurance, moderation
  that can ban/mute)? ____  If yes: a human reviews every consequential outcome,
  never auto-reject a person, and flag legal review to the user.
- For money/security/deletion/sending decisions, start conservative and measure
  false positives/negatives before loosening.

## 8. How we verify before trusting it
- Test inputs to run: ____
- What "good enough" looks like on those: ____
