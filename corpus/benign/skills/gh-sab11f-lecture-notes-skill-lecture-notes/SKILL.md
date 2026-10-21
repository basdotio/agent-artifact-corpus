---
name: lecture-notes
description: Turn lecture slides (PDF, PPTX export, Beamer, scanned handouts) into a print-ready, designed PDF workbook — explained notes, exact definitions, diagrams, and every exercise with a workspace plus a worked solution. Use this whenever a student shares slides, a lecture PDF, "prosojnice", a chapter from a course, or asks for study notes, zapiski, an exercise book, a summary to print, or "make this easier to learn from" — even if they don't say "notes". Also use when they ask to add a lecture to an existing course workbook.
---

# Lecture notes → print-ready workbook

Slides are a speaking aid, not a text: they list bullets, skip the "why", repeat each slide 3–5 times for overlays, and leave exercises unsolved because the lecturer solves them on the board. This skill rebuilds one lecture into a document a student can learn from alone and print, with one fixed look across every course. The output is a PDF built from HTML/CSS (`theme/theme.css`), never a Word file — Word cannot do colored callouts, SVG diagrams and clean page breaks.

Work one lecture (one PDF) per run. Feeding a whole semester at once produces shallow notes; the student can run the skill again for each chapter and the numbering/cover keep them consistent.

## Workflow

### 0. Setup (first run in an environment)

```bash
bash <skill>/scripts/setup.sh      # pdftotext, markdown-it-py, playwright+chromium, KaTeX
```

`<skill>` is the folder containing this file. If the skill was saved to Claude without its files (only `SKILL.md`), fetch them first:

```bash
git clone --depth 1 https://github.com/SaB11F/lecture-notes-skill /tmp/lns && export SKILL=/tmp/lns/skills/lecture-notes
```

### 1. Extract the slides

```bash
python3 <skill>/scripts/extract.py slides.pdf work/slides.txt
```

It strips footers repeated on every page and collapses overlay pages (a page whose text is a prefix of the next). Typical result: 176 pages → 58 real slides. Read `work/slides.txt` **in full** before writing anything; it is usually 3–6k words. If it comes back nearly empty, the PDF is scanned — run OCR (`ocrmypdf` or `tesseract`) first, or read the pages as images with the Read tool.

Also look at a few slides as images when they contain figures, plots or hand-drawn diagrams that text extraction loses; decide which ones need to be redrawn as diagrams.

### 2. Plan the structure

List the slide section titles (they repeat across overlay pages — dedupe). Group them into 6–12 numbered sections (`#`) with subsections (`##`) for distinct concepts. Keep the lecturer's order and terminology — the student will be examined on the lecturer's words, not yours.

Then list **every exercise** on the slides: anything introduced with "Example:", "Exercise:", "Zgled:", "Naloga:", "Show that…", "Prove…", "Solve…", "izpeljite doma", or a question without an answer. Each becomes a `task` box. Keep this list; step 5 checks it.

Then ask the student one question, showing the planned section list: **which sections are new to them**. New sections get more depth (extra idea boxes, a second example, 1–2 extra tasks); familiar sections get the slides' content and exercises only. Default language = the language of the slides; ask only if the slides mix languages.

**Video boxes are for mathematics only, from one source only:** if the lecture is a mathematics course, look up Andrej P. Škraba's videos (catalog `astra.si`) per section as described in `references/video-sources.md` and add a `video` box where there is a match. Any other subject gets no video boxes, and no other channel is used — don't ask the student for one.

### 3. Write `content.md`

Read `references/content-format.md` (the markdown dialect: boxes, math, diagrams, frontmatter) and `references/writing-rules.md` (what good notes contain) before writing. Author in the language of the slides.

Frontmatter minimum:

```yaml
---
course: Matematika 1
chapter: 1
title: Logika in množice
institution: FIŠ Novo mesto
source: Slides by J. Povh / K. Bešter Štorgel, 2026
lang: sl            # sl | en | de | hr | it  → box labels, "work space", "Solutions"
accent: "#1d5c8a"   # one accent colour per course, keep it across chapters
solutions: inline   # inline (under each task) | end (appendix)
videos: astra.si    # mathematics lectures only; omit for other subjects
---
```

