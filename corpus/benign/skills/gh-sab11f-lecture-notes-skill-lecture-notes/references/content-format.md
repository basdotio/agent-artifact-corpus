# content.md format

CommonMark + tables + `$math$` + fenced boxes + `@@diagram` lines. `scripts/build.py` turns it into the PDF.

## Frontmatter

```yaml
---
course: Matematika 1          # footer + cover
chapter: 1                    # big number on the cover; "" for none
title: Logika in množice
institution: FIŠ Novo mesto   # cover, small
source: Prosojnice J. Povh    # cover, small – credit the lecturer
lang: sl                      # sl | en | de | hr | it  (box labels, workspace label, "Solutions")
labels: task=Vaja;sol=Odgovor # optional per-label override
accent: "#1d5c8a"             # course colour: headings, def boxes, diagrams
solutions: inline             # inline | end  (end = all solutions in an appendix)
videos: astra.si              # optional, documents which catalog the video boxes come from
binding: left                 # left (22 mm inner margin) | none (symmetric)
paper: A4                     # A4 | Letter
---
```

## Headings

`#` = numbered section (1, 2, …), `##` = subsection (1.1, 1.2). Both go to the table of contents on the cover. Don't use `###` for structure the TOC should show.

## Boxes

```
::: def Naslov
Exact definition text. Auto-numbered "Definicija 1".
:::
```

| Fence | Label (sl/en) | Use for | Numbered |
|---|---|---|---|
| `::: def` | Definicija / Definition | definitions, notation — verbatim from slides | yes |
| `::: thm` | Izrek / Theorem | theorems, rules, identity tables, laws | yes |
| `::: ex` | Zgled / Example | worked examples **the slides already solve** | yes |
| `::: task` | Naloga / Exercise | an exercise the student should attempt | yes |
| `::: sol` | Rešitev / Solution | the solution for the task directly above | no |
| `::: idea` | Ideja / Idea | the "why", intuition, how to think about it | no |
| `::: warn` | Pozor / Watch out | pitfalls, common mistakes, slide errors | no |
| `::: proof` | Dokaz / Proof | a longer proof standing on its own | no |
| `::: summary` | Povzetek / Summary | end-of-chapter table | no |
| `::: video` | Video razlage / Video explanations | list of the student's teacher's videos for this section: `- Title — \`youtu.be/id\` (m:ss)` | no |

The title after the fence name is optional and may contain `$math$`. Boxes cannot nest. A box never splits across pages, so keep a single box under about two thirds of a page; split long ones.

## Exercises (workbook pattern)

```
::: task Obljuba očeta Andreja
Oče reče: »Če Blaž naredi maturo, mu kupim avto.« Kdaj oče laže?
:::
@@space 4.5
::: sol
| Matura | Avto | A ⇒ B | … |
…
**Ključno:** …
:::
```

`task` + `@@space` are kept together on a page; `sol` may flow to the next page. With `solutions: end` the `sol` boxes are moved to an appendix titled "Rešitve nalog" and labelled by task number.

## Math

Inline `$a^2 + b^2$`, display `$$ … $$` on its own line (the builder inserts blank lines around `$$` automatically). KaTeX syntax; `\begin{aligned}…\end{aligned}` for multi-line derivations with `&&\text{(reason)}` comments; `\underbrace{x}_{1}` for annotated evaluation; `\blacksquare` to end proofs. Decimal comma in Slovenian: `0{,}999`.

## Tables

GitHub-style pipe tables. Inside `def`/`thm` boxes they get a light background. Use them for comparisons, rule lists, truth tables that the `@@truth` diagram cannot express (extra columns), and result tables in solutions.

## Diagrams

A line starting with `@@name` followed by `|`-separated fields and `key=value` options. See `diagram-catalog.md`. `@@space N` is the workspace (N in cm). The line must be alone on its line; put a blank line before the next fence.

## Markdown gotchas

- Lines inside a box that should be separate lines need a blank line between them (soft breaks are merged into one paragraph).
- Bold the term being defined once, inside the def box.
- Quotation marks: use the language's typographic quotes (»…« in Slovenian).
- No HTML needed, but raw HTML is allowed for one-off layouts.
