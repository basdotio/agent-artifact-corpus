# Cognitive Accessibility — skill

Audits a website, app, screenshot, or Figma design against 9 research-based heuristics
for cognitive accessibility — written for **neurodivergent people and anyone whose
processing differs**.

Where WCAG covers perception and motor access, these cover **focus, memory, learning,
decision-making, communication and masking** — the demands that decide whether a product
is usable or exhausting for someone who processes information differently.

The heuristics were formulated from research with autistic adults of working age (see
[Source](#source)) and are written here for the broader neurodivergent population they
serve.

Findings come back with fixes tiered **Quick / Structural / Foundational**, so you can
ship something this week without pretending the deep problem is solved.

## Install

**Claude Code / Claude Desktop** — clone into a folder named after the skill, then copy
it in:

```bash
git clone https://github.com/amachador/cognitive-accessibility-skill.git cognitive-accessibility
cp -r cognitive-accessibility ~/.claude/skills/
```

The folder name has to stay `cognitive-accessibility` — that's how the skill is
identified. Use `.claude/skills/` inside a repo to scope it to one project.

**Claude.ai** — upload the zip under Settings → Capabilities → Skills.

**Other LLMs** — plain Markdown with YAML frontmatter. Paste `SKILL.md` into custom
instructions and attach the six reference files as project knowledge. `scripts/` is not
needed; the skill detects it can't run and carries on.

## Use

```
Audit https://example.com for cognitive accessibility
Review this screenshot for neurodivergent users
Check these Figma frames against the cognitive accessibility heuristics
```

**Depth is automatic.** A single screenshot or frame gets a one-screen **quick triage**;
a flow, several frames, code or a live URL gets the **full report**. Say "quick look" or
"full audit" to override.

### Give it the user and the task

This is the single biggest factor in output quality. A heuristic violation only matters
relative to someone trying to finish something — without that, you get generic advice.
The skill will ask; answering well is worth 30 seconds:

| Tell it | Example |
|---|---|
| **Who the user is** | "Warehouse supervisor, uses this daily, sensitive to motion, reads labels literally" |
| **What task** | "Submit a leave request before Friday's cutoff" — not "use the HR portal" |
| **Stakes** | Required path? Money/health/legal/employment? First use or daily? |

If you don't provide them, the skill states its assumptions in the report header and
proceeds — flagging which findings would change.

### What each input can reach

| Input | Covers | Can't see |
|---|---|---|
| Live URL | Most of the 9 | Settings and notification behavior you don't trigger |
| Screenshot | Sensory load, language, density, standards | Motion, audio, errors, timeouts, personalization |
| Figma frames | As screenshot, plus tokens and naming | Everything runtime |
| Figma flow + code | Nearly all | Real-world timing and interruption |

Whatever it can't test comes back as **questions you can answer in seconds**, not as a
silent gap. Reports are short on purpose — ask for more on any finding.

## The 9 heuristics

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

## Where the report goes

By default the report is published as a **shareable page**, with screenshots of the most
severe findings embedded in it. Where that isn't available, the skill prints the report
and says a page is possible.

## Optional: annotated screenshots

**The skill is plain Markdown and works anywhere.** This is the only part that needs
anything installed, and it is entirely optional.

Given shell access **and** a live URL **and** these two packages already present, the
skill crops a screenshot of each 🔴 Blocker and 🟠 High finding with the problem
outlined:

```bash
pip install playwright pillow && python3 -m playwright install chromium
```

**The skill never installs them for you.** If they're missing it skips the screenshots
and tells you at the end of the report that they're available — the decision to install
anything stays yours. Everything else works identically: all 9 heuristics, the checks,
the fix ladder and the questions.

## Reading the output

| Convention | Meaning |
|---|---|
| **H1–H9** | The nine heuristics |
| **Finding 1, 2, 3…** | Individual issues found (never abbreviated to F1) |
| 🔴 Blocker · 🟠 High · 🟡 Medium · 🟢 Low · ⚪ Can't assess | Severity |
| **Quick / Structural / Foundational** | Fix cost tier |
| ✅ · ⚠️ · ❌ | A step in the task walkthrough worked, caused friction, or broke |

## Contents

```
cognitive-accessibility/
├── SKILL.md                     # Workflow, judgment rules, output rules
├── scripts/
│   └── crop.py              # Cropped, outlined screenshots for live-URL findings
└── references/
    ├── heuristics.md            # The 9 in full + the 6 cognitive demands
    ├── checklist.md             # ~70 checks, "Ask the user" questions, severity rubric
    ├── fixes.md                 # Quick / Structural / Foundational ladder per heuristic
    ├── examples.md              # Real-product precedents, good and bad
    ├── conflicts.md             # When heuristics pull apart — tie-breakers and resolutions
    └── report-template.md       # Output formats and length limits
```

## Source

Alejandro Machado R. (2025). *Heurísticas para el diseño de experiencias inclusivas
para personas dentro del espectro del autismo en edad laboral activa*. Tesis de grado.
Universidad de la República (Uruguay), Facultad de Arquitectura, Diseño y Urbanismo.
Chapter 8, "Heurísticas", pp. 68–112.

Full text: https://hdl.handle.net/20.500.12008/54819

Structure adapted from Nielsen & Molich (1994) and Bastien & Scapin (1993). Translated
from the Spanish original; heuristic names are kept in both languages in
`references/heuristics.md`.

**Complementary, not a replacement** — applying these does not substitute for WCAG
conformance or conventional usability evaluation.

## Licence

This skill is licensed **[CC BY 4.0](LICENSE)** — use and adapt it freely, including
commercially, as long as you credit the author and say what you changed.
`scripts/crop.py` is additionally available under the **[MIT licence](scripts/LICENSE)**.

The thesis this derives from remains **CC BY-NC-ND 4.0** on Colibrí. Cite it through its
handle rather than redistributing the PDF.
