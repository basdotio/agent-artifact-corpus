# Output format

**Short by default.** The reader should be able to act after the first screen, then ask
for more. Say less and offer the rest.

## Format is chosen automatically — never ask

| Input | Format |
|---|---|
| One screenshot or one frame | **Quick triage** |
| Several frames, a flow, code, or a live URL | **Full report** |

If the person says "quick look" or "full audit", do that instead.

## Length limits

| Part | Limit |
|---|---|
| Verdict | 2 sentences |
| Fix in this order | ≤ 5 rows |
| Task walkthrough | ≤ 6 rows + 1 closing line |
| Findings | ≤ 6 written out; the rest as one line each under **Also noticed** |
| Each finding | Observed ≤ 2 sentences · ≤ 2 heuristics · Cost 1 sentence · 1 row per fix tier |
| Working well | ≤ 3 bullets |
| Tensions | Only if real · ≤ 2 sentences |
| Over to you | ≤ 4 questions |

Leave out by default: precedents, background, technical evidence, extra fix tiers. The
closing line offers them.

## Labelling

| Thing | Written as |
|---|---|
| Heuristic | `H1`–`H9` with its name: `H2 Clarity and straightforwardness` |
| Finding | `Finding 1`, `Finding 2`… — **never `F1`** |
| Fix tier | `Quick` / `Structural` / `Foundational` |
| Severity | 🔴 **Blocker** · 🟠 **High** · 🟡 **Medium** · 🟢 **Low** · ⚪ **Can't assess** — emoji and word, always |
| Walkthrough step | ✅ as expected · ⚠️ friction · ❌ breaks — never mixed with severity |

- Finding heading is exactly `Finding N, <severity> · <outcome>`. No heuristics in it.
- Heuristics go in a bulleted list under **Observed**, one short clause each.
- `H` only ever means heuristic.

---

## Full report

```markdown
# Cognitive accessibility audit — [product / screen]

| | |
|---|---|
| **Evaluated** | [URL / file / frames] · [date] |
| **User** | [given, or ⚠️ assumed: …] |
| **Task** | [given, or ⚠️ assumed: …] · [stakes, if high] |
| **Method** | 9 cognitive accessibility heuristics (Machado R., 2025) |
| **How to read this** | **H1–H9** = heuristics · **Findings** numbered 1–N · 🔴 Blocker / 🟠 High / 🟡 Medium / 🟢 Low |

## Verdict

[2 sentences: where the load concentrates and whether the task can be done.]

| | Heuristic | Result | Findings |
|---|---|---|---|
| **H1** | Purposeful sensory stimulus | 🟢 Pass | — |
| **H2** | Clarity and straightforwardness | 🟠 Issues | Findings 1, 3 |
| … | | | |

**Fix in this order**

| Order | Fix | Tier | Resolves |
|---|---|---|---|
| 1 | [Fix] | Quick | 🟠 Finding 1 |

## Task walkthrough

| # | Step | Expected | Actual | Result | Finding |
|---|---|---|---|---|---|
| 1 | [What the person does] | [What they expect] | [What happens] | ❌ | 🟠 Finding 1 |

**[Reached the answer in 4 steps, after 1 dead end.]**

---

## Findings

### Finding 1, 🟠 High · [Outcome in plain words]

**Observed** — [Quoted string, location or measurement. ≤ 2 sentences.]

**Heuristics**
- **H2 Clarity and straightforwardness** — [the breach]

**Cost** — [Demand + consequence, 1 sentence.]

**Fix**

| Tier | Action |
|---|---|
| Quick | [Concrete fix] |

> Before: "…" · After: "…"   ← copy fixes only

### Also noticed
- 🟢 [One line per extra finding]

## Working well
- **[What works]** (H1) — [one line]

## Tensions
**H1 ↔ H9.** [Who wins for this task, and why — 2 sentences max.]

---

## Over to you — I couldn't test these

| | Question | Affects |
|---|---|---|
| ☐ | **[Question the reader can answer in seconds?]** [Optional one-line context.] | H1 |

[Closing lines — see "Closing lines" below]
```

---

## Quick triage

