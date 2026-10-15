# QA campaign — <app name>

> Template. Replace everything in `<angle brackets>`, delete what doesn't apply, keep the shape.
> The rules this plan is built on are in the skill's `SKILL.md`; don't restate them here.

**Started:** `<date>` · **Build at start:** `<commit>` · **Skill at start:** `<qa-campaign commit>` · **Status:** `<in progress | closed <date> at <commit>>`

**Offline depth:** `<none | short | full>` — because `<the clue in the code: a pending-writes queue, a cache, no server…>` (SKILL.md R1) ·
**Fix mode:** `<fix severe | fix all | report only>` · **Commits:** `<at each gate | never — leave for review>` ·
**Docs live in:** `<path, and whether it is versioned>` ·
**Build users get:** `<store release | flavor | the debug build a device manager pushes>` — findings are rated for that one (SKILL.md §2.3) —
asked once at setup (SKILL.md §2.1), not per finding.

**What already existed** (SKILL.md §2.1, asked before building anything) —
**Devices:** `<which, and any attached device that is off-limits>` ·
**Test server:** `<address; disposable copy or shared; whose data it holds>` ·
**Accounts:** `<which, and their roles>` · **Data not to touch:** `<…>` ·
**Earlier QA work:** `<test plans, an earlier campaign, scripts — used as a baseline, not overwritten | none>`.
Anything the campaign built or started on top of that: `<list, with who agreed>`.

---

## 1. Scope and order

One platform at a time. Within a platform: the shell, then one process per module, then every
**second context** that can invalidate the first (another form factor or window size, offline, a
second device or account), then the build — the order R1 gives. Add and remove rows freely; the
shape that matters is *gate per process*.

A gate closes on what was **proved**: anything its criterion needed and nobody could tell is written
down as **unproven** and keeps it open, or goes to the queue as itself (R1).

| # | Process | Area | Where | Gate |
|---|---|---|---|---|
| 00 | Setup | harness, fixtures, session injection, absence sweeps for the whole product (§6) | — | the harness drives the app and reads its store, and the app on the device reaches the server (`net.sh reach`) |
| 01 | Shell | launch, **login / logout** (the screen and the injected-session path — the one real login is a queue item, R11), navigation, settings, theme, **non-UI entry points** (deep links, notifications, widgets) | `<primary target>` | every entry point reachable, back stack sane, logout leaves nothing behind |
| 02… | `<one row per module>` | full control sweep, online then offline (short or full depth), + this module's absence-sweep rows (§6) | `<primary target>` | inventory covered; P0/P1 fixed, P2 fixed or deferred |
| … | `<second form factor / window size>` | layout, navigation, `<orientations or window sizes>`; **state that lives in a pane** — delete, sign out or share away what a detail pane is showing | `<secondary target>` | no dead ends specific to this layout; nothing left in a pane after it's gone |
| … | Offline / degraded — *only at full depth; delete otherwise* | every write queued and drained; nothing lost, nothing lied about | `<primary target>` | STORE and API agree after the network returns |
| … | Multi-context | same account in two places (the second client is the API adapter — the web needs a typed login); **B** and **C** for anything shared, one account per role (R7) — *delete only if nothing is shared and there are no roles* | `<both>` | conflicts, prunes and permissions verified on each side |
| … | Minimum OS | the shell, plus every inventory row that depends on a permission or an API level, on an emulator at the app's **minSdk** | `<min-version device>` | nothing crashes and nothing is unreachable at the oldest version the app claims to support |
| … | Release build | **earlier processes re-driven where a later fix touched their module**, signed/minified artefact, **version number above the highest one shipped from any branch**, size and packaging checks, smoke test, **upgrade in place** over the previous release with data (R14) — previous release built from its tag with the same key; **the real login again** (queue it now: not debuggable, no injection, no STORE) | `<primary target>` | the release artefact runs and upgrades |
| … | Publication gate | store/host requirements, policy, branding | — | `<store or host>` accepts it |

## 2. Devices

| Alias | What | Notes |
|---|---|---|
| `<primary>` | `<emulator / browser profile / simulator>` | the default; `--device <alias>` in the harness |
| `<secondary>` | `<the second form factor, if any>` | `<what changes at this size>` |

