# NOTICE — teach

This `teach` skill is a **fork** of Matt Pocock's `teach` skill, extended with a visual +
interactive lesson design system. The pedagogy, workspace model, and `*-FORMAT.md` files are
Pocock's, kept faithfully; the design layer (`references/HTML-LESSON.md`,
`VISUAL-TREATMENT-MAP.md`, `INTERACTION-MENU.md`, `assets/lesson-kit.*`, the golden example, and
the validator) is added on top.

| Source | License | What was drawn from it |
| --- | --- | --- |
| [Matt Pocock — `skills/productivity/teach`](https://github.com/mattpocock/skills/tree/main/skills/productivity/teach) | MIT (© 2026 Matt Pocock) | The whole pedagogy and workspace: mission-grounding, knowledge/skills/wisdom, fluency-vs-storage-strength, ZPD, the learning-record / glossary / resources formats, the self-contained-HTML-lesson output contract, and the "Think Tufte / reuse-first `./assets/`" stance. The four `*-FORMAT.md` files are copied verbatim. |
| `frontend-craft`, `emil-design-eng`, `design-motion-principles`, `design-taste-frontend` (this repo) | MIT | Distilled into `references/HTML-LESSON.md`: the OKLCH tinted-neutral token system, reading-typography scale + 65ch measure, WCAG floor + `:focus-visible`, CSS-only motion recipes + reduced-motion, and the anti-slop "tells". Not invoked at generation time — distilled once into a compact contract. |
| `schritte-html-tutor` (personal German-lessons skill) | — | Architecture inspiration: token-driven self-contained HTML, the visual-treatment decision map, the retrieval-first interaction menu with a `data-*` contract, and the progressive-enhancement / print discipline. Colours and language-specific machinery were **not** copied — only the generalizable approach. |
| [open-spaced-repetition — FSRS](https://github.com/open-spaced-repetition/fsrs4anki) | MIT | `assets/fsrs-scheduler.js` uses the FSRS-6 scheduling algorithm shape and published default parameters for the optional spaced-repetition module. |
| Learning science — Mayer (multimedia learning), Paivio (dual coding), Karpicke & Roediger (retrieval practice), Sweller (cognitive load), Bjork (desirable difficulty) | — | The evidence grounding the design choices (pair words with visuals; make recall the default; fade worked examples; ban seductive details). |

Offered under the MIT License. Upstream projects remain under their own licenses above.
