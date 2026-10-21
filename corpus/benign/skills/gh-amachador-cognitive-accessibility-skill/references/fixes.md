# Fix ladder

Every finding gets fixes at up to three tiers. Pick from here; adapt to the product.

| Tier | Cost | Scope | Who ships it |
|---|---|---|---|
| **Quick** | Hours | Copy, labels, attributes, defaults, one toggle | One dev or designer, no meeting |
| **Structural** | Days–weeks | Components, layout, flow, state, persistence | A team, one cycle |
| **Foundational** | Weeks–months | IA, design system, content model, research | Roadmap item |

**The visible-label rule**

A label only counts as a cognitive-accessibility fix if the person can **see it without
acting**. This rules out the two things most often proposed:

| Mechanism | Who it reaches | Counts as a fix? |
|---|---|---|
| **Rendered text** beside or under the control | Everyone looking at the screen | ✅ Yes |
| `title` tooltip | Mouse users who hover and wait; nobody on touch | ❌ No — a supplement at best |
| `aria-label` / `sr-only` text | Screen-reader users only; **invisible to everyone else** | ❌ No — different barrier, different audit |

A person who can see the icon perfectly well but cannot infer what it means is the case
this skill exists for. An accessible name does nothing for them. Adding one is correct
and worth doing — it is simply not the answer to *this* finding, and must never be
offered as the Quick tier for an unlabeled control.

The same applies to any information hidden behind hover: file sizes, exact timestamps,
full names, status. If it matters to a decision, render it.

**When to still mention ARIA:** as a secondary note (`also add an accessible name for
screen-reader users`), never as the fix itself.

**Rules**
- Always offer the Quick tier if one exists — then say what it leaves unsolved.
- One tier is often the right answer. Don't manufacture three.
- A Quick fix that masks a Foundational problem must say so: *"ships today, does not
  resolve the underlying naming inconsistency."*
- Order by impact-per-cost. A Quick fix that removes a blocker outranks a Foundational
  one that removes friction.

---

## H1. Purposeful sensory stimulus

| Tier | Fix |
|---|---|
| **Quick** | Honor `prefers-reduced-motion: reduce` — swap transforms for opacity, cut durations, freeze loops. |
| | Remove `autoplay`; add `muted` + `playsinline`; require a click to start. |
| | Add a pause control **on** the looping element, not only in settings. |
| | Make dark mode complete: audit for surviving light surfaces in modals, legacy views, embedded iframes, print styles. |
| | Drop max-saturation fills to a tint; keep contrast, lose the vibration. |
| | Default notifications to off/digest instead of on/instant. |
| **Structural** | Motion toggle in the UI, persisted (localStorage or account) and synced across devices. |
| | Notification preference centre: per channel, per event type, per urgency. |
| | Density setting (comfortable / compact / minimal) applied via one layout token. |
| | Chrome-on-demand: hide toolbars while the person is creating, reveal on intent. |
| **Foundational** | Motion system with tiers — *essential* (conveys state), *supportive* (guides attention), *decorative* (cut under reduce-motion). Every animation declares its tier. |
| | A stimulus budget per screen: how many simultaneous attention-claiming elements are allowed, enforced in review. |
| | Color as a semantic system, not a palette — every hue maps to a meaning, arbitrary color is not available. |

**Examples:** Brave (autoplay off by default) · Notion (chrome hides while typing) ·
Chrome download page (in-context pause button) · counter-examples: SuccessFactors
(arbitrary saturated color), Windows 11 + Excel (incomplete dark mode).

---

## H2. Clarity and straightforwardness

| Tier | Fix |
|---|---|
| **Quick** | Rewrite every CTA as **verb + outcome**: "Get started" → "Start 30-day trial — no card required". |
| | Add **visible** text labels to icon-only controls. See the visible-label rule above — `aria-label` is not a substitute. |
| | Replace the figurative label with the literal one: "Unleash your workflow" → "Create a workflow". |
| | Give the decline an equal, plainly-named option: "No thanks" — never "I'd rather stay disorganized". |
| | Passive → active: "Your request has been submitted" → "We received your request". |
| | State the consequence before the button, not in fine print below it. |
| | Say what succeeded, not that something did: "Saved" → "Saved to Q3 Planning". |
| **Structural** | Microcopy components with required slots for *action*, *outcome*, and *reversibility*, so an ambiguous CTA can't be built. |
| | A confirmation/feedback component that always renders what changed and where it went. |
| | Glossary component surfacing definitions inline for domain terms. |
| **Foundational** | Content design standard: reading level target, active voice, banned-pattern list (confirmshaming, false urgency, ambiguous CTAs), enforced in design review. |
| | Content model where every action declares its consequence as data, so labels can't drift from behavior. |

