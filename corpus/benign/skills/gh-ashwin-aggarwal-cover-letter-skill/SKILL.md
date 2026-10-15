---
name: cover-letter-builder
description: Builds cover letters as ATS-parsable LaTeX source for Overleaf, from a pasted job description, the candidate's stored experience, a fixed template, and a strict anti-cliché style guide. Use this whenever the user pastes a job description, asks for a cover letter, or mentions applying to a specific role at a company, even if they don't say "cover letter".
---

# Cover Letter Builder

Produces one cover letter per run as complete .tex source to paste into Overleaf (compiler: XeLaTeX). Read these files before drafting:

- `assets/template.tex`: the fixed template. Edit ONLY the values in its SKILL-EDITABLE REGION. Never touch the USER CONFIG region.
- `references/context.md`: routing matrix, archetype voice, and experience entries. The only permitted source of facts about the candidate.
- `references/style.md`: banned phrasing and voice rules. Applies to every sentence you write.

## Step 0: Setup check

- If `references/context.md` is missing, stop. Tell the user to copy `references/context.example.md` to `references/context.md` and fill it in.
- If `assets/template.tex` is missing, stop. Tell the user to copy `assets/template.example.tex` to `assets/template.tex` and fill in the USER CONFIG region.
- Lines marked [FILL] or [CONFIRM] in context.md are unknown. Never use them.

## Step 1: Inputs

Draft immediately from whatever is provided. Do not ask clarifying questions first.

| Input | If missing |
|---|---|
| Job description | The one input worth stopping for. Ask for it. |
| Role name | Take it from the job description. |
| Company name | Take it from the job description. |
| Date | Today's date, formatted "Month D, YYYY". |
| Role archetype (as defined in context.md) | Infer from the job description and state the inference in one line. |
| Recipient name, address | Leave the values empty. The template handles it. |
| Company fact | Research it in Step 2. |

## Step 2: Company research

If the user gave a company fact, use it. Otherwise search the web for one concrete, recent item (roughly the last 12 months): a product launch, an engineering blog post, a paper, an open-source release. Prefer items connected to the role's team or stack.

Also note the company's domain (healthcare, fintech, devtools, defense, consumer, etc.) and what this team builds. Step 3 uses both.

If nothing concrete turns up, the hook is empty. Never invent or generalize a company fact.

## Step 3: Parse and score

1. Extract the hard requirements from the job description: 5 or 6 normally, 7 for archetypes whose evidence pool in the routing matrix has 4 or fewer entries. Rank by prominence: in the title, repeated, listed first, "required" over "preferred". Ignore culture, benefits, and EEO boilerplate.
2. Filter context.md entries to those checked for the archetype in the routing matrix. Unchecked entries are ineligible even when keywords match.
3. Score each eligible entry 0 to 3 on each of: requirement overlap (weighted toward top-ranked requirements), company domain fit, and stack overlap. Sum the three.
4. Take the top two. On a tie, prefer the entry with a real metric.

Before the code block, show a short scoring summary: each chosen entry, its score, and a one-phrase reason. A few lines, so the user can override the picks.

Situational mentions are never scored and never count as one of the two evidence entries.

## Step 4: Draft

Paragraph map. The template's fixed `\OPENER` comes first, then four editable values:

- `\HOOK`: one sentence following the opener. Connects the company item from Step 2 to work the candidate has done or would do in the role. Not praise. Empty if Step 2 found nothing.
- `\EVIDENCEONE`: top-scored entry. What was built, the named stack, the outcome. Use that entry's framing line for the archetype. Connect it to the top requirement by naming the substance of the requirement, never with filler like "this aligns with".
- `\EVIDENCETWO`: second entry, same pattern. Ends with one sentence tied to this team or role specifically: its customers, data scale, product, or a technology named in the posting.
- `\CLOSING`: one or two sentences, specific to the team or product. One short thank-you is allowed.

Hard rules:
- Facts about the candidate come only from context.md. Never invent a project, metric, technology, title, or outcome.
- Use a metric only if the entry lists it. Entries marked "no metric" get none.
- Work listed as planned or in progress is never described as done.
- Anything under "Never mention" in context.md stays out.
- Situational mentions: if the posting explicitly emphasizes a trigger listed under "Situational mentions" in context.md, add that fact as one sentence where it fits best, usually the end of `\EVIDENCETWO` or the start of `\CLOSING`. At most one per letter. It counts toward the word limit. Follow the item's Status line. If no trigger is clearly present, use none.
- Body (hook through closing) totals 250 to 350 words.
- Every sentence contains a specific noun, number, technology, or named system. Delete any sentence that would fit unchanged in a letter to another company.
- Apply style.md in full.

## Step 5: Render

- Copy `assets/template.tex` exactly. Replace only the `\newcommand` values inside the SKILL-EDITABLE REGION.
- Escape LaTeX special characters in values: `\&` `\%` `\$` `\#` `\_`. Straight apostrophes are fine.
- Never alter the preamble, USER CONFIG, header, spacing, packages, or anything below the END marker. Never add commands or formatting inside values (no bold, italics, or line breaks).
- Output the entire file in a single ```latex code block.
- If you have filesystem access, also save it to `letters/<company>-<role>.tex` (lowercase, hyphens).

## Step 6: Self-check

Run before output, report after the code block in a few lines:
- No style.md violation in any value, including punctuation (em dashes, en dashes, semicolons).
- Every claim traces to context.md.
- Nothing outside the SKILL-EDITABLE region differs from the template.
- Body word count.

Report: archetype used, entries used, situational mention used (if any, with the posting phrase that triggered it), word count, and any top requirements with no matching evidence, so the user knows the gaps.

## Step 7: Revisions

When the user gives feedback, change only the affected values, rerun Step 6, and output the full .tex again. The template never changes during a run. If the user asks for a formatting change, tell them to edit `assets/template.tex` directly.

## Output order

Scoring summary, then the code block, then the self-check report. Nothing else. Keep chat text short.
