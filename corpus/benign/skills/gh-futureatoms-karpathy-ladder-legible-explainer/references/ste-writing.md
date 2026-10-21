# Writing in ASD-STE100 (Simplified Technical English)

ASD-STE100 is a controlled language standard. The aerospace industry made it
for maintenance documentation, so that a reader whose first language is not
English, under time pressure, reads one meaning only. The same rules make any
explanation faster to read. This file paraphrases the rules for use in
explanations; it is not the standard. The standard (Issue 9, 15 January 2025:
53 writing rules in 9 sections and a dictionary of about 900 approved words)
is free to download from asd-ste100.org and is the authority. Do not copy text
from it into outputs. Facts here checked against the STEMG FAQ, ASD and
tcworld notes on Issue 9, and an Issue 9 dictionary copy, as of 2026-10-03.

## Contents

- The rules, by section
- The dial: 80% and strict
- Substitution table
- STE for explanations (beyond maintenance text)
- Keep the meaning
- Before and after
- History, for sheets about STE itself
- What the linter checks

## The rules, by section

**1 Words.** Use approved words only in their approved meaning and part of
speech. "Close" is a verb ("close the valve"), never an adjective meaning
"near". "Check" and "test" are approved only as nouns: write "do a check of
the oil level", not the verb. "About" means only "concerned with"; for a
rough number write "approximately". Issue 9 calls the words of a trade
**technical nouns** (names of parts, tools, software objects, protocols) and
**technical verbs** (verbs of the trade, such as "compile" or "deploy"). They are
not in the dictionary: the dictionary lists approved words and common
unapproved words, and the writer adds the technical nouns and verbs of the
subject under the Part 1 rules. Use
them when no approved word can replace them, and use each only in its own part
of speech: a technical noun is never a verb ("cache the response" uses the
noun "cache" as a verb; write "keep a copy of the response"), and a technical
verb is never a noun ("a deploy"). Use the same word for the same thing every
time: do not switch between "server", "host" and "machine" for one thing. Use
American spelling.

**2 Multi-word nouns.** Issue 9 calls them multi-word nouns (Issue 8: noun
clusters). Do not write one of more than 3 words. Break a long one with a
preposition or a relative clause: "the cache invalidation event handler"
becomes "the handler for cache invalidation events". An established technical
noun of more than 3 words can stay, but explain it the first time.

