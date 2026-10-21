# Checks, questions, severity

**Assessability:** `S` static image is enough · `L` needs the live product · `F` needs
the whole flow.

With a live URL, run the `L` checks — don't downgrade them to questions. Keyboard,
reduced-motion, autoplay and timers are testable in seconds and hide the severe
findings.

Each heuristic ends with **Ask the user** — the questions to hand back when you
genuinely couldn't test. Put them in the report as an inline checklist, not prose.

**In the report, bold the question and put it first**; any evidence or caveat of yours
goes after it, unbolded. A reader scanning only the bold text must still know what
you're asking.

**Ask in plain language.** These go to designers, not engineers — no selectors, no API
names, no browser internals. "Turn on reduce motion and reload" beats "does it honor
`prefers-reduced-motion`". Format details in `report-template.md`.

## The visible-label rule — read before checking H2

A label resolves a cognitive-accessibility finding only if the person **sees it without
acting**.

- ✅ **Rendered text** — visible to everyone looking at the screen.
- ❌ **`title` tooltip** — requires hover and a wait; absent on touch entirely.
- ❌ **`aria-label` / visually-hidden text** — reaches screen readers only; **invisible
  to a sighted person who can't decode the icon**, who is exactly who this skill is for.

So: an icon with a perfect `aria-label` and no visible text is **still a finding here**.
Don't mark it as passing, and don't prescribe ARIA as the fix — that's a WCAG audit's
job, and this skill explicitly doesn't restate WCAG. Mention it only as a secondary note
alongside the real fix.

---

## H1. Purposeful sensory stimulus

| | Check | |
|---|---|---|
| 1.1 | Count elements competing for attention. Is there one clear primary, or several equals? | S |
| 1.2 | Count hues and large saturated fills. Does color mean something consistent, or is it decorative? | S |
| 1.3 | Dark mode: present, and complete? Any surviving light surface in modals, legacy views, iframes? | L |
| 1.4 | Anything animating, looping, autoplaying or moving without user intent? Pausable — near the element, not only in settings? | L |
| 1.5 | Does the site respond to the operating system's "reduce motion" setting? Check the stylesheets **and** the scripts — a motion library ignores the CSS setting. Report the result in plain words. | L |
| 1.6 | Do transitions move elements across the screen where a fade would do? | L |
| 1.7 | Any sound without explicit user action? Is volume separate from system volume? | L |
| 1.8 | Pop-ups, modals, toasts, interstitials per session — how many unrequested? Disableable? | L/F |
| 1.9 | Notifications: controllable per channel? Is the default quiet? | L |
| 1.10 | Do images/icons disambiguate (recognition), or just decorate (extra load)? | S |

**Ask the user**
- Does anything move, flash, loop or autoplay that I can't see here?
- Is there sound anywhere — alerts, hover, background, video? What's the default?
- How many interruptions (pop-ups, toasts, banners, emails, pushes) does a person get in
  a normal working hour?
- Turn on "reduce motion" in your computer's settings and reload. Does anything look different?
- Is there a dark mode? Does *every* screen honor it, including older ones?

---

## H2. Clarity and straightforwardness

| | Check | |
|---|---|---|
| 2.1 | Quote every CTA. Does each state what happens? Flag "OK", "Continue", "Learn more", "Get started", "Submit". | S |
| 2.2 | Do icon-only controls have **visible** text labels? A `title` tooltip or `aria-label` does **not** satisfy this — see the visible-label rule below. | S |
| 2.3 | Any metaphor, idiom, pun or abstraction that must be decoded to act? Quote it. | S |
| 2.4 | Passive voice or nominalization where active is shorter? Quote and rewrite. | S |
| 2.5 | For every offer/upsell/consent: is there an explicit, equally visible, plainly-named decline? Flag confirmshaming and loss-framed declines. | S |
| 2.6 | Urgency, scarcity, guilt or emotional pressure in the copy? Quote it. | S |
| 2.7 | Does success feedback say *what* happened, not just that something did? | L |
| 2.8 | Are expectations set before the task — length, steps, what's needed, end result? | S/F |
| 2.9 | Is important information visually reinforced, or is everything one weight? | S |
| 2.10 | Any label ambiguous between two plausible readings? | S |
| 2.11 | Is any decision-relevant information available **only on hover** — file size, exact time, full name, status, counts? Render it instead. | S/L |

