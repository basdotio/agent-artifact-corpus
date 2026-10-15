# Review — qa-campaign

Branch `review/fable-pass`, from `a1ee970`. All six phases done. Nothing pushed, no PR.

`./tests/run`: **51 tests, OK, 27.8 s** before · **71 tests, OK, 34.8 s** after (Python 3.14.8, bash
3.2.57, macOS; the 71 also pass on the system Python 3.9.6, 42.7 s). No device was used: every
claim below about device behaviour comes from the code and the stub.

## (a) Fixed

Each regression test was seen failing before its fix, on its own assertion.

| # | What was wrong | Seen red as | Commit |
|---|---|---|---|
| 1 | **`ui.py`: the `packagePrefix` list was ignored by the input guard, the BACK check and the crash filter.** The config documents the list as "count several variants as one app", but those three compared with `android.package` alone. With the listed debug variant in front, input was refused; worse, its crash came out as `0 crashes`, exit 0 — a silent all-clear. | `refusing input: com.example.app.debug is in front` · `1 != 0 : 0 crashes` | `80a8a25` |
| 2 | **`net.sh`: a `$ADB` that is not a file fell through to the adb on PATH.** `ui.py` refuses this case on purpose; `net.sh` did not. | exit 0, the PATH adb was asked | `e43dc33` |
| 3 | **`net.sh on`: `${ANDROID_SERIAL#emulator-}` on an unset variable under `set -u`.** As I read the bash manual, bash 4+ stops there with "unbound variable" instead of the "network not validated" message. **Not seen red and not confirmed:** bash 3.2 (the only bash here) tolerates it, so the test was removed and this one-token change has no test. | — | `e43dc33` |
| 4 | **`redcheck.py`: a report timestamp with no zone was read as local time.** Gradle up to 8.x writes GMT with no marker (Ant's `DateUtils`; checked in Gradle's source at v7.6.0 and v8.5.0 — current Gradle writes `…Z`). East of Greenwich a report written seconds ago looked hours old, was "ignored", and a real red came back NOT RUN. Now stale means stale under both readings. **Trade-off:** for zone-less timestamps the stale check is weaker by the UTC offset. | `ignored … the report says it ran at 13:43:38, before this run started` → NOT RUN | `34c9335` |
| 5 | **`redcheck.py`: `--break` on one file spelled two ways** (`Repo.kt`, `./Repo.kt`) kept the already-broken text as the second "original", wrote it back, and crashed in the restore. Keyed by real path now. | `FileNotFoundError` in `restore`, exit 1 | `34c9335` |
| 6 | **`redcheck.py`: a timeout killed only the command, not what it started.** A child kept running and could write a report after the break was undone. The run now gets its own session and the whole tree is stopped (also on Ctrl-C / SIGTERM). | `the command's own child was still running after the timeout` | `34c9335` |
| 7 | `redcheck.py --help`: `--test` said "contains" (it is an identity match); `--reports` omitted `androidTest-results`. | — (help text) | `34c9335` |
| 8 | **`fake_server.py`: a credential in the query string was printed** (`?api_key=…`). README says the harness hides secrets "everywhere it prints". | secret found in the request log | `3e262d1` |
| 9 | **`fake_server.py`: the body was cut to 300 bytes before hiding**, so an object under a secret key never closed and its contents printed. | `"user": "4321"` in the log | `3e262d1` |
| 10 | **`fake_server.py`: `--header` with no colon** started fine and then dropped every connection (the app sees a network failure, not the status asked for). Refused at start now. | the server started | `3e262d1` |
| 11 | Doc drifts: README test count (51 → 71); `tests/README` "a couple of seconds" (it is ~35 s); `templates/inventory.md` pointed permissions at R4 (the rule is in R5); `templates/CAMPAIGN.md` had no slot for "which build users get" (asked in §2.1, rated by in §2.3); SKILL.md §2.1 step 7 "both" for three entries; `qa.config.example.json` said `db` refuses any unlisted alias (it also takes a path); `ui.py` docstring omitted `secretKeys`, `managedDevices`, `campaign`. | — (docs) | `f98b139`, `80a8a25` |
| 12 | SKILL.md: R5 announced "four ways" the UI oracle says less and listed five; R10 announced "three more things" on the real server and listed five. | — (docs) | `208d7ad` |
| 13 | README: the `qa.credentials.json` example carried `server.url` (the shape in `adapters/README.md` has none); both install commands sat in one block; `net.sh off · net.sh reach` was not shell; "it asks" for two things the skill decides from the code; two of three fix modes named; the docs folder stated as fixed; "Python 3" with no version (3.9+, verified). `examples/shiori/README.md` described `00-setup.md` as holding the harness, session injection and API oracle — it is a setup delta without them. | — (docs) | `fd20e1b` |