**Examples:** MATLAB (CTA names the trial and its length) · macOS Finder (optional icon
labels) · counter-examples: Windows 10 "Limited experience" decline, Edge/TocToc
emotional-pressure prompts.

---

## H3. Assistance

| Tier | Fix |
|---|---|
| **Quick** | Replace every empty state with 2–3 examples or templates. |
| | Add a one-line "what happens next" under the primary action. |
| | State cost up front: steps, time, what to have ready. |
| | Turn rejection messages into teaching ones: what's wrong, why, how to fix. |
| | Offer starter prompts/suggested actions instead of a bare input. |
| **Structural** | Step indicator showing position, total, and each step's outcome. |
| | Inline validation that explains as it corrects. |
| | A notes/description field on saved items so people can leave themselves context. |
| | Follow-up suggestions after a result, to bound the next choice. |
| | Second route to key functions: search, command palette, or direct link. |
| **Foundational** | Task-based IA — organize around what people are doing, not around features. |
| | Guided flows for high-stakes or infrequent tasks, with a review-before-commit step. |
| | Assistive layer (recommendations, autofill, drafting) that removes recall work. |

**Examples:** Notion & Word (templates at creation) · Grammarly (explains the mistake,
not just the fix) · Perplexity (follow-up questions bound the next choice) · Notion
formulas (graphical picker + examples) · counter-examples: Excel formulas (pure recall),
Dia (bare prompt field as the only entry point).

---

## H4. Progressive discovery

| Tier | Fix |
|---|---|
| **Quick** | Add counts and position: "Showing 1–20 of 340", "Chapter 3 of 8". |
| | Make every tutorial, coachmark and intro **skippable** — and re-openable later. |
| | Hide options that don't apply right now (seasonal, role-gated, unavailable). |
| | Collapse secondary regions by default. |
| **Structural** | Pagination or drill-down instead of infinite scroll. |
| | Split long forms into steps with saved progress. |
| | One primary region per screen; everything else behind a tab or disclosure. |
| | Persistent progress indicator for long documents or flows. |
| **Foundational** | Staged rollout infrastructure: opt-in period, a way back to the previous version, and documentation of what moved where. |
| | Progressive disclosure as a system-wide pattern with rules for what surfaces when. |
| | Role-based views so people see only their slice. |

**Examples:** Hey.com Screener (one item at a time) · Facebook & Figma (revert to
previous UI + docs) · counter-examples: Workday (dense dashboard, no drill-down), DGI
(seasonal tools always visible).

---

## H5. Control and customization

| Tier | Fix |
|---|---|
| **Quick** | Persist filters, sort and view choice across sessions. |
| | Remember the last-used view per person, per context. |
| | Add sort/filter to any list that can exceed one screen. |
| | Let people mute, pin or star to define their own priority. |
| **Structural** | View switcher — list / cards / board / calendar / timeline over the same data. |
| | Saved views, shareable and named. |
| | Rearrangeable and hideable layout regions. |
| | Async equivalent for every synchronous interaction: written summary, recording, transcript. |
| **Foundational** | Profiles, spaces or workspaces to compartmentalize contexts. |
| | Preference architecture: one store, synced across devices, surviving redesigns. |
| | Async-first communication norms — synchronous only with advance notice and an agenda. |

**Examples:** Obsidian (graph view alongside list) · Outlook/Gmail (granular priority)
· Arc (profiles and spaces) · Superlist (visual personalization synced across devices) ·
counter-examples: Zendesk (one fixed grouping), IBM Support (52k results, no filters).

---

## H6. Cohesion

