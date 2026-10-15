# `<NN>` — `<area>` · `<device>`

> Model for the ONE file each process writes, `NN-<area>.md` (SKILL.md §2.1 step 4). Don't copy it
> blank into the campaign folder: write it when the process starts, and delete these two lines.

> Build `<commit>` · device `<alias>` (`<what it is>`) · account `<A>` · `<date>`. Screenshots in `<dir>`.

## Inventory

`<the process's inventory, in the shape of templates/inventory.md, one heading level down — or, only
if it is too big to read here, a link to NN-<area>-inventory.md>`

## Findings

| ID | Sev | Origin | What actually happens | Where | Status |
|---|---|---|---|---|---|
| `<ID>` | **P0/P1/P2** | `<from a change since the earlier campaign | missed last time | first campaign>` | **`<one bold sentence a non-developer understands>`** — then the mechanism, and the measurement that proves it | `<file:line>` | one of: ✅ **fixed and verified in the running system**: `<what you did and what you saw>` · `<N>` tests, seen red for the reason they name (R6), on the build with the fix · negative pair `<yes / n/a>` — or — ✅ **device-only, no test — because `<why>`** — or — ⏸ **deferred**, queue item `<#>`: `<P2 outside the fix mode / a product decision>` — or — ⚠️ **unproven**: `<what could not be told, and what stopped you — it does not close the gate (R1)>` — or — 📋 **reported** (report-only mode): steps to reproduce · evidence from each oracle · likely fix |

> Evidence names **which** fixture, account and build, and the order the oracles were read in (R5):
> two oracles about two different rows read exactly like two oracles about one. One line per claim is
> enough — `QA_Item_17 · account A · build a1b2c3 · phone · UI "Saved" → STORE syncStatus=SENT → API GET
> version=8` — and it is what makes the chain checkable by someone who wasn't there. Every severity names the
> line of the table it matches; when none of them fits, the finding goes to the queue instead.
> Severity scale: SKILL.md §2.3. What must be fixed before the gate depends on the fix mode in
> CAMPAIGN.md; in report-only mode nothing is.
> A fix that touched code beyond this process's own module ends its Status with
> `modules: <what git diff --stat showed>` — the release gate re-drives the earlier processes those
> modules belong to (SKILL.md §2.2 step 3).

## Screens looked at (EYE)

Every screen this process calls verified, with its screenshot opened — not only saved (R5).

| Screen | Screenshot | What was seen |
|---|---|---|
| `<screen>` | `qa-shots/<name>.png` | `<cut off / overlapping / crowded / unlabeled / fine — in words>` |

## What happened

| What | Result |
|---|---|
| `<the full cycle you drove, in the order you drove it>` | ✅ / ❌ |
| `<absence sweeps re-run for this module (R4), if its code changed: candidates · discarded · driven · confirmed · unproven>` | ✅ / — |
| Full repository test suite | ✅ `<N>` tests, 0 failures |
| Crashes / hangs (of the app, not the harness) | ✅ 0 / 0 |
| `QA_` fixtures cleaned and verified through the API | ✅ |

## Open

`<what this process did not cover and why — the honest half. If a defect could not be reproduced
from the harness, say so here and say what the test actually covers instead. If the harness was
wrong about something, say that here too (R8, R12).>`
