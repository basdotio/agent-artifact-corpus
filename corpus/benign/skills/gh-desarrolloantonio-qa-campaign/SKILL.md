---
name: qa-campaign
description: Test a whole product before release and come out with evidence instead of confidence — gated processes, every control inventoried, sweeps for what the product is MISSING, every claim checked against more than one oracle, and no regression test that has not been watched failing first. Use when asked to test an app or a feature properly, to audit one end to end, to prepare a release or a store submission, or when "we tested it" has to mean something. An Android device harness is included; other platforms need their own. Not for writing unit tests, chasing one known bug, or setting up CI.
license: MIT
metadata:
  keywords:
    - qa
    - release
    - testing
    - android
    - ios
    - web
    - offline-first
    - regression
---

# QA campaign

A process for testing a whole product before release, in a way that produces evidence instead of
confidence.

**The scripts in `harness/` are the cheap half.** What finds defects is the set of rules below.
Each earned its place on a real release campaign — most because its absence let a real bug through,
a few because they stopped the campaign from lying about what it had done. Read them before running
anything.

The rules are generic. The **examples are not**: they come from the campaigns this was extracted from
and tried on — a multiplatform client for a self-hosted server (notes, boards, bookmarks), a bookmarks
client, a travel log, and a fleet terminal with a realtime cloud database. When a rule mentions a
trash, a shared note or a server quirk, read it as *"the kind of thing"*, and substitute your own.

**Where things are.** This file: the rules (§1), how a campaign runs (§2), what the harness gives you
(§3). Read §1 before running anything; the rest is read when you reach it.

| When | Read |
|---|---|
| Setting a campaign up | §2.1, then [`references/setup-notes.md`](references/setup-notes.md) at steps 5 and 6 |
| Filling in the plan, a process report, an inventory | [`templates/`](templates/) |
| Asking the server what is true | [`adapters/README.md`](adapters/README.md) |
| Driving Android, or something makes no sense | §3, [`harness/README.md`](harness/README.md), [`harness/android/GOTCHAS.md`](harness/android/GOTCHAS.md) |
| Another platform | [`harness/README.md`](harness/README.md) — the seven capabilities a harness must provide |

---

## 1. The rules

### R1 — Gates, not a checklist

Split the product into **sequential processes** and put a **gate** at the end of each. A *module*
here is a feature area of the product — a top-level destination and the screens under it — not a
build module. What closes
a gate depends on the **fix mode** chosen at setup (§2.1):

- **Fix severe** *(default)* and **fix all**: every finding the mode covers is fixed and verified in
  the running system; the rest is **deferred with an id in the user queue (R2)**.
- **Report only**: every finding is **documented** to the standard of §2.3 — exact steps, the
  oracles' evidence, the file:line, the likely fix — and nothing in the product is changed.

In every mode: the full suite is green (R13), the fixtures are cleaned (R10) and the run report is
written. Items sitting in the user queue are not "open work" for gate purposes — that is what the
queue is for.

The order, one platform at a time:

```
shell → one process per feature module (primary target, online)
→ second form factor / window size → offline → second device or account → release build
```

When the product's devices are **shared between people** — a fleet app, a shift terminal — switching
the signed-in person is the core of the shell, not a late process: put it in the shell gate.

Later processes are the ones that can invalidate earlier work if they change; that is why they come
after, not before. Drop what does not apply. `templates/CAMPAIGN.md` is this order as a table;
§2.2 is what closing a gate means step by step.

**How deep offline goes** is decided once, at setup, from the code — not by habit. Whether to test
offline at all depends on one thing: **does the product talk to a server?** How deep depends on
what it keeps locally:

| Depth | The product… | Offline testing |
|---|---|---|
| **None** | talks to no server | no offline gate, no API oracle, no adapter — the rest of the method stands |
| **Short** | talks to a server but keeps no data of its own (always online), or keeps a **read-only cache** | inside each module's process only: every screen says clearly that it can't reach the server, nothing spins forever (S4), nothing pretends a write was saved, and it recovers when the network returns. No gate of its own |
| **Full** | keeps its own data and **writes it locally first** (offline-first) | each module's controls driven online *and* offline, **and** the drain-and-reconcile gets a gate of its own: every write queued, sent later, conflicts resolved, nothing lost |

The kind of storage is a hint, not the answer: a local database can be only a cache (short), and a
preferences file can hold a list of pending changes (full). The clues that decide it:

- **a queue of pending writes** — a background job that sends changes later (WorkManager,
  BackgroundTasks, Background Sync), or a *pending / dirty / syncStatus* field in the stored data →
  **full**. It has to carry the **user's own writes**: a shared logging or telemetry worker is not an
  offline-first store, and counting it marked every app in a repository "full" (audit);
- **screens read the local copy first** and refresh from the server afterwards, *and* edits land
  locally before the server answers → **full**;
- local reads but every edit waits for the server → **short** (a cache);
- network calls and nothing stored beyond settings and the session → **short**.

When the clues disagree, take the deeper level. **An outbox nobody reads back** — writes queued and
sent, never shown again — is full depth without conflicts: what replaces the conflict and mix checks
is the retry policy against duplicates (unique work, KEEP vs REPLACE), whether the input the job
needs is still there when it finally runs, and what the user is shown when it gives up. At either depth, **test the recovery on its own**:
"it says it can't reach the server" and "it works again when the network returns" are two checks. A
map said the first and never did the second — the P1 was in the half that's easy to skip (measured).

**At full depth, test the mix, not only the two halves.** For every kind of write: make it offline,
then — **before the queue drains** — make another change to the same record online, and check both
reach the server. An online save that sends only its own field and then marks the row as synced
throws away what was waiting in the queue. Measured: four P0s in one campaign, in three modules,
none of which showed up offline-only or online-only.

A flat checklist of N scenarios × M devices is never executed. A short list of gates with a hard
stop at each one is.

**A gate waiting on the human** — a device to create, an account to fill in — doesn't stop reading.
The next process may be **prepared from the code**: its inventory, its suspects. Nothing is driven,
fixed or committed for it until the gate closes, and what was prepared is re-read then, because the
human's answer can change it. When **the gate's own criterion** depends on the human — "every entry
point reachable" needs them signed in to another app — close it **assuming the queue item**, name the
item in the log, and reopen when the answer comes back different (R2).

**UNPROVEN is a result, and it never closes a gate.** Three outcomes look alike in a report and are
not: it works, it is broken, and *nobody could tell*. The third one gets written down with that word,
in the report, next to what it was about. The harness says it too, in its own vocabulary — a refusal,
`NOT RUN`, `NOT PROVEN`, `UNPROVEN` — and none of those is a pass. What produces one: a selector that
matched two different controls, a measurement the device would not give (a density, a screen size), an
oracle that was not available, a report whose origin can't be pinned to this run, a mutation that
changed nothing, a candidate nobody could drive, a flow that needs an account you don't have. An
unproven item either keeps the gate open or goes to the human queue as itself (R2) — turning one into
a pass, quietly, is the cheapest way there is to make a whole campaign worthless.

### R2 — Defer everything that needs the user

Anything that needs a human — a real login, a physical device, a product decision, any
**irreversible action on real data** (emptying a trash, deleting an account) — goes into a **single
queue at the end of the plan**, not inline. Otherwise the campaign stalls on
its first blocker and never restarts.

Every queue entry records **which gates were closed assuming what**. When the human answer changes
that assumption, those gates reopen — the same logic R1 applies to platform and form factor.

**Putting the queue to the human.** Don't walk it one question at a time: thirteen questions in a
row tire the human, who stops reading them halfway (measured). Two groups, in this order:

1. the few items that **change what the campaign does next** — a real login, a scope decision, a
   suspect to chase — one at a time;
2. everything else — "fix or accept" on a small finding, a wording, a display format — in **one
   list**, each with your recommendation and why in one line, answered in one go.

**Don't stop for each finding.** A campaign that asks after every bug turns the human into the
bottleneck and gets abandoned; findings go into the run report and the gate is where the human
reads them. Stop **at once**, and only, when:

1. **A P0** — data loss, a security hole, or real data at risk. The human needs to know now, not at
   the gate. First check **which builds reach it**: a screen or path gated by build type or flavor
   is rated for the builds users get — a campaign stopped for a P0 in a debug screen only its staging
   flavor shows (measured). A P0 found while setup is still **looking**, before its round of
   questions, goes to the human in that same round, first.
2. **A blocker** — the finding makes the rest of the process untestable (the app won't launch,
   login is broken). Carrying on only produces noise; say what is blocked and what still can be
   tested.
3. **Leaving the agreed ground** — what setup agreed on (§2.1, "what already exists"): creating or
   deleting a device, building or starting a server, downloading and running something, pointing at
   a server that is not the agreed test server, or any irreversible action on data the campaign did
   not create. Ask first.
