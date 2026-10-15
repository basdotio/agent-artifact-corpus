# QA campaign — Shiori Android Client (second campaign)

**Started:** 2026-09-24 · **Build at start:** `c2b2206` (= v1.52.02 `44a8b2d` + the AGENTS.md rename; versionCode 57) · **Branch:** `qa/2026-09-24` from `develop` · **Skill at start:** `3072ea4` · **Status:** closed 2026-09-24 at `0c3caa0`

**Offline depth:** **full** — unchanged from the first campaign: Room first, WorkManager `SyncWorker` sends CREATE/UPDATE/DELETE/CACHE later (R1) · **Fix mode:** fix severe · **Commits:** at each gate, on `qa/2026-09-24` · **Docs live in:** `docs/qa/2026-09-24/`, gitignored — **local to this Mac, no backup**

**What already existed** — **Devices:** `emu` = `avd:Resizable_Experimental` (API 37.1, emulator-5560), shared by turns with the AdventureLog campaign; <a work phone> is a work phone, listed in `managedDevices`, never touched · **Test server:** the NAS test copy, Shiori 1.8.0 (`192.168.1.20:18080` from the Mac, `ds224…ts.net:18080` from the emulator); its 81 bookmarks and 8 tags are never touched · **Accounts:** A `shiori` (id 1), B `Claude` (id 3), owners, credentials in `qa.credentials.json` · **Data not to touch:** everything not `QA_` (marker in the URL) · **Earlier QA work:** the first campaign, `docs/qa/*.md` (2026-09-14/15, 00–06 all closed, shipped as 1.52.02) — the baseline, not overwritten. Harness `scripts/qa/` reused.

