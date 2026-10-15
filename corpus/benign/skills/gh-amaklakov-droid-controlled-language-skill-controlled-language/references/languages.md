# Languages

The skill works with text in any language. English is the native
language of the approach. ASD-STE100 is a standard for English, and the full
rule set of this skill comes from it. For other languages, the skill uses
the same principles in a form that fits the language.

## Contents

1. [Universal rules and English-only rules](#universal-rules-and-english-only-rules)
2. [Levels in each language](#levels-in-each-language)
3. [Language files](#language-files)
4. [Languages without a language file](#languages-without-a-language-file)
5. [Sentence length in each language](#sentence-length-in-each-language)
6. [Signal words](#signal-words)
7. [Documents with more than one language](#documents-with-more-than-one-language)
8. [Translation into a controlled language](#translation-into-a-controlled-language)
9. [Output note](#output-note)

## Universal rules and English-only rules

The catalog in [rules.md](rules.md) has 39 rules.

- **32 universal rules** apply to all languages. They control the structure:
  sentence and paragraph length, one instruction per sentence, the
  condition first, active voice, one term per concept, specific values,
  noun chains, consistent spelling, lists, procedures, descriptions, and
  safety instructions.
- **7 English-only rules** apply only to English text. They depend on
  English grammar or on the ASD-STE100 vocabulary:
  - W4 one part of speech per word;
  - W5 approved general vocabulary;
  - W6 no "-ing" forms;
  - T3 technical verbs from the domain only;
  - N2 articles;
  - V2 simple verb forms;
  - V3 no phrasal verbs.

The **All languages** column of the matrix in [rules.md](rules.md) shows
which rules are universal.

For each language, a **language file** can add rules that apply the
universal rules to the grammar of that language. For example, in Russian a
chain of nouns in the genitive case is a long noun cluster (N1), and an
adverbial-participle clause is similar to an English "-ing" form.

## Levels in each language

All three levels exist in all languages. The strength of each universal
rule at each level is the same as in English.

| Level | English | Other languages |
| --- | --- | --- |
| 1 Light | 19 "must" rules of 39 | Universal rules at Level 1 strength, and the language rules at Level 1 strength |
| 2 Standard | 34 "must" rules of 39 | Universal rules at Level 2 strength, and the language rules at Level 2 strength |
| 3 Strict | All 39 rules, and only approved ASD-STE100 general words | All 32 universal rules and all language rules are "must". There is no approved vocabulary. |

Level 3 in other languages has no vocabulary control, because no approved
dictionary exists for them. When you apply Level 3 to text that is not in
English, tell the user this in one short sentence.

## Language files

Language files are in the [languages/](languages/) folder. Each file is
named with the language code: `ru.md`, `de.md`, `pt-BR.md`.

| File | Language | Status |
| --- | --- | --- |
| [languages/ru.md](languages/ru.md) | Russian | reviewed |
| [languages/de.md](languages/de.md) | German | draft |
| [languages/fr.md](languages/fr.md) | French | draft |
| [languages/es.md](languages/es.md) | Spanish | draft |

A language file contains:

- the standard instruction form (for example, the polite imperative);
- the signal words (WARNING, CAUTION, NOTE) in the language;
- the language rules, with IDs (for example `RU2`) and a strength for each
  level;
- a word-choice table. The checker script reads it.

Before you work on text in a language, read its language file if it
exists. Use the rule IDs of the file in review reports.

A "draft" file did not get a review from a native speaker. Use it, but if
the user is a native speaker, ask them to report wrong rules.

To add a language, copy [languages/_template.md](languages/_template.md).

## Languages without a language file

If there is no language file for the language:

1. Apply the 32 universal rules at the level.
2. Use the standard conventions of technical writing in that language: the
   usual instruction form, the usual signal words, the usual way to address
   the reader.
3. Apply the same ideas as the language files: verbs instead of nouns made
   from verbs, no formal filler words, short noun chains, and one action
   per sentence.
4. Tell the user that the language has no language file yet. Suggest that
   a native speaker adds one.

## Sentence length in each language

Use the same word limits in all languages (rule S2):

| Level | Procedural sentence | Descriptive sentence | Paragraph |
| --- | --- | --- | --- |
| 1 | 25 words | 30 words | 8 sentences |
| 2 | 20 words | 25 words | 6 sentences |
| 3 | 20 words | 25 words | 6 sentences |

Some languages need fewer words than English for the same sentence (for
example, Russian has no articles). Thus, the limits are a little less strict
in these languages. A language file can give lower limits.

For languages that do not use spaces between words (Chinese, Japanese,
Thai), count characters. Use approximately 2 characters for each English
word. The limit is 40 characters for a procedural sentence and 50
characters for a descriptive sentence. The checker script does not count
characters, so it does not find long sentences in these languages.

## Signal words

Use the signal words of the language file. If there is no language file,
use the standard equivalents of WARNING, CAUTION, and NOTE in the language.
If the project glossary gives translations, use them.

## Documents with more than one language

Apply the rules of the language of each paragraph. Keep UI labels in the
language of the product UI, even if it is different from the language of
the text. For example, a Russian guide for an English UI keeps the label
**Settings** in English.

## Translation into a controlled language

A user can ask you to translate a document and to apply a level at the same
time. Then:

1. Translate the meaning, not the sentence structure of the source.
2. Apply the universal rules and the language rules of the target language
   at the level.
3. Keep terms, code, UI labels, and links as the target project requires.

## Output note

At the end of the output, add one short line in the language of the user.
The line tells which rules you applied. For example: "Level 2. Universal
rules and the Russian language rules (ru.md). The vocabulary rules
of ASD-STE100 apply only to English."