**New tests for paths nothing covered** (`2e131e5`). No bug found in them; each was seen red by one
deliberate break in the harness, then the break was put back:

| Test | The break that turned it red |
|---|---|
| a managed device is not rotated | `"rotate"` out of `DEVICE_CHANGING` |
| a device another campaign is driving is refused until released | `LOCK_STALE_S = 0` |
| text the device would drop is refused, not typed | non-ASCII check → `if False` |
| `--in` takes the control of the item it names | `find_in` ignores the anchor |
| `assert` exits 1 when wrong, in either direction | `if present == a.absent` → `if False` |
| `find` with no match is not exit 0 | `raise` → `print` |
| `db` hides a secret column | `secret = [False …]` |
| `db` hides the value of a row whose key is secret | `row_secret[i] = False` |
| a binary store is never printed | control-character check → `if False` |
| `net.sh` refuses an unknown `--device` alias | `|| exit 1` → `|| true` |

Also in `80a8a25`: a control test for the other direction of fix 1 (another app's crash is still not
the app's).

## (b) Proposals — ranked, none applied

Grouped by phase, ranked inside each group. **The five with most impact overall:** skill 1 (§2.2 does
not carry the rules), skill 2 (§2.1 has no step for session injection), skill 3 (UNPROVEN and the
gate), harness 1 (`type` and backslashes — one device check), docs 1 (the README leaves a dirty tree
that the skill then stops on).

### Harness (phase 3)

1. **`ui.py type` probably types stray backslashes — unproven, needs one device check.** It
   backslash-escapes `\ " ' $ & | ; < > ( ) * ? ! # ~` and the backtick, *then* wraps the result in
   `shlex.quote`. Inside single quotes the device's shell keeps backslashes literally, and `input text`
   only interprets `%s`, so `type "a&b (1)"` should arrive as `a\&b (\1\)`. Fixtures like `QA_Note1`
   never hit it. Check: `ui.py type "a&b (1) it's"` into any field. If confirmed, drop the backslash
   step and keep `%s` + `shlex.quote`. I did not change it because I could not see it on a device.

2. **`ui.py db` can print a secret column under an implicit alias.** The guard refuses
   `select password as p`, but `select password p from users`, a subquery or a CTE rename the column
   with no `as`, and the result prints unhidden. A fix that does not depend on parsing SQL: an sqlite
   authorizer that records which columns are read, and hides or refuses when a secret-looking one is
   read under another name. It changes how `db` decides, so it is your call.

3. **Refusals that are still Python tracebacks.** R8 says a traceback reads like a harness bug. Left:
   `require_device` when adb does not answer in 20 s; `fake_server.py` on a port in use, a routes file
   that is not JSON, or a route that is not an object; `net.sh` on a `qa.config.json` that is not valid
   JSON; `redcheck.py` when the command does not exist. Each is a few lines; together they are a
   behaviour pass over four scripts, so I listed them.

4. **`redcheck.py` says NOT RUN when *any* task came FROM-CACHE**, including a compile task while the
   test task itself ran and wrote a fresh report. It errs on the safe side and the message says what to
   add (`--no-build-cache`), but it is a false NOT RUN. Narrowing it to the test task needs a rule for
   which task that is.

5. **`net.sh` interpolates the configured host, port and path into a device shell command unquoted.**
   The values come from the project's own `qa.config.json`, so the risk is a typo, not an attacker; a
   character check on the host (as the path already has) would close it.

6. **`net.sh` asks for a device and claims it before printing usage.** `net.sh --help` with no device
   says "no device reachable". Moving the usage case up is harmless, but it reorders the script.

7. **`redcheck.py`: a report file with only crashes counts as "green"** in the "two report files
   disagree" message (`not f and t > s`). The verdict is still NOT RUN; only the wording is wrong.

8. **SKILL.md §3 lists `state` among "what a script gates on"**, but it exits 0 for both ON and off —
   only a missing switch is exit 1. Either the doc or an `--expect on|off` flag.

9. **Still no test:** `rotate`/`size` read-back, `kill`, `hide-keyboard`, `installed --apk`, `shot`
    on a second display, `reach` over https, `slow`/`full` succeeding, `a11y`'s clipped-vs-small rule.
    The stub needs more state for these (a rotation that changes, a pid that dies).

### The skill as instructions (phase 4)

Read as the agent that has to follow it. Line numbers are SKILL.md's.

1. **§2.2 does not carry the rules it is supposed to execute — this is where an agent cuts corners.**
   Step 2 is one line: "Drive them with the harness, asserting against the oracles (R5)". Everything
   that makes a process more than a click-through lives only in §1 and has no step: recreating the UI
   on each screen (R9), the short-depth offline checks and the recovery check "inside each module's
   process" (R1), the online/offline mix per kind of write (R1), `a11y`, `crashes` (the report template
   has a row for it, no step produces it), noting the account's counts before the process (R10),
   confirming the installed build and the session before driving. `templates/run-report.md` has rows
   for EYE, suite, fixtures and crashes, so skipping those shows; it has none for R9, offline/recovery
   or `a11y`, so skipping those does not. Proposal: one line per obligation in §2.2 (a pointer, not the
   rule again) and a matching row in the run-report template. Highest impact: it is the difference
   between rules an agent read once, 800 lines earlier, and rules it is asked for at every gate.