## 3. Accounts

| Alias | Role |
|---|---|
| A | owner — creates everything |
| B | recipient — receives the shares, or a role with fewer rights *(one row per role)* |
| C | negative control — receives nothing, or the role with the fewest rights |

*B stays wherever the app can have more than one signed-in identity — it is what one session leaves
for the next. Delete C only when there is nothing to be denied: no sharing and no roles (R7).*

What signs each account in — a password, an app password, or a token made with the server's secret —
lives in `qa.credentials.json` (gitignored in this repo; `<generated from <file> — regenerate when that
file changes | filled in by the human>`), read **only by the scripts** — the adapter
signs in through the API with it. **No password is ever typed by the agent**, not even from that file
(R11): the session is `<made of …>` and injected by `<mechanism>`; where injection is impossible, the
sign-in is queue item `<#>`. **App under test:** `<app id>` — `<whether a real install of the app is
on the test device, and how the campaign avoids touching it>`.

## 4. Fixtures

Everything the campaign creates carries **`QA_`** in `<the field the server stores as sent — checked
by reading one fixture back through the API>` and is deleted at the gate that created it. Destructive
tests run only against these (R10).

⚠️ `<list here which of your backend's deletes are permanent rather than a trash>`

⚠️ Side effects the clean-up can't undo — emails, push notifications, public links, webhooks, charges:
`<which actions trigger which, and how the campaign keeps them away from real people>` (R10).

## 5. Oracles

| Oracle | How it is queried here |
|---|---|
| UI | `<harness> dump` / `<harness> a11y` |
| STORE | `<harness> db <alias> "<sql>"` / `<harness> file <alias>` — and `<project-side reader>` for formats the harness can't decode |
| API | `<your adapter>` — or, for a backend you don't own, `<vendor console / second device>` |
| EYE | `<harness> shot` + review |
| LOG | `<harness> log` — the app's own log, secrets hidden (`android.secretKeys` for this product's credentials); never clear the buffer |
| REF | `<the implementation that defines what the domain supports — vendor web client, spec>` |

## 6. Absence sweeps (R4: S1 data never shown · S2 dead control · S3 expected absence · S4 stuck when something fails)

Run **once, for the whole product, at setup** (process 00); each finding goes under its module. Each
module's process re-reads its rows before writing its catalogue, and re-runs the sweeps for that
module only if its code changed since. Record every finding, including the ones that turn out to be
measurement errors — and say which ones were.

What each grep did, not only what survived it (R4) — the numbers have to add up:

| Sweep | Candidates | Discarded (by the rule) | Driven | Confirmed | Unproven |
|---|---|---|---|---|---|
| S1 | | | | | |
| S2 | | | | | |
| S3 | | | | | |
| S4 | | | | | |

| ID | Module | Sweep | Sev | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| ABS-01 | | S1 | | | | |

> An S3 row — and any row that came from comparing with a sibling — starts its `Status` with what the
> absence turned out to be: **defect** · platform difference on purpose · the backend does not offer it ·
> product decision (→ queue, no severity) · not applicable · unknown (→ queue). Only the first is a
> finding (R4).

## 7. User queue (R2)

Everything that needs a human, collected here instead of blocking a process. When an answer changes
an assumption, the gates closed on it reopen. At a gate, put it to the human in two groups (R2): the
items that change what happens next, one at a time; everything else as one list with the
recommendations below, answered in one go.

| # | What | Why it needs you | Recommendation | Gates closed assuming | Reopen on resolution |
|---|---|---|---|---|---|
| 1 | | | | | |

## 8. Log

One row per process, added at its gate.

| Process | Build | Date | Covered | Result | Gate |
|---|---|---|---|---|---|
| 00 | | | [`00-setup.md`](00-setup.md) | | |

## 9. Close-out

Written when the last gate closes: total findings, total fixed, total deferred with their queue ids,
the biggest one per process, the final full-suite result, and **what remains open and why**. When
there was an earlier campaign: how many findings came **from a change** since it and how many it
**missed**, with their ids. Then offer the friction log upstream, without the project in it
(SKILL.md R12) — `<issue link | not sent: why>` — and set **Status** at the top to
`closed <date> at <commit>`.
