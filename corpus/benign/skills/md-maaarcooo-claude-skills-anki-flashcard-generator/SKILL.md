---
name: anki-flashcard-generator
description: Generate Anki flashcard decks from PDF or Markdown study materials. Use only when "Anki flashcard" or "Anki deck" is explicitly mentioned. Do not trigger for generic flashcard requests. Outputs in Anki-importable format (Question | Answer).
---

# Anki Flashcard Generator

Generate study flashcards from PDF or Markdown content in Anki-importable format. Card design follows evidence-based principles to optimize active recall and long-term retention under spaced repetition scheduling.

## Process

1. Read the source file (PDF or Markdown) thoroughly
2. Verify accuracy of all information in the source — correct any errors
3. Identify all key content: **bolded terms**, highlighted text, and Higher Tier material
4. Generate flashcards covering all essential topic content, selecting the most effective card type for each piece of knowledge (see Card Types below)
5. Run the interference check: scan the full card set for confusable pairs and add discriminative cards where needed
6. Format output as one card per line: `Question | Answer`

## Core Design Principles

These principles are ordered by impact on retention. Every card must satisfy the first three. The remaining principles should be applied wherever the content allows.

### 1. Understand-first rule

Never create cards for content the learner has not yet studied or that the source does not explain. Cards built on material the learner does not understand become intractable leeches (cards failed 8+ times that consume disproportionate review time). A flashcard consolidates existing understanding into long-term memory; it does not teach new concepts from scratch.

### 2. Minimum information principle (atomicity)

Each card tests exactly one atomic piece of knowledge. This is the single highest-impact design decision.

**Target:** Each card should be answerable in under 6 seconds during review. If a card regularly takes longer, it likely violates atomicity and should be split.

### 3. Production over recognition

Cards must require the learner to produce an answer from memory, not merely recognize it. Retrieving information strengthens memory far more than re-reading.

**In practice:** Avoid yes/no or true/false questions. Frame cards so the answer must be generated, not selected. A card like "Is copper a good conductor? | Yes" is weak. Prefer: "Name a metal that is a good electrical conductor | Copper" or "Why is copper used for electrical wiring? | Copper has low resistivity because its outer electron is weakly bound and moves freely as a delocalised charge carrier."

### 4. Depth of processing

Wherever possible, frame questions using "why," "how," or "explain" to force elaborative processing rather than rote retrieval. This is especially valuable for exam preparation, where explain/justify questions carry the most marks.

### 5. Dual coding

When the source contains diagrams, graphs, or spatial information, extract all factual content from them and convert it into text-based cards. The learner may later attach images to these cards manually in Anki, but the generated output must not include image tags, comments, or any markup beyond the standard `Question | Answer` format.

### 6. Personal connection and self-reference

Where the content allows, frame cards using concrete, relatable scenarios rather than abstract statements. This is particularly useful for "explain" cards where a real-world application can serve as the prompt.

```
Why does a metal spoon feel colder than a wooden spoon at the same temperature? | Metal has higher thermal conductivity, so it transfers thermal energy away from your hand faster, producing a greater rate of heat loss
```

## Card Types

Select the card type that best fits the knowledge being tested. A single source topic will typically use a mix of several types.

### Definition cards (forward + reverse)

For key terms and concepts. Always create both directions to build bidirectional retrieval links, strengthening the association from both term-to-meaning and meaning-to-term. This forces the brain to form two distinct retrieval routes, reducing the chance that the knowledge becomes accessible from only one direction.

```
What is [term]? | [definition]
[definition] — what term describes this? | [term]
```

### Explain/justify cards

For concepts where understanding the reasoning matters, not just the fact. These target common "explain" and "justify" style exam questions (typically 2-4 marks).

Answers must include the full cause-and-effect chain, not just restate the fact. The goal is to train the learner to reproduce the reasoning under exam conditions. "Because of temperature" is not an acceptable answer. State the mechanism: what happens, why it happens, and what effect it produces. If the chain has multiple steps, include all of them. However, if the chain has more than 3 logical steps, split into multiple cards that each cover a segment of the chain plus one linking card that tests the overall sequence.

```
Explain why [phenomenon occurs] | [reasoning with cause-and-effect chain]
Why does [X] lead to [Y]? | [mechanism/reasoning]
```

### Cloze-style cards

For facts embedded in context where the surrounding sentence provides a natural retrieval cue. Useful for dense factual material.

**Rules for cloze cards:**
- Delete exactly one semantically critical keyword per card. Deleting function words or words recoverable from grammar alone produces trivial pattern-matching, not genuine recall.
- If a sentence contains multiple important terms, create separate cloze cards for each, deleting only one per card.
- The surrounding context must not make the answer trivially obvious. If the sentence structure gives away the answer, rephrase.

```
The SI unit of electrical resistance is the [...] | ohm (Ω)
In a series circuit, the current is [...] at all points | the same
Ohm's law states that V = [...] | IR
```

### Compare/contrast cards (interference prevention)

For related concepts that are commonly confused or examined together. These cards serve a dual purpose: they test knowledge and they directly combat interference, which is the primary cause of forgetting in mature SRS collections.

Both sides of the comparison must be addressed in the answer so the learner understands the actual distinction. When two concepts share surface similarities but differ in mechanism or outcome, make the card highlight the specific point of divergence.

```
How does [concept A] differ from [concept B]? | [A does X because of mechanism P; B does Y because of mechanism Q]
What is the similarity between [A] and [B]? | [shared properties]
```

### Formula and equation cards