Per concept, the skeleton is: short **idea** box (why this exists, in plain words) → exact **def** / **thm** boxes (verbatim from the slides, boxed and auto-numbered) → an **ex** (worked example from the slides) → a diagram or table where the concept has structure → a **warn** box for the pitfall students actually make. Exercises are `task` → `@@space N` → `sol`. In a mathematics lecture, a section with matching Škraba videos ends with a `video` box (`references/video-sources.md`).

### 4. Build

```bash
python3 <skill>/scripts/build.py work/content.md out/<course>_<chapter>_<title>.pdf
```

Produces `.html` (open it to debug) and the PDF: A4 cover with table of contents, numbered sections, footer with course and page number, 22 mm inner margin for binding (`binding: none` for symmetric margins).

### 5. Verify before delivering

```bash
python3 <skill>/scripts/render_check.py out/<file>.pdf     # contact sheets, 6 pages each
```

Look at every sheet. Check: no raw `$…$` or `:::` text (a box or formula did not parse — usually a missing blank line before `$$` or a diagram line that swallowed the next line); diagrams readable and not overlapping their labels; no task separated from its workspace; tables not cut mid-row. Then grep the HTML for `math-error` and `[diagram` and fix every hit.

Cross-check the exercise list from step 2 against the `task` boxes — every exercise on the slides must have a task **and** a solution. Spot-check three definitions against `slides.txt` word for word.

Deliver the PDF. If a folder is connected, write it beside the slides. Tell the student in two lines what was added beyond the slides (solved exercises, flagged slide errors), and ask nothing else.

## Rules that matter most

- **Definitions and theorems verbatim.** Rephrase the explanation around them, never the statement itself. The exam uses the lecturer's wording.
- **Solve every exercise.** The slides' open exercises are the highest-value content; a note without the solutions is just a nicer slide deck. Show the method, not only the answer, and name the rule used at each step.
- **Explain the why.** Each concept gets at least one sentence the slides do not have: motivation, intuition, or the mistake the concept prevents.
- **Flag, don't silently fix.** A wrong date, a typo in a formula, a missing case on the slides goes into a `warn` box titled "Napaka na prosojnicah" / "Error on the slides" with the correction. The student needs to know the slide is wrong, not just see a different value.
- **Diagrams where there is structure**, not decoration: operations → Venn, orderings → ladder, numeric sets → number line, hierarchies → tree/nested, processes → flow, chronology → timeline, induction → dominoes, dependency between quantifiers → depend. One diagram per concept at most. Catalog in `references/diagram-catalog.md`; for shapes the catalog lacks, write inline SVG in the same palette (stroke 1.5, Inter labels, accent colour).
- **Workspace size by effort:** 2.5–3 cm for a one-line answer, 4–5 cm for a short derivation or table, 6–7 cm for a proof, induction, case analysis or anything with a truth table.
- **Do not add** flashcards, quizzes, learning objectives, motivational text or emoji. The student asked for notes, not a course platform.

## Files

- `scripts/extract.py` — PDF → deduplicated slide text
- `scripts/build.py` — content.md → HTML → PDF (KaTeX math, Chromium print)
- `scripts/diagrams.py` — the `@@` diagram catalog (parametric SVG)
- `scripts/render_check.py` — contact sheets for visual QA
- `scripts/setup.sh` — dependencies
- `theme/theme.css` — the design; change colours/fonts here only
- `references/content-format.md` — markdown dialect reference
- `references/writing-rules.md` — pedagogy and quality bar, with before/after examples
- `references/diagram-catalog.md` — every diagram with its syntax
- `references/video-sources.md` — mathematics only: how to find Andrej P. Škraba's videos per section via astra.si; how familiarity sets depth
- `examples/content.md` + `examples/output.pdf` — a complete real lecture (Matematika 1, Logika in množice, 176 slides → 33-page workbook; the source slides are not included); copy its structure for the first run on a new course
