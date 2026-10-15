---
name: course-lab
description: Generate courses and chapters that test the learner. Every chapter ends with a 10-question MCQ quiz (3 easy, 4 medium, 3 hard), the course gets a final test, the page grades instantly with a level and topic-wise breakdown, and Claude evaluates pasted results and builds targeted retests. Built on course-studio (writing) and Anatomy (figures). Use when the user asks to generate a course or chapter with questions, a quiz, a test or assessment, "test me on this chapter", or pastes course-lab results to be evaluated.
---

# Course Lab

Course Lab = **course-studio** (writes the course and chapters, with Anatomy figures) **+ a quiz layer** that checks whether the learner can use what they read, and a loop that turns their mistakes into a targeted retest.

```
plan/write with course-studio ─▶ write quiz.json per chapter ─▶ lab.py build ─▶ learner takes the quiz in the page
                                                                                   │ instant grade: score, level, by difficulty,
                                                                                   │ by topic, misconceptions vs guesses, revisit links
                                                                                   ▼
                                   retest page ◀─ diagnosis in chat ◀─ "Copy results for Claude" pasted back
```

## Files

- `scripts/lab.py`: `build <course-dir>` (course-studio build + every quiz), `validate <quiz.json>`, `quiz <retest.json> <course-dir>` (standalone page).
- `scripts/check_lab.py <dist>`: course-studio's page check plus taking every quiz headless (all-right, all-wrong, mixed with guesses and a blank) and checking grading, links, report and retake.
- `assets/quiz.js`, `assets/quiz.css`: the in-page quiz and evaluator (styled with course-studio's tokens; light, dark, phone).
- `references/questions.md`: what to test, the 3/4/3 mix, distractors with rationales, per-course patterns, final test, retests, verification.
- `references/quiz-format.md`: the JSON format and commands.
- `references/evaluation.md`: reading pasted results, diagnosing (misconception / gap / shaky / slip), the reply, the retest loop.
- `examples/courses/dsa/chapters/05-hashing/quiz.json`: a finished quiz for course-studio's example Hashing chapter. Read it before writing your first quiz.

## Dependencies

This skill **uses course-studio for everything except the quizzes**: load it (`course-studio`) and follow it for planning, writing, figures and page builds; its own instructions load Anatomy for figures. `lab.py` finds course-studio automatically (`/mnt/skills/*/course-studio`, `.claude/skills/course-studio` in the project or home, a Claude Code plugin install, or `COURSE_STUDIO=<path>`) and stops with a clear error if it can't. Needs Python with markdown, pyyaml, pygments; playwright for the checks.

## Decide the scope

| The user asks | Do |
|---|---|
| "Generate a course on X" / "make the System Design course" | course-studio course plan (`course.json`, course page) → write the chapters (below) → each with its quiz → final test once ≥ 2 chapters are written. For one of course-studio's four preset courses (`dsa`, `system-design`, `javascript-deeply`, `low-level-design`), or any course over ~5 chapters, write chapter 1 (or the one they name) first and offer the rest; each chapter with its figure is real work. For a short new course (≤ 5 chapters) asked for "complete", write them all; build figures in parallel subagents when the Agent tool is available. |
| "Write chapter N" / "chapter on X" | course-studio chapter workflow → quiz for it → rebuild (and extend the final test if one exists). |
| "Add a quiz/test to chapter N" | Quiz for the existing chapter → `lab.py build`. |
| "Final test for the course" | `final-quiz.json` across written chapters → build. |
| Pasted "course-lab results …" or "evaluate me" | evaluation.md: diagnose → reply → retest page. |
| A standalone "test me on X" with no course | That's the `mcq-test` skill's job (timed exam pages), if it's available; use course-lab when the test belongs to a course. |

## Workflow: chapter + quiz (main path)

1. **Write the chapter with course-studio** (its chapter workflow, including the Anatomy figure and its checks). Do not start the quiz from the outline: the quiz tests the finished chapter.
2. **Plan the quiz** from the chapter's outcomes and sections: list 10 targets (which outcome, which section, which difficulty): 3 easy / 4 medium / 3 hard, ≥ 3 topics, ≥ 4 sections (questions.md §1–2). Hard questions are transfer: a case the chapter didn't show verbatim.
3. **Write `chapters/<nn-slug>/quiz.json`** (quiz-format.md). Every wrong option is a specific mistake and gets a rationale; every question gets an explanation and its `section`.
4. **Verify** (questions.md §8): compute every number and every distractor's mistake, run every snippet, trace algorithms with the chapter's own code or the figure's `model.mjs`. Then `lab.py validate … --course-dir …` until it prints `ok` with no WARNs.
5. **Build** with `lab.py build <course-dir>` (never course-studio's build alone after this: it would drop the quizzes). Add `--catalog` when the course list changed.
6. **Check** with `check_lab.py <course-dir>/dist --all` (desktop, then phone + dark; pass one page instead of `dist` to check just it). It takes the quizzes several times in a headless browser, so allow a few minutes. Fix every PROBLEM (pending Anatomy figures are reported separately and are fine only if you're deliberately leaving them). Open `shots/quiz-*-result.png` and read it as the learner: are the revisit links the right sections, do the explanations teach?
7. **Final test**: when the course has ≥ 2 written chapters, write or extend `final-quiz.json` (questions.md §6) and rebuild.
8. **Deliver** as course-studio does (artifact in claude.ai: the chapter page is self-contained, quiz included; or the files in their project). End with one line: what was made, the quiz mix, and that learners can paste their results back for an evaluation and retest.

**Never print questions or answers in chat**: the quiz lives in the page. If the user explicitly asks to review the questions as the author, show them from `quiz.json`.

## Workflow: evaluating results

Follow evaluation.md: find the quiz source by its id, classify every miss (misconception / gap / shaky / slip), reply in ≤ ~250 words with the fix-first misconceptions, sections to re-read and concrete practice, then build a 10-question retest weighted to the weak topics with `lab.py quiz` and deliver it. On a repeat attempt, compare with the previous report and change the explanation angle for anything still wrong.

## Quality bar

- Answerable from the chapter, exactly one right answer, verified by running it.
- The mix is real: easy is one step, hard is transfer, not longer wording.
- Every distractor is a named mistake with a rationale, so the evaluation can say *what* the learner believes, not just that they're wrong.
- Grading, links and the copy-for-Claude report pass `check_lab.py` on desktop, phone and dark.