**Ask the user**
- Paste the copy for your error, confirmation and empty states — those are usually the
  weakest and I can rarely reach them.
- Which CTA do people most often click by mistake, or ask about before clicking?
- Does anything in the flow use a countdown, a limited-time offer, or a pre-ticked box?

---

## H3. Assistance

| | Check | |
|---|---|---|
| 3.1 | Multi-step task: are the steps, current position and endpoint visible? | F |
| 3.2 | Is each step's outcome stated before the person commits? | F |
| 3.3 | **Blank-canvas test:** at any point of creation (new doc, empty state, prompt, empty list) — template, example or suggestion, or just an empty field? | S |
| 3.4 | More than one route to key functionality (nav, search, command palette, direct link)? | L |
| 3.5 | When input is rejected, does the message teach — why, and how to fix? | L |
| 3.6 | Can people leave themselves a note on an item to resume later? | L |
| 3.7 | Anything the person must remember between steps that the UI could carry? | F |
| 3.8 | Is an open-ended choice bounded into concrete next actions? | S |

**Ask the user**
- What do people most often ask support or a colleague about? That's the missing guidance.
- Where does the flow branch, and is the consequence of each branch stated before it's chosen?
- Can someone complete this task without being shown once first?

---

## H4. Progressive discovery

| | Check | |
|---|---|---|
| 4.1 | Count discrete data regions shown at once (widgets, tables, charts, cards). Could any be deferred? | S |
| 4.2 | Options shown that are irrelevant now — seasonal, role-inapplicable, unavailable? | S |
| 4.3 | Infinite scroll on a large collection? Any total, position, or pagination? | L |
| 4.4 | Onboarding/coachmarks: visual, **skippable**, re-openable? | L |
| 4.5 | Is the information at first contact proportional to the first decision? | S |
| 4.6 | If a redesign: gradual rollout, opt-out, a way back, docs on what moved? | L |
| 4.7 | Does one task force switching between contexts, tabs or apps? | F |

**Ask the user**
- How long is this flow end to end — screens, fields, minutes? Does the person know that
  before starting?
- Has this been redesigned recently? Was there a way back to the old version?
- Can a person stop halfway and resume without losing work or their place?

---

## H5. Control and customization

| | Check | |
|---|---|---|
| 5.1 | More than one view of the same content where the task would benefit? | L |
| 5.2 | Can people sort and filter by what matters to them — and does it **persist**? | L |
| 5.3 | Any large result set without filters or refinement? | L |
| 5.4 | Can layout, ordering or grouping be rearranged or hidden? | L |
| 5.5 | Can the person define what counts as important (priority, pin, mute)? | L |
| 5.6 | Can contexts be kept separate — accounts, profiles, workspaces? | L |
| 5.7 | Any interaction that's synchronous-only, with no written/async equivalent? How much notice is given? | F |
| 5.8 | Are personalization settings discoverable, and do they survive across devices? | L |

**Ask the user**
- What do people customize first, and what do they ask to customize but can't?
- Do their filter/sort/view choices survive a reload? A new device?
- Does any part of this require being present live — a call, a live chat, a
  real-time-only step?

---

## H6. Cohesion

| | Check | |
|---|---|---|
| 6.1 | Do nav structure and labels match how users describe their work, or the internal org chart / schema? | S/F |
| 6.2 | Same concept, same name everywhere? List terms used for two things, and two terms for one thing. | F |
| 6.3 | One visual language across all areas — type scale, spacing, components, interaction model? | F |
| 6.4 | Is one task's information fragmented across pages, tools, tabs or apps? | F |
| 6.5 | Can you predict where an unseen feature lives from the structure you've seen? | F |
| 6.6 | Design system in use — applied consistently, including legacy and embedded areas? | S/F |

**Ask the user**
- Which parts of the product were built by different teams or at different times?
- Is there a term your team uses that users don't, or vice versa?
- How many separate tools does one person touch to finish this task?

---

## H7. Consistency and standards