2. **§2.1 has no step for half of what the setup gate is meant to deliver.** R11 says of session
   injection "the setup gate builds it", and the template's row 00 lists "fixtures, session injection".
   The ten steps contain neither. Also missing as steps: looking at whose install is on the device
   before writing a session (R11), the cold start that proves an injected session survives (R11),
   reading one fixture back to see the `QA_` marker survived (R10), creating `SKILL-FRICTION.md` and
   recording *Skill at start* (R12 — "when it happens, not reconstructed at the end" needs the file to
   exist), and `ui.py release`. An agent that follows §2.1 literally closes setup with a harness that
   drives the app and no way to sign in.

3. **"UNPROVEN never closes a gate" is not what the text then says.** Line 122 states it as a
   headline; line 129 says an unproven item "either keeps the gate open or goes to the human queue as
   itself", and R1 says queue items "are not open work for gate purposes". So unproven → queue → gate
   closed is allowed, and it is the cheapest path there is: the Shiori campaign closed gate 00 with
   S4-13 queued as unproven. Either the headline is the rule (then say what may be queued) or the body
   is (then the headline should be "is never a pass"). As written, an agent can quote the skill for
   both.

4. **Setup's order does not work as numbered.** (a) Step 4 fills in the process list; step 10 decides
   offline depth, which "sets whether the campaign has an offline gate at all". (b) Steps 1, 2 and 3
   record answers "at the top of `CAMPAIGN.md`", which step 4 creates. (c) Step 6 writes
   `qa.config.json` and points at the credentials note, which says "add it to `.gitignore` first (step
   7)". (d) Lines 832–841 are a list numbered 1–4 (the questions) directly followed by a list numbered
   1–10 (the steps), and the text between refers to "steps 1, 3 and 5": "step 1" has two readings.
   Reordering and renumbering is restructuring, so it is listed, not done.

