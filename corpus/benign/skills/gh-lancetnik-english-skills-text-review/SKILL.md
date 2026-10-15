---
name: text-review
description: "Review the learner’s writing or replies during conversation practice: explain errors in their preferred language and provide a corrected version. Use for text checks and smalltalk practice; English is the default target language."
---

# Reviewing text in the target language

## Languages

- **Target language** — the language of the text being reviewed. Defaults to English; if the text is in another language, that becomes the target language (until explicitly changed).
- **Explanation language** — use the user's stated preference or learner profile; otherwise use the language of the request without assuming it is their native language. Respond in the explanation language; quotes and corrections are in the target language.

When the user submits their own text in the target language for review, work through the structure below. Keep a supportive tone: acknowledge what works first, then cover mistakes, without diminishing the effort.

## Response structure

1. **Overall assessment** — 2–3 sentences: what is clear and good, the approximate level of the text (A2/B1/...), and any systemic problems. In conversational mode this becomes an explicit **"What worked well" (in the explanation language)** block FIRST: 2–4 specific fragments quoted verbatim with a ✓ and a one-line reason (a rule applied, a natural collocation, a target structure hit). Do not defer praise to the end — it must come before the error list.
2. **Errors by category**, each formatted as:
   - ✗ *original fragment*
   - ✓ *corrected fragment*
   - A brief explanation in the explanation language (the rule, why it is wrong).
   Categories: grammar (tenses, articles, agreement, prepositions), word choice (wrong word in an otherwise grammatical sentence), style and naturalness (calques from the user's native language, unnatural phrasing), spelling and punctuation. Collect typos in a single list.
3. **Improved version** — the full rewritten text (depth of edits depends on what the user asked for: by default, fix errors and unnatural phrasing without changing meaning or the author's voice).
4. **Wrap-up** — the 2–3 most frequent problems in this text and a concrete suggestion on what to work on.

## Rules

- Do not invent errors: if a fragment is correct but could sound better, mark it as a "stylistic suggestion", not an error.
- If a fragment is ambiguous and the intended meaning is unclear, ask a clarifying question instead of guessing a correction.
- For long texts (300+ words), give a brief summary of the problems first, then the detailed breakdown.
- At the end, offer a mini exercise targeting the most frequent mistake.

## Typos vs real errors (hit-list discipline)

If the user has authorized maintaining learning notes, use their existing error file (conventionally `errors.md`, relative to the learning workspace, not the installed skill folder). Only patterns that genuinely need retraining go into it: recurring misspellings, homophone confusions, false friends, calques, grammar gaps. A one-off slip — a skipped letter, a dropped space, a missed capital — is noise, not a pattern: correct it inline in the review, but do NOT add it to the error file unless it appears more than once. Homophone slips (e.g. their/there, hear/here) DO count as patterns even if they occur once. When in doubt, fix in the review and watch for recurrence in later sessions.

## Conversational mode (smalltalk sessions)

When the user is practicing live dialogue (writing "spoken" replies in a conversation, not submitting a standalone text for review):
- Keep the conversation alive: react to the content naturally (in the target or explanation language) as part of the reply, then run the review.
- Use a compact variant of the structure: **"What worked well" block first (in the explanation language)** (2–4 specific ✓ fragments quoted verbatim + why) → errors by category (✗ / ✓ + short rule in the explanation language) → corrected version of the user's fragment → 1-line wrap-up with the 2–3 most frequent problems.
- Prioritize the learner’s stated goals and recurring errors. Without a profile, start with articles, prepositions, calques, word forms, tense markers, and typos.
- Celebrate correct usage explicitly ("correct ✓") — praising what works builds confidence.
- Keep follow-up conversation questions in the target language and explanations in the explanation language. Match corrected examples to the learner’s productive level; preserve their voice and sentence variety.