| | Check | |
|---|---|---|
| 7.1 | Are primary controls where comparable products put them? Flag relocations. | S |
| 7.2 | Do names use the verbs and nouns people already use for the action? | S |
| 7.3 | Any custom control reinventing a standard one? What does it gain in return? | S |
| 7.4 | Do icons carry conventional meanings? Any used against convention? | S |
| 7.5 | Colors conventional for state — red destructive, green success — and consistent? | S |
| 7.6 | Do standard keys work: Esc, Enter, Space/PageDown scroll, ⌘/Ctrl+S, ⌘/Ctrl+Z, browser Back? | L |
| 7.7 | Does anything break muscle memory **without** a way to restore it? | L |

**Ask the user**
- What tools does this person use right beside yours all day? Match those patterns.
- Did you move or rename anything in the last release? Can people get it back?
- Are there custom keyboard shortcuts that override platform standards?

---

## H8. Resilience and error tolerance

| | Check | |
|---|---|---|
| 8.1 | Quote every error. Does each give what happened, why, and the next step? | L |
| 8.2 | Does any error blame the person? Rewrite. | L |
| 8.3 | Any bare code, trace or opaque string with no human explanation? | L |
| 8.4 | Is every destructive or permanent action confirmed — better, undoable? | L |
| 8.5 | Are third-party-affecting actions (send, mass mention, share, publish, invite) guarded by confirmation or an undo window? | L |
| 8.6 | Are send/publish actions reversible — edit, delete, recall, undo-send? | L |
| 8.7 | Does the system catch likely mistakes *before* they're committed? | L |
| 8.8 | Any countdown, timeout or time-limited decision on a non-urgent action? Postponable? | L |
| 8.9 | Does search/filter tolerate typos and partial matches — with exact match available? | L |
| 8.10 | Is work autosaved and synced, or losable by navigation, crash or forced restart? | L |
| 8.11 | Is help reachable without asking a person? | L |

**Ask the user**
- Paste your three most common error messages verbatim.
- What's the worst thing a person can do here by accident? Is it undoable?
- Does anything time out? What happens to work in progress when it does?
- What action, once taken, notifies other people? Is there a window to take it back?

---

## H9. Focus management

| | Check | |
|---|---|---|
| 9.1 | Is remaining time visible for timed things, without switching context? | L |
| 9.2 | Focus / DND mode — **granular** (app, person, channel, schedule, place, urgency) or all-or-nothing? | L |
| 9.3 | Do alerts map to distinct, consistent urgency levels, or arrive at one intensity? | L |
| 9.4 | Does the interface pull attention toward what needs action, or compete with it? | S |
| 9.5 | Anything supporting breaks, session length, or noticing that time has passed? | L |
| 9.6 | Is there a low-distraction reading/writing mode? | L |
| 9.7 | After an interruption, can the person see where they left off? | F |

**Ask the user**
- How long does a person typically stay in this product in one sitting?
- Can they tell how much time is left in whatever they're doing, without leaving it?
- What can interrupt them here, and can they turn each source off independently?
- If they're pulled away mid-task, what do they see when they come back?

---

## Severity

Always write the emoji **and** the word: 🔴 Blocker · 🟠 High · 🟡 Medium · 🟢 Low.
The emoji makes the report scannable; the word carries the meaning if color is lost.

Assign from effect on the person, not implementation cost.

| | Severity | Definition |
|---|---|---|
| 🔴 | **Blocker** | Prevents task completion, causes irreversible loss, or triggers overload severe enough to end the session. Unrecoverable destructive actions · unexplained errors with no way forward · no way to decline a consequential offer · forced time limits on consequential decisions · content reachable only one way and that way is blocked. |
| 🟠 | **High** | Completable, at substantial cost — repeated confusion, real anxiety, needing another person's help, or likely error. Manipulative copy · ambiguous primary CTAs · uncontrollable motion or autoplay · no undo on actions that notify others. |
| 🟡 | **Medium** | Steady friction, degrades autonomy over time. Unlabeled icons · dense screens with no drill-down · non-persistent filters · inconsistent naming. |
| 🟢 | **Low** | A refinement. Worth raising, doesn't block or meaningfully tax. |

**Escalate one level** when the issue is on a **required** path · the task is
**high-stakes** (money, health, legal, employment, identity) · the barrier **repeats**
across the product · **several demands** are taxed by one element · there is **no way to
configure around it**.

**De-escalate one level** when a discoverable, well-signposted control changes the
behavior. Always state the default anyway.