```markdown
# Quick triage — [product / screen]

| | |
|---|---|
| **Evaluated** | [file / frame] · [date] |
| **User · Task** | [given, or ⚠️ assumed: …] |
| **Method** | 9 cognitive accessibility heuristics (Machado R., 2025) |

> **Share the full flow or a live URL for this one.** [Only if the task involves money,
> legal, health, employment or identity, or a 🔴 turned up.]

**Task:** [Can it be done from this screen? One line.]

| | Heuristic | Result | Note |
|---|---|---|---|
| **H1** | Purposeful sensory stimulus | 🟠 Issues | About 20 offers compete; none is the task |
| **H2** | Clarity and straightforwardness | 🟠 Issues | "WIN YOUR RM300 · Get now" — doesn't say what happens |
| **H5** | Control and customization | ⚪ Can't assess | Needs the live app |
| … | | | |

**Top 3 fixes**
1. [Fix — replacement copy verbatim if it's copy]
2. …
3. …

---

## Over to you

- ☐ **[Question?]** [Optional context.]

Share the flow or a live URL for a full report.
[Closing lines — see "Closing lines" below]
```

---

## Closing lines

End every report with these, in this order. Include only the ones that apply, each on
its own line. Keep them to one line each — they are offers, not apologies.

1. **Always:** `Ask me to expand any finding, show the evidence, or suggest more fixes.`
2. **If you couldn't publish it as a page:** `I can publish this as a shareable page —
   just ask.`
3. **If 🔴/🟠 findings have no screenshots and the input was a live URL:** `I can add
   cropped screenshots of the top findings. That needs Playwright and Pillow installed
   locally — say the word and I'll give you the command.` Never install them yourself.
4. **Always, last:** `Heuristics: Machado R., 2025 —
   https://hdl.handle.net/20.500.12008/54819`

## Publishing as a page

Default to publishing the report as an artifact where that's available — it's easier to
share and read than chat text.

- Embed 🔴/🟠 screenshots **inline as data URIs**; externally hosted images won't load.
- Keep the same structure, separators and length limits.
- If artifacts aren't available, print the report and use closing line 2.

## Worked finding — calibration

### Finding 1, 🟠 High · The number field never shows the format it requires

**Observed** — The only instruction is "Ingrese el número de Expediente". The field
silently requires `000000-000000-00`, and the error says only "El formato del número
ingresado no es correcto".

**Heuristics**
- **H8 Resilience and error tolerance** — the error withholds the rule
- **H3 Assistance** — no example at the field

**Cost** — Decision-making: the person retries blind or gives up.

**Fix**

| Tier | Action |
|---|---|
| Quick | Show `Formato: 000000-000000-00 (ej. 980000-000102-02)` beside the field and in the error. |
| Structural | Insert the hyphens as the person types. |

---

## Writing rules

**Walkthrough**
- Take the most likely path, not the correct one.
- Describe steps in the person's terms, not the interface's.
- Every ⚠️ and ❌ links to a finding. Close with one line: steps, dead ends, done or not.

**Over to you**
- **Question first, in bold**; context after, plain. The bold part must stand alone.
- Answerable in seconds. Say when a severity depends on the answer.
- ❌ *I found 0 `prefers-reduced-motion` blocks in 3,297 CSS rules… Does anything change?*
- ✅ ***Turn on "reduce motion" and reload. Does anything look different?*** *I found no sign the site responds to it.*

**Plain language** — keep the numbers, cut the code.

| Instead of | Write |
|---|---|
| "`input[name='url']` at y=173" | "The large search box in the banner" |
| "`.subline a` 9.33px, 3.54:1" | "The details line is 9px light grey" |
| "`localStorage` is empty" | "The choice isn't remembered between visits" |

Technical terms are fine in the Fix column and inside quoted interface copy.

**Tensions** — resolve with `conflicts.md`: name both heuristics, say who wins for this
task and why. Delete the section if there are none.

## Rules

- Quote the real string. Write the replacement. Never "make it clearer".
- Name the cognitive demand in **Cost**.
- A label must be **visible** to count — never prescribe `aria-label` or a tooltip as the fix.
- Verify a negative before reporting it — a dead control may be your tooling.
- "A neurodivergent person may…", never "neurodivergent people are…".
- Critique the artifact, never the people who made it.
