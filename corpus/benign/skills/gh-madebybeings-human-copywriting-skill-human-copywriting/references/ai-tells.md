# AI tells: the pattern catalogue

Patterns that make prose read as model output, ordered from strongest signal to weakest. Group A
justifies an edit on a single sighting. Anything marked *weak alone* needs company from other
tells in the same passage before you act, because careful human writers use it on purpose too.

Sources: the structural passes in Cameron Knight's Human Copywriting v1.1 (sections 12.9, 12.10, 12.14
and 12.15), the staging categories in [blader/humanizer](https://github.com/blader/humanizer) (MIT)
and the community taxonomy in Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing). Descriptions
and examples here are our own wording.

**Why these exist.** A model predicts the most broadly acceptable next token, so by default it
signals importance instead of adding a fact, applies rhythm devices everywhere, inflates ordinary
claims and formats by rule. Word habits drift with each model release ("delve" peaked in 2024).
Structural habits persist, which is why structure leads this list.

**The fix is never a synonym.** State the point the sentence was circling. If a sentence has no
point once the tell is gone, delete it.

---

## A. Staging instead of stating (act on one sighting)

### A1. Not X but Y

**Watch for:** "it's not X, it's Y"; "not just X, but Y"; "not only… but also"; the split form
("This doesn't mean X. It means Y."); the clipped tail (", no guesswork").
**Why it reads as AI:** the negative half rebuts a claim nobody made so the positive half sounds
bigger. Keep a contrast only when the reader actually believes the negative half.

> Before: A website isn't just a brochure. It's your hardest-working salesperson.
> After: Most of our clients' enquiries now arrive through the website before anyone picks up the phone. `[VERIFY: only if the client data says so]`

### A2. One-line closers and dramatic fragments

**Watch for:** a single-sentence paragraph that restates the one above; "That's the real win.";
"Let that sink in."; a run of fragments ("No templates. No shortcuts. No compromise.").
**Why:** it asks the reader to pause without giving them anything new. A short sentence earns its
place when it carries a new fact.

> Before: We rebuilt the checkout in three weeks. Conversion went up 18%. The result? Growth.
> After: We rebuilt the checkout in three weeks and conversion went up 18%.

### A3. Sayings that sound deep

**Watch for:** "at its core", "the real question is", "what really matters", "X is the language
of Y", "the currency of trust", "the architecture of growth".
**Why:** an ordinary point dressed as an aphorism. Replace it with the specific claim.

### A4. A staged run-up before the point

**Watch for:** "Let's dive in", "Here's the thing", "Here's what you need to know", "Honestly?",
"The short answer?", "So, what does this mean for you?".
**Why:** it announces the point instead of making it. Delete the run-up and start with the point.

### A5. Arguing with no one

**Watch for:** "To be clear", "This isn't to say", "Don't get me wrong", "You might think… but",
"A tempting approach would be".
**Why:** it answers an objection that appears nowhere else, usually left over from the model's own
drafting. Keep a rebuttal only if the reader genuinely holds the belief.

---

## B. Rhythm by rule

### B1. Forced triads

**Watch for:** three adjectives, three clauses or three examples in paragraph after paragraph.
**Why:** real lists have the length of their content. Use two when there are two.

### B2. The metronome

**Watch for:** long runs of sentences between 12 and 26 words, all subject-verb-object, with
similar paragraph lengths. `scripts/prose_check.py` reports the share in that band.
**Fix:** let length follow the thought. Don't vary mechanically, and don't insert fragments to hit
a ratio.

### B3. Repeated openers

**Watch for:** three or more sentences or paragraphs in a row that start the same way ("This…",
"It…", "By…", "With…").

### B4. Dashes as the universal connector

**Watch for:** em or en dashes joining clauses. House style bans them outright, and they are
also one of the most-cited tells. Use a comma, colon, parentheses or a full stop.

### B5. Stacked qualifiers *(weak alone)*

**Watch for:** "can potentially help", "may often", "somewhat relatively". Keep hedges that carry
real uncertainty. Cut the ones that are reflexive.

---

## C. Inflation and borrowed authority

### C1. Model vocabulary *(weak alone)*

