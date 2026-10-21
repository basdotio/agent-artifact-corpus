# Interaction Menu

Retrieval-first: **every lesson has ≥1 active-recall surface**, and recall should appear *through* the
lesson, not only at the end. Learners systematically undervalue testing themselves, so make retrieval
the default interaction — not an optional quiz bolted on. Feedback must be immediate, tell the learner
*why*, and be rationed (don't grade on every keystroke).

These are the **core, subject-agnostic** widgets. Their markup is a fixed `data-*` contract wired by
`lesson-kit.js`; **pick from this menu, don't invent new widgets.** Copy the markup from
[`../examples/0001-golden-example.html`](../examples/0001-golden-example.html).

Language/audio-specific widgets (TTS read-aloud, dictation scoring, spaced-repetition decks, card
grids) are **opt-in modules**, not core — add them only when the subject is genuinely
vocabulary/pronunciation-shaped. See the parent SKILL for the optional-module note.

## Core widgets

### 1. Reveal — hide an answer / aside (zero-JS, always print-open)
```html
<details class="reveal"><summary>Why does X happen?</summary>
  <p>…the payoff, hidden until they've tried to recall it…</p>
</details>
```

### 2. MCQ — one right answer, instant "why"
```html
<div class="quiz" data-id="unique-slug">
  <p class="quiz__q">The question?</p>
  <button class="quiz__option" data-correct="false">Distractor</button>
  <button class="quiz__option" data-correct="true">Answer</button>
  <p class="quiz__why" hidden>Why the answer is right (shown after they choose).</p>
</div>
```
**Fairness rule (from teach):** every option should be about the same length in words and characters.
Never let formatting leak the answer (the longest/most-hedged option is a giveaway).

### 3. Cloze — fill in the blank (free text, forgiving match)
```html
…simplifies to O(<span class="cloze"><input data-id="slug"
  data-answer="n^2|n²|n squared" aria-label="complexity" placeholder="?"></span>).
```
`data-answer` is a `|`-separated list of accepted answers; matching is case/space/quote-insensitive
(accents and umlauts preserved). Grades on blur — never mark an empty field wrong.

### 4. Flashcard flip — term ↔ definition (opacity crossfade, never 3D)
```html
<div class="flip" data-id="slug">
  <div class="flip__front"><strong>Prompt</strong></div>
  <div class="flip__back">The thing to recall.</div>
</div>
```

### 5. Faded worked example — full → blank-a-step → solo
The highest-value pattern for skills: show a fully-worked case, then make the learner supply the next
step, then a step with less scaffolding. (This is the general form of "problem → solution.")
```html
<div class="worked">
  <pre><code>…the snippet / problem…</code></pre>
  <div class="worked__step" data-id="s1"><strong>1. First move.</strong>
    <button class="worked__reveal">reveal</button>
    <span class="worked__answer">…the step, hidden until they try…</span>
  </div>
  <!-- later steps: reveal less, ask more -->
</div>
```

### 6. Ordering / sequence — put steps in the right order
JS adds up/down controls and a check button. JS-off keeps the given order readable; print reveals the
answer key.
```html
<div class="sequence" data-id="cycle-order">
  <p class="sequence__q">Order the phases after new moon.</p>
  <ol class="sequence__list">
    <li class="sequence__item" data-order="2">Full moon</li>
    <li class="sequence__item" data-order="1">First quarter</li>
    <li class="sequence__item" data-order="3">Last quarter</li>
  </ol>
  <p class="sequence__why" hidden>Waxing comes before full; waning comes after.</p>
  <p class="sequence__answer" hidden>Answer: first quarter, full moon, last quarter.</p>
</div>
```

### 7. Matching pairs — connect term to cue
Use matching when the learner must retrieve a relationship, not just recognise a label.
```html
<div class="match" data-id="phase-terms">
  <p class="match__q">Match each word to its cue.</p>
  <div class="match__grid">
    <div class="match__col match__left">
      <span class="match__label">Term</span>
      <button class="match__button" data-key="wax">waxing</button>
      <button class="match__button" data-key="wane">waning</button>
    </div>
    <div class="match__col match__right">
      <span class="match__label">Cue</span>
      <button class="match__button" data-key="wane">lit part shrinks</button>
      <button class="match__button" data-key="wax">lit part grows</button>
    </div>
  </div>
  <p class="match__answer" hidden>waxing = grows; waning = shrinks.</p>
</div>
```

### 8. Predict the output — commit before reveal
Use this for code, calculations, grammar transformations, or any deterministic input → result.
```html
<div class="predict" data-id="predict-cue">
  <p class="predict__q">A crescent is visible after sunset. Predict: waxing or waning?</p>
  <textarea class="predict__input" data-answer="waxing" aria-label="prediction"></textarea>
  <p class="predict__answer" hidden>Answer: waxing.</p>
  <p class="predict__why" hidden>After sunset means the Moon is east of the Sun, so the lit part is growing.</p>
</div>
```

### 9. Self-rate — metacognitive check, no scheduling
This only emits an event. It does not choose the next review date.
```html
<div class="self-rate" data-id="confidence">
  <p class="self-rate__q">How solid does this feel?</p>
  <div class="self-rate__buttons">
    <button class="self-rate__button" data-rating="again">Again</button>
    <button class="self-rate__button" data-rating="hard">Hard</button>
    <button class="self-rate__button" data-rating="good">Good</button>
    <button class="self-rate__button" data-rating="easy">Easy</button>
  </div>
  <p class="self-rate__feedback" hidden aria-live="polite"></p>
</div>
```

## Notes
- Each graded widget emits a `teach:graded` `CustomEvent {id, correct, type}` on `document`. `matching`
  also includes `pair`; `self-rate` also includes `rating`. Core does nothing with the event beyond an
  optional `.recall-score` tally for MCQ + cloze; it's the seam an opt-in progress/SRS module would
  listen on later (kept out of core deliberately). New types are `sequence`, `matching`, `predict`,
  and `self-rate`.
- **Optional learner-model feature keys:** put `data-teach-features`, `data-feature`, `data-skill`,
  or `data-topic` on a graded widget or nearest tagged ancestor. Values may be comma, space, or
  pipe-separated. Without an author key, the learner model falls back to `<type>:<id>`.
- **Thin progress tie-in (optional, agent-side):** after a session, *you* (the teacher) may write a
  markdown [learning record](../LEARNING-RECORD-FORMAT.md) capturing what the learner demonstrated.
  That is the non-adaptive, on-brand way to remember progress — no client-side model required.
- Keep to **≤2 interactive patterns per screen.** Interactivity serves retrieval, never spectacle.
