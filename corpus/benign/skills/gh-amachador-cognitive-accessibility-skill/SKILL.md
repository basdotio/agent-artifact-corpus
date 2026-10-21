---
name: cognitive-accessibility
description: Evaluate a website, app, screenshot, or Figma design for cognitive accessibility using 9 research-based heuristics for neurodivergent and cognitively diverse users (sensory load, plain language, guidance, progressive disclosure, customization, cohesion, consistency, error tolerance, focus management). Returns short, scannable findings with fixes tiered quick / structural / foundational. Use when asked to audit, review, or improve a digital product for cognitive accessibility, neurodivergent users, autistic users, neuroinclusive design, cognitive load, sensory overload, or when a WCAG-style review needs to cover cognition rather than only perception and motor access.
---

# Cognitive Accessibility

9 heuristics for **neurodivergent people and anyone whose processing differs**. They
cover what WCAG and Nielsen miss: **focus, memory, learning, decision-making,
communication, masking**. Formulated from research with autistic adults of working age
(Alejandro Machado R., 2025).

| | Heuristic | Do this |
|---|---|---|
| **H1** | Purposeful sensory stimulus | Let people regulate how much stimulus they get. |
| **H2** | Clarity and straightforwardness | Explicit, direct language. No metaphor, no manipulation. |
| **H3** | Assistance | Show the steps and what each one produces. |
| **H4** | Progressive discovery | Information in parts. Gradual change. |
| **H5** | Control and customization | Let people reshape how information is processed. |
| **H6** | Cohesion | Logical hierarchy, familiar names, minimal fragmentation. |
| **H7** | Consistency and standards | Use the patterns other products already taught them. |
| **H8** | Resilience and error tolerance | Errors fast to understand, easy to recover from. |
| **H9** | Focus management | Support concentration, hyperfocus, and time. |

## 1. Context

Ask once, in one short message, then proceed:

> Who is the user (familiarity, and any traits that matter — sensitive to motion, reads
> literally, prone to hyperfocus)? And what specific task are they finishing?

No answer → state the assumption in the report header and continue. Never block.

## 2. Depth — decide it yourself

| Input | Format |
|---|---|
| One screenshot or one frame | **Quick triage** |
| Several frames, a flow, code, or a live URL | **Full report** |

Never ask the user to choose. Honor it if they say "quick look" or "full audit".

**Quick triage**: one question per heuristic (table below), the top 3 fixes, and up to 3
questions. Mark ⚪ **Can't assess** whenever a still image can't show it — never 🟢 Pass
on assumption. If the task involves money, legal, health, employment or identity, or a
🔴 turns up, open by asking for the flow or a live URL.

| | Triage question |
|---|---|
| **H1** | One clear focal point, or several things competing? |
| **H2** | Does every button say what happens? Do icons have visible labels? |
| **H3** | Where the person must act, is there an example or next step? |
| **H4** | Is what's shown proportional to the first decision? |
| **H5** | Can the person change the view, and is it remembered? |
| **H6** | Do names and structure match how the user describes the task? |
| **H7** | Are controls where comparable products put them? |
| **H8** | If they get it wrong, does it say how to fix it? Can they undo? |
| **H9** | Can they tell where they are and how much is left? |

## 3. Evaluate (full report)

**a. Walk the task** as the assumed user would — the *most likely* path, not the correct
one. Record each step: ✅ ⚠️ ❌. Every ⚠️ and ❌ becomes a finding.

**b. Run the checks** in `references/checklist.md` (`S` static · `L` live · `F` flow).

- **Test, don't assume.** On a live URL, check what screenshots hide: motion, reduce-motion
  support, autoplay, keyboard, timers.
- **Verify a negative.** A dead control may be your tooling. Confirm in the source first.
- **Labels must be visible.** `aria-label` and tooltips don't count (rule in `fixes.md`).
- **A 🟢 Pass needs evidence** from that heuristic's own checks, in any format. Nothing
  tested → ⚪ Can't assess.
- **Contact details never satisfy H8.** H8 is about recovering without asking for help;
  a phone number is the fallback it tries to make unnecessary.

## 4. Fix

From `references/fixes.md`, up to three tiers: **Quick** (hours) · **Structural**
(days–weeks) · **Foundational** (weeks–months). Give Quick whenever it exists. One tier
is often enough. Order by impact per cost.

**Screenshots for 🔴 and 🟠 findings** — live URL only. If you can run shell commands
*and* Playwright and Pillow are **already installed**, crop each one with
`scripts/crop.py` (usage in its header) and read every image back before using it.

**Never install anything to make this work.** No `pip install`, no `brew install`, not
even a "quick" one. If the tools are missing, skip the screenshots and close the report
with the offer in `report-template.md`, so the person can decide.

## 5. Report

Follow `references/report-template.md`. Stay inside its length limits.

- **Publish it as an artifact by default** — a shareable page, with the 🔴/🟠 screenshots
  embedded inline. If you can't publish artifacts, print the report and offer it in the
  closing lines.
- **Short.** Leave out precedents, background and evidence; offer them in the closing line.
- **Separators** (`---`) between the opening tables and Findings, and before Over to you.
- **Closing lines** — the offers, then the attribution last. See `report-template.md`.
- **Plain language** — keep the numbers, cut the code.
- **Questions for what you couldn't test** — bold question first, context after.
- **Heading:** `Finding N, <severity> · <outcome>`. Never `F1`.

Before sending, check the report against the nine: emphasis means something (H1), plain
and quoted (H2), every finding has a fix (H3), verdict first (H4), one vocabulary and
one shape (H6/H7), limits stated and no blame (H8), length fits the input (H9).

## Judgment

- "A neurodivergent person may…" — never "neurodivergent people are…". Needs can be
  opposite; the answer is often **control**, not a new default.
- No neurotypical baseline: ask "does this tax a demand?", not "is this normal?"
- A buried setting is not a fix. The default is what most people get.
- When heuristics conflict, use `references/conflicts.md`.
- Don't restate WCAG. Mention it only where it changes cognitive load.
- Critique the artifact, never the people who made it.

## Files

| File | For |
|---|---|
| `references/heuristics.md` | The 9 in full |
| `references/checklist.md` | Checks, severity rubric, questions to ask |
| `references/fixes.md` | Fixes per heuristic, by tier |
| `references/examples.md` | Real-product precedents |
| `references/conflicts.md` | When two heuristics pull apart |
| `references/report-template.md` | Output formats and length limits |
| `scripts/crop.py` | Optional screenshots — live URL, shell required |

## Source

Alejandro Machado R. (2025). *Heurísticas para el diseño de experiencias inclusivas
para personas dentro del espectro del autismo en edad laboral activa*. Tesis de grado.
Universidad de la República (Uruguay), Facultad de Arquitectura, Diseño y Urbanismo.
Chapter 8, "Heurísticas", pp. 68–112. Full text: https://hdl.handle.net/20.500.12008/54819

Structure adapted from Nielsen & Molich (1994) and Bastien & Scapin (1993).
