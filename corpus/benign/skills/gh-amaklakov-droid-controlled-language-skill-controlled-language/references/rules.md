# Rule catalog

This catalog describes the rules that the skill applies. The rules follow
the principles of ASD-STE100 Simplified Technical English. The
wording, numbering, and examples here are original to this project. They are
not a copy of the ASD-STE100 standard. For certified work, use the official
standard. ASD (Aerospace, Security and Defence Industries Association of
Europe) gives it free of charge on request.

## Contents

1. [How to read this catalog](#how-to-read-this-catalog)
2. [Rule matrix](#rule-matrix)
3. [Words (W)](#words-w)
4. [Terms (T)](#terms-t)
5. [Noun phrases (N)](#noun-phrases-n)
6. [Verbs (V)](#verbs-v)
7. [Sentences (S)](#sentences-s)
8. [Procedures (P)](#procedures-p)
9. [Descriptions (D)](#descriptions-d)
10. [Safety instructions (SF)](#safety-instructions-sf)
11. [Punctuation and word count (PU)](#punctuation-and-word-count-pu)

## How to read this catalog

Each rule has an ID (for example `S2`). Use the ID in review reports so that
writers can find the rule quickly.

Each rule has a strength for each level:

- **must**: apply the rule every time. A break of the rule is a violation.
- **prefer**: apply the rule when it does not make the text less clear or less
  accurate. A break is a suggestion, not a violation.
- **—**: the rule is off at this level.

The **All languages** column shows if the rule applies to all languages
("yes") or only to English text ("English only"). For other languages, the
universal rules have the same strength at each level as in English. The
language files add rules for each language. See
[languages.md](languages.md).

The examples in this catalog are in English. The language files give
examples in other languages.

**Procedural text** tells the reader to do something: steps, instructions,
commands, checklists. **Descriptive text** gives information: overviews,
explanations, concepts, release notes. Some rules have different limits for
the two types. If a sentence is an instruction, it is procedural, even when it
is inside a descriptive section.

## Rule matrix

| ID  | Rule                                                        | L1 Light       | L2 Standard    | L3 Strict | All languages |
| --- | ----------------------------------------------------------- | -------------- | -------------- | --------- | --------------- |
| W1  | One word, one meaning                                       | prefer         | must           | must      | yes |
| W2  | Simplest common word                                        | prefer         | must           | must      | yes |
| W3  | Literal language only                                       | must           | must           | must      | yes |
| W4  | One part of speech per word                                 | —              | prefer         | must      | English only |
| W5  | Approved general vocabulary                                 | —              | prefer         | must      | English only |
| W6  | No "-ing" forms                                             | —              | prefer         | must      | English only |
| W7  | Be specific                                                 | must           | must           | must      | yes |
| W8  | Consistent spelling                                         | must           | must           | must (US) | yes |
| W9  | Define abbreviations                                        | must           | must           | must      | yes |
| T1  | One term per concept                                        | must           | must           | must      | yes |
| T2  | Explain unfamiliar terms                                    | prefer         | must           | must      | yes |
| T3  | Technical verbs from the domain only                        | —              | prefer         | must      | English only |
| N1  | Short noun clusters (max nouns)                             | must (4)       | must (3)       | must (3)  | yes |
| N2  | Keep articles; no telegraphic style                         | prefer         | must           | must      | English only |
| V1  | Active voice                                                | must / prefer  | must           | must      | yes |
| V2  | Simple verb forms only                                      | —              | prefer         | must      | English only |
| V3  | No phrasal verbs                                            | prefer         | must           | must      | English only |
| V4  | Verbs, not nouns made from verbs                            | prefer         | must           | must      | yes |
| V5  | Clear obligation words                                      | prefer         | must           | must      | yes |
| S1  | One topic per sentence                                      | must           | must           | must      | yes |
| S2  | Sentence length (procedural / descriptive)                  | must (25 / 30) | must (20 / 25) | must (20 / 25) | yes |
| S3  | Do not omit words to shorten                                | prefer         | must           | must      | yes |
| S4  | Vertical lists for series                                   | must           | must           | must      | yes |
| S5  | No semicolons; clear connectors                             | prefer         | must           | must      | yes |
| S6  | Positive statements                                         | prefer         | must           | must      | yes |
| P1  | Imperative instructions                                     | must           | must           | must      | yes |
| P2  | One instruction per sentence                                | prefer         | must           | must      | yes |
| P3  | Condition before instruction                                | must           | must           | must      | yes |
| P4  | Steps in order, results separate                            | must           | must           | must      | yes |
| P5  | Notes give information only                                 | prefer         | must           | must      | yes |
| D1  | Key information first                                       | must           | must           | must      | yes |
| D2  | Paragraph length (max sentences)                            | must (8)       | must (6)       | must (6)  | yes |
| D3  | Same structure for similar information                      | prefer         | must           | must      | yes |
| SF1 | Command first, then the risk                                | must           | must           | must      | yes |
| SF2 | Correct signal word, never in a note                        | must           | must           | must      | yes |
| SF3 | Specific safety text                                        | must           | must           | must      | yes |
| PU1 | Word count conventions                                      | must           | must           | must      | yes |
| PU2 | Parentheses for short references only                       | prefer         | must           | must      | yes |
| PU3 | Colon before a vertical list                                | prefer         | must           | must      | yes |

Count: Level 1 has 19 "must" rules of 39 (about 50%). Level 2 has 34 "must"
rules (about 85%). Level 3 has all 39. Level 2 is close to the "80% of the
way" idea: the structure rules are strict, and the vocabulary rules are soft.
32 rules apply to all languages. 7 rules apply only to English.

---

## Words (W)

### W1 — One word, one meaning

Use each word with one meaning in a document. If a word has a second meaning,
do not use it for that second meaning. Use a different word.

- Not: "The **release** notes describe the bug fix. **Release** the lock before
  you continue."
- Use: "The **release** notes describe the bug fix. **Unlock** the file before
  you continue."

Words with two frequent meanings:

| Word | Meaning 1 | Meaning 2 |
| --- | --- | --- |
| fall | move down | decrease |
| about | concerned with | approximately |
| since | from a time | because |
| while | at the same time | but |
| once | one time | after |
| as | because | at the same time |

- Not: "**Since** the update failed, restart the service."
- Use: "**Because** the update failed, restart the service."

### W2 — Simplest common word

Use the shortest, most common word that gives the correct meaning. Readers
with limited English know common words. Translation tools also give better
results with common words. See [word-choices.md](word-choices.md) for a list of
words to avoid and their replacements.

- Not: "**Utilize** the CLI **in order to** **initiate** the migration."
- Use: "Use the CLI to start the migration."

### W3 — Literal language only

Do not use idioms, metaphors, slang, jokes, cultural references, or
exaggeration. A non-native reader or a translation tool can read them
literally and get the wrong meaning.

- Not: "This setting is a **game changer**. Just **give it a shot**."
- Use: "This setting makes the build 40% faster. Try it on a test project
  first."

### W4 — One part of speech per word

Use a word only as the part of speech that the reader expects. Do not use a
noun as a verb or a verb as a noun when this can confuse the reader.

- Not: "**Action** the request." / "Send us an **ask**."
- Use: "Process the request." / "Send us a request."

At Level 3, use each general word only with the part of speech that
ASD-STE100 approves for it. For example, the standard approves "check" only
as a noun ("do a check of the log"), not as a verb.

### W5 — Approved general vocabulary

At **Level 3**, write general words only with words that ASD-STE100 approves,
in their approved meaning and part of speech. Words that are not general
(product names, parts, tools, technical actions) are terms. Rules T1–T3
control them.

This project does not include the ASD-STE100 dictionary, because ASD owns its
copyright. Use your own knowledge of the standard:

1. If you are sure that a general word is approved, use it.
2. If you are not sure, use a simpler word that you are sure of.
3. If no simpler word gives the correct meaning, keep the word. Put it in
   the "Words to verify" list of your output.

Do not guess and then present the text as fully compliant.

At **Level 2**, prefer words that you know are approved. Other common words
are acceptable if they have only one meaning in the sentence.

### W6 — No "-ing" forms

Words that end in "-ing" can be a verb, a noun, or an adjective. This can make
a sentence ambiguous. "Testing equipment" can be equipment for tests or
equipment that does tests.

- Not: "**Before installing** the agent, stop the service."
- Use: "**Before you install** the agent, stop the service."
- Not: "**Running** the script deletes the cache."
- Use: "The script deletes the cache **when you run it**."

Exceptions: technical nouns ("logging", "load balancing", "string") and
words that are not verb forms ("during", "something", "nothing",
"anything", "everything", "ceiling").

At Level 2, remove "-ing" forms when they make the sentence ambiguous or
long. At Level 3, remove all of them except the exceptions.

### W7 — Be specific

Give the reader values, names, and criteria. Do not use vague words. For
example: "properly", "correctly" (without a criterion), "appropriate", "as
needed", "some", "several", "soon", "large", "fast", "regularly", "etc.".

- Not: "Set an **appropriate** timeout and restart the service **if
  needed**."
- Use: "Set the timeout to 30 seconds. If the service does not respond after
  30 seconds, restart it."

If you do not know the value, do not invent it. Keep the vague word and flag
it for the writer.

### W8 — Consistent spelling

Use one spelling variant in a document. In English, use US or UK spelling,
not both. At Level 3, use American English spelling, because ASD-STE100
uses American English as its base. In other languages, use one spelling of
each word (for example, of the Russian letter «ё»). Keep
the spelling of names, identifiers, and quoted text.

### W9 — Define abbreviations

Write an abbreviation in full at its first use, then give the short form in
parentheses. Do not define abbreviations that all readers of the document
know (for example "URL" in a developer guide). Do not make new abbreviations
only to make a sentence shorter.

---

## Terms (T)

Terms are words and phrases that belong to the subject of the document.
Examples are product names, components, UI elements, data types, tools, and
actions of the domain. ASD-STE100 calls them **technical nouns** and **technical verbs**. The
project glossary lists them (see [configuration.md](configuration.md)).

### T1 — One term per concept

Use one term for one concept, and use it every time. Do not change the term
to make the text less repetitive. A reader thinks that a different word means
a different thing.

- Not: "Create an **API key**. Copy the **token** to the config file. Keep
  the **secret** safe."
- Use: "Create an **API key**. Copy the **API key** to the config file. Keep
  the **API key** safe."

If the glossary gives a preferred term, use it exactly. Use the same
capitalization as the glossary and the UI.

### T2 — Explain unfamiliar terms

If the reader possibly does not know a term, explain the term at its first
use. Use a short sentence or a short clause.

- "Open the **dashboard**. The dashboard is the page that shows the status of
  all your services."

### T3 — Technical verbs from the domain only

A technical verb is an action of the domain that has no simple general
equivalent: "deploy", "commit", "compile", "click", "download", "sign" (a
transaction), "mint". Use technical verbs only for their technical meaning.

At Level 3, use only technical verbs that the glossary lists or that are
standard actions of the domain. At Level 2, use them when they are
unambiguous.

- Not (Level 3): "**Spin up** a new instance."
- Use: "**Deploy** a new instance." ("Deploy" is in the glossary.)

---

## Noun phrases (N)

### N1 — Short noun clusters

A noun cluster is a group of nouns (and adjectives) in a row. Long clusters
are hard to understand because the reader cannot see which word changes which
word. The maximum number of words in a cluster is **4** at Level 1 and **3**
at Levels 2 and 3.

To make a cluster shorter:

- Use prepositions: "database connection pool timeout setting" → "the
  timeout setting **of the** database connection pool".
- Define a short form after the first use: "the connection pool of the
  database (the pool)".
- Use a hyphen for a compound modifier: "a two-factor authentication code".

A product name or a glossary term counts as one word.

### N2 — Keep articles; no telegraphic style

Use "a", "an", "the", "this", and "these" where normal English uses them. Do
not remove articles to make the text shorter.

- Not: "Click button to open dialog."
- Use: "Click the button to open the dialog."

Labels, table cells, and headings can be shorter, but keep them clear.

---

## Verbs (V)

### V1 — Active voice

In procedural text, always use the active voice (the imperative). The reader
must know who does the action.

In descriptive text:

- **Level 1**: prefer the active voice.
- **Level 2**: use the passive voice only when the agent (the person or thing
  that does the action) is unknown or not important to the reader.
- **Level 3**: use the passive voice only when the agent is unknown.

- Not: "The configuration file **is read** at startup."
- Use: "The service **reads** the configuration file at startup."
- Not: "The token **must be renewed** every 24 hours."
- Use: "**Renew** the token every 24 hours."

### V2 — Simple verb forms only

Use only these verb forms:

- the imperative ("Open the file.")
- the infinitive ("Use this command to open the file.")
- the simple present ("The service opens the file.")
- the simple past ("The service opened the file.")
- the simple future ("The service will open the file.")
- the past participle as an adjective ("the opened file", "the file is
  closed")

Do not use the perfect tenses ("has opened", "had opened") or the continuous
tenses ("is opening", "was opening").

- Not: "If the migration **has completed**, the status **is showing** Done."
- Use: "When the migration is complete, the status **shows** Done."

At Level 2, prefer these forms. At Level 3, use only these forms.

### V3 — No phrasal verbs

A phrasal verb is a verb and a particle that together have a new meaning:
"set up", "turn off", "find out", "carry out", "look into", "back up".
Non-native readers often do not know the meaning. Use a one-word verb.

| Avoid      | Use                       |
| ---------- | ------------------------- |
| set up     | install, configure, make  |
| turn on    | start, enable             |
| turn off   | stop, disable             |
| find out   | find, learn               |
| carry out  | do                        |
| look into  | examine                   |
| fill in    | complete, write           |
| log in     | sign in (if the UI uses it) |
| back up    | make a backup (of)        |
| point out  | show                      |

If the UI or the glossary uses a phrasal verb as a term ("Sign in"), keep it
as a term (T1).

### V4 — Verbs, not nouns made from verbs

Use the verb for the action. Do not use a weak verb with a noun that comes
from the action verb.

- Not: "**Perform the installation of** the package."
- Use: "**Install** the package."
- Not: "The tool **makes a comparison of** the two files."
- Use: "The tool **compares** the two files."

At Level 3, some action verbs are not approved, for example "check". For
these verbs, use the approved noun with "do": "Do a check of the log."

### V5 — Clear obligation words

Use words that show clearly whether an action is necessary or possible:

- "must" for a requirement.
- "can" for a possibility or an ability.
- "do not" for a prohibition.

Do not use "should", "may", "might", "could", or "would" in instructions. The
reader cannot know if the action is necessary.

- Not: "You **should** restart the service."
- Use: "Restart the service." / "You **must** restart the service."
- Not: "The import **may** take several minutes."
- Use: "The import **can** take up to 10 minutes."

---

## Sentences (S)

### S1 — One topic per sentence

Give one idea in one sentence. If a sentence has two ideas, make two
sentences.

- Not: "The service restarts automatically, and you can see the logs in the
  dashboard, which updates every minute."
- Use: "The service restarts automatically. You can see the logs in the
  dashboard. The dashboard updates every minute."

### S2 — Sentence length

| Level | Procedural sentence | Descriptive sentence |
| ----- | ------------------- | -------------------- |
| 1     | max 25 words        | max 30 words         |
| 2     | max 20 words        | max 25 words         |
| 3     | max 20 words        | max 25 words         |

Count words as [PU1](#pu1--word-count-conventions) describes. Do not make
every sentence the maximum length. Most good sentences are much shorter. Use
different sentence lengths in descriptive text so that it is easy to read.

### S3 — Do not omit words to shorten

Do not remove necessary words (articles, verbs, "that", prepositions) only to
make a sentence shorter. Make two sentences.

- Not: "If error, retry."
- Use: "If an error occurs, try again."

### S4 — Vertical lists for series

Use a vertical list (bullets or numbers) when the text has three or more
parallel items, steps, options, or conditions. A list is easier to read and
to translate than a long sentence with commas.

### S5 — No semicolons; clear connectors

Do not use semicolons. Make two sentences. Use clear connecting words to show
the relation between sentences: "then", "but", "because", "if", "when",
"after", "before", "also".

### S6 — Positive statements

Say what to do, not what to avoid, when you can. Do not use double negatives.

- Not: "Do not forget to save the file."
- Use: "Save the file."
- Not: "It is not uncommon for the cache to be invalid."
- Use: "The cache is frequently invalid."

Prohibitions in safety instructions are correct: "Do not disconnect the
device during the update."

---

## Procedures (P)

### P1 — Imperative instructions

Write instructions as commands to the reader. Start with the verb, or with a
condition and then the verb.

- Not: "The user needs to click Save." / "Clicking Save is required."
- Use: "Click **Save**."

### P2 — One instruction per sentence

Give one instruction in one sentence. You can put two actions in one sentence
only if the reader does them at the same time.

- Not: "Open the terminal, go to the project folder, and run `make`."
- Use:
  1. Open the terminal.
  2. Go to the project folder.
  3. Run `make`.
- Acceptable: "Hold **Shift** and click the file." (the actions are
  simultaneous)

At Level 1, two closely related actions in one sentence are acceptable.

### P3 — Condition before instruction

If the reader must know a condition before the action, write the condition
first. Then the reader does not do the action too early.

- Not: "Delete the folder if you do not need the old version."
- Use: "If you do not need the old version, delete the folder."

### P4 — Steps in order, results separate

- Write the steps in the order that the reader does them.
- Use a numbered list for steps that must be in sequence.
- Give one action in each numbered step. A step can also have a short result
  or explanation as a separate, descriptive sentence.

```
3. Click **Connect**.
   The status changes to **Online**.
```

### P5 — Notes give information only

A note gives information that helps the reader. A note does not give an
instruction, and a note never contains a safety instruction (SF2).

- Not: "Note: Restart the browser after the update."
- Use a step: "4. Restart the browser."
- Correct note: "Note: The update does not change your saved settings."

---

## Descriptions (D)

### D1 — Key information first

Start each section and each paragraph with the most important information.
The first sentence of a paragraph tells the reader the topic.

### D2 — Paragraph length

Give one topic in each paragraph. The maximum number of sentences in a
paragraph is **8** at Level 1 and **6** at Levels 2 and 3. A one-sentence
paragraph is acceptable.

### D3 — Same structure for similar information

Use the same structure, order, and wording for similar items:

- the same heading pattern for similar sections;
- the same sentence pattern for similar list items;
- the same table columns for similar tables.

The reader then sees
the differences quickly.

---

## Safety instructions (SF)

### SF1 — Command first, then the risk

Start a safety instruction with a clear command. Then, in a short sentence,
give the risk or the result if the reader does not obey.

- Not: "WARNING: Since the operation is irreversible and will result in all
  data being lost, it is recommended that a backup be made."
- Use: "WARNING: Make a backup of the database before you continue. This
  operation deletes all data permanently."

### SF2 — Correct signal word, never in a note

Use a signal word that shows the type of risk:

- **WARNING**: a risk to people, to security, to money, or of permanent loss.
  Examples: deleted data that you cannot recover, leaked credentials, a
  transfer that you cannot cancel.
- **CAUTION**: a risk of damage to equipment, data, or a service that you can
  repair or recover.

Put the safety instruction before the step that it applies to. Never put a
safety instruction in a note.

### SF3 — Specific safety text

Say exactly what to do and what can occur. Do not write "Be careful" or "Use
caution". Do not make the risk less clear to make the text softer.

- Not: "Be careful when you edit this file."
- Use: "CAUTION: Make a copy of `config.yaml` before you edit it. A syntax
  error in this file stops the service."

---

## Punctuation and word count (PU)

### PU1 — Word count conventions

Use these conventions to count words for S2:

- A number with its unit is one word: "30 seconds", "5 MB".
- A hyphenated word is one word: "read-only".
- A code element, file name, command, URL, or identifier is one word:
  `npm install`, `config.yaml`.
- A product name or a glossary term is one word: "Smart Wallet", "API key".
- A UI label is one word: **Save as Draft**.
- Each item of a vertical list is a separate sentence for the count. The
  introduction to the list ("Do these steps:") counts separately.

### PU2 — Parentheses for short references only

Use parentheses only for short references, labels, abbreviations, and codes:
"(see Figure 2)", "(Ctrl+S)", "(API)". Do not put necessary information in
parentheses. Make a separate sentence.

### PU3 — Colon before a vertical list

Use a colon at the end of the sentence that introduces a vertical list.
