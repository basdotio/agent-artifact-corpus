---
name: human-copywriting
description: >-
  Use when writing or rewriting publishable prose (articles, landing pages, case studies,
  proposals, social, emails) so it reads as if a person chose every sentence. Edits structure
  before wording, ranks AI tells by strength, locks facts and never invents detail. Triggers
  on 'humanise this', 'make this sound less like AI', 'rewrite this naturally', 'polish this
  article'. Not for translation, summaries or grammar-only fixes.
license: MIT
---

# Human Copywriting

Write and rewrite prose that reads as if a specific person chose every sentence for a specific
reader, while keeping every fact, number, name and caveat exactly as the source has it.

Version 1.0.0 by [Made By Beings](https://madebybeings.com), adapted from Cameron Knight's
Human Copywriting Project Skill v1.1 (a ChatGPT Project skill), which builds on Stephen Offer's
[human-voice](https://github.com/stephenoffer/human-voice) (MIT). The pattern catalogue also draws
on [blader/humanizer](https://github.com/blader/humanizer) (MIT) and Wikipedia's
[Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) guide.
Licences and attribution: `NOTICE` in the repository root.

## Layering with your own voice

This skill is a base layer. Put your own style guide on top of it.

| Layer | Governs |
|---|---|
| **This skill** | Structure, selectivity, rhythm, the AI-tell catalogue, fact integrity. |
| Your style guide | Voice, vocabulary, greetings, warmth, habits. Wins on voice. |
| The task or channel | Format and what the piece must contain. Wins on format. |

Facts beat all three.

## Reference files (read on demand)

- `references/full-guide.md`: registers, the 18 editing passes, anti-overcorrection, self-critique
  and audit output. **Read it before any Full-depth job** (published article, homepage, proposal).
- `references/ai-tells.md`: the pattern catalogue, strongest first, with before and after pairs.
  Read it for any rewrite of AI-drafted text.
- `references/research.md`: what the studies actually show about human and model writing. Cite
  from here, never from memory.
- `scripts/prose_check.py`: a mechanical pre-flight (dashes, Oxford commas, stock phrases,
  sentence-length band, repeated openers). It flags. It never decides.

## The core idea

Machine-sounding prose is mostly an editorial problem, not a vocabulary problem. A model makes the
choice that fits the widest range of readers, so its drafts explain everything, weight every
point equally, resolve every tension and end on a lesson. A person writing for one reader makes
uneven, specific choices: more space for what matters, nothing for what the reader already knows,
and an ending that stops when the point has landed.

So work in this order, and touch wording last:

1. **Intent**: what must the reader understand, feel, decide or do?
2. **Shape**: does the structure suit this channel, or is it chat-answer shape?
3. **Substance**: which real details, numbers and mechanisms carry the piece?
4. **Selectivity**: what gets a paragraph, what gets a sentence, what goes?
5. **Rhythm**: does sentence length follow the thought, or sit in one band?
6. **Syntax**: stacked model habits (cleft openers, trailing "-ing" riders, not X but Y).
7. **Stance**: say what you think where the evidence supports it.
8. **Consistency**: one term per concept, one dialect, one relationship with the reader.
9. **Diction**: inflated words, stock transitions.
10. **Mechanics**: punctuation and house style.

## Non-negotiables

1. **Never invent support.** No invented fact, statistic, date, quote, citation, customer, result,
   anecdote, testimonial or personal detail, to make copy feel human or for any other reason. If
   a missing detail matters, ask one compact batch of questions. If it must be visible, mark it
   `[SOURCE NEEDED]`, `[VERIFY]` or `[FIGURE?]`. Otherwise write around the gap.
2. **Lock factual invariants in a rewrite**: numbers, dates, names, product and feature names,
   code, commands, paths, URLs, citations, the strength and direction of every claim, caveats,
   scope conditions and attributions. A smoother sentence is never worth a changed fact.
3. **Protect voice invariants** where they work: humour, bluntness, regional phrasing, an odd but
   natural sentence shape, a memorable awkward detail, a real preference or objection. The
   rewrite should still sound like the same sender.
4. **Never fake humanness.** No planted typos, random slang, forced lowercase, Unicode tricks,
   invisible characters, manufactured self-corrections or invented experiences.
5. **Detector-aware, never detector-led.** Detectors are one weak signal. Never degrade writing to
   move a score, and never promise that text will pass one.

## House defaults (edit these)

These are Made By Beings' defaults. Change them to match your own style guide.

- **No em dashes and no en dashes** in prose. Rewrite with a comma, colon, parentheses or a new
  sentence; never swap in a double hyphen. Don't overuse colons and semicolons to compensate.
- **No Oxford comma**: "design, build and launch". Reword if a list is ambiguous without it.
- **Australian English** unless the client, publication or source uses another dialect. Keep one
  dialect throughout.
- Hyphens in real compounds (drop-down, well-known) and required characters inside URLs, code,
  names and identifiers are untouched.

Apply this skill by default whenever you draft publishable prose. Relax it for literal tasks
(translation, extraction, summaries, grammar-only edits, legal or safety wording, quotes) and when
the user asks for a different style. Relax only the rule that conflicts.

## Modes

**Fix mode** (the user supplies prose): preserve meaning and claim strength, find the
communication job, lock invariants, strip assistant shape, cut what the reader doesn't need,
rebalance emphasis, rebuild rhythm, sharpen supported stance, test the ending and return the
finished copy.

**Generate mode** (the user supplies a brief): treat the brief and supplied sources as the fact
boundary. Start from the actual situation, not generic polished copy. Use the concrete detail you
have, give the most space to what matters most, and let the reader make obvious connections. Run
the same critique before returning.

## Depth

| Depth | Use for | Do |
|---|---|---|
| Quick | captions, short paragraphs, low-stakes copy | Silent job check, strip obvious tells, protect invariants. No audit. |
| Standard | web sections, social, sales copy, internal docs | The compact workflow below once, plus one self-critique. |
| Full | published articles, key pages, proposals | Read `references/full-guide.md`; run all 18 passes, the read-aloud and ownership tests, up to three critique rounds and the claim-preservation check. Run `scripts/prose_check.py` on the result. |

Stop when another pass would make the writing different rather than better.

## Compact workflow

1. Understand the job: reader, what they know, what they should do next.
2. Lock facts, then note voice worth keeping.
3. Gather the author's real material (a number, a failed attempt, a client's own words, a
   constraint). This is the strongest human signal there is, and it cannot be faked.
4. Decide what matters. Give it room. Compress or cut the rest.
5. Leave obvious implications unstated. Once a point lands, move on.
6. Rebuild shape for the channel: fewer headings, prose where bullets were reflexive, no recap.
7. Break symmetry that meaning doesn't justify (equal sections, a triad in every paragraph).
8. Rebuild rhythm so sentence length follows the thought.
9. Remove stacked syntax habits and templates (see `references/ai-tells.md`).
10. Sharpen stance where evidence supports it. Keep real uncertainty.
11. Unify voice: one term per concept, one dialect, stable formality.
12. Clean diction last.
13. Test the ending: delete the last paragraph; if nothing necessary goes, leave it out.
14. Read it aloud in your head.
15. Ownership test: could almost any company have published this? If yes, restore real context.
16. Claim check: no new claims, no changed numbers or names, no strengthened certainty, no
    dropped caveats, no changed links.

## The five tells that survive a rewrite

After any rewrite, search specifically for these, because they come back most often:

1. A "not X but Y" contrast, including the split and clipped forms.
2. A one-line closer that restates the paragraph above it.
3. A dash doing the work of a comma or colon.
4. A triad where the meaning has two items, or four.
5. A bold label on every bullet or a heading on every small idea.

## Output

Return the finished copy first. Don't announce that it was humanised, don't attach a score or
change log unless asked, and keep unresolved source gaps visible. If the user asks for an audit,
report only register, main patterns removed, invariants preserved, open sourcing gaps and residual
risks.
