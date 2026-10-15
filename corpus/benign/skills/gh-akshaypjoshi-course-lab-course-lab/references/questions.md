# Writing the questions

Contents: 1. What a course-lab quiz measures · 2. The 3 / 4 / 3 mix · 3. Every question · 4. Distractors and rationales · 5. Per-course question patterns · 6. Final test · 7. Retests · 8. Verify before building

---

## 1. What a course-lab quiz measures

A chapter quiz answers one question for the learner: **can I use what this chapter taught, or do I only recognise it?** So:

- Every question is answerable **from the chapter** (the text, its code, its figure). Nothing from a later chapter; nothing that needs outside trivia.
- Questions test the chapter's outcomes (`outcomes:` in the front matter); map each outcome to at least one question.
- Spread over **at least 3 topics** and at least 4 different `##` sections. No two questions test the same fact.
- Never reuse a `[!CHECK]` question from the chapter verbatim; a variant is fine.

## 2. The 3 / 4 / 3 mix

10 questions: **3 easy, 4 medium, 3 hard**, ordered easy → hard. Grading weights them 1 / 2 / 3 points (max 20), so the level reflects depth, not just count.

| Level | What it tests | Time | Example (Hashing) |
|---|---|---|---|
| **Easy** | One fact or one step, straight from the text: a definition, a rule, a one-line computation | ≤ 45 s | load factor of 6 keys in 16 buckets |
| **Medium** | Two ideas, or 2–3 steps; applying a rule to a small new case; reading code the chapter explained | ~75 s | total keys moved by resizes for 12 inserts |
| **Hard** | Transfer: a situation the chapter didn't show verbatim, a trace through a mechanism, a "what breaks if…", a trade-off with numbers | 1.5–3 min | naive delete in linear probing, then `get` |

Hard means more reasoning, not longer wording or obscure facts. If a hard question can be answered by pattern-matching one sentence of the chapter, it's medium.

The level badge the learner sees: **Mastered** (≥ 85% weighted *and* at least 2 of 3 hard right), **Proficient** (≥ 65%), **Developing** (≥ 40%), **Needs review** (< 40%).

## 3. Every question

- **One defensible answer.** If an expert could argue for two options, rewrite it.
- **4 options**, similar length and form (all numbers, all complexities, all short clauses). Keep natural orders (O(1) < O(log n) < O(n)…) and balance answer positions across the quiz instead: no position correct more than 4 times in 10, at least 3 positions used.
- **`explanation`**: 1–3 sentences with the working or the reason: what a tutor would say, not a restatement of the answer.
- **`section`**: the `##` heading where the answer is taught (heading text or its start: `"Open addressing"` matches `## Open addressing: no lists at all`). It becomes the "Revisit" link.
- **`topic`**: a short syllabus-style name, shared across questions on the same idea ("Open addressing", "Resizing"). Topics drive the by-topic breakdown, so 3–5 topics per quiz.
- **Code** goes in `code` (plain newlines, no fences), in one of the course's languages. "What does this print?" and "which line is the bug?" are good medium/hard formats.
- Inline formatting in question, options, explanation and rationales: `` `code` ``, `**bold**`, `*em*`. No HTML.
- No "all/none of the above", no "which is NOT" unless the negation is bold (`**not**`), no trick wording.

## 4. Distractors and rationales

Distractors are where the diagnosis comes from. Each wrong option must be **the answer someone would reach through one specific mistake**:

- a formula inverted (m/n instead of n/m), an off-by-one, `>` vs `≥`, quotient vs remainder
- the average case where the worst case was asked
- what the *correct* version of the code would do, when the question shows a buggy one
- a true statement that answers a different question
- the misconception the chapter's `[!PITFALL]` warns about

Write a `rationales` entry for every option (`null` for the correct one): **why it's tempting and why it's wrong**, in one sentence. The page shows the rationale of the option the learner picked, and Claude's follow-up evaluation uses the picked options to name misconceptions precisely, so a rationale like "wrong" is useless; "That's m/n upside down: α is keys per bucket" is the point.

## 5. Per-course question patterns

**DSA**: trace an algorithm on a small input (state after k steps); complexity of a variant; which edge case breaks this code; pick the data structure for a requirement; invariant-based "why is this branch correct". Hard: a modified algorithm, an adversarial input, amortised reasoning.

**System Design**: back-of-envelope with real numbers (QPS, storage, bandwidth); which component fails/bottlenecks first under a scenario; pick the strategy for stated requirements (consistency vs latency); what a protocol message sequence guarantees. Hard: a failure scenario with two interacting components; quorum/replication arithmetic; choosing under conflicting requirements.

**JavaScript, Deeply**: predict the output (event loop order, closures in loops, `this`, hoisting/TDZ, coercion); which change fixes the bug; what the spec rule implies. Run every snippet in Node and copy the real output into the options.

**Low-Level Design**: which pattern fits a requirement; which class should own a responsibility; what a new requirement forces you to change in a given design; which SOLID principle a snippet violates; concurrency hazards in a method.

**Any other subject**: the same shape (recall → apply → transfer), with distractors from real mistakes in that field.

## 6. Final test

`final-quiz.json` at the course root, built only when **at least 2 chapters are written**. 10 questions, same 3 / 4 / 3 mix, every question has `"chapter": n` plus `section`. Spread across the written chapters roughly by their length/importance (at least 1 per chapter, at most 4 from one). Favour questions that **connect chapters** for the hard ones ("binary search on the answer with a hash set inside: total cost?"). Results group by chapter, so a weak chapter is obvious.

Rebuild and extend the final test whenever a new chapter is written.

## 7. Retests

After an evaluation (evaluation.md), a retest is a standalone page: `<course>/retests/<id>.json`, built with `lab.py quiz`. 10 questions, still 3 / 4 / 3, but **at least 7 on the learner's weak and misconception topics**, and 2–3 on strong topics to confirm they hold. New questions only: never repeat an item they saw; target the same misconception from a different angle.

## 8. Verify before building

- **Compute every numeric answer** in Python (or Node for JS), and compute each distractor's mistake too, so it's the number that mistake really gives.
- **Run every code snippet** and paste the true output.
- **Trace every algorithm question** with the chapter's own code (import it from the chapter's code blocks or the figure's `model.mjs`).
- Re-read each question as a learner who just finished the chapter: is the answer in the chapter, and is exactly one option right?
- `lab.py validate <quiz.json> --course-dir <course>` until it prints `ok` (no WARNs), then build.
