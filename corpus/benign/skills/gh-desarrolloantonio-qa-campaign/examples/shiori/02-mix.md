# 02 — Offline mix (and the online edits it led to)

Build `f993848` → fix build (same branch, uncommitted until this gate) · account A · `emu` phone · fixtures `QA_Mix01–03` (ids 104–106), tags `qa_mix1–3`, all created and deleted by this process.

## Inventory — writes and how each can reach the server

| Write | Path | Mix driven |
|---|---|---|
| Edit (tags, Public) | Room first → UPDATE job (unique per bookmark, REPLACE) → worker reads Room when it runs | offline edit + online "Add tags to selected" before the drain · two offline edits in a row + a server-side tag meanwhile |
| Add tags to selected | **online only**, straight to `PUT /api/v1/bookmarks/bulk/tags` | against a pending UPDATE, and alone followed by an edit |
| Add / Delete / Update cache | CREATE / DELETE / CACHE jobs | covered by the first campaign's 04 (C1, #13); not re-driven: no online path writes the same record while those wait |
| Tag rename / delete | online only (Manage tags), no queue | n/a to the mix |

The first campaign's C1 already covered **web edit + offline app edit** for URL/title/excerpt. Tags weren't part of it.

## Findings

| ID | Sev | What actually happens | Where | Status |
|---|---|---|---|---|
| M-03 | **P0** — data loss (§2.3) | **Editing a bookmark in the app silently deleted tags added anywhere else since its last sync.** The upload treated every tag the server had and the local copy lacked as one the user removed, and stripped it. Triggers: a tag added on the web or another device, and the app's own "Add tags to selected" (Shiori 1.8.0 answers that call with `"message": null`, so the app never stored the new tags). Driven online on `QA_Mix03`: server `qa_mix1`+`qa_mix2` → app edit that only turned Public on → job SUCCEEDED → server `qa_mix1`. **Stopped the process (R2 stop 1); user confirmed P0 and the fix** | `BookmarksRepositoryImpl.editBookmark` (removal block) · `addTagsToBookmarks` | ✅ fixed, verified on the device |
| M-02 | **P1** — blocked, no workaround | **Removing a bookmark's last tag never reached the server.** The removal used the bulk route, which answers 400 "tag_ids should not be empty": 5 retries, FAILED, card without the tag, server keeping it; "Retry all" can only fail again | same removal block | ✅ fixed, verified on the device |
| M-04 | P2 — workaround: reopen the app | After "Add tags to selected" the card doesn't redraw with the new tag, although Room and the cross-refs have it; it shows after a relaunch | feed list invalidation — not located | queue |
| M-05 | P2 | The editor's suggestions didn't offer `qa_mix1`/`qa_mix2` although both were in Room's tags table | editor suggestions source — not located (probably the same staleness as T-02) | queue |
| FLAKY-01 | P2 (test) | `SettingsViewModelLogoutConfirmationTest` "cancelling the confirmation logs nobody out" failed once (staging flavor): *UncaughtExceptionsBeforeTest: There were uncaught exceptions before the test started* (an earlier test in the same JVM leaks); passed on two reruns | presentation unit tests | queue |

## The fix (one change for M-02 and M-03)

- **What is removed:** only the tags the user took off. `EditBookmarkUseCase` computes them (Room before − edited) and adds whatever a still-waiting edit was going to remove (`SyncWorks.pendingTagRemovals`), minus anything put back. The job carries them in its input and in a `removedTags_` work tag (WorkInfo doesn't expose input); "Retry all" re-queues with them.
- **How it is removed:** `DELETE /api/v1/bookmarks/{id}/tags` per tag (exists on 1.8.0, measured: 200, and it removes a last tag). The bulk route is no longer used for removal.
- **Bulk add with a null answer:** the added tags are merged into the Room row (tags only, so an edit waiting to upload keeps the rest).
- Touched (`git diff --stat`): `:network` RetrofitNetwork · `:data` BookmarksRepository(+Impl), SyncWorks(+Impl), SyncWorker · `:domain` EditBookmarkUseCase · tests. **Upgrade edge:** an UPDATE queued by 1.52.02 carries no removals; if it drains after the update, a tag removed in that edit stays on the server. Acceptable: nothing is lost, the user can remove it again.

**Red / green (R6, R7)**, `--rerun --no-build-cache`, from reports this run wrote:

| Test | Break | Red on |
|---|---|---|
| `BookmarksRepositoryTest` "a tag added on the server since the last sync survives an edit that did not remove it" (M-03) | removal filter back to "server − local" | `NeverWantedButInvoked` removeTagFromBookmark. **First attempt was red on an NPE (unstubbed call), not the check. `redcheck` rightly said NOT RED; the stub was added and it went red on its own `verify`** |
| "a tag removed in an edit is removed on the server too" (the pair) + "removing a bookmark's last tag is sent as a removal of that tag" (M-02) | removal filter `{ false }` | both `WantedButNotInvoked` removeTagFromBookmark |
| "tags added to a selection reach Room when the server sends no bookmarks back" | `if (updated.isNotEmpty())` → `if (true)` | `WantedButNotInvoked` updateBookmarkWithTags |
| `EditBookmarkUseCaseTest` "the job removes what the user took off and what a waiting edit was going to take off" | drop the pending removals | `expected <[qa_b, qa_old]> but was <[qa_b]>` |
| "a tag kept or put back is not removed" (pair) | don't subtract kept tags | `expected <[]> but was <[qa_old]>` |
| all, fix in place | — | GREEN 23 + 2 |

Changed existing tests: the old "tag removed in an edit" test now passes the removal explicitly (it had encoded the P0's rule); `AddBookmarkUseCaseTest` gets a 4th matcher for the new parameter.

**Device (1.52.02-staging with the fix, confirmed byte for byte), on `QA_Mix03` (106), read in this order: UI → STORE → API**

| Step | Result |
|---|---|
| "Add tags to selected" `qa_mix2` | Room + cross-refs `qa_mix1, qa_mix2` · API both · card shows `qa_mix2` only after a relaunch (M-04) |
| edit: Public off | job SUCCEEDED · API `qa_mix1, qa_mix2`, public 0 ✅ (before the fix: `qa_mix2` stripped) |
| API adds `qa_mix3` (not in Room) → edit: Public on, remove `qa_mix1`, `qa_mix2` | SUCCEEDED · API `['qa_mix3']`, public 1 · Room learnt `qa_mix3` ✅ |
| edit: remove `qa_mix3` (last tag) | LOG `DELETE …/106/tags ← 200` · SUCCEEDED · API `[]`, Room `[]` ✅ (before: 400 ×5, FAILED) |
| **mix**: offline edit 1 removes `qa_mix2` → offline edit 2 turns Public off (job carries `removedTags_["qa_mix2"]`) → API adds `qa_mix3` → network back | SUCCEEDED · API public 0, `['qa_mix3']` · Room the same ✅ |
| Recovery on its own (R1) | network back → the queue drained without any action ✅ |
| Old build's failed jobs (104, 105) | "Retry all" → 3 SUCCEEDED, sheet empty |

**Suite (R13):** 340 tests ran, 1 failure = FLAKY-01, which passed on two reruns of `:presentation:testStagingDebugUnitTest` (all green). androidTest sources compile (staging + `:data`). Instrumented tests not run: the device holds the injected session (`connectedAndroidTest` wipes it).

**Fixtures (R10):** `cleanup` → 3 `QA_` bookmarks + 3 `qa_` tags deleted; API 81 bookmarks, tags back to the 8 originals; Room 81 rows, 0 `QA_`, 0 `qa%` tags. 0 crashes.

## Gate 02 — closed