**Watch for:** delve, leverage, utilise, robust, seamless, crucial, pivotal, comprehensive,
multifaceted, landscape, realm, tapestry, testament, elevate, unlock, empower, supercharge,
game changer, meticulous, intricate, underscore, showcase, navigate (a challenge), foster, boast.
Also: "In today's fast-paced…", "When it comes to…", "It's worth noting…", "Furthermore",
"Moreover", "At the end of the day", "In conclusion".
**Fix the sentence, not the word.** A common word is fine. It becomes a tell when it is doing
filler, exaggeration or abstraction or when several cluster.

### C2. Inflated significance

**Watch for:** "plays a pivotal role", "marks a significant milestone", "reflects a broader
shift", "stands as a testament to".
**Why:** an ordinary fact made to sound historic. Say what happened and let the reader judge.

### C3. Copula avoidance

**Watch for:** "serves as", "stands as", "functions as", "represents", "boasts" where "is" or
"has" is the honest verb.

### C4. Trailing "-ing" riders

**Watch for:** ", making it…", ", allowing teams to…", ", ensuring…", ", highlighting…" tacked
onto a finished sentence.
**Fix:** if the consequence is a real claim, give it its own sentence with its own evidence. If
it isn't, cut it.

### C5. Borrowed authority

**Watch for:** "Studies show", "Experts agree", "Research suggests", "Industry leaders say" with
no named source.
**Fix:** name the study, year and finding or remove the claim. This one is also a truth problem.

### C6. Sales gloss

**Watch for:** "powerful solution", "cutting-edge", "world-class", "best-in-class",
"take your X to the next level", "designed to help you".
**Fix:** replace the adjective with the mechanism or the measured result.

---

## D. Formatting by rule

### D1. Decorative bold

Bold lead-in labels on every bullet, or bold scattered through prose for emphasis the sentence
already has.

### D2. A heading for every idea

Headings on two-paragraph sections, title-case headings on a blog that uses sentence case, and
"Key takeaways", "Final thoughts" or "Conclusion" sections that repeat the body.

### D3. Chat-answer shape in a published piece

Bullets where prose would carry the reasoning better, a summary box that restates the article,
horizontal rules between every section, emoji section markers.

### D4. Uniform bullets

Every bullet the same length, the same grammatical form and ending with a full stop, whatever
its content.

---

## E. Leftovers from the chat

### E1. Chatbot residue

"Great question", "Absolutely!", "I hope this helps", "Feel free to reach out", "Let me know if
you'd like another version", "Here's a polished version".

### E2. Knowledge-limit hedges

"As of my last update", "while specific details are limited", "it's likely that" wrapped around
a fact that should have been checked.

### E3. The heading echoed in the first sentence

A section titled "Why page speed matters" that opens "Page speed matters because…".

### E4. Writing about the previous draft

"This updated version…", "As mentioned above", "Now let's revisit…" when nothing above needs
revisiting.

---

## F. Deeper structure (from the narrative research)

These come from StoryScope (Russell et al., 2026; see `research.md`), which found that models are
identifiable from *what they choose to say* even after style edits. They are the hardest tells to
remove, and the ones that matter most in long-form.

- **Over-explaining the theme.** The piece tells the reader what it means, often twice. Trust the
  reader to draw the conclusion from the evidence.
- **Tidy single-track structure.** One clean argument, no digression, no loose end. Real analysis
  often has a side observation that doesn't serve the thesis and stays because it's useful.
- **Low ambiguity.** Every tension resolved, every tradeoff concluded. Where the evidence is
  mixed, say so and stop.
- **Flat escalation.** Every section at the same intensity. Give the strongest material the most
  room and put it where it will land.
- **The neat lesson ending.** A closing paragraph that turns the piece into a moral. End on the
  last useful fact, the decision or the next step.

---

## When not to act

- Inside quotations, titles, proper names, code or a passage discussing the phrase itself.
- On a *weak alone* pattern with no other tells nearby.
- On text written before late 2022, which was not written by a chatbot.
- When the writer's own sample uses the pattern deliberately. Match the sample.

Judging by feel is unreliable, and human writers absorb model habits too. Several tells together
are the signal; one is not.