| Tier | Fix |
|---|---|
| **Quick** | Fix naming collisions: one concept, one term, everywhere. List every term used for two things and every two terms used for one. |
| | Rename functions to the user's vocabulary, not the database's. |
| | Apply existing design-system components to the one screen that skipped them. |
| **Structural** | Unify the navigation model across modules — same placement, same interaction, same hierarchy. |
| | Consolidate fragmented resources for one task into one surface. |
| | Bring legacy and third-party-embedded areas into the design system. |
| **Foundational** | Rebuild IA from card sorting / tree testing with real users rather than the org chart. |
| | Single design-system governance across teams, with adoption tracked. |
| | Shared content model so the same entity means the same thing in every module. |

**Examples:** Uruguayan State portal (shared style guide across agencies) · Teams
(unified notes, calendar, contacts, calls) · counter-example: SAP (modules with
diametrically different interaction models).

---

## H7. Consistency and standards

| Tier | Fix |
|---|---|
| **Quick** | Restore standard keyboard behavior: Esc closes, Enter submits, Space/PageDown scrolls, ⌘/Ctrl+S saves, ⌘/Ctrl+Z undoes, browser Back works. |
| | Move relocated primary controls back to the conventional position — or make the position configurable. |
| | Rename to the conventional verb: "Grabar" → "Emitir"/"Issue"; "Commit" → "Save". |
| | Use icons with their conventional meanings; red = destructive, green = success. |
| **Structural** | Replace bespoke controls (custom select, custom scroll, novel gesture) with library components. |
| | Let people restore a layout you changed. |
| | Adopt platform conventions per platform rather than one cross-platform compromise. |
| **Foundational** | Adopt or align to a mature design system rather than maintaining bespoke UI. |
| | Document the platform conventions the product commits to, and review against them. |
| | When a standard must be broken, ship a migration: announcement, docs, temporary way back. |

**Examples:** Nanoscope + MATLAB (shared patterns across vendors aid transfer) ·
counter-examples: Teams call controls (relocated, non-configurable), Zureo ("Grabar" to
issue an invoice).

---

## H8. Resilience and error tolerance

| Tier | Fix |
|---|---|
| **Quick** | Rewrite every error as **what happened / why / next step**. |
| | Remove blame: "You entered an invalid date" → "That date is in the past. Pick today or later." |
| | Never show a bare code — pair it with a human sentence. |
| | Add a confirmation to destructive actions; require typing the name for irreversible ones. |
| | Add a send delay (5–30s undo window) before messages go out. |
| | Remove countdowns from non-urgent decisions; add "Remind me later". |
| **Structural** | Soft delete with a restore window, stated in the dialog. |
| | Autosave + sync; never lose work to navigation, crash or forced restart. |
| | Fuzzy/partial matching in search and filters, with exact match available. |
| | Proactive checks before commit: missing attachment, mass mention, out-of-hours send, unusual amount. |
| | Self-service help reachable without contacting a person. |
| **Foundational** | Error taxonomy: every error class has an owner, a plain-language explanation and a recovery path. |
| | System-wide undo rather than per-feature confirmations. |
| | Architecture where no single action can destroy unrecoverable work. |

**Examples:** Gmail (undo send, missing-attachment warning) · Slack (confirm before mass
mention, especially out of hours) · Outlook (recall/replace) · counter-example: macOS
update timer that can't initially be postponed.

---

## H9. Focus management

| Tier | Fix |
|---|---|
| **Quick** | Show remaining time for anything timed — meeting, session, deadline, long job. |
| | Surface the existing OS/app focus mode instead of hiding it in settings. |
| | Stop sending non-urgent notifications instantly; batch them. |
| | Direct attention: make the element that needs action the only animated or highlighted thing. |
| **Structural** | Granular do-not-disturb: per app, person, channel, schedule, place, urgency. |
| | Alert-level taxonomy — map urgency to channel and intensity, consistently. |
| | Low-distraction reading/writing mode that hides non-essential chrome. |
| | Resume affordance: show where the person left off after an interruption. |
| **Foundational** | A product-wide attention model: what may interrupt, when, and at what intensity. |
| | Break and session-length support built into long workflows. |
| | Calendar/time integration so the product knows what else is competing for attention. |

**Examples:** Windows 11 Focus Sessions (timers + ambient sound) · Notion Calendar
(remaining time visible without context switch) · iA Writer (focus mode, highlight
current passage) · macOS granular Focus · counter-example: Windows 10 Focus Assist
(all-or-nothing, enables hyperfocus).