For mathematical relationships. Create the formula card plus at least one application card that requires identifying when and why the formula is used, not just what it is.

```
What is the equation for kinetic energy? | Ek = ½mv²
When calculating the energy of a moving object, which equation is used? | Ek = ½mv² (kinetic energy equation)
State Ohm's law in equation form | V = IR
A component has a potential difference of 6V and current of 2A. What is its resistance? | R = V/I = 6/2 = 3Ω
```

Keep calculation cards to single-step applications only. Multi-step numerical problems are not suitable for flashcard review.

### Enumeration cards (sets and lists)

When the source contains a set of items (e.g., types of electromagnetic radiation, Newton's three laws), avoid creating a single card that asks the learner to recall the entire list. Instead, use one of these approaches:

**Preferred — individual cards per item:**
```
What type of electromagnetic radiation has the longest wavelength? | Radio waves
Which EM radiation is used in thermal imaging? | Infrared
```

**Acceptable — overlapping cloze for short lists (3-5 items):**
```
Newton's three laws: 1) Inertia, 2) [...], 3) Action-reaction | F = ma (force equals mass times acceleration)
Newton's three laws: 1) [...], 2) F = ma, 3) Action-reaction | An object remains at rest or in uniform motion unless acted on by a resultant force (inertia)
```

**Avoid:** "List all seven types of EM radiation in order" — this is a multi-fact card that violates atomicity.

## Card Design Rules

### Conciseness

Use simple, direct language. Strip unnecessary words. Short answers are easier to self-assess during review. Aim for answers under 25 words for factual cards. Explain cards may be longer but should still be as concise as the reasoning chain allows.

### Unambiguous phrasing

Each question must have exactly one correct answer. If a question could reasonably be answered multiple ways, it will produce inconsistent self-grading that corrupts the SRS scheduling signal. Rephrase to be more specific.

**Bad:** "What is important about copper?" (ambiguous — conductivity? ductility? colour?)
**Good:** "Why is copper used for electrical wiring?" (targets one specific property)

### Bidirectional links for definitions

Always create both forward (term → definition) and reverse (definition → term) cards for key terms. Each direction tests a different retrieval pathway. The forward card tests comprehension; the reverse card tests vocabulary recall. Both are needed for flexible knowledge access.

### Interference management

After generating all cards, scan the set for pairs that are likely to be confused with each other (similar terms, similar mechanisms, similar values). For each confusable pair, ensure at least one dedicated compare/contrast card exists that directly highlights the distinguishing feature. This is the primary defense against interference, which research identifies as the single greatest cause of forgetting in mature SRS collections.

Common high-interference situations:
- Terms with similar names (e.g., fission vs fusion, elastic vs inelastic)
- Quantities with the same units but different meanings
- Processes that share steps but diverge at a key point
- Formulas with similar structure (e.g., Ek = ½mv² vs E = mc²)

### Exclusions

Do not create:
- Questions that depend on interpreting a diagram or visual to answer (factual content shown in diagrams should still be converted into text-based cards)
- Multi-step numerical calculations (single-step formula application is fine)
- Yes/no or true/false questions (these test recognition, not production)
- Cards that list more than 3 items in the answer (split into individual cards instead)
- Cards for content the source does not adequately explain (understanding must precede memorisation)

## Coverage Guidance

Aim for thorough coverage of the source material. As a rough guide, a typical A-level topic page should yield 10-25 cards depending on density. Prioritise content by examinability:

1. **High priority:** Definitions, laws, key equations, and relationships that appear repeatedly in exam mark schemes
2. **High priority:** Common explain/justify points, especially multi-step reasoning chains that students typically struggle to reproduce
3. **Medium priority:** Frequently confused pairs (generate compare/contrast cards)
4. **Medium priority:** Units, standard values, and conditions
5. **Lower priority:** Supplementary context, historical details, or edge cases (include only if the source emphasises them)

Do not pad with trivial or redundant cards. Every card should earn its place in the deck by testing knowledge the learner genuinely needs to retrieve under exam conditions.

## Output Format

One card per line, question and answer separated by a pipe:

```
Question | Answer
```

**Example output:**
```
What is the unit of electrical resistance? | Ohm (Ω)
A material that allows electric current to flow through it is called what? | A conductor
Define specific heat capacity | The energy required to raise the temperature of 1 kg of a substance by 1°C
The energy required to raise 1 kg of a substance by 1°C — what quantity is this? | Specific heat capacity
The SI unit of energy is the [...] | joule (J)
Explain why resistance increases with temperature in a metal | At higher temperatures, metal ions vibrate with greater amplitude, so conduction electrons collide more frequently with ions, transferring less charge per unit time
How does electrical conduction differ between metals and semiconductors? | In metals, resistance increases with temperature (more ion vibrations impede electron flow). In semiconductors, resistance decreases with temperature (more electrons gain enough energy to enter the conduction band, increasing the number of charge carriers)
What is the equation for kinetic energy? | Ek = ½mv²
When calculating the energy of a moving object, which equation is used? | Ek = ½mv² (kinetic energy equation)
Why does a metal spoon feel colder than a wooden spoon at the same temperature? | Metal has higher thermal conductivity, so it transfers thermal energy away from your hand at a greater rate, producing faster heat loss
```

## Quality Checklist

- [ ] All bolded/highlighted terms covered with both forward and reverse cards
- [ ] Higher Tier content included
- [ ] Every card tests exactly one atomic fact or one reasoning chain (no multi-fact cards)
- [ ] No diagram-dependent or multi-step calculation questions
- [ ] Clear, concise phrasing throughout (target under 25 words for factual answers)
