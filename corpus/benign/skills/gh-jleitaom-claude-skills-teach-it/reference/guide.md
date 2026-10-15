# Essentials guide — theory only

File: `<TOPIC>_ESSENTIALS.md`. Plain English, adjusted to the level setting. Read
top to bottom once, then used as a reference.

## Header

```markdown
# <Topic> — The Essentials

> A <level> guide in <N> parts. Each part has live figures in the lab.
>
> **Interactive lab:** [`<TOPIC>_ESSENTIALS_LAB.html`](<TOPIC>_ESSENTIALS_LAB.html)
> — open it in your browser.
```

## Parts (adapt to the topic; 4–6 parts, keep this order of ideas)

| Part | Covers |
|---|---|
| 1. The big picture | What it is (intuition + everyday analogy), what problem it solves, how it differs from nearby fields (table), core vocabulary (table: term, meaning, example), the core loop or mechanism as one diagram |
| 2–4. How it works | The key concepts, one section each, building on each other. The one or two equations worth knowing, each explained in words. One example worked by hand with real numbers, every step shown. The family tree of methods and when to use each |
| 5. In the real world | 2–3 real applications as case studies (format below), how it's evaluated in practice, common pitfalls (table: pitfall, symptom, fix) |
| 6. Limits | When NOT to use it, with simpler alternatives; open problems; glossary |

Number sections (§n) so the lab figures and quizzes can refer to them. Add a table
of contents with anchor links. In Parts 1–4, teach with simple illustrative
examples (a made-up shop, a toy dataset), clearly framed as illustrations. A
one-line mention of a real system is fine where it helps, without numbers.

## Real-application case study format

```markdown
### <System or company> — <what it does>
- **Problem:** what they needed to solve
- **How <topic> is used:** the concept from §n, mapped to their setup
- **Why it fits / what they gave up:** trade-offs, and what simpler thing they compared against
- **Source:** <link to paper, engineering blog or talk> — ✅ read in full
```

Fewer cases, better checked:
- Pick 2–3 cases with a primary source you can open and read in full: the paper,
  the company's own engineering blog, a recorded talk.
- Every number must come from a source you read. If you can't open the original
  (blocked, paywalled, only mirrors or search snippets), drop the number and keep
  the story, or pick a better-documented case.
- Mark the source line ✅ read in full, or ⚠️ secondhand with the reason, so the
  user sees it in the guide, not only in chat.

## Example kickoff outline (topic: transformers, beginner)

```
Part 1 — The big picture (§1–4)
  Figures: attention as a heatmap over a sentence; the encoder/decoder diagram
  Real use: Google Translate's switch to neural translation
Part 2 — Attention, step by step (§5–7)
  Figures: playable Q·K·V on a 4-word sentence; softmax temperature slider
Part 3 — Building blocks and training (§8–9)
  Figures: animated transformer block; loss curve as data grows
Part 4 — In the real world (§10–12)
  Case studies: machine translation, code completion, protein structure
Part 5 — Limits (§13–15)
  Figures: cost vs context length chart; "should I use a transformer?" helper
```

## Visuals inside the .md

- Diagrams: Mermaid (flowcharts, sequence, state) or ASCII when simpler.
- Each part points to its lab figures: "▶ Try it in the lab: <figure name>".
- Static charts belong in the lab, not as images in the .md.

## Style

Short paragraphs, tables over prose where it helps, bold for key terms. Every
abstract idea gets a concrete example.
