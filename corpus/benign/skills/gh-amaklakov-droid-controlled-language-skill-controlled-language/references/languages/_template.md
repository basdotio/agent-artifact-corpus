# <Language name in English> (<code>)

Use this template to add the rules for a new language. Copy it to
`<code>.md`, where `<code>` is the BCP 47 language code (for example `de`,
`pt-BR`). Then replace all text in angle brackets. Write the explanations in
English. Write the examples in the language.

A native speaker of the language must review the file before we change its
status to "reviewed". See `docs/en/translating.md` in the repository.

| Field | Value |
| --- | --- |
| Code | `<code>` |
| Script | <Latin, Cyrillic, Arabic, Han, ...> |
| Status | draft: waits for a native-speaker review |
| Reviewers | — |

## Instruction form

<Which form do technical instructions use in this language? For example, the
polite imperative, the informal imperative, or the infinitive. Which form of
"you" do they use? Give one example.>

## Signal words

| English | <Language> |
| --- | --- |
| WARNING | <standard equivalent> |
| CAUTION | <standard equivalent> |
| NOTE | <standard equivalent> |

## Rules

Each rule applies one universal rule from `../rules.md` to this language.
Give each rule an ID: the language code in capital letters and a number
(for example `DE1`). Use the same strength values as the main matrix: must,
prefer, or —.

| ID | Rule | L1 | L2 | L3 | Universal rule |
| --- | --- | --- | --- | --- | --- |
| <XX>1 | <Instruction form> | must | must | must | P1 |
| <XX>2 | <Verbs, not nouns made from verbs> | prefer | must | must | V4 |
| <XX>3 | <Words that make the text formal or long> | prefer | must | must | W2 |
| <XX>4 | <Active voice> | prefer | must | must | V1 |
| <XX>5 | <Short noun chains or compounds> | must (4) | must (3) | must (3) | N1 |
| <XX>6 | <Constructions that put two actions in one sentence> | — | prefer | must | S1, P2 |

### <XX>1: <Rule name>

<One or two sentences that explain the rule.>

- Not: «<bad example>»
- Use: «<good example>»

## Word choices

The checker reads this table. Keep the five columns. Separate alternatives
in the **Avoid** column with a comma. Put a phrase that contains a comma in
double quotes. An entry that ends with `*` matches all words that start with
it. Write all forms of a word that the checker must find, or use `*`.

<!-- controlled-language: off -->
| Avoid | Use instead | From level | Lint | Note |
| --- | --- | --- | --- | --- |
| <word, form 2, form 3> | <replacement> | 2 | yes | Rule <XX>3. |
<!-- controlled-language: on -->
