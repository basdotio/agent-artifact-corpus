---
name: teach-it
description: Teaches a new topic in theory only — no coding projects. Builds an essentials guide split into parts, each with interactive figures, diagrams, charts, examples from real applications and a self-check quiz, plus an interactive lab page (a local HTML file) and a PROGRESS.md to resume from. Works step by step with the user, or builds everything at once.
argument-hint: <topic>  (or no argument to resume the topic in the current folder)
disable-model-invocation: true
---

# Teach It

The user wants to *understand* the topic: the intuition, how it works, where it is
used in the real world and when it isn't the right tool. **No coding projects.**
Instead of building things, they learn by seeing and playing: diagrams, charts,
interactive figures and real case studies.

## Quick start

`/teach-it transformers` → show the outline (4–6 parts), then the settings
(mode, folder, level, depth, quizzes) → write Part 1 of
`TRANSFORMERS_ESSENTIALS.md` and its lab figures → stop → Part 2 … → final review.
`/teach-it` with no topic, inside a topic folder → resume from `PROGRESS.md`.

## How to work with this user

- **Plan first.** Show the outline and settings before writing any file.
- **Follow the mode** they chose (see Modes below).
- **Ask in conversation, never with a question form** (no AskUserQuestion). Put
  numbered options in your message; they reply casually and may decide later.
- **Open requests = your judgment.** You pick what is worth visualizing.
- **Show, don't just tell.** Every key concept gets at least one visual: a diagram,
  a chart, or an interactive figure.
- **A few real cases, done well.** 2–3 real case studies, from sources you read
  in full; never make up numbers or results. Everywhere else, teach with simple
  illustrative examples, clearly framed as such ("imagine a shop that…").
- **Honest scope.** Every topic gets a "when NOT to use it" part.

## Modes

- **Step by step (default).** You build one part, then stop. Say what you covered
  and why, point to the lab figures to try, and wait. They read it, answer the
  quiz, ask questions, ask to zoom in or change the next part; only then move on.
- **All at once.** You build every part, the lab and the final review in one go,
  then give a short tour: what each part covers, the best lab figures to start
  with, and which parts to read first. Then help them through it in chat.

They can switch modes at any time ("just finish the rest", "let's slow down").

## Where things go

Ask in the kickoff, with the current folder as the default:

1. **Here** — `./<topic_slug>/` in the folder they called the skill from (if that
   folder is already named `<topic_slug>`, use it directly).
2. **`~/learning/<topic_slug>/`** — the shared learning folder.
3. **Both** — files live here, and `~/learning/<topic_slug>` is a symlink to them,
   so `~/learning/` stays an index of everything they're learning.

```
<topic folder>/                   # <topic_slug>: lowercase, underscores
├── PROGRESS.md                   # see reference/progress.md
├── <TOPIC>_ESSENTIALS.md         # the guide, in parts (links to the lab)
└── <TOPIC>_ESSENTIALS_LAB.html   # the lab: a local HTML file
```

The folder and guide format match `teach-it-with-projects`, so the user can add
projects to the same topic later.

## Workflow

```
- [ ] 0. Start or resume
- [ ] 1. Kickoff: outline, then settings
- [ ] 2. Parts 1…N: guide section + lab figures + real examples + quiz
- [ ] 3. Final review
```

The user can reorder, skip or zoom into parts — follow them. Update `PROGRESS.md`
at the end of every part.

**0. Start or resume.** Look for `PROGRESS.md` in the current folder,
`./<topic_slug>/` and `~/learning/<topic_slug>/`. If found, read it, summarize
where they are in 3–5 lines, propose the next part, and stop.

**1. Kickoff (one message).** First the outline from
[reference/guide.md](reference/guide.md): 4–6 parts, each with its sections, the
figures you plan, and the real applications you plan to use. Then, at the end,
the settings with defaults filled in, as a numbered list they can correct:

```
Settings (correct anything)

1. Mode: step by step — I build one part, then stop so you can read it, use the
   lab and ask questions. Or: all at once — I build everything, then walk you
   through it.
2. Folder: here (./<topic_slug>/). Or: ~/learning/<topic_slug>/, or both.
3. Level: beginner
4. Depth: intuition, plus the key math explained in words. Or: intuition only,
   or full math.
5. Quizzes: on
```

Stop. Create the folder once they confirm.

**2. Each part.** Write the part's guide sections per
[reference/guide.md](reference/guide.md), add its figures to the lab per
[reference/lab-page.md](reference/lab-page.md), and end with a quiz per
[reference/quiz.md](reference/quiz.md). In step-by-step mode, stop after each part.

**3. Final review.** A one-page summary at the end of the guide (the 10 ideas worth
remembering, a concept map diagram), a cumulative quiz, and "where to go next"
(books, courses, papers — and `/teach-it-with-projects` if they want to build).
