# Control inventory — `<module>` (`<platform>`)

> Model for the first section of each process's file, `NN-<area>.md` — not a file to copy blank
> into the campaign folder (SKILL.md §2.1 step 4). Delete this paragraph when you use it.

> Derived from the UI code and the manifest/router on `<date>`, build `<commit>`. This is the list
> of things to test (R3). It is blind to what the module is MISSING — that is what the absence
> sweeps are for (R4).

## Screens

### `<Screen name>` — `<file>`

| # | Control | Kind | What it should do | Oracles | Suspect? |
|---|---|---|---|---|---|
| 1 | `<label or test id>` | button / menu / dialog / gesture / field | | UI (+STORE+API if it writes) | |

> **Oracles**: a control that writes, syncs, grants or deletes needs two of UI/STORE/API; one that
> only opens or navigates needs UI plus a second look (EYE, or the UI again after R9).
> **Suspect** = something you noticed while reading the code that looks wrong but isn't proven yet.
> Number them and carry them into the run; an unchecked suspect is not a finding.

## Entry points that are not controls

Deep links, share targets, notification actions, widgets, shortcuts — from the manifest or the
router, not the UI layer. Each is a row here and gets driven (`<harness> open <url>`).

| # | Entry point | Declared in | Lands on | Oracles |
|---|---|---|---|---|

## System permissions

Every dangerous permission the manifest declares — the ones the OS asks about. One row each, driven
like any other control (SKILL.md R5).

| Permission | Screen that asks | Denied → | "Don't ask again" → | Revoked, then relaunched → |
|---|---|---|---|---|

## UI state fields

Every field of the state object, and where it is painted. A field with nowhere to be painted is an
**S1** hit (R4).

| Field | Painted in | S1? |
|---|---|---|

## Suspects carried out of this inventory

| # | What | Why it looks wrong |
|---|---|---|
