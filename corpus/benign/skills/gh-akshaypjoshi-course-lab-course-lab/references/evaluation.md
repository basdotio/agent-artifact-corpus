# Evaluating a learner

The page grades instantly. This file is for the second step: the learner presses **Copy results for Claude** and pastes the report into the chat. Your job is a short, precise diagnosis and a plan, then a retest.

Contents: 1. Reading the report · 2. Diagnosis · 3. The reply · 4. The retest · 5. Progress over attempts

---

## 1. Reading the report

The pasted text looks like:

```
course-lab results
Quiz: Hashing, chapter test [dsa-05-hashing] · Data Structures & Algorithms
Score: 4/10 · weighted 6/20 (30%) · level: Needs review
Difficulty: easy 2/3, medium 2/4, hard 0/3
Answers:
Q1 [easy · Load factor & resizing] picked C: correct (guessed)
Q2 [easy · Hash functions] blank: wrong, answer B
Q6 [medium · Pitfalls] picked A: wrong, answer B (was sure)
…
```

Find the quiz source from the id: `<course>/chapters/<dir>/quiz.json` (id `<slug>-<dir>`), `<course>/final-quiz.json` (id `<slug>-final`) or `<course>/retests/<id>.json`. Read it: for every answer line you need the question, the option they picked, and that option's **rationale**: that's what turns "Q6 wrong" into a named misconception. If the source isn't available (a different session, no workspace), work from the report alone and say the diagnosis is coarser.

## 2. Diagnosis

Sort every miss into one of four kinds; they need different fixes:

| Kind | Signal | What it means | Fix |
|---|---|---|---|
| **Misconception** | wrong and *was sure* | A wrong rule they believe. Most important. | Name the wrong rule (from the picked option's rationale), state the right one, show the smallest example where they differ. |
| **Gap** | wrong and guessed, or blank | They don't know it yet. | Point to the exact section; one-sentence summary of what's there. |
| **Shaky** | right but guessed | Knowledge they can't rely on. | Include in the retest. |
| **Slip** | easy wrong while harder questions on the same topic are right | Carelessness, not knowledge. | Mention once; no revision needed. |

If the picked option's rationale doesn't explain the pick (no rationale, or the learner's number matches no listed mistake), don't invent a misconception: say plainly that the answer doesn't match a known mistake, and prescribe a trace of that exact question with the chapter's code. Then fix the quiz's rationale for the next learner.

Then look across questions:
- **Pattern**: the same misconception behind several misses (e.g. treating average-case as guaranteed in Q3 and Q9). One root cause, one fix.
- **Difficulty profile**: easy/medium solid but hard 0/3 → knows rules, can't apply them yet (prescribe tracing practice); easy misses with hard hits → slips or a skipped section.
- **Topic profile**: weak topics map to sections; that's the revision list.

Be accurate and kind: never inflate the level, never pile on. One sentence on what's genuinely solid, then the work.

## 3. The reply

Keep it scannable, because the learner is going to act on it:

1. **Verdict** in one line: level, weighted score, and the honest headline ("You know the definitions; applying them to probing is where it breaks.").
2. **Fix first, misconceptions**: one short block each: *You believed X (Q6). Actually Y. Smallest example: … Re-read §N.*
3. **Then, gaps**: a bullet per section to re-read, with what to look for there. Link to the chapter page section when you built it (`dist/05-hashing.html#open-addressing-no-lists-at-all`).
4. **Practice**: 1–3 concrete exercises (trace this input, write this function, compute this number) aimed at the hard misses. Not "practise more".
5. **Retest**: build it (§4) and give it as the last line.

About 250–300 words before the retest line (links don't count). Merge misconceptions that share a root cause into one block. Don't reprint the quiz or every answer.

**Practice must not preview the retest**: exercises rehearse the skill, not the retest's items or numbers.

**Links**: in claude.ai, link sections on the published chapter artifact (`<artifact url>#<section-id>`); in a project, give the path to the built page (`courses/dsa/dist/05-hashing.html#open-addressing-no-lists-at-all`).

If they scored **Mastered**: say so in one line, name anything they guessed, and point to the next chapter (or the final test when it exists). A retest isn't needed unless they ask.

## 4. The retest

1. Write `<course>/retests/<quiz-id>-retest-<k>.json` (k = 1, 2, …); format in quiz-format.md, rules in questions.md §7: 10 new questions, 3 / 4 / 3, ≥ 7 on misconceptions, gaps and shaky topics, 2–3 confirming strong topics. Each question has `chapter` (or a top-level `chapter`) and `section`.
2. Verify answers (questions.md §8), then `python3 scripts/lab.py quiz <retest.json> <course-dir>` → `dist/<id>.html`.
3. `python3 scripts/check_lab.py <course-dir>/dist` must pass.
4. Deliver the page the same way as the course (artifact in claude.ai, or the file path in their project).

## 5. Progress over attempts

The page keeps the last 10 attempts per quiz in the learner's browser and shows them under the result. When a learner pastes a second report for the same quiz or a retest of it, compare: what moved from misconception to correct, what's still wrong. A topic that's wrong twice gets a different explanation angle the second time (an analogy, a worked trace, the figure's tour beat), not the same words louder.

When the course owner wants results tracked across learners, that's a platform feature: the report format is stable and line-based, so the platform can store it as-is and parse `Q<n> [difficulty · topic] picked X: correct|wrong` lines.
