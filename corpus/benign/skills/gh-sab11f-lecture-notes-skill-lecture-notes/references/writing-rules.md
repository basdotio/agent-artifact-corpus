# Writing rules — what separates notes from reformatted slides

The student will read these notes alone, without the lecturer talking, often the night before an exam. Everything the lecturer *said* but did not *write* has to be reconstructed. The slides give the skeleton; the notes add the muscle.

## 1. Per concept: idea → definition → example → structure → pitfall

**Idea first.** One to three sentences in plain words: why does this concept exist, what problem does it solve, how to think about it. This is the part slides never have.

> Slides: "Implikacija. Izraža se v obliki 'Če A, potem B.' Oznaka: A ⇒ B."
> Notes, idea box: "Implikacija je obljuba. Prelomljena je samo, če pogoj velja in posledica ne. Če pogoj ne velja, obljuba ni bila preizkušena — zato velja."

**Definition verbatim.** Copy the lecturer's wording into a `def` box. Fix only obvious typos, and flag anything that looks wrong in a `warn` box rather than silently correcting it. Bold the term once.

**Example.** If the slides have one, keep it (as `ex`). If the slide's example is thin, add a second one, clearly yours.

**Structure.** If the concept has structure — cases, an ordering, nesting, a mapping — draw it. A truth table is a diagram. A one-dimensional set is a number line. A hierarchy is a tree. Don't draw what has no structure (a plain definition does not need a picture).

**Pitfall.** What do students get wrong here? Negating "all" into "none"; thinking 0 ⇒ anything is false; confusing sup with max; believing 0,999… < 1. One `warn` box per real pitfall. Skip it where there is none.

## 2. Exercises are the product

Every exercise on the slides gets a `task` box, a workspace and a `sol` box. In the solution:

- Restate the method in one sentence before the computation ("Prevedemo v logični izraz, vstavimo vrednosti, ovrednotimo po prednosti.").
- Show each step, and name the rule it uses when a rule exists (identity, theorem number, definition).
- End with the answer in bold and, where useful, one sentence of interpretation.
- For "prove that" tasks, a complete proof with a visible structure: baza/korak, assumption/contradiction, both inclusions.
- For "think about whether" tasks, decide, then give a concrete counterexample or argument.

If the slides mark something as homework ("izpeljite doma", "for next time"), it is still a task — solve it; the student checks their own attempt against it.

## 3. Gap-filling

Slides skip steps that the lecturer fills in orally. Fill them in writing — intermediate algebra, why a case split is needed, what a symbol is read as. When you add knowledge that is not on the slides (a standard textbook fact), say so briefly ("Standardni rezultat, ni na prosojnicah:") so the student knows what is examinable from the slides and what is context.

Do not expand into a textbook. The notes should be 2–4× the word count of the deduplicated slides, not 10×. Depth goes into the exercises and the "why", not into extra topics.

## 4. Language and tone

- Write in the language of the slides. Keep the lecturer's terminology, including Slovenian/German/… technical terms exactly as used; put a foreign-language synonym in parentheses only if the slides do.
- Direct, plain sentences. No "In this section we will…". No emoji. No motivational filler.
- Second person plural/formal as the slides use it (Slovenian: "zapišite", "pokažite").
- Numbers, symbols and notation exactly as on the slides (⇒ not →, ⊆ vs ⊂ as the lecturer uses it).

## 5. Length and page economy

Target: a 60-slide lecture → 20–30 A4 pages with workspaces, 15–20 without. Every section needs enough on the page that a student is not flipping constantly: keep a definition, its table and its example within one or two pages.

## 6. What not to do

- No flashcards, quizzes, learning objectives, "key takeaways" lists, or summary at the start. One summary table at the end is enough.
- No decorative diagrams. If the diagram does not show a mechanism, delete it.
- No invented numbering that differs from the lecturer's (if the slides number theorems, keep their numbers in the box title).
- Don't drop content because it looks like filler on the slides (history, names, dates). It is exam material somewhere; compress it into an `idea` box.

## Checklist before building

- [ ] Every slide section appears in the notes, in the lecturer's order
- [ ] Every definition/theorem is boxed and verbatim
- [ ] Every exercise on the slides is a task with a solution
- [ ] Each section has at least one idea box and the real pitfalls have warn boxes
- [ ] Diagrams only where structure exists; labels not overlapping
- [ ] Slide errors flagged, not silently changed
- [ ] Summary table at the end covers every section