4. **Calibration, once per campaign** — after the **first P1-or-worse finding**, show it and
   confirm the severity and the fix mode match what the human expects. Then carry on uninterrupted.

### R3 — Inventory before catalogue

Before testing a module, **enumerate its controls**: every button, menu entry, dialog, gesture and
field of its UI state — *and* every entry point that is not a control: deep links, share targets,
notification actions, widgets, shortcuts. Those live in the manifest or the router, not the UI
layer; a shell gate that says "every entry point reachable" without them has not tested them.
`templates/inventory.md` is the shape. Some entry points exist **only with certain data** — a Home
section shown only when something is coming up was one of a screen's two ways in, and on the day it
was tested it wasn't there (measured). Note them as such, and re-check "every entry point reachable"
when the data changes, not only when the code does.

**A delegated inventory is a list of suspects.** A subagent reading a large area is fast and
thorough, but it states claims from the code with the same confidence as facts, and two of them didn't
hold on the device (measured). Take its rows as controls to drive; a finding exists only once driven.

Enumerating from the code gives you everything the product **has** — which most plans never do, so
they test a guess at the product instead of the controls that exist. What it cannot see is what the
product **lacks**. That is R4.

### R4 — The absence sweeps (what the product does NOT have)

R3 is **structurally blind to missing features**: a feature that doesn't exist leaves nothing to
enumerate. So run five sweeps — **once, for the whole product, at setup** (§2.1), filing each finding
under its module. *The whole product* is the app under test plus the shared modules it depends on —
in a repository of several standalone apps, not the whole repository (a sweep run repo-wide returned
391 hits, half of them another app's; audit). Before writing a module's catalogue, re-read that module's findings; re-run the
sweeps for it only if its code changed since. Each sweep is a **grep for candidates followed by a
fixed discard list** — reproducible, but not judgement-free, and the discard list is part of the
rule:

| # | Sweep | How | Discard | Catches |
|---|---|---|---|---|
| **S1** | Data held but never shown | For each field of your domain models / UI state, grep for references in the UI layer. Zero references = candidate. Also **values the screen computes and decides with but never states** — today's date on a calendar, the one-year window it asks the server for — which no grep of fields finds (measured). | fields that are ids, timestamps, or sync bookkeeping; credentials and session tokens (never shown by design) | A settings screen that never says which server or user you're connected to |
| **S2** | Dead control | Empty or TODO handlers, *including* empty lambdas passed down as arguments: Compose `grep -rnE 'onClick *= *\{ *\}|\w+ *= *\{ *\}|/\* *TODO' --include='*.kt'`; web `grep -rnE '=\{\(\) *=> *\{\}\}|href="#"' --include='*.tsx'`; SwiftUI `grep -rn 'action: {}' --include='*.swift'`. Then routes: every `navigate(x)` has a matching destination. | previews and showcase modules — **filter them mechanically**, they are most of the hits: a candidate inside a `@Preview` function is not a dead control (walk back from the enclosing `fun` through its annotation lines); read-only chips, disabled placeholders; an empty **default value** in a function's signature (`onClick: () -> Unit = {}`) — for those, follow the callers: a candidate only if a real screen leaves it empty | "Privacy Policy" and "Help" buttons that do nothing (a store blocker) |
| **S3** | Expected absence | **Enumerate REF (R5), not your imagination**: walk the reference implementation's navigation, settings and menus and write down every feature name; grep your code for each term; zero files = absent. | features REF has that are out of scope *by written decision* — **while the code still agrees**. A written decision the code has since contradicted ("out of scope" in the README, built by a later commit) is not a discard: it goes to the queue as "which decision stands" | No quota, no licences, no changelog, no clear-cache |
| **S4** | Stuck when something fails | Controls that work when everything goes right and never recover when something goes wrong. Find where work starts — a flag set to true, a `Loading` state, a button disabled — and check each is undone on the **failure** path too, not only on success. Then error handlers that are empty or only log, searched **across lines**. Commands below the table. Drive each candidate with the network cut or the server stopped. | undone in a `finally`, or by one state that covers both outcomes; clean-up, close and stop handlers with no UI behind them | A spinner nothing ever clears after the server says no; a save button that stays disabled |
| **S5** | Placeholder that ships | User-visible strings that were never meant for users: `grep -rniE 'lorem|ipsum|\bTODO\b|FIXME|test123|asdf' ` over string resources and UI literals; then, on the device, `ui.py dump` of each screen checked for the same words and for **raw resource keys** (`common.submit`, `@string/…`). | test and preview sources; debug-only screens absent from the build users get (§2.3) | A "TODO" label in a dialog, an untranslated key as a button's text |

The S4 searches, Kotlin first. Each misses something if you narrow it: `ing *= *true` alone missed
`_isRefreshing.value = true` and sealed `Loading` states, and a one-line `catch {}` grep found **0**
on a codebase with 16 empty or log-only handlers, because formatted code puts the body on its own
line (measured):

```bash
# where work starts, PRECISION first: the names that mean "something is running"
grep -rnE '(isLoading|isRefreshing|isSyncing|isSaving|isSending|inProgress|_loading|_refreshing)[A-Za-z]* *(\.value)? *= *true' --include='*.kt' .
# …then RECALL, when the precise list comes back thin — noisier by an order of magnitude
grep -rnE 'ing *= *true|\.value *= *true|enabled *= *!' --include='*.kt' .
grep -rnE '(emit|value|update) *[({].*Loading' --include='*.kt' .          # sealed Loading states
# empty or log-only error handlers, across lines (-U lets a match span lines)
# -c counts LINES, not matches: `rg -U -n … | wc -l` said 128 where there were 44 (audit). Count the
# `file:line:` prefixes instead, and read them — the list is meant to be read, not totalled.
rg -U -n 'catch\s*\([^)]*\)\s*\{\s*((//[^\n]*|/\*.*?\*/|(Log\.\w+|println|Timber\.\w+|logger\.\w+|\w+\.printStackTrace)\s*\([^()]*(\([^()]*\))?[^()]*\))\s*)*\}' --glob '*.kt' .
rg -U -n 'onFailure\s*\{\s*\}' --glob '*.kt' .                                   # Kotlin Result
rg -n 'runCatching\b' --glob '*.kt' .        # then check each one's Result is consumed:
                                             # onFailure|getOr|exceptionOrNull|fold in the lines after it
rg -U -n 'catch\s*\{\s*\}' --glob '*.swift' .                                     # Swift
rg -U -n '\.catch\(\s*\(\s*\w*\s*\)\s*=>\s*\{\s*\}\s*\)' --glob '*.{ts,tsx,js}' .  # JS
# no ripgrep: perl -0777 reads a whole file at once, so the same pattern can span lines
```

**A candidate you can't provoke** — a save racing the screen closing, a server refusing one item
among several — can't be driven by cutting the network or stopping the server. Don't file it as
clean, and don't guess. **First, change the campaign's own fixture on the server so that one call
fails** — moving a `QA_` bookmark's URL made the app's upload fail once while the refresh still
worked, and confirmed a P0 in minutes (measured). Only when the data can't do it: in a fix mode, add
a **debug-only fault switch** (a flag in the debug build
that makes that one call fail, with a test proving the release build ignores it) and drive it; in
report-only, or when the switch would touch too much, queue it as *"unproven — can't be driven"*,
with the code path as the evidence.

S2's greps are first-order: a handler that calls an empty function escapes them. Say so in the
report. S4 exists because S2 only finds controls that are dead for everyone; the more common dead
control works on the happy path and dies when something fails — which is exactly when the user needs
it. S3 needs an input you don't have in the repo — a REF. Without one it degrades to a list you
wrote yourself, and a list you wrote yourself has the same blind spot as your code: **skip S3, say
why in the report, and queue "is there a reference?"** rather than run the degraded version.

Comparing against a **sibling** — the other platform's client, the previous version — is a
*different* net: it catches what one has and the other lacks. It says nothing when **both** are
missing something. You need both nets, and R5 says which is which.

**A grep generates candidates; a candidate is not a finding.** Each sweep reports its numbers, and they
have to add up: `27 candidates · 19 discarded (previews, default values) · 8 driven · 3 confirmed · 1
unproven`. A sweep that reports only what survived hides the two ways it can be wrong — a discard list
applied too widely, and hits nobody drove. **Zero hits is not zero problems** either: say which grep
returned zero, because the next person needs to know whether the sweep ran or found nothing.

**An absence is not automatically a defect.** S3 and the sibling net both end in "the product does not
have X", and that sentence has six endings. Write which one, beside X:

| Ending | When |
|---|---|
| **defect** | something in the product already promises X — a menu, a setting, a label, a written plan. This is the only ending that is a finding |
| platform difference on purpose | another platform has it and this one is not meant to |
| the backend does not offer it | REF talks to a newer server, or to a different one |
| product decision | nobody has decided: it goes to the human queue with what you found, not into the report with a severity you chose |
| not applicable | X makes no sense here — a desktop idea on a phone |
| unknown | you could not tell. An honest answer, written down, plus a queue item; not a discard |

REF is the list of what the domain supports, not the list of what this product owes its users: a
feature REF has is a **candidate**, and the ending above is what turns it into a finding or a question.

### R5 — Never one oracle

An oracle is something you can query that answers yes or no:

| Oracle | What it is | Where it comes from |
|---|---|---|
| **UI** | the screen as text — accessibility tree, DOM | the harness |
| **STORE** | the client's own persistence — SQLite, IndexedDB, settings files, the background work queue | the harness — and a project-side reader for formats it can't decode |
| **API** | the server, queried independently of the client | your adapter |
| **EYE** | a screenshot, read by a human or a model | the harness |
| **LOG** | what the app writes to the system log — where secrets leak, and evidence of which path ran; never proof that anything was saved | the harness (`ui.py log`, secrets hidden) |
| **REF** | the implementation that is the **full list of what the domain supports** — the vendor's web client, the spec | you |

Siblings (the other platform's client, the previous release) are *not* REF: they share your blind
spots. The **UI / STORE / API triple** is what every platform has: a backend service has the
response it gave, the row it wrote and what a downstream system sees; a CLI has stdout, the files it
touched and the exit code. EYE is any rendered artefact a human can look at; REF is whatever
document or system defines what the product should do.

**Scope.** A claim that something was *written, synced, granted or deleted* needs at least two of
UI / STORE / API — an optimistic UI that reported success for a write the server refused is
invisible to any single one. A pure-UI claim (a dialog opened, the back stack is sane) needs the UI
oracle plus a second look: EYE, or the same UI read again after a recreation (R9).

**Two oracles only agree when they are about the same thing.** "The API said 200 and the screen said
saved" is a chain of evidence only if both point at the **same operation**: the same fixture, named by
its id or its `QA_` name, and the second reading taken **after** the write. Two correct answers about
different rows read exactly like one correct answer — and it is an easy line to write, because by then
the run is already green. So a claim names the fixture, the account, the build, and the order the
oracles were read in. `QA_Item_17` costs nothing to write and lets someone who wasn't there check the
chain; "the item" does not.

Five ways the UI oracle says less than it seems, all measured:

- **A form that closes on save has told you nothing.** The screen going back is not the write: every
  finding in one process needed the API to be seen.
- **Some screens only hold what they draw.** A map's markers exist in the tree for the current
  viewport only, so the same filter answers differently wherever the map happens to be. Bring such a
  screen to one known view (fit everything, zoom out) before comparing.
- **A modal window hides the rest.** With a sheet or dialog open, the dump is that window alone; a
  message raised behind it is invisible until it closes. Before concluding something is missing,
  close what is modal and look again.
- **Accessibility is more than `a11y`'s warnings.** It reported 0 on screens where the selected filter
  chip and the only action on the page exposed no state and no action. For what matters on each
  screen, check that its state (selected, checked) and its action are exposed — **in the attribute
  that control uses**: a Compose filter chip or switch says `checked` (✓ in `dump`), a tab or nav item
  says `selected` (•). A finding "the chosen chip exposes no state" was filed on `selected="false"`
  while the chip said `checked="true"` all along (measured).
- **A screenshot nobody opened is not an oracle.** Across nine processes screenshots were taken and
  saved, and every screen was judged from the dump — which says what text is there, not whether it is
  cut off, overlapping or crowded. The human saw a date field pushed out of its card in one glance;
  opening the screenshots then found eight more (measured). **Every screen a gate calls verified has
  had its screenshot opened and described**, and the report quotes what was seen.

**When oracles disagree**, that is a finding until R8 shows an oracle wrong, and the report names
which. Online, API decides. Offline, STORE's pending queue decides and API is consulted only after
the drain. When the API contradicts *itself* (a list endpoint says one thing, the item endpoint
another), the outcome of a **write** is the oracle, and the read quirk goes into the adapter's
quirk list. **A backend that acknowledges before it shows the change** is not a disagreement yet: the
adapter re-reads until the two agree or a recorded limit passes (say which in the finding), and only
then is it a finding. Note the lagging endpoint in the adapter's quirk list too — knowing which ones
settle late is worth as much as the defect.

**Permissions are a screen too.** Every dangerous permission in the manifest is a flow: the screen
that asks, what the app does when it is denied, what it does when "don't ask again" leaves only the
system settings, and what happens when it is taken away between runs. Revoking one with
`pm revoke <pkg> <perm>` also **kills the app's process**, so it is a process death and a relaunch
(R9) — drive it that way, and use `tap --any-app` for the system dialog, which belongs to the OS, not
the app.

**When it is unclear what the product should do, REF decides** — open it, look, copy the behaviour.
What REF does not settle, or where REF looks wrong, is a product decision: R2 queue, not a guess.
Record which REF you copied and its version.

### R6 — Seen red, always

**A regression test does not exist until you have watched it fail.** This is not mutation testing;
it is one deliberate break per test, recorded:

- a test for a **fix**: revert the fix, run, see red, restore, see green;
- a **negative pair** (R7): invert the guard it protects;
- a **migration test** (R14): drop the column default or the `ALTER`;
- a fix that **removes** something — a stored field, a parameter, a call — has nothing to revert
  *to* without rewriting the old code: break the part that can come back instead (the clean-up of
  what was stored, the guard that stops the call) and say in the report that this was the break;
- a fix that lives in a **build-type value** (a release or QA `buildConfigField`, a manifest
  placeholder) that no unit-test variant compiles: the red and green are **the generated files of
  each variant** — read the built `BuildConfig` or merged manifest before and after, and say so; it is
  a check, not a test (measured: AGP 9 builds unit tests for debug only);
- anything else: name the one-line change that must make it fail, and make it.

**Red for the reason the test names.** Read the failure: it must be the test's own check saying
"expected this, got that". A crash, a compile error, a timeout or a test-runner failure *before* the
check is not red — the test never ran. Measured: on an Android 17 emulator every UI test crashed
inside the testing library before checking anything, and that crash was read as the red. The same
goes for green: the test ran and passed — not skipped, and **not handed back by a build cache**. The
red and the green of the test a fix touches come from a real run — `harness/redcheck.py` runs the test and says RED, GREEN or NOT RUN from
the reports that run wrote, and with `--break FILE OLD NEW` makes the break itself and puts the file
back, checked byte for byte (measured: a break undone by hand left four files broken after a correct
red) (by hand, Gradle: `--rerun --no-build-cache`
on that test task), and **the result you read must be from that run**: check the report's time is
after the run started. Measured twice in a row: a break re-applied after a restore came back
UP-TO-DATE, and the report on disk was the previous run's. **In shared code, name the target:** a
Kotlin Multiplatform test has an Android task and an iOS task, and a final run re-ran only the iOS one
while the Android copy of the very test the fix added was up to date (measured) — the green you report
says which target ran it. The whole identity of a regression test is **task + report file + class +
method**: `--test` gives the last two, the report path `redcheck.py` prints gives the first two, and
`--reports <dir>` narrows the search to one task when a class name is shared. Two report files
answering to one `--test` with different colours is NOT RUN, not a red.

**A green is the runner's verdict, not the product's.** A test that returns early, swallows its
exception, or ends in an assertion that cannot fail passes exactly like one that checks something.
Nothing in a report distinguishes them — which is why the red comes first: *that* is what proves the
test can see the behaviour. A green with no red behind it is an UNPROVEN dressed as a pass.

**A break that was applied is not a mutation that was validated.** When you break the code and the
test stays green, the honest reading is not "this test won't go red": it is one of two findings —
the break missed what the test asserts, or the test does not cover it. Break the line its own
assertion depends on; if it still passes, **the test is the finding**. `redcheck.py` refuses a break
that only moves whitespace and says MUTATION NOT VALIDATED for the rest.

**Check what the test touched.** A red is only as good as the element it acted on:
- **a selector that can match twice** — two panes on screen, each with a back arrow of the same
  description — takes the first one. A test pressed the wrong arrow and "rotating leaves Notes" was a
  finding the selector invented (measured). When a red is surprising, count the matches (`ui.py find`
  lists them) and scope the selector to its pane;
- **what isn't on screen doesn't exist** for UI tests: in landscape, a field below the fold of a
  scrolling dialog is invisible to UiAutomator, and a rotation test looking for it was red with and
  without the fix (measured). Assert on something visible in both orientations, or scroll to it first.

**A test that never ends is neither red nor green.** A regression test for an endless re-save looped
inside the test and held the module's run at full CPU for twenty minutes, in silence (measured).
Give every run a time limit — Gradle `tasks.withType<Test> { timeout.set(Duration.ofMinutes(15)) }`,
JUnit 5 `@Timeout`, JUnit 4 `@Test(timeout = …)`, coroutines `runTest(timeout = …)`; macOS has no
`timeout` command (`gtimeout` from coreutils, or `perl -e 'alarm shift; exec @ARGV' 900 ./gradlew …`),
and a test task has no limit of its own by default. Make a loop *fail* rather than spin — a fake that refuses the call after the few it expects — and a run that
stays silent past its limit is stopped and reported as a hang, which is a finding in itself.

A fix with **no** test is allowed — a visual defect, a device-only behaviour — and the report says
so in those words (`device-only, no test — because …`). What is not allowed is a test that was never
seen red: that is how a suite grows to a thousand green tests that assert nothing. **When the test
environment can't reproduce the defect** — a Compose test window is taller than a phone, so a sheet
cut off on the device shows whole in the test (measured) — a test written anyway stays green whatever
the fix does: delete it, and call the fix device-only with that reason. The same when the test **can't
drive the path reliably** — list rows with no test tag, where every way of tapping them from the test
flaked (measured): verify the fix on the device, call it device-only, and put the missing hook (a
`testTag`, an accessibility id) in the user queue as the change that unblocks the test. A test that
passes one run in three is not kept in the suite, and the fix is not held back waiting for it.

### R7 — Negative pairs

A test that asserts "X is not deleted" needs its twin asserting the case where X *should* be
deleted. Otherwise a fix that simply breaks the whole feature passes.

Every "doesn't happen" test carries its "does happen" pair. Where there is no absence to assert — a
cosmetic fix — there is no pair, and the report says "n/a".

**A break that leaves the test green means the test is wrong**, not that the pair is unnecessary.
Measured: inverting the guard of a "not pruned" test left it green, because its fixture page still
contained the bookmark — the assertion was true for another reason. Find that reason before trusting
either test.

The same shape applies to **authorisation**, and it's cheap: three accounts — **A** owns, **B** is
granted access, **C** is granted nothing. Every share/permission feature is tested from B (sees it,
can do what was granted and nothing more) *and* from C (sees nothing). C is the negative pair; a
campaign that only ever logs in as the owner has not tested permissions at all.

**Roles are permissions too.** An owner and a read-only visitor, an admin and a member: each role
gets its own account, and each is tested for what it can do *and* for what it must not — the
read-only account's write is refused by the server, and the app says so instead of pretending. The
account with the fewest rights is the negative pair. **B is needed wherever the app can have more
than one signed-in identity**, sharing or no sharing; only a product with a single fixed account has
nothing to leave behind. C goes when there is nothing to be denied — no sharing and no roles.

**A second account is still needed whenever the app keeps anything per account** — a session, a
cache, a search, a log — even on a backend where every account sees the same data. There B is not
about permissions: it is about **what one session leaves for the next**. Measured: on a single-library
server with no sharing or roles, B found a leftover search and the previous account's network log.

### R8 — The harness is under test too

When your tooling reports a defect, **its first suspect is itself**.

Real example: an accessibility checker flagged two "touch targets below the minimum" on a tablet.
Both were the tool measuring elements that were half-scrolled out of view — `uiautomator` reports
*visible* bounds. Fixing the tool removed two false findings and, more importantly, stopped training
the operator to ignore it.

A false positive costs more than a miss: a missed defect is one defect, but a tool that cries wolf
gets ignored, and then it misses everything. The mirror image is a **silent all-clear**: a tool that
cannot reach the device, or has no configuration, must refuse — never print "0 warnings".

When you change the harness, prove the change in **both directions**: the false positives are gone,
*and* a real finding is still caught (re-introduce one and check).

The harness in this repository has its own tests — `tests/run`, a fake `adb` and no device — and each
one is a sentence about what the tool must **refuse**: an ambiguous selector, a device that is not on
the allow-list, an open port that answers no HTTP, a report an earlier run wrote. Run them after
touching anything under `harness/`, and when a campaign catches the harness lying, the fix arrives with
the test that would have caught it (R12).

### R9 — "The UI gets recreated" is an axis of its own

Every platform has a moment where it throws the UI away and rebuilds it from whatever state you
bothered to save. That is where badly-saved state falls over, and **no catalogue derived from the UI
will ever cover it**, because nothing in the code enumerates it.

| Platform | What recreates the UI |
|---|---|
| Android | rotation, process death (`ui.py kill`), font-size or theme change, split-screen |
| Web | reload, restore from bfcache, tab discard |
| iOS | rotation, jetsam, scene reconnection, multitasking resize (Split View / Stage Manager — a compact↔regular size-class change) |
| Desktop | window resize across a breakpoint, sleep/wake |

**First find out what recreates the UI in *this* app.** An app can declare that it handles some of
those changes itself — on Android, `android:configChanges` in the manifest (`orientation`,
`screenSize`, `uiMode`, `fontScale`…). Then rotating recreates nothing, and `rotate` proves the
screen turned, not that any state was rebuilt: counting it as an R9 test counts a non-event
(measured on a Compose app that declared them all). For each change the app handles itself, test
something different — the layout adapts and nothing typed is lost as it re-lays out. **Process
death** (`ui.py kill`) recreates the UI in every app, so it is always an R9 test — except where a
cold start is **by design a sign-out** (the session is re-read from elsewhere on every start): there R9
checks that it signs out cleanly and leaves nothing behind, and "state lost after kill" is not a
finding (measured on a fleet app).

Ask it of every screen — especially with a **half-filled form, an open dialog, or a scrolled list**.
On a single-device iPad campaign the "second form factor" of R1 is a window size, not a device.

⚠️ **Assert that it actually happened.** On Android,
`adb shell settings put system user_rotation 1` writes the property and **does not rotate the
screen** while auto-rotate is on: the test passes without having tested anything. Whatever your
platform, read the rotation or size back from the system before asserting anything else.

### R10 — Destructive only on fixtures you made

**First choice: a server nobody else uses.** When the backend is something you can run yourself —
open source, self-hosted, a container — a disposable copy started for the campaign takes real data
out of the picture entirely: every account and every row on it is the campaign's. Propose it at
setup when there is no test server yet (§2.1, "what already exists"); don't just start one — the
human may already have a test server, and starting one is a stop (R2). On a disposable server,
record how it is started and thrown away, and which version of the server it runs.

Otherwise — a shared test server, or the real one — error paths and destructive flows get tested
only against fixtures **the campaign created**, with a recognisable prefix (`QA_`). Clean them up at
the gate and verify the cleanup through the API.

**A fixture you did not choose the id of is not yours yet.** Sample data that ships with the project —
a seeding script, a demo record in the code — can carry the **same id** as a live record: injecting one
overwrote a real record on the server (measured). Before injecting any fixture, ask the server whether
that id is already taken, and give the campaign's copies ids of their own.

**A stored flag has other readers.** Flipping something in the app's own store to reach a screen — a
licence bit, a feature flag, a role — is not a read-only act: one flipped to open a screen also changed
which records the app's own clean-up deleted, and it deleted a record that was not the campaign's
(measured). Grep who reads a flag before changing it, and say in the report that it was changed.

**On the real server**, five more things:

- **Test accounts, never a personal one.** The human creates them — A, and B and C if R7 needs them
  — and the campaign never creates or deletes an account itself (R2, stop 3).
- **Server errors come from somewhere else than the real server.** Cut the network, point the app at
  an address that doesn't answer, or run a **fake server** on the computer that answers with the
  errors you need (a 500, a 412, an HTML page instead of JSON) — `harness/fake_server.py` does that
  and prints what the app sent. From an emulator, reach it through `adb reverse` and `127.0.0.1`:
  the device's shell reached `10.0.2.2`, the app didn't (measured). Never break the real one to see an error. Ending **the campaign's own** session — signing it out, revoking its token through the API —
  is a fine way to get a "session ended" error: it touches nothing but the campaign. Another
  account's session, never.
- **A 401 is not a 403.** Code often sends "the session expired" down the same branch as "you may
  not do this", and a rejection handler written for the second then discards or locks what the user
  wrote. With a write waiting in the queue, answer **401** from the fake server, and check that the
  write survives, nothing turns read-only, and it goes up after signing in again. Measured: an expired
  session made notes read-only for good and threw away the text. Provoke 401s on the fake server
  only: repeated failed sign-ins against a real server trip its brute-force protection, and the
  computer's address got 429s (measured).
- **Side effects the clean-up can't undo.** Sharing or inviting can send an email or a push
  notification to a real person, create a public link, fire a webhook or cost money. List them in
  `CAMPAIGN.md` §4 before the first test that could trigger one; if one would reach someone outside
  the campaign, use addresses the human controls, or queue it.
- **The ones that need no action at all.** Before the first launch, grep every outbound channel the
  app has — chat and messaging APIs, webhooks, push, crash reporting, third-party SDKs — and ask what
  fires **on start**, on an error, or on a health check. A test device is not a real one, and what it
  is *missing* can be the trigger: an app that alerts a real chat when a companion app is absent did
  it on every cold start on the emulator (measured). Agree an off switch with the human before driving
  anything.

A backend nobody can query directly (a vendor sync service) changes the API oracle, not these rules:
`adapters/README.md`, "A backend you don't own".

**Put the marker where the server keeps it.** Servers rewrite what you send: a title replaced by the
page's own title, a name trimmed or lowercased — and the app may have no field for the title at all.
Create one fixture, read it back through the API, and check the prefix survived; if it didn't, move
it to a field the server stores as sent (a URL, a tag, a description). Record that field in
`CAMPAIGN.md` §4, because the clean-up searches it.

**The server also makes records of its own.** A `QA_` place with coordinates and a visit marked a
whole region "visited" for the account, and deleting the place didn't undo it (measured). A clean-up
that searches for `QA_` can't see that. Before each process, **note the account's counts** —
statistics, visited or derived lists — and compare them after the clean-up.

Know which of your product's destructive actions are **irreversible** — no trash, no undo, no
server-side copy — and say so in the plan; those are tested last, and only on fixtures.

### R11 — The agent never types credentials

Sessions are injected, never typed. The skill cannot ship this — every app stores its session its
own way — so the setup gate builds it. It is two questions.

**What the session is made of**, best first:

- **A token made with the server's own secret.** On a disposable server you run yourself (R10),
  where sign-in tokens are signed with a key you hold, make the token for account A, B or C
  directly. No password exists anywhere.
- **A token or app password the adapter gets once**, from credentials the human wrote into the
  gitignored `qa.credentials.json`; only the token is kept.
- **The password itself**, from that same file, when the app accepts nothing else.

**How it gets into the app**, in order of preference:

1. **A test that runs inside the app and writes the session** — an instrumentation test on a
   debuggable build writes to the app's secure storage exactly what the login would have written.
   Works for any Android app; ~50 lines. The test runs on the device and the credentials file is on
   the computer: put the value into the **test build** when it is built (generated into the build
   folder from the gitignored file, never into source), and uninstall the test app once the session
   is written. Never pass it with `am instrument -e` (a command line, visible to other processes
   and kept in shell history) and never `adb push` the file (a loose copy left on the device).
2. **Write the store directly** (`run-as` on a debuggable build) when the session lives in a plain
   preferences file or database. The transport is the part to get right, because the obvious two
   break the rules above: **stream it over stdin**, so the value is never an argument and no copy is
   left on the device —
   `adb -s "$(ui.py serial qa)" shell run-as <pkg> tee shared_prefs/<file>.xml < local.xml >/dev/null`
   (`ui.py serial` because raw adb doesn't know the allow-list). Paths are relative to the app's data
   folder. `tee` rather than `sh -c 'cat > …'` because the redirection has to reach the device's shell
   as **one** argument: unquoted, `sh -c 'cat > …'` was taken apart on the way and answered
   "Permission denied" (measured on API 37; `adb shell "run-as <pkg> sh -c 'cat > …'"`, all in one
   string, works too). A session inside SQLite needs the device's own `sqlite3` — emulators have it,
   many phones don't — and where it isn't there, mechanism 1 is the answer. The harness has no `put` command on purpose: what the session is made
   of is the project's, not the skill's.
3. **A debug-only launch argument** that accepts a token — app code, development builds only, and
   **only for a token that is ordinary test input**: one minted on a disposable server you run, or a
   declared test identifier. A real server's token never goes on a command line (above).
3b. **A credential read from hardware** — an NFC card, the IMEI, a serial: the emulator cannot
   produce it. Inject the session it results in (1–3), ask at setup whether the **server** also checks
   the device, and put the real tap on a physical test phone in the queue.
4. **Log in once by hand and snapshot the device** — the human signs in, the emulator or
   simulator is snapshotted logged-in, and every run starts from that snapshot. This is the answer
   for iCloud, two-factor and anything else with no programmatic path.
5. **The session belongs to another app** — a companion app hands it over (a ContentProvider, a
   launch intent with the user's id). Drive that route: the companion signed in by the human, or its
   launch extra with a **test** identifier (below). **Whether writing the app's own store works at
   all is read from the receiving code, not assumed**: an app that keeps a copy of the hand-off can
   be injected and survives a cold start; one that re-reads the companion on every start signs out
   again, which is what was measured here. Before writing an injector, grep the receiving Activity
   for `getStringExtra`/`hasExtra` to learn the exact extras it parses — and for a debug injector the
   app may already have.
   **Keep a simulated hand-off consistent with its source:** a launch extra saying "this driver" while
   the companion app reports nobody signed in is a state no user has, and the next cold start signs
   out by design (measured). Don't file what only that contradiction produces.

**Cold-start once before relying on an injected session.** An app that re-reads its session from
somewhere else on every start wipes an injected one before the first screen (measured: the app
cleared its stored session whenever the companion app reported nobody signed in).

Whatever the mechanism, `session.injectCommand` in `qa.config.json` names it, and a **real**
password is never typed, echoed, or passed on a command line by the agent.

**The credentials file feeds the scripts, never the login screen.** `qa.credentials.json` is how the
adapter signs in *through the API* — to ask the server what is true, and to get the session that is
injected into the app. The agent runs those scripts and never sees what they read. It does **not**
type a password from that file into the app, and won't even when the human asks: that refusal is the
agent's own rule, not only this skill's, so don't plan a step that needs it. **Session tokens count
as credentials too**: never on a command line (`curl -H "Authorization: Bearer …"` is readable by
other processes) — go through the adapter.

**Reading the store never prints a credential.** The place the session lives often holds a token or
an encrypted password next to ordinary settings. Select the columns you need, never `select *`, on
anything that holds a session. `ui.py db` and `ui.py file` hide secret-looking columns and keys; a
project-side reader (for a format the harness can't decode) must do the same. To check a logout,
assert the value is **empty**, not what it was.

**Before writing a session or testing logout, look at whose app it is.** The app may already be
installed on the test device holding someone's real account — logout wipes it, and an injected
session overwrites it. Check whether it is installed and signed in. If it may be a real account,
test a **separate build with its own app id** (a debug or staging variant: same code, its own data)
so the real install is never touched — or ask. **When no variant has its own id** (debug = release),
propose a QA build type with an `applicationIdSuffix` — it changes the build file, so ask first. If
the app needs another app's signature permission, that build may need the release key: then it must
never leave the test device, and the build file says so (measured on a work phone holding the
production app). Don't trust a note that says what is on the device;
look.

The rule protects real credentials, not the password field. **A test identifier the human declares
as test data** — a test account's NFC card, a test user number — is ordinary test input: it can go on
an adb command line (`am start … --es <extra> <id>`). Keep it in `qa.credentials.json`, and in docs and
commits call it by its role ("the test chip"), never by its value. Without that declaration, treat any
sign-in value as a real credential (measured: a campaign rightly refused to put a driver's card id on
a command line until the human said it was a test card). **Invented values against a disposable
or local test server** — a wrong password to test the error path, a fixture account the campaign
created — are ordinary test input: use them without asking. The **one real,
end-to-end login** is a user-queue item (R2): the human does it once, and it is the only part of
login that cannot be automated.

**After that real login, compare what it stored with what the injection writes — field by field**,
secrets hidden. Every field the injection sets that a real login doesn't, or sets differently, is a
place where a test on the injected session tests a state no user ever has. Measured: the injection
wrote an account `id` and `owner`, which the real login never stores, and a fix looked done on the
injected session only. Ask for the real login early — in the first queue round, before the shell
gate closes — and **don't wait for it**: keep driving on the injected session and close gates assuming
it (R1). When it comes, the comparison shapes the injection and reopens only what it contradicts.
Measured: a campaign stopped after setup to wait for that login, and the human, seeing nothing move,
took it for a hang.

**Switch accounts once without a process death.** Injection stops the app to write the store, so
every injected account switch is also a process death (R9), and whatever lives in memory after a
logout can never show up that way. Log out and sign in as the next account **by typing, in the same
process** — with invented credentials against a disposable or fake server (allowed above), or as the
human's queue item. Measured: two leftovers from the previous account appeared only on a switch
inside one process. Against a fake server, sign-in is not enough: **every screen the fake account
visits needs its routes answering empty**, not erroring — an error screen hides exactly the leftover
you are looking for. List the calls the shell and tabs make, route them, let the rest 404. When
neither a fake nor a disposable server can sign the next account in, **the in-process switch is the
human's queue item** — never claimed from injected switches, which are all cold starts. **A second
client** for "the same account in two places" is the API adapter, not the web: the web needs a
typed login the agent doesn't do.

### R12 — Report what happened, including your own mistakes

When you got it wrong, the report says so in the same voice it reports everything else:

> *"My first alignment check computed the zip offsets by hand and reported 0 of 20 aligned. **That
> was my mistake** — it didn't account for local header padding. The official tool says the file is
> fine."*

A campaign that never records an operator error is not being honest, and its other results are worth
less because of it. Equally: when a defect cannot be reproduced from the test harness, **rename the
test to say what it actually covers** instead of claiming coverage you don't have.

**The same goes for what you tell the human.** A message that closes a process or the campaign lists,
in that same message, what was driven and what was not. "Everything works" or "only X is left" is
allowed only when the not-driven list is empty; otherwise name each gap and why it was left. A gap the
human finds by asking is a finding against you, and the run report records it as an R12 mistake
(measured: a release gate summarised as "everything works" after one write of each kind, with share,
PDF, attachments, trails, camera and invitations never driven on that build).

**And when the skill is what went wrong, log it too.** A rule that made you guess, an assumption that
isn't true in this project, a harness command that lied or was missing, an instruction that makes no
sense here: one line in `SKILL-FRICTION.md`, in the campaign's docs folder, **when it happens** — not
reconstructed at the end. Each line carries a tag — **GUESS**, **FALSE-ASSUMPTION**, **TOOL** or
**NONSENSE** — then where in the skill (`SKILL.md` R6, `ui.py tap`), what happened, and what you did
instead. The file's first line names the skill version the campaign started with (its commit, when
the skill is a git checkout: `git -C ~/.claude/skills/qa-campaign rev-parse --short HEAD`, and
`git -C … log --oneline <that>..HEAD` at the end lists what changed under you; "none — copied install"
when it is not a checkout). Don't edit the skill from inside a campaign; work around it in the
project and log the line. Most rules in this file after the first campaign came from lines like
these.

**At close-out, offer the log to the skill's maintainers** — as an issue on the skill's repository
(its `git remote` when the skill was installed from git; otherwise the one in its `README.md`).
Sending it is **publishing**: nothing goes out without the human's yes, asked every time.
1. Write `SKILL-FRICTION.public.md` next to the log, **without the project in it**: no paths, host
   names, addresses or URLs, no account or person names, no titles or content from the product's
   data, no file:line of the project's code. Keep the tag, where in the skill, what happened in general
   terms ("a list screen", "a sync queue", "the project's login script"), what you did instead, and the
   measured numbers. Name the kind of product and platform, and the skill version.
2. Show the human that text, and say where it would go.
3. On a yes, file it — `gh issue create --repo <skill repo> --title "Friction: <kind of product>,
   skill <version>" --body-file SKILL-FRICTION.public.md` — and put the issue's link in the close-out.
   No `gh`, no repository or a no: the public file stays in the docs folder for the human to send.

### R13 — Run the whole suite before closing a gate

Per-module test runs pass while the repository-wide build is broken — typically stale fakes in
*other* modules after an interface changed. Run the full suite at every gate, not at the end. **A fix
that changes wording** breaks every test that pinned the old words, in modules the fix never touched:
grep the test sources for the old string before running the suite, and update them in the same
change (measured).

A result restored from the build cache counts here: same inputs, same result, and the gate asks
whether the repository as it stands is green. Say it in the report — *"722 tests, 688 from cache"* —
because a cached pass is not the real run R6 needs for the tests the fix touched (measured: 688
results came back in 5 s without running).

Two ways the count lies, both measured: Gradle's `--rerun` applies to **the task just before it** —
`gradlew test --rerun` reran nothing that hadn't changed, so name the task
(`:data:testDebugUnitTest --rerun`) — and a report folder keeps XML from tasks the build no longer
runs, so summing every `TEST-*.xml` inflated three gates' totals. **Count only the reports this run
wrote**: their time is after the run started.

On a multi-module build most modules are up to date and write no report at all, so the honest count
has two parts — say it that way: *"405 tests ran this time; the other modules were up to date with
unchanged inputs (last green at `<commit>`)."* When a process changed no code, the honest line is
*"no code changed in this process, so no test ran; last green at `<commit>`"* — not "0 results",
which reads like a broken command. And **a task that never reached the device is not
green**: a module that failed with *"No compatible devices connected"* inside an otherwise green run,
with the device connected, ran nothing (measured). Run that module alone and report both runs.

**A test that fails and then passes** within the same gate is not noise to be dropped: name it by id
in the suite line — *"1.103 passed, 2 passed on a rerun: `<ids>`"* — and file it as a finding (P2,
unless what it failed on is the product's). Excluding it from the run hides exactly what a campaign
exists to see.

**On a repository with several application modules**, the suite is the app under test plus every
module downstream of what the fix touched — read that from the build files, run them as named tasks,
and say in the report which modules were left out and why.

### R14 — Every change to the local store ships with its migration, and the migration with a test

If the client persists anything, a released version has users with data in the **old** shape. A
schema change without a migration is data loss on upgrade; a migration without a test is a guess.
Test it against the real engine (a migration test helper, a fixture database at the old version),
and see it red (R6): drop the `ALTER` and watch the test fail. The release process then does the
thing the test only models: **install the previous release, create data, install the new build over
it**, and check STORE and API.

**"Once" means once per device, not once per version.** A one-time job — pushing local data into a
new store, a backfill, a re-registration — gated on "the version changed" runs again at **every**
upgrade, and the second run overwrote newer data with this device's stale copy (measured). Gate it on
"has never run here", and let its test upgrade **twice**: the second upgrade must do nothing.

**The version has to be above what users already have.** Before building the artefact, compare its
version number with the highest one **shipped from any branch** — a release branch was numbered below
what the maintenance branch had already published, and the in-place install died with
`INSTALL_FAILED_VERSION_DOWNGRADE` (measured). It costs one command, it doesn't need the human, and a
unit test pinning "above the last shipped" keeps it that way. While there, look on disk for an earlier
artefact to upgrade from before queueing the human for one.

Three more things that process needs, all found the hard way:

- **Scope it from what the build type changes, not from a sample.** List every path that R8, signing
  or build-type values can reach: serialization, file providers and intents, reflection, endpoints
  only some features call. Drive each one, or put it in the report as not driven. One write of each
  kind proves the serializers and nothing more.
- **Signing.** An update only installs over an APK signed with the same key, and the published one is
  usually signed with a key that lives only in CI. Build the previous release **from its tag** with
  the same local key as the new build — its size matching the published APK is a cheap check that it
  is the same code (measured).
- **The human, again.** A release build isn't debuggable: no injected session and no STORE oracle.
  The one real login is needed once more, and every claim in that process rests on UI and API only —
  say so in its report. Put that login in the queue **when the release process is planned**, not
  when it is reached. **Before queueing it, try the fake server**: record the real server's answers
  for the routes the app calls (through the API adapter), serve them from `fake_server.py`, and sign
  the release build in to it with invented credentials. That drove an R8 pass of every screen with no
  password typed (measured). It proves R8 and the release packaging. It does not prove the real server
  accepts what the build sends, so a write the app sends still needs the API oracle on the real server.

---

## 2. Running a campaign

### 2.1 Set up (once per project)

**Resuming a campaign that already exists?** When `CAMPAIGN.md` is already there, don't start setup
over — and don't skip it either. Read the plan, the process files and the queue; then check each
step below against what the plan records, **including steps the skill has added since the campaign
began** (compare with *Skill at start* in `CAMPAIGN.md`), and ask the missing ones **before** doing
any more work. Uncommitted changes left by the earlier run are step 2's question. Measured: a
resumed campaign got the setup questions after the fixes they were meant to shape.

**Unless that campaign is closed.** When its last gate closes, `CAMPAIGN.md` says `Status: closed`,
with the date and the commit. A closed campaign is not resumed: running the skill again starts a
**new** campaign, in a dated folder inside the same docs folder (`docs/qa/<date>/`), and the closed
one is earlier QA work for it (step 3).

**Look first, then ask once.** Good questions need facts, so setup starts by **looking without
touching**: which AVDs exist and which are already running (`ui.py avds`), whether the server
answers, what the manifest and the build files say, **whether the release build is even shippable**
— three commands: its version number against the highest one already published from any branch, the
signing key present (`apksigner verify --print-certs` on the last published artefact against the
local key), and the release variant building and launching once — and **what QA work the repo already
has** — test
plans, an earlier campaign's reports, QA scripts, a client for the server, test credentials kept in
some file (steps 3 and 6). "Before anything else" in step 1 means before *changing* anything, not
before looking.

Then the questions of steps 1, 3 and 5 go to the human **in one round of at most four** — question
tools take four, and a second round gets skipped:

1. **Fix mode** (step 1);
2. **Commits**, and where the campaign docs live (step 1);
3. **Devices** — propose one from what you saw, and name the ones that are busy or off-limits
   (step 5); **which app**, when the repo holds several; and **which build users get** (a store
   release, a flavor, or the debug build a device manager pushes), because that decides how findings
   are rated (§2.3);
4. **Server and accounts** — which server, whether it holds real data, which account for each role
   (step 3). Test data defaults to *"only what the campaign creates, marked `QA_`, is touched"*;
   say so in the question, and the human corrects it only if something else must be protected. Name
   here too any **outbound channel that fires on its own** (R10) and ask for its off switch.

1. **Ask two questions, once, before changing anything** — in the setup round above — and record
   the answers at the top of `CAMPAIGN.md`. Never ask them again per finding.

   **Fix mode**

   | Mode | What happens to a finding | When it fits |
   |---|---|---|
   | **Fix severe** *(default)* | P0 and P1 are fixed, with their test seen red (R6). P2s and anything that is a **product decision** (wording, whether to confirm, what to show) go to the user queue | your own product before a release |
   | **Fix all** | also fixes P2s — product decisions still go to the queue | polishing your own product |
   | **Report only** | nothing in the product is touched. Each finding is written up to §2.3 with exact reproduction steps, the oracles' evidence, file:line and the likely fix | code you don't own, a frozen release branch, an audit |

   **Commits, and where the work goes** — may the agent commit at each gate, or only leave the
   changes for the human to review? **On a branch of its own (`qa/<date>`) or on the branch that is
   checked out?** Ask; don't assume: a project forbade new branches as a standing rule (measured).
   Where do campaign docs live if `docs/` is not versioned in this repo — **and is `docs/` served
   anywhere?** Grep for that before asking (a GitHub Pages `/docs` source, a deploy or sync script, a
   static-site config): one repo copied its whole `docs/` folder to a web host on every sync, which
   would have put run reports — server addresses, account names, defect detail — on the open web
   (audit). When something serves it, propose a folder nothing serves. Notes kept only on this
   machine have **no backup** — say so when that is the answer.

   In the fix modes every fix ships with its regression test (R6, R7) — that is part of fixing, not
   an extra. *Report only* changes nothing in the repository's source: no fixes and **no test
   files**; the report names the test that would prove each fix instead. The harness, the adapter
   and the campaign docs are written in every mode.
2. **Start from a clean tree, on a campaign branch.** Run `git status` before touching anything.
   If there are uncommitted changes, **stop and ask** — commit them, stash them, or explicitly
   accept them as part of the baseline — because otherwise the campaign's diff mixes with
   someone's work in progress, a finding can come from a half-done change instead of the product,
   and reverting a fix to see its test red (R6) touches code that was never the campaign's. Then,
   set up the work where step 1's answer said — **a branch of its own, `qa/<date>` from the current
   commit, is the default when the human has no preference**; only stay on the branch that is checked
   out when they ask for it — and record that commit as **Build at start** in
   `CAMPAIGN.md`. Every gate's diff is then that process and nothing else.
3. **Ask what already exists before building anything.** One question, four parts:
   - **devices** — which emulators, simulators or phones are for testing (step 5);
   - **a test server** — is there one already, at what address, and does it hold anyone's real
     data? (R10 says what to propose when there is none);
   - **test accounts** — which ones, and for which roles (R7);
   - **test data** — anything that must not be touched, and anything already prepared.

   Use what exists. Build, start or create only what is missing — and ask before doing it (R2,
   stop 3). The answers go at the top of `CAMPAIGN.md`: they are the "agreed ground" every later
   stop refers to.

   **QA work already in the repo** is found by looking, not asked, and it is a **baseline, not the
   plan**:
   - the inventory is still derived from the product (R3); the old one is a cross-check — a control
     it lists that you didn't find was either removed or missed;
   - defects it records as fixed are **re-checked, not re-reported**: still fixed, or a regression —
     and a regression is a finding;
   - scripts that work are reused once proven (R8): an existing client for the server becomes the
     adapter (step 8) instead of being written again;
   - nothing of it is overwritten or moved. The campaign's docs go in their own folder, and the
     earlier ones stay the record of that campaign;
   - **what changed since it closed** — the commits since its closing commit (or its date, when it
     recorded none), the server's and its apps' versions, the target OS — sets the **order**, not what
     is skipped: untouched screens still break through shared code and a changed server. Changed
     areas go first, and every finding says whether it comes **from a change** or was **missed
     last time**. The misses are what the earlier campaign could not see; the close-out names them;
   - **`QA_` records already on the server** are an earlier run's fixtures, not this campaign's.
     Count them per account **by owner** while looking, and say so in the setup round: a record
     shared with another account shows up in that account too, and cleaned from there it takes the
     share with it (measured: a cleanup would have deleted a read-only note B shared with A, counted
     as A's leftover). Clean a record up only from the account that owns it. Reuse them when the seed
     script finds and reuses existing ones; otherwise ask before cleaning them up (R10).
4. Copy `templates/CAMPAIGN.md` into the campaign's docs folder and fill in the process list. The
   other two templates are **models, not files to copy now**: each process writes **one file**,
   `NN-<area>.md` (`01-shell.md`, `02-bookmarks.md`), shaped like `templates/run-report.md`, with
   the process's inventory (`templates/inventory.md`) as its first section. Only an inventory too big
   to read inside the report gets its own `NN-<area>-inventory.md`. Never leave a blank template in
   the folder: it reads as a process that was never done.
5. **Pick devices before creating any.** List what exists — `ui.py avds` shows every AVD with its
   Android version and whether it is **already running**, read from the computer's processes
   without touching any emulator; `emulator -list-avds` and `adb devices` alone don't say which AVD
   is behind which running serial (measured: a campaign proposed an AVD as free that was another
   campaign's running emulator) — and **ask before creating or deleting a device**. Test first at the product's **target** OS
   version, and at its minimum only as a later, separate pass. **No image for the target installed?**
   Use the nearest installed one, write the difference down, and ask before downloading the right one
   (R2, stop 3). One resizable emulator can cover
   phone and tablet layouts. Any physical device attached that is not explicitly the test device is
   **off-limits** — list the test devices in `devices` and pass `--device` on every command. Once
   `devices` lists anything, the scripts **refuse any device that is not on the list**, so nothing
   lands on someone's personal or work phone by accident — **but that guard is the harness's, not
   adb's**, and a monorepo has more than one app to pick from. Both, with the device-naming rules
   (AVD not serial, `-port`, `ANDROID_SERIAL` on raw adb and Gradle):
   **[`references/setup-notes.md`](references/setup-notes.md) §Devices**.
6. Copy `qa.config.example.json` to `qa.config.json`. The scripts read `android.*`, `devices`, `managedDevices` and `campaign`;
   the rest (`server`, `session`, `fixtures`, `app`) documents the plan. **Secrets never go in it**:
   the adapter reads a separate `qa.credentials.json` (its shape: `adapters/README.md`).

   **Saying what that file is for, using one the project already has, and creating an empty one to
   fill in** — three notes that have each cost a round trip:
   **[`references/setup-notes.md`](references/setup-notes.md) §Credentials**.

7. Add them to the project's `.gitignore` — the skill's own `.gitignore` does not apply to your
   repo: `printf 'qa.config.json\nqa.credentials.json\nqa-shots/\n' >> .gitignore`.
8. Write the **API adapter** for the test server agreed in step 3 (see `adapters/README.md`). This
   is the only part the skill cannot give you: it's how the campaign asks the server what is true.
   Then check that **the app on the device reaches that same server** — `net.sh reach` (§3) — before
   setup closes: the computer reaching it says nothing about the device. Measured: setup closed with
   "the harness drives the app" while the app could not resolve the server's name, and it surfaced a
   gate later as "deleted notes that don't disappear".
9. Run the five absence sweeps (R4) once, for the whole product, and file each finding under its
   module — before writing any catalogue.
10. **Decide how deep offline goes** — none, short or full (R1) — from the clues in the code, and
    write it at the top of `CAMPAIGN.md` with the clue that decided it. It sets whether the
    campaign has an offline gate at all.

### 2.2 Per process

A gate closes on what the process **proved**. Anything its criterion needed and nobody could tell is
written into the report as **unproven**, with what stopped you, and either keeps the gate open or goes
to the human queue as itself (R1).

1. **Inventory** the controls and entry points of the area under test (R3) — the first section of
   the process's file, `NN-<area>.md` (§2.1 step 4), in the shape of `templates/inventory.md`.
2. Drive them with the harness, asserting against the oracles (R5). **For every edit form, once:
   change the record elsewhere first** — through the API, or the web client — **then save from the
   app**, and check the other change is still there (or that the app says it conflicts). Forms that
   save through **one code path** share one check — show the shared path in the report instead of five
   round trips through the UI. It is
   cheap with the API oracle already built, and it found a lost update on an app with no sync at all:
   the form saved the list's stale copy over a change made a minute earlier (measured).
3. For each finding the **fix mode** covers: fix it, write the regression test, **see it red**
   (R6), add its negative pair where the test asserts an absence (R7). Everything else: write it up
   (§2.3) and queue it. Stop only for what R2 lists. **Record which modules the fix touched** —
   `git diff --stat` — in its row: a gate closes on the code as it was that day, and a later fix in
   shared code can undo it without anything noticing (audit). At the release gate, re-drive the
   inventory rows of earlier processes whose module a later fix touched, and list them in that
   report.
4. Run the whole suite (R13).
5. Verify each fix **in the running system**, not only in the test — and first prove the running
   system **is the build with the fix**. A failed build stops here: never install whatever the last
   successful build left behind, and **never hide the build's exit code**: a build piped through
   `grep` to shorten its output looked fine, the install pushed the previous APK, and the run that
   followed damaged data (measured). Install only when the build command itself exited 0. Measured
   again elsewhere: a build failed, the install pushed the previous APK, and old code on the device
   read as "the fix does not work". On Android, `ui.py installed --apk <file>`
   refuses unless the installed app is that exact file. Then drive it **in the exact state the finding
   was measured in** — the same data, an empty account if it was empty — and **the way the user gets
   there**: a gesture, not the function behind it. A fix went green in its test, which called
   `refresh()` directly, and failed on the device, where an empty list passed no drag to
   pull-to-refresh at all (measured). A test proves the function; only the device proves the path.
6. **Open the screenshot of every screen you are about to call verified**, and write down what you
   see — cut off, overlapping, crowded, unlabeled, or fine — in the report's EYE table (R5).
7. Finish that same file as the run report, in the shape of `templates/run-report.md`, with the
   finding table, and link it from the log in `CAMPAIGN.md`.
8. Clean up fixtures (R10) and verify through the API.
9. Commit if the setup answer allows it; otherwise say what is left uncommitted. Then, and only
   then, the next process — and when the campaign stops here, `ui.py release`, so a campaign taking
   turns on the same device isn't refused.

### 2.3 What a finding looks like

Every finding gets an id, a severity, **what actually happens** (not what's wrong in the code), the
file:line, and its status. Severity, the same everywhere in the campaign:

| | |
|---|---|
| **P0** | data loss, **a security hole** — a password, a session token or private data readable by someone or something that shouldn't have it (another app, a backup, a log) — or a state the user cannot recover from |
| **P1** | the user is lied to (told "saved" when it wasn't), or blocked with no workaround |
| **P1** | it stops the release: a store or fleet requirement the build does not meet (a missing privacy policy, a dead "Help" link the review checks, a version below what is already published). It blocks everyone, and there is no workaround |
| **P2** | a workaround exists, or it is cosmetic. Harness `a11y` warnings (small target, unnamed icon) are P2 unless they block a flow. Hardening that exposes nothing by itself (a too-wide file-sharing path, a session not revoked on the server) is P2 |

**A secret in the system log** is **P0** when anyone but the developer collects logs from the devices
users have — a company's device management, bug-report or crash tools — and **P1** otherwise: on a
plain phone the log needs adb or a privileged app. Say which case applies and why.

**Rate for the builds users get** — and **ask at setup which build that is**: a store release, a
flavor, or, in a managed fleet, the **debug** build pushed by the device manager (measured: an app
whose trucks run the debug build, where "debug-only" protects nobody). Then check whether the screen
or path exists in *that* build (`BuildConfig.DEBUG`, the flavor, a debug-only menu) before calling
anything P0: a leak visible only in a build nobody receives is a finding for that build, not a P0 for
users.

**If you cannot point at the row, it is not your call.** Every severity in the report names the line of
that table it matches. A finding that matches none of them, or whose severity depends on what the
product is *meant* to do, goes to the human queue with your reasoning — not into the report with a
number you picked. Severity is where a plausible-sounding paragraph turns a P0 into a P2, so this is
the one judgement the method does not leave to the agent alone.

The "what" is written so that someone who has never seen the code understands the consequence:

> **P1 — "Note updated" over an edit the server refused.** A note shared read-only answers the PUT
> with **412**, not 403, so it fell into the conflict branch: the row was correctly reverted, but
> `updateNote` still returned success. The editor closed, the user read "Note updated", and the
> screen was left showing the rejected text as if it were the note.

If you can't write that sentence, you haven't understood the defect yet.

**A P0 or P1 is attacked before it is reported.** Hand a subagent only the evidence — screenshot,
dump, store and server output, no reasoning — and ask it to refute the finding. What it refutes goes
back to you, not into the report; what it cannot settle goes to the queue (R2).

---

## 3. The harness

The rules above are platform-independent. A **harness** is what makes them executable on one
platform, and it has to provide exactly seven things — enumerate the screen as text, act on it, read
the local store, screenshot, cut the network, force a UI recreation, and read crashes.
[`harness/README.md`](harness/README.md) is that contract: the seven capabilities, the command each
maps to, and what other platforms' equivalents are.

`harness/android/` is the **reference implementation** — used on a real release and proven against
a second, unrelated app. For any other platform you write the seven capabilities behind the same
command names; nothing above this line changes.

`ui.py` drives an Android device or emulator over `adb`, reading the accessibility tree rather than
pixels — it is text, it can be asserted on, and it is cheap.

```bash
# Run it from the project root, so it finds qa.config.json:
#   python3 ~/.claude/skills/qa-campaign/harness/android/ui.py --device phone dump
ui.py --device phone dump               # the screen as text; device by alias (or --serial / ANDROID_SERIAL)
ui.py tap "text=Add item"               # selectors: text= text~= desc= desc~= id= id~= class= class~=
                                        #            clickable= scrollable= enabled= checked= selected=
                                        # several DIFFERENT controls = a refusal, not the first one (--index N / --any)
ui.py tap "text=Save" --expect "text=Edit item"   # only if that screen is showing; stops otherwise
ui.py tap "desc=Delete" --in "text=QA_Item1"      # the Delete of THAT item — refuses if it can't be sure
ui.py assert "text=Delete" --absent     # exit 1 if wrong — what a script gates on (`wait`, `watch`, `state` too)
ui.py installed --apk <file>            # does the device run that exact build? (§2.2 step 5)
ui.py kill                              # process death that KEEPS saved state (R9); `stop` discards it
ui.py db <alias> "select ..."           # the app's own store, secrets hidden (`files`, `file`, `log` too)
ui.py shot <name>                       # with `demo on` first, so two screenshots are comparable
ui.py crashes                           # crashes/ANRs OF THE APP, not of the harness (R8)
ui.py avds · serial <alias> · release   # which AVDs exist and are in use · alias → serial · free the device
ui.py --help · ui.py <cmd> --help       # every command and every flag, from the script itself
```

`harness/net.sh on|off|status|slow|full` toggles airplane mode and **waits until the change is real**,
refusing when it cannot prove it. `net.sh reach` checks that the **device** can open a connection to
the test server — a validated network only means internet, and this computer reaching the server says
nothing about the device. When it can't, try **another address for the same server** first (a VPN or
Tailscale name the device resolves) before building a relay; if the computer resolves it and the
device doesn't, that is DNS — [`harness/android/GOTCHAS.md`](harness/android/GOTCHAS.md) has the fix.

Every command first checks that a device answers and refuses with adb's own message if not. Nothing
project-specific is in the scripts: package, database aliases and device aliases come from
`qa.config.json`. Pointing the harness at a different app is one config file.

### Gotchas

Android-specific traps that each cost a session — a managed device, two campaigns on one computer,
Compose `id=` selectors, the keyboard's stylus pill, a Toast that is not in the tree, tests on the
device reinstalling the app: **[`harness/android/GOTCHAS.md`](harness/android/GOTCHAS.md)**. Read it
before deciding that a screen, a control or a crash is the app's fault.

---

## 4. What this does not do

- It does not replace unit tests. It finds the defects unit tests were never pointed at.
- It does not run unattended. The judgement calls — is this a defect or my tool lying? — are the
  work.
- It does not know your product. Oracles come from your backend and your reference implementation;
  the skill knows *that* you need them, not *what* they say.
- It ships one harness. The Android one is done; any other platform is a harness that implements
  the seven-capability contract in `harness/README.md` — a real piece of work, not a shim.

**Blind spots, by design.** This process is strong on state, sync, permissions and dead controls —
things a driver can provoke and an oracle can confirm. It does **not** cover: performance under
load; concurrency beyond what surfaces as a sync conflict; **time** — token and session expiry,
scheduled sync while backgrounded or killed, date rollover; localisation, RTL and non-ASCII data;
accessibility beyond touch targets and names (screen-reader flow, contrast); security beyond
authorisation. Each of those needs its own method. Knowing that is the point of R4 applied to the
process itself.
