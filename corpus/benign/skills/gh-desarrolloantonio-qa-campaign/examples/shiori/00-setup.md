# 00 — Setup delta

Build `c2b2206` + LOG-01 fix (uncommitted until this gate closes) · account A · `emu` (emulator-5560, API 37.1) · app `com.desarrollodroide.pagekeeper.staging` 1.52.02-staging (versionCode 57), confirmed byte for byte with `ui.py installed --apk`.

## Reach
`net.sh reach` said NOT reachable — **the tool was wrong** (SKILL-FRICTION): from `run-as` no name resolves on this emulator, not even `google.com`. The app's own reach, proved: cold start 09:55, then LOG `INSERT OR REPLACE INTO bookmarks … [1..8]` = the test server's rows written into Room after launch.

## LOG-01 — the Room query log (P1, fixed)

**What happens:** every Room query goes to logcat with its bound values, in release too. On every sync each bookmark's URL, title, excerpt and author land there, and so does the readable HTML: its inserts go through the same callback (`BookmarkHtmlDao.insertOrUpdate`). There is no other logging of readable HTML (`ReadableContentViewModel` logs only status messages). Anyone with adb or a bug report reads the whole library. **P1** for plain phones (§2.3, secret-in-log row); **P0** for a managed fleet that collects logs.

**Fix:** `BookmarksDatabase.create` calls `.logQueriesIf(BuildConfig.DEBUG)`; the callback only exists behind that flag. `:data` gets `buildConfig = true`. The `minified` app build type falls back to the library's `release` → `DEBUG = false`. Touched: `data/build.gradle.kts`, `BookmarksDatabase.kt`, new `QueryLogTest.kt` (module `:data` only).

**Red / green (R6, R7):**

| Test | Break | Result |
|---|---|---|
| `QueryLogTest` "outside debug the database gets no query callback" | `if (enabled)` → `if (true)` | **red** on its own check: Mockito `NeverWantedButInvoked` (redcheck mislabelled it a crash — SKILL-FRICTION) |
| negative pair "in debug the database logs its queries" | `if (enabled)` → `if (false)` | **red**: `WantedButNotInvoked … zero interactions with this mock` |
| both, fix restored | — | **green**, 2 passed, from reports this run wrote (`:data:testDebugUnitTest --rerun --no-build-cache`) |

**Build-type check (a check, not a test — unit tests compile debug only):** `strings -a` on the dex, counting `SQL Args`:

| Artefact | Hits |
|---|---|
| published `Shiori v1.52.01.apk` (release, minified, before) | **1** |
| `Shiori v1.52.02.apk` `productionMinified` with the fix (after) | **0** |
| `Shiori v1.52.02-staging.apk` debug with the fix | 1 — intended, debug keeps it |

**Device:** the release build was not run on the device. The production app id on `emu` holds the user's real session, so it isn't touched (R11). Debug behaviour is unchanged by design. Evidence for release = the dex above. **Device-only verification of release: not done, and not needed for this claim.**

**Suite (R13):** 332 tests ran this time, 0 failures (`:data`, `:domain`, `:presentation` ×2 flavors); the other modules were up to date with unchanged inputs (last green at `44a8b2d`). androidTest sources compile (staging + `:data`).

## Other logging that prints user data — listed, not fixed (user: "only fix this one now")

Sweep: `Log.[vdiwe](|println(|printStackTrace|HttpLoggingInterceptor` over `*/src/main` → **77 lines** = 1 LOG-01 · 4 `HttpLoggingInterceptor` (import + level; already safe, BODY only when `DEBUG` since the first campaign) · 7 below · 65 discarded (status text, counts, ids, `e.message` of network errors). The 7, none gated by build type:

| ID | Where | What reaches logcat | Proposed |
|---|---|---|---|
| LOG-02 | `SyncWorksImpl.kt:152` | **bookmark title** (decoded) of every pending job, each time the pending sheet/flow re-emits | P2 → queue |
| LOG-03 | `SyncWorksImpl.kt:74` | WorkInfo `tags`, which carry `bookmarkTitle_<url-encoded title>` | P2 → queue (same fix as LOG-02) |
| LOG-04 | `CrashHandlerImpl.kt:39`, `:48` | the whole crash log, twice: exception message + stack trace; a message can carry a URL or a title | P2 → queue |
| LOG-05 | `SyncWorker.kt:51` | `UpdateCachePayload` — ids and flags only; **no user data**, listed for completeness | accept |
| LOG-06 | `LoginViewModel.kt:133`, `:158` | server liveness / version info, not user data | accept |

No token or password found in any `Log` call. The session lives in DataStore, which has no query callback.

## Absence sweeps under the new R4 (whole app: `presentation`, `domain`, `data`, `network`, `model`, `common` — `src/main`)

The first campaign's S1–S3 rows (ABS-01…15) and S4-01…11 are the baseline. Re-checked, not re-reported. New here: the S4 precision/recall/multi-line greps, S2's preview filter, S1's computed values, S3's endings.