5. **Length.** 1,106 lines, about 14,000 words, and "Read §1 before running anything" is roughly 800
   of those lines. About fifty lines with a "(measured)" anecdote carry the reasons, and several rules have grown by
   insertion until the instruction is hard to find: R11 is 120 lines with mechanisms numbered 1, 2, 3,
   3b, 4, 5; R6's "Red for the reason the test names" paragraph (line 362) holds a sentence with two
   parentheses in a row that no longer parses; lines 102, 194, 535 and 606 each have a new topic
   appended to the end of a line. The skill already uses `references/` for steps 5 and 6. Moving the
   same kind of material — R11's mechanisms, R10's real-server list, R14's release details, the S4
   greps — would leave each rule as its statement plus a pointer. A judgment call on what is rule and
   what is detail, so only proposed.

6. **"Stop at once, and only, when" (line 152) lists four cases; the skill asks to "ask first" in at
   least five others.** A dirty tree (§2.1 step 2), a new build type with its own app id (R11, "it
   changes the build file, so ask first"), cleartext for `127.0.0.1` in the debug network config
   (`harness/README.md`), a device setting for the stylus pill (GOTCHAS), flipping a stored flag (R10
   says only "say in the report"). None is in stop 3's list, and nothing says whether "ask" means stop
   now or queue it. Adding "changing the build configuration or a device setting" to stop 3 would
   settle it.

7. **When the human is actually asked is never placed in time.** R2 describes how to put the queue
   ("two groups") and says "the gate is where the human reads them"; §2.2's nine steps have no step
   that does it, and nothing says whether a gate waits for the answers. The two readings — never ask
   until close-out, or ask at every gate — are both defensible from the text.

8. **Two rules about a gate that depends on the human, and no test for which applies** (lines
   115–120). "A gate waiting on the human" → prepare the next process, drive nothing. "The gate's own
   criterion depends on the human" → close it assuming the queue item. R11 then says "don't wait …
   close gates assuming it". The examples (a device to create vs being signed in to another app) do
   not generalise, so an agent picks the convenient one.

9. **No close-out section.** What ends a campaign is spread over §2.1 ("Status: closed"), §2.2 step 9
   (`ui.py release`), R12 (offer the friction log, write the public copy) and the template's §9. A
   short §2.4 listing them in order would make the last gate as mechanical as the others.

10. **The harness path is assumed.** Lines 713 and 1053 use `~/.claude/skills/qa-campaign`; `npx
    skills add` (the README's first install line) may link it elsewhere, and a project can vendor it.
    "The folder this file is in" is always right. The Shiori campaign used its own wrapper
    (`scripts/qa/ui`), which the skill never mentions as an option. Related: step 5 says "pass
    `--device` on every command" and most examples in §3 omit it.

11. **R11's title says more than the rule.** "The agent never types credentials" — and line 684 asks
    it to sign in "by typing" with invented credentials against a fake or disposable server. The body
    is consistent (the rule protects *real* credentials); the title is what an agent remembers.

12. **When sweep candidates are driven is not said.** R4 runs the sweeps "once, for the whole product,
    at setup" and requires numbers that include "8 driven". At that point the session may not exist
    yet (see 2). S1 also appears twice: as a setup sweep and as the "UI state fields" table in every
    module's inventory.

13. **§2.2 writes the report (step 7) before cleaning the fixtures (step 8)**, and the report has the
    row "`QA_` fixtures cleaned and verified ✅". Swap them, or the row is written before it is true.

14. **§2.3:** the secret-in-the-log rating is a paragraph, not a row, while "every severity names the
    line of that table it matches" (the Shiori report cites it as "secret-in-log row"). And P0's "a
    state the user cannot recover from" overlaps P1's "blocked with no workaround".

### Friction log (`examples/shiori/SKILL-FRICTION.md`)

| Line | Status |
|---|---|
| **TOOL · `net.sh reach`** blamed the app when `run-as` resolved no name at all | **Resolved.** `reach` asks a control host from the same context and answers NOT PROVEN (`net.sh`, in `reach`), GOTCHAS documents it, two tests cover both directions |
| **TOOL · `redcheck.py`** called Mockito's `WantedButNotInvoked` / `NeverWantedButInvoked` a crash | **Resolved for Mockito and MockK**, with a test. **Partly open:** the suggestion was "treat any `AssertionError` subclass as the verdict", and a JUnit report only carries the type's *name*, so a subclass whose name does not say so is still a crash — Espresso's `NoMatchingViewException` on a `check(…)` is the likely next one. The line's puzzle ("a later run reported the same failure as RED") is explained by the code: a crash next to a real failure in the same run is RED with a note; a crash alone is NOT RED |

Friction the campaign met and did not log (visible in its reports, not in the friction file): the
scope question. The Shiori plan records "the scope is only what the new rules can see (user's
decision)" and the README shows the skill asking "what a new campaign should cover" with three
options — §2.1's round of four questions has no scope question (docs 2 below).

### Docs for humans (phase 5)

1. **Following the README makes the skill stop at its second step.** "Try it" has the human copy
   `qa.config.json` and append three lines to `.gitignore`, then type `/qa-campaign`. §2.1 step 2 runs
   `git status` and, on uncommitted changes, "stop and ask" — and `.gitignore` is now modified. Steps 6
   and 7 then do the same copy and the same `printf` again. Either the README leaves both to the agent
   (it already says the campaign writes its own `CAMPAIGN.md` and credentials template), or it says to
   commit the `.gitignore` line first. Which one is a choice about the entry point, so it is yours.

2. **The README shows a question the skill does not have.** `docs/img/interview-scope.png` is a real
   first question — "The code hasn't changed since the last campaign. What should this new campaign
   cover?", three options with their cost. §2.1's round has four questions and none is scope; a repeat
   campaign is told only that what changed "sets the order, not what is skipped". The Shiori campaign
   did narrow its scope on the user's decision. Add the question to §2.1 for a repeat campaign, or
   caption the image as what an agent may ask.

3. **The install path after `npx skills add` is assumed.** The next block copies from
   `~/.claude/skills/qa-campaign/`. I did not run the installer (it would install into your machine),
   so whether it lands there or in the project is unverified; if it is the project, that `cp` fails
   for everyone who took the first install line. Same root as skill 10.

4. **`examples/shiori/README.md` says the server's LAN address was scrubbed; `CAMPAIGN.md` line 7
   still has `192.168.1.20:18080`** (and the emulator serial, and account names `shiori` / `Claude`).
   It is a private-range address, so the exposure is small, but the sentence is not true as written.
   The example is published "unchanged", so I did not touch it: scrub the address, or change the
   sentence to "the server's hostname".

5. **The example's summary says "Deferred: 11 P2s".** The close-out lists about 17 P2 findings in 8
   groups, and the queue has 11 rows of which one is the calibration and one the version bump. I could
   not find the count that gives 11 P2s.

6. **The example's reports do not have the template's shape**, and the template was already this
   shape at the skill version the campaign ran on (`3072ea4`): no `Origin` column in any findings
   table, no "What happened" or "Open" section in `01-eye.md`, sections 2–5 of `CAMPAIGN.md` folded
   into one line. Reasonable for a delta campaign — but a newcomer told "this is exactly what you
   get" will compare the two. One sentence in the example's README would cover it.

7. **How many products.** SKILL.md's introduction lists four (a multiplatform client, a bookmarks
   client, a travel log, a fleet terminal); README's Status says "extracted from a production
   campaign … then run on four more", which is five.

