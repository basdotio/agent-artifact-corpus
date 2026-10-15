# Quiz files

Three kinds, one format. All are JSON (double quotes, no trailing commas; the `//` comments below are explanations only; real files have none).

| File | Scope | Where it appears | Questions need |
|---|---|---|---|
| `chapters/<nn-slug>/quiz.json` | one chapter | end of that chapter page, as the last numbered section "Test yourself" (+ a contents entry) | `section` |
| `final-quiz.json` (course root) | whole course | end of the course page, "Final test" | `chapter` + `section` |
| `retests/<id>.json` | any | its own page `dist/<id>.html` | `chapter` (per question or top-level) + `section` |

```json
{
  "title": "Hashing, chapter test",          // shown in reports; required
  "id": "dsa-05-hashing",                     // optional; default <slug>-<chapter dir>, <slug>-final, or the file name
  "heading": "Test yourself",                 // optional section heading
  "intro": "Ten questions, easy to hard. Tick **I'm guessing** when you are.",   // optional, inline markdown
  "chapter": 5,                               // retests only: default chapter for every question
  "mix": {"easy": 3, "medium": 4, "hard": 3}, // optional; the standard mix, change only if the user asks
  "questions": [
    {
      "difficulty": "hard",                   // easy | medium | hard
      "topic": "Open addressing",             // groups the breakdown (3–5 topics per quiz)
      "chapter": 5,                           // final test / retests
      "section": "Open addressing",           // a ## heading's text, its start, or its id → "Revisit" link
      "question": "Linear probing, m = 8 … What does `get(19)` do?",
      "code": "optional\nplain text code block",
      "options": ["…", "…", "…", "…"],
      "answer": 3,                            // 0-based index
      "explanation": "1–3 sentences with the working.",
      "rationales": ["why A is tempting and wrong", "…", "…", null]   // null for the correct option
    }
  ]
}
```

Commands (from the skill's `scripts/`):

```bash
python3 lab.py validate courses/dsa/chapters/05-hashing/quiz.json --course-dir courses/dsa   # before building
python3 lab.py build courses/dsa [--catalog]      # course-studio build + all quizzes
python3 lab.py quiz courses/dsa/retests/dsa-05-hashing-retest-1.json courses/dsa
python3 check_lab.py courses/dsa/dist [--mobile] [--dark]
```

Revisit links: in a chapter quiz they point at `#section` on the same page; in the final test and retests they point at `<nn-slug>.html#section` and the label gets "(Ch nn)". Retest pages are written into the same `dist/` folder as the chapters, so those links work.

`lab.py build` always rebuilds the pages through course-studio first, so quizzes are never injected twice. Don't run course-studio's `build_course.py` directly afterwards: it would rebuild the pages without their quizzes; run `lab.py build` again instead.

In the page the quiz payload is base64 JSON (answers aren't readable at a glance, which is enough for self-study, not for exams). For a platform that needs real secrecy, keep `quiz.json` server-side and grade on the server using the same rules (weights 1/2/3, level thresholds in questions.md §2).