| Sweep | Candidates | Discarded (by the rule) | Driven | Confirmed | Unproven |
|---|---|---|---|---|---|
| S1 | 2 computed values (hidden tag, last sync time) | 2 — the hidden tag is stated on the feed ("Hidden: X"); `lastSyncTimestamp` is sync bookkeeping, read by nothing | 0 | 0 | 0 |
| S2 | 94 lines | 68 in `@Preview` functions · 8 empty **default values** (callers checked: every real caller that leaves one empty is among the hits) · 6 `LoginContentSample` (preview helper the filter missed) · 2 TODO comments with nothing behind them in the UI · 6 `InfiniteProgressDialog(onDismissRequest = {})` (not dismissable by design; moved to S4) · 2 `onConfirm = {}` on `ConfirmDialog` (the dialog closes itself) · 1 Theme row (`ThemeOption` handles its own click) | 1 | **1** (S2-16) | 0 |
| S4 | precision 2 · recall 21 · sealed `Loading` 5 · log-only `catch` 2 (both `CrashHandlerImpl`) · `onFailure {}` **0** · `runCatching` 8 | 21 recall hits that open dialogs or sheets (no work starts) · `FeedContent:94` (undone by `delay`) · `DeleteLocalBookmarkUseCase`/`TagsRepositoryImpl`/`NetworkBoundResource` Loading (consumers end on Error — S4-04/05/10 fixed in the first campaign) · editor spinner + error dialog (`bookmarkUiState` never leaves idle: dead, not stuck) · CrashHandler catches (no UI) · 8 `runCatching` all consumed (`getOrNull`/`onFailure`/`getOrElse`) | 2 | **1** (S4-12) | **1** (S4-13) |
| S3 | the first campaign's 3 S3 rows with no ending | — | — | endings below | — |

S2 is first-order: a handler that calls an empty function escapes it.

| ID | Module | Sev | Finding | Evidence | Status |
|---|---|---|---|---|---|
| S2-16 | bookmarks | **P2** (workaround: the tags button on the toolbar filters) | **A tag chip on a card looks tappable, ripples, and does nothing.** The chips used to be invisible (BM-01), which is why the first campaign couldn't drive ABS-10. Tapped "android" on `https://m3.material.io/`: screen identical, no filter, no message | `FeedContent.kt:168` `onClickCategory = { }` · UI dump before/after identical · EYE `s2-chip.png`: three teal chips under the date, nothing selected | queue |
| S4-12 | bookmarks | **P2** (workaround: a successful download, or a restart, re-arms the dialog) | **Epub download: the second failure in a row says nothing.** Offline, Epub on bookmark 81 → "Download Error". Accept, Epub again → no dialog, no spinner, nothing, although the request did go out and fail | LOG `10:08:11 --> GET …/bookmark/81/ebook ← HTTP FAILED UnknownHost` and again at `10:08:29` · UI after 5 s: feed only · `FeedScreen.kt:196-208`: `openDialog = remember { mutableStateOf(true) }` stays false while `downloadUiState.error` never clears (same shape as S4-04) | queue |
| S4-12b | bookmarks | P2, wording | The error shows the raw exception: *Unable to resolve host "ds224…": No address associated with hostname*. The feed says "Could not reach the server" for the same thing | EYE `epub-err1.png`: centred dialog, readable, not cut off; text is the exception | queue (product: wording) |
| S4-13 | reader | — | **Unproven, can't be driven with the network.** A readable-content `Success` with a null body leaves the reader's undismissable spinner up for good (`result.data?.let` with no else) | `ReadableContentViewModel.kt:77-85` · needs a server that answers 200 with no body (fake server) | queue: unproven |
| — | bookmarks | — | Recovery on its own (R1): network back → Epub → "Success — Epub file downloaded, would you like to share it?" | UI + EYE `epub-online.png` | ✅ recovers |

**S3 endings** for the first campaign's rows that had none (R4):

| Row | Absence | Ending |
|---|---|---|
| ABS-07 | change password, account management, language selector | **product decision** → queue |
| ABS-12 | edit title / excerpt / URL | **defect** in the R4 sense: `BACKLOG.md:148` plans the title. Already known, P2 → queue |
| ABS-14 | archive view, `tag:`/`-tag:` search, untagged filter, batch ebook | **product decision** → queue |

## Release shippable (§2.1)
`versionCode=57` on disk = what 1.52.02 shipped (tag `v1.52.02`, on `origin/master`), so **the next release must be 58**. The release key lives only in CI. `productionMinified` builds (exit 0, 3.3 MB). It was not launched: the production app id holds the user's real session.

## Gate 00
Sweeps recorded with their counts; app reaches the server (LOG + STORE; `net.sh reach` was wrong). LOG-01 fixed. No fixtures created. Suite: 332 tests ran after the fix, 0 failures; no code has changed since. **Closed.**