8. **Prerequisites the README does not list:** `rg` for the S4 sweeps (SKILL.md gives a `perl`
   fallback in one line), `gh` for sending the friction log (optional), and a build that can run its
   tests from the command line.

### Promo video (phase 6)

Builds: nothing to fix. Two notes, neither a defect: `package.json` is still named `promo-test`, and
it has no `typecheck` script (the check below is `tsc` called directly).

## (c) Verified OK

- **SKILL.md → files:** every path it names exists (`templates/` ×3, `references/setup-notes.md`, `adapters/README.md`, `harness/README.md`, `harness/android/GOTCHAS.md`, `qa.config.example.json`); section cross-references (§2.1 steps, §2.2, §2.3, `CAMPAIGN.md` §4/§5/§6) point where they say.
- **SKILL.md / harness README → `ui.py` commands:** all 34 subcommands and the flags the docs name (`--expect`, `--in`, `--index`, `--any`, `--any-app`, `--absent`, `--gone`, `--until`, `--apk`, `--out`, `--grep`, `--force`, `--allow-device-change`) exist and behave as described.
- **Config keys:** the scripts read exactly what the docs say — `android.package/packagePrefix/databases/files/secretKeys`, `devices`, `managedDevices`, `campaign`, plus `server.url/urlFromDevice` in `net.sh`; the rest is documentation, as stated.
- **`redcheck.py` promises in R6:** RED / GREEN / NOT RUN, `--break` byte-for-byte restore, whitespace-only break refused, MUTATION NOT VALIDATED, `--reports`, two files disagreeing = NOT RUN, exit codes 0/1/2/3.
- **`fake_server.py` promises:** status, body, type, delay, routes, repeated headers, HEAD without body, no DNS lookup on bind.
- **`net.sh` promises:** on/off wait and read back, `reach` goes DNS → TCP → HTTP, NOT PROVEN when `run-as` resolves nothing, offline proved from the app's side, exit codes 1/2.
- **Friction issue #13 (Shiori):** both lines are fixed in the code and have a test (`reach` control host; Mockito verification = the test's own check).
- **Portability:** `net.sh` runs on bash 3.2 (no bash-4 syntax); `ps -ax -o command` is not truncated on macOS, with or without a tty or `COLUMNS`; Python sources parse on 3.9. Linux and bash 5 were not run.
- **Links:** every relative link in README, SKILL.md, the harness/adapters/tests READMEs and `examples/shiori/` resolves (checked by script; the one miss is `templates/CAMPAIGN.md` → `00-setup.md`, a placeholder for the campaign's own folder).
- **`examples/shiori/`:** read in full, not edited (published "as it came out").
- **SKILL.md, internal references:** every "R<n>", "§2.x", "S1–S4", "stop <n>" and "step <n>" it cites exists and says what the citing sentence claims, except the points in (b) phase 4.
- **SKILL.md vs templates:** the gate order (R1), the six oracles (R5), the six S3 endings (R4), the queue's two groups (R2), the finding statuses and the A/B/C accounts (R7) are the same in `templates/`.
- **Frontmatter:** `name` matches the folder, the description says when to use it and when not to.
- **README vs the code:** the four scripts, the seven capabilities, the fourteen rules, the fake-server examples, `android.secretKeys`, the two issue templates and the `Skill at start` command are all as described.
- **README's references:** issue #13 exists (closed) and PRs #11 and #12 are merged and are the two fixes it says; `docs/img/interview-scope.png` shows what its alt text says; the promo `.gif` and `.mp4` are in the repo.
- **Promo video:** `npm ci` exit 0 (257 packages, 0 vulnerabilities, Node 22.14.0); `npx tsc --noEmit -p .` exit 0 over the 5 files in `src/` (TypeScript 5.9.3, `strict`); `remotion versions` reports all packages consistent. Not rendered.
