---
name: article-review
description: Review and improve articles, essays, blog posts, diaries, and business or technical writing. Use when the agent needs to evaluate a text's quality, structure, persuasiveness, reader value, tone, safety, or human distinctiveness; produce a scored editorial report; prioritize revisions; or rewrite selected passages. Triggers include requests such as "review this article", "evaluate this essay", "critique this blog post", "記事を評価して", "記事をレビューして", or "改善案とリライトを出して".
---

# Article Review

## Overview

Review text like an editor, not a casual commenter. First classify the piece as Mode A (information and utility) or Mode B (emotion and empathy), then score it on seven dimensions, flag factual or social risk, and finish with prioritized improvements plus a small number of high-leverage rewrites.

## Input Expectations

- Require the text itself. Ask for the title only if it is missing and would materially improve the report.
- Treat target audience, publication context, and the author's goals as optional context, not blockers.
- Match the user's language. Default to Japanese when the surrounding conversation is Japanese.
- If publication context is missing, review as if the text could be published publicly.

## Mode Selection

1. Determine the text's primary reader value.
   - `Mode A: Information and utility first` for technical articles, business writing, explainers, guides, or argument-driven analysis.
   - `Mode B: Emotion and empathy first` for essays, columns, diaries, memoir-like writing, or voice-driven reflection.
2. If the text mixes both, choose the dominant mode and note the secondary lens in one short line.
3. Keep the chosen mode stable through the report unless the text clearly changes purpose midstream.

## Review Workflow

Follow these steps in order:

### 1. Build context

- Skim the full piece before judging details.
- Identify thesis, intended audience, likely publication context, and the main promise to the reader.
- Note early risk markers: unsupported claims, sweeping generalizations, borrowed phrasing, tonal mismatch, or likely misreadings.

### 2. Decide whether verification is needed

- For factual, technical, legal, medical, financial, or time-sensitive claims, verify against current primary sources when feasible.
- When verification is incomplete, mark the claim as unverified instead of guessing.
- Never inflate the score for reliability when key support is missing.

### 3. Score the seven dimensions

- Use the rubric in `references/review-rubric.md`.
- Score each dimension from `0.0` to `5.0` with one decimal place.
- Be strict. If uncertain between two scores, choose the lower score.
- Treat the overall score as editorial judgment, not a simple arithmetic average.

### 4. Find the highest-leverage fixes

- Isolate the few changes that would most improve the piece's publishability, clarity, impact, or safety.
- Prefer structural and meaning-level fixes over cosmetic line edits.
- Keep the top improvement list short and prioritized.

### 5. Rewrite only the most valuable passages

- Rewrite `1-3` passages by default.
- Preserve the author's intent and voice unless the user explicitly asked for a stronger tonal shift.
- Use rewrites to demonstrate the fix, not to replace the entire article unless the user asked for a full rewrite.

## Scoring Rules

- `5.0`: Exceptional. Information writing is near textbook-grade, or voice-driven writing is memorable and deeply affecting.
- `4.0`: Strong professional quality. Comfortable to share or publish with minor edits.
- `3.0`: Competent and readable, but ordinary or uneven.
- `2.0` or below: Clear editorial work is still needed.
- For `炎上リスク・社会的配慮`, higher is safer.
- If the safety score is below `3.0`, explicitly say that publication should be reconsidered until revised.
- If a claim cannot be verified, say so plainly and lower the reliability score as needed.

## Output Pattern

Use the default report structure in `references/report-template.md` unless the user asked for a different format.

Always include:

- mode decision
- overall score
- safety score
- human distinctiveness score
- per-dimension findings with strengths and fixes
- top three improvements
- rewrite examples for the most important passages

## Default Rules

- Evaluate the text, not the author.
- Separate taste from craft. Do not hide concrete editorial issues behind vague preference language.
- Quote only the minimum needed to support a point.
- Do not invent sources, evidence, or author intent.
- When a piece is mixed or experimental, reward successful ambition but do not excuse confusion.
- Prefer actionable edits over abstract encouragement.
- If the user asks for a fast review, shorten the prose, not the rigor.

## References

- Read `references/review-rubric.md` before assigning scores.
- Read `references/report-template.md` before writing the final report.
