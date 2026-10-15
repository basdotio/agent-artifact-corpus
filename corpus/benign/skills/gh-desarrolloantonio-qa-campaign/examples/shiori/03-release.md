# 03 — Release (shrunk build)

Build `0c3caa0` · `stagingMinified` = the release build type's R8 shrinking and resource shrinking, staging app id, debug key (same certificate SHA-256 `0d019a18…` as staging debug, so it installed over the test app **keeping its injected session**). Not debuggable → evidence is UI + API + LOG only, no STORE. The production app id (the user's real session) was never touched.

| Check | Result |
|---|---|
| Earlier rows whose module a later fix touched (§2.2 step 3) | `:data` (LOG-01 → then gate 02) — dex re-checked on this build: `SQL Args` **0**; logcat after a full sync and 3 edits: 0 `SQL Query` lines. Bookmarks edit/tags rows: re-driven below |
| Launch with the kept session, sync | feed loaded, the new `QA_Rel01` (107) arrived with `qa_rel1` → Retrofit + Gson under R8 OK |
| Add tags to selected (`qa_rel2`, bulk answering `null`) | API `qa_rel1, qa_rel2` · the editor then showed both → the Room merge ran |
| Edit: Public on | API public 1, **both tags kept** (M-03) |
| Edit: remove both tags | API `[]` via the new DELETE route (M-02); no pending badge |
| Crashes | 0 crashes, 0 ANR |
| Version | versionCode 57 = what 1.52.02 shipped → **the next release must be 58** (queue #8, user's step) |
| Upgrade in place from 1.52.02 | not re-run: no schema or store change in this campaign (WorkManager tags only); the first campaign's 06 covered it |
| Fixtures | `cleanup` → API 81 bookmarks, 8 original tags; debuggable staging build put back (same bytes as built), Room 81 rows, 0 `QA_`, 0 `qa%` tags; device released |

## Gate 03 — closed
No code changed in this process; last suite at `0c3caa0`: 340, FLAKY-01 green on rerun.