**What changed since it closed:** app code — **nothing** (`44a8b2d` = tag v1.52.02; `develop` has no later commit). Server — same 1.8.0. Skill — ~30 commits (`5588b46` → `3072ea4`). So every finding here is a **miss of the first campaign**, and the scope is only what the new rules can see (user's decision, 2026-09-24).

---

## 1. Scope and order

| # | Process | What the first campaign could not see | Where | Gate |
|---|---|---|---|---|
| 00 | Setup delta | sweeps re-run under the new R4 (S4 precision+recall greps, multi-line `catch`, `runCatching`; S1 computed-but-never-stated; S3 six endings; numbers that add up) · LOG oracle (new) · release shippable (versionCode above 57) · `net.sh reach` | — | sweeps recorded with their counts; app reaches the server |
| 01 | EYE pass | **every screen's screenshot opened and described** (R5 — the first campaign judged screens from the dump) · a11y **state** in the attribute each control uses (checked/selected) · phone, tablet, dark | `emu` phone + tablet sizes | every screen has an EYE row |
| 02 | Offline mix | for every kind of write: offline change, then an online change to **the same record before the queue drains** — both reach the server (R1, new) · **recovery on its own** per screen (R1, new) | `emu` phone | STORE and API agree, nothing lost |
| 03 | Release | suite; earlier rows re-driven where a fix touched their module; version above 57; minified build smoke — **only if 00–02 changed code** | `emu` | the artefact runs |

**Not covered, by decision:** minimum OS (minSdk 26 — no image below API 31 installed; user, 2026-09-24). **Not applicable:** permission flows (R5) — the only permission is INTERNET (both manifests). Account switch in one process: done in the first campaign's 05, not repeated.

## 2–5. Devices, accounts, fixtures, oracles

As in the first campaign's `CAMPAIGN.md` §2–§5, plus **LOG** = `scripts/qa/ui --device emu log` (secrets hidden). App under test: `stagingDebug` `com.desarrollodroide.pagekeeper.staging`; the production install on the emulator (his) is never touched.

## 6. Absence sweeps

Counts and every row: [00-setup.md](00-setup.md). Confirmed: LOG-01 (P1, fixed), S2-16, S4-12 (P2). Unproven: S4-13. S3 endings given to ABS-07/12/14.

| ID | Module | Source | Sev | Finding | Evidence | Status |
|---|---|---|---|---|---|---|
| LOG-01 | data (all screens) | LOG oracle, 00 | **P1** — §2.3 "a secret in the system log … P1 otherwise": plain user phones, reading it needs adb or a bug report. **Would be P0** for a managed fleet whose tooling collects logs. Confirmed by the user at calibration | **Every Room query is written to the system log with its values, in release builds too.** Every bookmark's URL, title, excerpt and author (and the readable HTML when it is saved) goes to logcat as `D SQL Query: … SQL Args: [...]` on each sync. Anyone with adb, or a bug report, reads the user's whole library. Missed by the first campaign: it had no LOG oracle. | `BookmarksDatabase.kt:106-108` — `setQueryCallback` + `Log.d`, not gated by build type; no `-assumenosideeffects` for `Log` in `proguard-rules.pro`. The published `Shiori v1.52.01.apk` (release, minified) contains the `SQL Args` string in `classes.dex`; since 2024-08-22 (`cd786d4`). Seen live: 1.52.02-staging, 09:55:13, rows 1–8 of the test server | ✅ **fixed** — details in [00-setup.md](00-setup.md) §LOG-01 |

## 7. User queue

| # | What | Why it needs you | Recommendation | Gates closed assuming | Reopen on resolution |
|---|---|---|---|---|---|
| 2 | S2-16 tag chip on a card does nothing | P2 = queue in fix-severe | fix: tapping a chip filters by that tag, like the toolbar | — | — |
| 3 | S4-12 Epub error silent on the 2nd failure · S4-12b raw exception text | P2 + wording | fix both: clear the error on dismiss, say "Could not reach the server" | — | — |
| 4 | S4-13 reader stuck on an empty 200 | unproven | accept as unproven, or I drive it with the fake server (~20 min) | — | — |
| 5 | LOG-02/03/04 titles and crash log in logcat | P2 | fix together, same pattern as LOG-01 | — | — |
| 6 | ABS-07, ABS-14 | product decision | leave out | — | — |
| 7 | ABS-12 edit title | known, in BACKLOG | leave it in BACKLOG | — | — |
| 9 | T-02 tag filter never refreshed from the server | P2 | fix: fetch tags on every feed start, as the bookmarks sync does | — | — |
| 10 | EYE-01…07 (reader margins, broken image, update dialog, card a11y name, compact gap, tablet title, wording) | P2 / wording | fix EYE-04 (a11y) and EYE-01; the rest one batch when convenient | — | — |
| 11 | M-04 card doesn't redraw after Add tags · M-05 editor suggestions stale · FLAKY-01 | P2 | fix M-04 with T-02 (same staleness); FLAKY-01 fix the leaking test | — | — |
| 8 | next release versionCode 58 | release is yours | — | — | — |
| 1 | Calibration (R2 stop 4): LOG-01 severity and fix | first P1-or-worse finding | ✅ answered 2026-09-24: P1 (P0 for a managed fleet); callback debug-only; test seen red + `strings` on the release dex; other logging listed, not fixed | — | — |

## 8. Log

| Process | Build | Date | Covered | Result | Gate |
|---|---|---|---|---|---|
| 00 | `c2b2206` + gate-00 commit | 2026-09-24 | [`00-setup.md`](00-setup.md) | LOG-01 (P1) fixed + seen red + dex checked; sweeps: S2-16, S4-12 (P2) confirmed, S4-13 unproven; suite 332/0 | ✅ closed |
| 01 | `f993848` | 2026-09-24 | [`01-eye.md`](01-eye.md) | 21 screens opened and described (phone, dark, compact, tablet); T-02 + EYE-01…07, all P2; 0 crashes; no code changed | ✅ closed |
| 02 | `f993848` + gate-02 commit | 2026-09-24 | [`02-mix.md`](02-mix.md) | **M-03 (P0)** tags added elsewhere stripped by the next edit · **M-02 (P1)** last tag never removable — one fix, 5 tests seen red, verified on the device incl. the offline mix; M-04, M-05, FLAKY-01 (P2) queued; suite 340 (1 flaky, green on rerun); fixtures cleaned | ✅ closed |
| 03 | `0c3caa0` | 2026-09-24 | [`03-release.md`](03-release.md) | stagingMinified over the test app (session kept): sync, bulk tags, edit, last-tag removal OK; dex and logcat free of the query log; 0 crashes | ✅ closed |

## 9. Close-out

On identical app code (1.52.02), the new rules found **3 severe findings the first campaign missed, all fixed**, each with tests seen red and checked on the device:
- **M-03 (P0):** editing a bookmark deleted tags added elsewhere.
- **M-02 (P1):** a bookmark's last tag could not be removed.
- **LOG-01 (P1):** the whole library went to logcat in release builds.

They came from the LOG oracle (new since the first campaign) and the online/offline mix rule.

**Deferred, all P2, in the queue (#2–#11):**
- S2-16: a tag chip on a card does nothing.
- S4-12 / S4-12b: the Epub error doesn't show a second time, and shows the raw exception.
- T-02: the tag filter is never refreshed from the server.
- M-04: the card doesn't redraw after "Add tags".
- M-05: the editor's tag suggestions are stale.
- EYE-01…07: reader margins, update dialog, card accessibility name, compact view gap, tablet title, wording.
- LOG-02…04: bookmark titles and the crash log in logcat.
- FLAKY-01: a unit test that failed once.

**Unproven:**
- S4-13: the reader stuck on an empty 200 answer.
- EYE-02: the cause of the broken image in the reader.

**Not covered, by decision:** minimum OS, and the visitor role (as in the first campaign). Permissions: n/a (INTERNET only).

**Final suite:** 340 tests, 1 flaky that passed on rerun. Instrumented tests were not run (they would wipe the session).

**Branch:** `qa/2026-09-24`, 3 commits (`c2b2206`, `f993848`, `0c3caa0`), not pushed.

**Friction log:** 2 lines (`net.sh reach` false negative; `redcheck` labelling Mockito verify failures). Upstream issue: https://github.com/DesarrolloAntonio/qa-campaign/issues/13