**3 Verbs.** Use only these forms: the imperative ("Close the valve."), the
simple present ("The valve closes."), the simple past ("The valve closed."),
the simple future ("The valve will close."), the infinitive ("Turn the knob to
close the valve.") and the past participle as an adjective ("the closed
valve", "make sure that the valve is closed"). Do not use the progressive
("is closing") or the perfect ("has closed"). Use the -ing form of a verb only
as a technical noun or as a modifier in a technical noun ("landing gear",
"logging"); "before starting the pump" and "by using the tool" are not STE.
Words that only end in -ing, and approved -ing words such as "during",
"missing" and "remaining", are fine. Use the active voice. In an instruction,
never the passive ("The valve must be closed." is not an instruction in STE;
write "Close the valve."). In a description, the passive only when the agent
is not known.

**4 Sentences.** Write short sentences. Write only one topic in each sentence.
Do not leave out words to make a sentence shorter: keep "the", "a" and "that".
Use a vertical list for complex text. Use connecting words ("then", "but",
"because") to join sentences into a logical sequence.

**5 Procedures.** No more than 20 words in a sentence of an instruction. Write
one instruction in each sentence, unless two actions occur at the same time.
Write instructions in the imperative. When there is a condition, put it first
("If the light comes on, stop the pump."). Put a note (useful information that
is not an instruction) separately from the instruction.

**6 Descriptive writing.** No more than 25 words in a descriptive sentence. No
more than 6 sentences in a paragraph, and one topic in each paragraph. Start a
paragraph with its topic sentence. Give the information in a logical order,
and use words like "first", "then" and "but" to show the order.

**7 Safety instructions.** WARNING is for a risk of injury or death, CAUTION
for a risk of damage to equipment. A project can choose how to map its own
risks; this skill maps data loss and security exposure to WARNING and outages
or damage to CAUTION. Start with a clear and simple command or condition, then
give the risk in a second sentence: "WARNING: Do not touch the brake unit until
it is cool. Hot parts can cause injury."

**8 Punctuation and word counts.** Do not use the semicolon at all. Use a colon
before a vertical list. A number with its unit counts as one word ("10 mm"),
and a hyphenated word counts as one word. The house style adds one rule: no
dashes as punctuation in running text.

**9 Writing practices.** When a word-for-word swap to approved words does not
work, change the construction of the sentence. Use each approved word
correctly. Do not use phrasal verbs ("set up", "carry out", "shut down",
"find out"): use one approved verb ("install", "do", "stop", "find"). Keep a
consistent style.

## The dial: 80% and strict

Karpathy found strict STE stiff and asked for "80% of the way" instead. That
is the default here. The dial relaxes vocabulary, never grammar.

| Rule | 80% (default) | Strict (on request) |
|---|---|---|
| Sentence length 20 / 25 | Keep. A rare sentence (at most 1 in 10) may run up to 3 words over when a split would separate a condition from its action. | Keep, no exceptions. |
| Paragraph of 6 sentences, one topic | Keep. | Keep. |
| Verb forms (no progressive, no perfect) | Keep. | Keep. |
| Other -ing verb forms (gerund, participle) | Avoid them; a few may stay when the rewrite is clumsy. | Remove them all. |
| Active voice, no passive in instructions | Keep. | Keep, and in descriptions too unless the agent is unknown. |
| One instruction for each sentence | Keep. | Keep. |
| Unapproved words, phrasal verbs, "check" and "test" as verbs | Replace the common ones (table below). Keep a non-STE word when the STE word is clumsy or loses meaning ("trade-off", "latency"). | Replace every one you know of. Keep only technical nouns and technical verbs. |
| Approved words in their approved part of speech | Try. | Keep. |
| UPPERCASE for approved words in examples | No. | Only in a dictionary-style table, if useful. |

In 80% mode the goal is the reader's understanding: if an approved word would
make a sentence unclear, use the clearer word. In strict mode, rewrite the
sentence until it is both strict and clear; if you cannot, tell the user which
sentence breaks which rule.

## Substitution table

Common words that STE does not approve, with the approved replacement. The
linter (`scripts/ste_lint.py`) knows this list. It is a small working subset
for this skill, not the STE dictionary. Approximately, frequently,
subsequently and transmit (for energy or a signal) are approved words: do not
replace them.

| Do not write | Write |
|---|---|
| about (meaning "approximately") | approximately |
| accomplish | do, complete |
| additional | more |
| advise | tell |
| allow | let |
| ascertain | find, make sure |
| assist | help |
| attempt | try |
| avoid | prevent, or "do not ..." |
| begin, commence, initiate | start |
| check (verb), verify | do a check of, make sure |
| choose | select |
| demonstrate, illustrate, indicate | show |
| determine | find, calculate |
| due to | because of |
| eliminate | remove |
| ensure | make sure |
| facilitate | help, make easier |
| in order to | to |
| in the event that | if |
| inspect | examine |
| it is imperative that | must |
| leverage, utilize | use |
| locate | find |
| maintain, retain | keep |
| modify | change |
| numerous | many |
| obtain | get |
| often | frequently |
| perform | do |
| permit | let |
| prior to | before |
| replenish | fill |
| terminate | stop |
| test (verb) | do a test of |
| via | through |
| whether | if |
| set up, carry out, shut down, find out, roll out | install or prepare, do, stop, find, release in steps |

Software words that are usually technical nouns or technical verbs (keep them
in their own part of speech): API, request, response, cache, commit, deploy,
compile, query, thread, token, endpoint, schema, latency, timeout, retry.

## STE for explanations (beyond maintenance text)

STE was made for procedures and descriptions of equipment. For explanations,
these habits add the most:

- Define a term in the sentence where it first appears, then never change it.
- Give the purpose before the mechanism: "The cache keeps copies of responses. Pages then load more quickly."
- One idea in each sentence. If a sentence has "and" between two ideas, make two sentences.
- Show cause with "because", "if" and "so". Show order with "first", "then", "after".
- Put numbers in digits with their units: "600 s", "3 replicas", "20 words".
- For a trade-off, write the gain and the cost as two separate sentences.
- Introduce a list by its subject ("What to check before phase 0:"), with no count.
- Write a WARNING or CAUTION only for a real risk, and give the reason after the command.

## Keep the meaning

Simplification must not change what the source says. Before you accept a
rewrite, compare it with the original for:

- certainty: "should reduce" is an expectation, so "the team expects that this will decrease";
- conditions: an "if" or "only when" in the source stays in the rewrite;
- negation and limits: "not", "at most", "only";
- attribution: who claims it ("the plan says", "the vendor states");
- numbers and units, exactly as in the source.

## Before and after

Original (not STE):
<!-- ste-ignore-start -->
> It is imperative that the operator ensures the hydraulic reservoir is
> replenished prior to commencing operation.

> The migration is being rolled out gradually, and once all traffic has been
> shifted to the new cluster, the old one will be decommissioned, which should
> reduce costs by approximately 30%.
<!-- ste-ignore-end -->

STE:

> Make sure that the hydraulic reservoir is full before you start the operation.

> The team moves traffic to the new cluster in steps. When all traffic is on
> the new cluster, the team will stop the old cluster. The team expects that
> this will decrease the cost by approximately 30%.

The second rewrite removes a progressive with a phrasal verb ("is being
rolled out"), a perfect passive ("has been shifted") and the unapproved
"decommission", and splits one 33-word sentence into three. It keeps
"approximately" (an approved word) and keeps the source's "should" as an
expectation.

## History, for sheets about STE itself

- 1979: European airlines asked AECMA (the European association of aerospace manufacturers) to study a controlled form of English.
- 1983: the AECMA Simplified English working group started (it later became the STEMG, the STE Maintenance Group).
- 1986: the first AECMA Simplified English Guide (document PSC-85-16598).
- 2004: AECMA merged into ASD, and the guide became ASD-STE100, Simplified Technical English.
- 2005: ASD-STE100 became an international specification.
- 2013 (Issue 6): free of charge.
- 15 January 2025 (Issue 9): 53 rules unchanged in number, 31 refined, 555 dictionary entries updated, technical nouns and technical verbs reclassified in line with ISO 1087-1:2019.

Sources: STEMG FAQ and history pages (asd-ste100.org), tcworld news on Issue 9, Wikipedia. Re-check before you quote them.

## What the linter checks

`ste_lint.py` reads text, Markdown, HTML and SVG (stdin is read as Markdown).
It counts words the STE way (a number with its unit is one word) and flags:

- errors in both modes: sentences over their limit (in 80 mode only more than 3 words over, or more than 1 in 10 sentences over), paragraphs over 6 sentences, progressive and perfect verbs, the passive in an instruction or with a named agent, semicolons, dashes, and the house rules ("caveat", headcount openers, "X, not Y");
- warnings in 80 mode, errors in strict: the words and phrasal verbs in the table, "check" and "test" as verbs, other -ing verb forms, two instructions joined by "and" or "then".

It does not check meaning, parts of speech in general, or multi-word nouns.
Read every finding: some are false alarms (for example a technical noun that
ends in -ing; pass it with `--allow`).
