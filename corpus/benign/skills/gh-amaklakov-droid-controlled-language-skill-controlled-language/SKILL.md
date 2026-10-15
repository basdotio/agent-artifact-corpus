---
name: controlled-language
description: >-
  Write, rewrite, and review any text so that it is clear, easy to read, and
  unambiguous: documentation, instructions, explanations, emails, reports,
  policies, UI text, or answers, in English or any other language, at three
  strictness levels (1 Light ~50%, 2 Standard ~80%, 3 Strict ~100%), with
  support for project terms. The rules come from the principles of
  ASD-STE100 Simplified Technical English; English gets the full rule set,
  other languages get the same principles adapted to their grammar (language
  files for Russian, German, French, Spanish). Use this skill whenever the
  user asks for text that is clear, simple, plain, readable, unambiguous,
  easy to translate, or easy for non-native readers; mentions ASD-STE100,
  STE, Simplified Technical English, controlled or plain language, or "80% of
  the way to STE"; asks to check or lint text for readability; or asks to
  explain something "in STE" — even without naming the standard ("make this
  clearer", "упрости текст", "перепиши понятным языком").
license: Apache-2.0
metadata:
  version: "1.1.0"
  repository: https://github.com/amaklakov-droid/controlled-language-skill
---

# Controlled Language

Make any text easy to read, hard to misread, and easy to translate, in any
language. This includes documentation, instructions, explanations, emails,
reports, and answers. The rules come from the principles of ASD-STE100 Simplified
Technical English, a controlled language that the aerospace industry made
for maintenance manuals. English is the native language of the approach and
gets the full rule set. Other languages get the same principles in a form
that fits their grammar. The skill applies the rules to the prose of a
document and keeps the terms of the project.

This skill is not affiliated with or endorsed by ASD (Aerospace, Security
and Defence Industries Association of Europe). ASD-STE100 is a trademark of
ASD, Brussels. The skill does not contain the ASD-STE100 dictionary. For
English at Level 3, it relies on your own knowledge of the approved
vocabulary (see rule W5).

## Workflow

Do these steps for each request:

1. **Find the mode**: write, rewrite, review, or respond (see
   [Modes](#modes)).
2. **Find the language** of the document (see [Languages](#languages)). If
   it is not English, read its language file.
3. **Find the level** (see [Levels](#levels)). Tell the user the level and
   where it came from, in one short line.
4. **Collect the terms** of the project (see
   [Project terms](#project-terms)).
5. **Mark the protected content**: code, commands, paths, URLs, identifiers,
   UI labels, names, quotations, and legal text. Do not change it.
6. **Apply the rules** of the level to the prose. The summary in
   [Rules at a glance](#rules-at-a-glance) is enough for Levels 1 and 2.
   Read [references/rules.md](references/rules.md) for Level 3, for review
   mode, or when you are not sure how a rule applies.
7. **Check the result** (see [Self-check](#self-check)).
8. **Give the output** in the format of the mode (see
   [Output](#output)).

The language of the conversation and the language of the document can be
different. Write the document in its own language. Write your notes and
questions in the language of the user.

## Modes

- **Write**: make a new text (a document, a section, a message, or an
  answer) from facts, notes, code, or a description.
- **Rewrite**: change existing text to the level. Keep all facts, values,
  conditions, and warnings. If you can edit files, edit the file and then
  summarize the changes.
- **Review**: find the rule violations in a text, and give a report with
  rule IDs and fixes. Do not rewrite the full text unless the user asks.
- **Respond**: the user asks you to answer or explain in a controlled
  language ("explain this in STE", "answer at Level 2 from now on"). Apply
  the descriptive rules to your own answers. Keep this mode until the user
  stops it.

If the request does not show the mode, select it from the input. If the user
gives text, use rewrite. If the user gives only a topic, use write.

## Languages

- **English** is the native language of the approach. All 39 rules apply.
  At Level 3, use only the general words that ASD-STE100 approves.
- **Other languages** get the 32 universal rules at the same strength for
  each level. 7 rules are for English only (W4, W5, W6, T3, N2, V2, V3).
  A language file adds rules for the grammar of the language, for example
  RU2 "verbs, not verbal nouns" for Russian.
- **Language files** are in [references/languages/](references/languages/):
  `ru.md`, `de.md`, `fr.md`, `es.md`. If a file exists for the language,
  read it before you start. If there is no file, use the universal rules
  and the standard conventions of technical writing in that language. Then
  tell the user that the language has no language file yet.
- **Level 3 in other languages** makes all universal rules and all language
  rules "must". There is no approved vocabulary for these languages. Tell
  the user this in one sentence.

For the details, read [references/languages.md](references/languages.md).
It covers sentence length in languages without spaces, signal words,
documents in more than one language, and translation.

## Levels

| Level | Name | Approximate share of rules | Use for |
| --- | --- | --- | --- |
| 1 | Light | 50% | Emails, chat answers, internal notes, blog-style guides, a first cleanup of old text. |
| 2 | Standard | 80% (default) | User guides, READMEs, help centers, reports, policies, explanations, UI text. |
| 3 | Strict | 100% | Safety-critical procedures, regulated products, text for machine translation into many languages. |

- **Level 1** makes the structure clear: short sentences, imperative steps,
  the condition first, active voice, clear warnings, and literal words. The
  vocabulary is free.
- **Level 2** makes the structure strict and the vocabulary soft: all
  sentence, procedure, and description rules apply. Use simple common words,
  one meaning for each word, verbs instead of nouns made from verbs, and
  clear obligation words.
- **Level 3** applies all rules. In English, it also allows only the
  general words that ASD-STE100 approves, simple verb forms only, no "-ing"
  forms, and American spelling.

**How to find the level.** Use the first level that you find:

1. The request: "level 3", "strict", "light", "80% of the way" (= 2).
2. The front matter of the document: `controlled-language: 3`.
3. A path override in `.controlled-language.yml`.
4. The `level` field in `.controlled-language.yml`.
5. Level 2.

Inline markers can change the level or turn the rules off for a part of a
document. See [references/configuration.md](references/configuration.md).

## Rules at a glance

IDs refer to [references/rules.md](references/rules.md). "L2+" means Level 2
and Level 3. Rules marked "(EN)" apply only to English. The English examples
show the idea. Apply the same idea in other languages.

**Sentences and paragraphs**

- One topic per sentence (S1). One topic per paragraph (D2).
- Maximum words in a sentence (S2): procedural 25 / 20 / 20, descriptive
  30 / 25 / 25 for Levels 1 / 2 / 3. Most sentences must be much shorter.
- Maximum sentences in a paragraph (D2): 8 / 6 / 6.
- Put the most important information first (D1).
- Use a vertical list for three or more items, steps, or conditions (S4).
- L2+: no semicolons (S5), do not drop words to make sentences shorter
  (S3), use positive statements (S6). Keep the articles (N2, EN).

**Instructions**

- Use the imperative: "Click **Save**." (P1). In other languages, use the
  instruction form of the language file.
- Write the condition first: "If X, do Y." (P3).
- Use one numbered step for each action, in the order that the reader does
  them. Write the result of a step as a separate sentence (P4).
- L2+: one instruction per sentence (P2), and notes give information only
  (P5).

**Verbs**

- Use the active voice. In instructions, always. In descriptions, use the
  passive only when the agent is unknown (L3) or not important (L2) (V1).
- L2+: use the verb, not a noun made from it, so "perform the installation"
  becomes "install" (V4).
- L2+: "must" for a requirement, "can" for a possibility, "do not" for a
  prohibition. No "should", "may", "might", "could", or "would" (V5).
- L2+ (EN): no phrasal verbs, so "set up" becomes "configure" (V3).
- L3 (EN): only the imperative, infinitive, simple present, simple past,
  simple future, and the past participle as an adjective (V2).

**Words and terms**

- Use literal language: no idioms, metaphors, slang, or jokes (W3).
- Be specific: give values and criteria, not "properly" or "as needed"
  (W7). If you do not know the value, do not invent it. Ask the user.
- Use one term for one concept, every time (T1). Define abbreviations (W9).
  Use one spelling of each word (W8).
- L2+: use the simplest common word (W2, see
  [references/word-choices.md](references/word-choices.md) for English and
  the language file for other languages). Use one meaning for each word
  (W1), and explain unfamiliar terms (T2). Keep noun clusters to three
  words or fewer (N1).
- L3 (EN): use only approved general words in their approved meaning and
  part of speech (W4, W5). Do not use "-ing" forms (W6). Use American
  spelling (W8). Use technical verbs only from the domain (T3).

**Safety**

- Start with the command, then give the risk (SF1).
- Use WARNING for a risk to people, security, money, or of permanent loss.
  Use CAUTION for damage that you can repair or recover (SF2). In other
  languages, use the signal words of the language file.
- Put the safety instruction before the step. Never put it in a note (SF2).
- Be specific. Never write "be careful" (SF3).

## Project terms

ASD-STE100 lets writers use the terms of their subject:

- **Technical nouns**: names of products, parts, UI elements, data types.
- **Technical verbs**: actions of the domain, such as "deploy", "click",
  "download".

These terms are not general vocabulary, so the vocabulary rules do not apply
to them.

1. If `.controlled-language.yml` has a `glossary`, use its terms exactly.
   Replace each `not` form of a `preferred_terms` entry with its `use` form.
2. If there is no glossary, find the terms in the context. Look at the
   product UI, the code, the existing docs, and the request. Use the form
   that the product uses.
3. Treat a term as one word for the sentence length (PU1).
4. Do not simplify a term into general words. "Load balancer" stays "load
   balancer".
5. In rewrite and review modes, list the terms that you found under
   "Glossary candidates". The user can then add them to the configuration
   file.

## Meaning comes first

The rules make text clearer. They must never make it wrong.

- Keep every fact, number, unit, condition, limit, and warning.
- Do not add facts or steps. Sometimes the original is vague and you do not
  know the specific value (W7). Then keep the information and ask the user.
- If a rule conflicts with accuracy, keep the accurate text. Tell the user
  which rule you did not apply, and why.
- Keep the legal meaning of legal text and safety text. If a legal team
  owns the text, do not change it. Suggest changes in your notes.

## Self-check

Before you give the output, read the text again and examine it for these
frequent problems:

- [ ] Each instruction is one imperative sentence or one numbered step.
- [ ] Each condition comes before its instruction.
- [ ] No sentence is longer than the limit. Count the long ones.
- [ ] No passive voice in instructions.
- [ ] No weak obligation words, for example "should", "may", «следует»,
      «рекомендуется» (L2+).
- [ ] No nouns made from verbs where a verb works (L2+).
- [ ] English: no phrasal verbs (L2+), no "-ing" forms (L3).
- [ ] The language rules of the language file are applied.
- [ ] One term for each concept, the same form every time.
- [ ] All facts, values, and warnings from the original are present.
- [ ] Code, commands, UI labels, and names are unchanged.

If you can run Python 3, run the checker on the result. It finds the
measurable problems: length, passive voice, phrasal verbs, "-ing" forms,
and the word choices of English and of the language files. It does not
understand meaning, so its warnings need your judgment. A finding inside a
project term (for example, "-ing" in "signing secret") is not a real
problem. Add the term to the glossary, or ignore the finding.

```bash
python3 <skill-folder>/scripts/check.py --level 2 docs/install.md
python3 <skill-folder>/scripts/check.py --level 3 --lang ru --format json - < draft.md
```

## Output

**Write and rewrite.** Give the document first. Then add a short "Notes"
block (five lines or fewer). Include only the items that apply:

- Level, language, and their source: "Level 2 (project config), Russian
  (ru.md)".
- Glossary candidates: terms that you treated as technical nouns or verbs.
- Words to verify (English, Level 3): general words that you are not sure
  are approved.
- Questions: missing values, and places where the meaning was not clear.

**Review.** Use this structure:

```markdown
## Controlled language review: Level <N>, <language> (source: <source>)

<n> sentences checked: <v> violations, <w> warnings, <s> suggestions.
Most frequent: <rule IDs and names>.

| # | Line | Rule | Problem | Fix |
| --- | --- | --- | --- | --- |
| 1 | 12 | S2 | 31 words in an instruction (max 20). | Make two steps: "..." / "..." |

Glossary candidates: ...
Questions: ...
```

A **violation** breaks a "must" rule. A **warning** needs human judgment
(for example, a passive voice in a description). A **suggestion** applies a
"prefer" rule. After the report, offer to apply the fixes.

**Respond.** Answer normally in the controlled language. Do not add a notes
block unless the user asks for one.

## Compliance claims

Do not say that a text "complies with ASD-STE100" or is "certified". Say
that it follows the rules of Level N of this skill. Level 3 in English is
as close to ASD-STE100 as a model can get without the official dictionary.
ASD-STE100 does not cover other languages.

Sometimes the user needs formal compliance. Then tell the user one time (not in each answer) to review the
text against the official standard. ASD gives the standard free of charge
on request at <https://www.asd-ste100.org/>.

## Reference files

| File | Read it when |
| --- | --- |
| [references/rules.md](references/rules.md) | Level 3, review mode, or a question about a rule. |
| [references/languages.md](references/languages.md) | The text is not in English, or has more than one language. |
| [references/languages/](references/languages/) | The language of the text has a file here (`ru.md`, `de.md`, `fr.md`, `es.md`). |
| [references/word-choices.md](references/word-choices.md) | You need a simpler English word, or you review English vocabulary. |
| [references/configuration.md](references/configuration.md) | The project has `.controlled-language.yml`, front matter, or markers. |
| [references/examples.md](references/examples.md) | You want to calibrate the difference between the levels. |
| [assets/controlled-language.example.yml](assets/controlled-language.example.yml) | The user wants to create a configuration file. |
| [scripts/check.py](scripts/check.py) | You can run Python and want a measurable second check. |
