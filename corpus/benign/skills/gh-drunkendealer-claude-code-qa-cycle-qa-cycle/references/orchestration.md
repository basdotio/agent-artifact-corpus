# Orchestration

## Structure

```
user ──task──▶ ORCHESTRATOR (you; the strongest model in the session)
                 │  plans, splits, dispatches, merges, keeps the tracker, talks to the user
                 ├─▶ mapper      (read-only)      builds the feature map
                 ├─▶ testers     (sandbox each)   one test unit each → findings
                 ├─▶ fixers      (worktree each)  one item / root-cause group each → commits on a branch
                 └─▶ verifiers   (sandbox each)   one fix each, fresh eyes → VERIFIED | FAILED + NEW
```

The orchestrator never fixes or verifies its own items; it only does the cheap glue: merging branches, building, making sandboxes, updating the tracker, resolving trivial merge conflicts (e.g. two fixers each adding a setup line to the same test).

Agents report back once, in a fixed format (see the rule templates). Their report goes to you, not to the user — relay what matters.

## Model per role

| Role | Agent type | Model / effort | Why |
|---|---|---|---|
| Orchestrator | — (you) | Opus | Judgement: splitting, triage, trade-offs, merge conflicts |
| Planner | `qa-planner` | Opus, medium | Designs the fix (root cause, invariant, approach, cases). Read-only. Quality comes from context — code paths, project skills, memory, prior verifier findings — more than from effort |
| Fixer | `qa-fixer` | Sonnet, medium | Executes the plan; stops with `PLAN GAP` instead of redesigning |
| Mapper | `qa-mapper` | Sonnet, medium | Read-only feature map from the code |
| Tester | `qa-tester` | Sonnet, medium | One test unit in its own sandbox → findings |
| Verifier | `qa-verifier` | Sonnet, medium | One fix, fresh eyes. All three execute a written brief; quality comes from the small scope and the brief |
| Quick look-ups | Explore / Haiku | — | "where is X handled" — never for judgement |

**Effort is set by the agent definition, not at spawn.** The Agent tool takes a `model` but no effort; an agent without an `effort` field inherits the session's level. The five `qa-*` definitions (in the configs repo's `agents/`) pin model and effort so spend is deterministic. `CLAUDE_CODE_EFFORT_LEVEL` would override everything for the session — don't set it during a loop.

**Escalate effort, not by default:** start everyone at medium. A planner revising after the **second** failed verification on the same item gets `effort: high` (spawn a one-off general-purpose Opus agent with the qa-planner brief, or bump the definition temporarily).

When you resume an existing agent with `SendMessage`, it keeps its original model and effort — prefer a fresh agent with a full brief unless the agent's context is the point (a fixer mid-way through a hard item).

## Load budget — estimate before every spawn

The user's machine is shared with the user. Before launching, classify each agent and keep within budget:

| Class | Typical agent | Concurrency |
|---|---|---|
| **High** | Browser suites over many cells/frames, render/export pipelines, repeated or stressed full test runs, Gradle/Xcode builds, anything on a booted emulator/simulator (the device itself counts as high) | **one, alone** |
| **Medium** | One server + a few short headless scripts; a single full test-suite run — **including the `merge.sh` gate** (full test + lint + build); a fixer with a browser repro | **a few** (≈2–3) |
| **Small** | Reading code, unit-test-only fixes, analysis, writing docs | **many** |

- **Merging is not free.** `merge.sh` runs the whole suite, so it takes a medium slot, and it counts as high next to a verifier running a browser suite. The script enforces it: it refuses while `agents.txt` has a `running` verifier or tester (`--force` overrides) — so keep `agents.txt` truthful (`agents.mjs set … done` the moment an agent hands back), and queue the merge (`agents.mjs queue "merge <branch> <IDs> after <verifier>"`) to run when it ends. Gates take minutes: **start `merge.sh` with Bash `run_in_background`** and keep working. `merge.sh` and `mkbox.sh` also serialize on the repo lock, and each gate command has a timeout (`gateTimeoutMs`).
- Queue the rest and launch as slots free up; write the queue into `agents.txt` (`agents.mjs queue "…"`).
- Tell every agent (in the rules templates): heavy steps serially — one headless browser at a time, never a full test suite while a browser suite runs — and stop every server/browser it starts **by PID** as soon as it's done.
- Cap scenario counts in the brief ("≤15 browser scenarios") for verifiers that tend to sprawl.
- After an interruption, look for orphaned servers in your port ranges (`lsof -iTCP -sTCP:LISTEN`), confirm their cwd is a sandbox/worktree, then stop them by PID.

## Scheduling — overlap everything that doesn't conflict

Before every spawn (not just at the start of a phase), lay out the open work as a dependency graph and run every node whose inputs are ready. Two separate checks decide what can overlap:

1. **Load** — the budget above.
2. **Code conflict** — two *writers* on the same functions/files serialize: the second would build on code that's about to change and its merge conflicts. Readers never conflict.

| Pair | Overlap? |
|---|---|
| planner ‖ anything | **Yes** — read-only. Plan the next items against the in-flight branch (`git -C <worktree> diff main`) and state the assumption (`+ assumes N168 merged`) |
| verifier ‖ fixer | Yes — the verifier's sandbox is a copy of main; mind the load budget |
| verifier ‖ verifier | Yes, within load budget, different ports |
| fixer ‖ fixer, disjoint files | Yes |
| fixer ‖ fixer, same functions | **No** — queue the second until the first merges |
| tester ‖ fixer | Yes, if the tester runs on main, not the fixer's branch |

The usual win is **fix N while planning N+1**: when items N1–N6 all edit the same functions, their fixers run one after another, but while N1's fixer works, planners write the N2/N3 and N4/N5 plans, each "assuming N1 merged". Each fixer then starts the moment the previous merge lands, with no planning wait. Likewise, while waiting on a verifier, plan the next item or let its sibling's fixer start. (e.g. six items N168–N173, all in one editor's layout functions in a single `state.js`.)

**Stale plans are the price of overlap; guard them in three places:**
- *Planner* stamps `BASE: main <sha> [+ assumes <ITEM> merged]` (the assumed item by ID, e.g. `+ assumes N170 merged`; never a branch sha — `merge.sh` cherry-picks, so a branch's shas are not on main), names functions (not only lines), and appends revisions as `REVISION n` instead of rewriting.
- *Orchestrator*, before handing a plan to a fixer: run `node <tooling>/stale.mjs <plan.md>` (`--rev N` for a specific REVISION). If the item it assumed merged differently (revised, PLAN GAP, extra commits) and the touched functions changed, send it back to a planner for a quick refresh first. Name the exact revision in the fixer's brief.
- *Fixer* runs `node <tooling>/stale.mjs <plan.md>` as its first step and stops with `PLAN GAP — stale` rather than adapting silently. The script does the arithmetic: it takes the plan's BASE and `+ assumes <ITEM> merged`, reads that item's shas from the tracker, requires each to be an ancestor of main (a plan's last REVISION block must carry its own BASE line, which may continue over indented or `+` lines; every `N<digits>` on it must be an assumed item or the script exits 2 naming it; an empty field or a non-ancestor sha means the item isn't merged: exit 2 `PLAN GAP — stale: assumed <ITEM> not merged`, and the orchestrator queues the fixer until it is), and prints the diff stat from the earliest sha's parent (or from BASE) to main, limited to the files APPROACH names, plus what landed on top of the assumed item. An item merged with `--partial` doesn't count unless the plan says it assumes the partial (`--allow-partial`). The fixer still reads the stat: if the functions the plan changes or relies on moved in ways its BASE didn't assume, that is the `PLAN GAP — stale`.

Never let a planner revise a plan file while a fixer is executing it. A fresh finding during a fix becomes a new item or a later revision, handed over only after the fixer reports.

Don't leave a slot idle just because the *fixers* are blocked. Ask what else is ready: planning, verifying, sweeping, or republishing the tracker. Tell the user what's running in parallel and why the rest waits.

## Resource sweep — free what finished agents left behind

Agents that finish, get stopped, or are cut off by a restart often leave servers, headless browsers and dev servers running — that's how RAM fills up over a long loop. Sweep:
- **when** an agent hands back or is reported stopped, after a session restart, before launching a high-load agent, and every ~30 min while agents run;
- **what** — only processes and devices you can tie to this loop (table below);
- **keep** anything belonging to an agent whose `agents.txt` row is `running` (its port range / sandbox / device);
- **stop** the rest by PID (never `pkill` by pattern), then re-check they're gone.

**Ownership is recorded, not guessed.** Ports and paths identify web leftovers; devices need their ID written to `agents.txt` by whoever boots them (emulator serial / AVD name, simulator UDID). Only recorded things may be stopped. Never touch what the loop didn't start — the user's emulators, simulators, browsers, IDE; if those load the machine, report it and hold high-load agents.

### Per platform

| Platform | Leftover | Weight | Find | Stop |
|---|---|---|---|---|
| any | uptime / top consumers | — | `uptime; ps -axo pid,pcpu,rss,etime,command -r \| head` | — |
| Web | dev/app server | medium | `lsof -nP -iTCP -sTCP:LISTEN` in loop port ranges | `kill <PID>` |
| Web | headless browser, Vite | medium | `pgrep -f 'chrome-headless-shell\|vite'` + `lsof -a -p <PID> -d cwd` under `<scratch-root>` or worktrees | `kill <PID>` |
| Android | emulator the loop booted | **high** (guest RAM + CPU) | `adb devices`; `pgrep -f qemu-system` + its `-avd` | `adb -s <serial> emu kill` |
| Android | Gradle / Kotlin daemons | 1–4 GB each | `pgrep -f 'GradleDaemon\|KotlinCompileDaemon'` + cwd = a worktree | `./gradlew --stop` in that worktree |
| Android | adb forwards | tiny, confuses later agents | `adb forward --list`, `adb reverse --list` | `adb forward --remove <spec>` |
| iOS | simulator the loop booted | **high** (~200 runtime processes) | `xcrun simctl list devices booted` | `xcrun simctl shutdown <UDID>` |
| iOS | xcodebuild / test runners | medium | `pgrep -f xcodebuild` + cwd | `kill <PID>` |
| RN / Flutter | Metro / Expo / flutter run | medium | listener on 8081 / 19000 + cwd | `kill <PID>` |
| any mobile | build dirs, DerivedData per worktree | disk (GBs) | worktree `build/`, `~/Library/Developer/Xcode/DerivedData/<worktree>-*` | delete when the worktree is removed |

```zsh
# web: listeners in the loop's ranges (qa.config.json `sweepPorts`), with cwd and whether a running agent owns them
node <tooling>/sweep.mjs
# then loop-owned browsers/servers by cwd
for p in $(pgrep -f 'chrome-headless-shell|server/index.js|vite'); do
  printf '%s ' $p; lsof -a -p $p -d cwd -Fn | sed -n 's/^n//p'; done | grep -E '<scratch-root>|worktrees'
```

### Devices: reuse, don't churn

- Boot **dedicated loop devices** (e.g. AVD `qa-pixel`, simulator `qa-iphone`) so they're unmistakable from the user's own.
- Boot them **headless**: Android `emulator -avd qa-pixel -no-window -no-audio -no-boot-anim -no-snapshot-save` (prefer an ATD system image — `aosp_atd`/`google_atd` — built for headless tests, lighter than a full Play image; cap guest RAM with `-memory 2048`); iOS `xcrun simctl boot <UDID>` without opening Simulator.app.
- One device serves many units in a row: between units only clear app state (`adb shell pm clear <pkg>`, `xcrun simctl uninstall`/`erase`). Shut it down at the end of the test or verify stage, or when the machine is overloaded and nothing is queued for it.
- Fixers don't boot devices — JVM/unit tests only; device repros belong to verifiers. Each fixer runs `./gradlew --stop` in its worktree before handing back.

## Ports and paths

Allocate disjoint port ranges per agent and write them in the brief: e.g. fixers `37x0–37x9` (dev server +1000), verifiers `39x0–39x9`. Each verifier sandbox is `<scratch>/<sandboxDir>/<ID>` (`scratch` is a durable path, not the session scratchpad), each fixer symlink `<scratch>/wt-<ID>` (some servers refuse paths under dot-directories like `.claude/worktrees`).

## Agent lifecycle

- **Launch** in the background; log it with `agents.mjs add <agentId> <role> <model> <items> --note "<sandbox> :<port>"` (the real agent id and the true role: `st.mjs verified --by <id>` checks a `verifier` row, and a `fixer` row for an item can never verify it; `|` and newlines are refused in any field); when it hands back or is stopped, `agents.mjs set <agentId> done|failed|stopped`. Resuming an agent is `add` again (same id → row goes back to `running`).
- **Wait** for the completion notification. Don't poll their transcript files; don't predict their results.
- **FAILED verification** → back to a `qa-planner` for a revision (verifier's repro, root cause, script paths), then a fixer executes the revision on a **fresh branch from current main**. Resume the previous fixer with `SendMessage` only when its context is the point (it is mid-way through a hard item and holds state a fresh agent would have to rebuild); otherwise spawn a fresh fixer with the full brief. Verifier results are `VERIFIED|FAILED|BLOCKED` plus `RESIDUAL` lines (never accepted by the verifier — they go to the user at the next gate); fixer results `FIXED|PARTIAL|NOT FIXED|NOT A BUG|PLAN GAP`. `PARTIAL` and `NOT FIXED` go back to the planner like a FAILED verification, and a PARTIAL commit is not merged as fixed.
- **Idle-looping agent** (wakes repeatedly with no tool use) → nudge once: what it's waiting for, don't poll.
- **Session restart / interrupted agents** → check each one's worktree for uncommitted work and resume it with a message saying where it stopped; re-spawn interrupted verifiers fresh (their sandboxes can be resynced).
- **Usage limits** → stop the lowest-value agents, resume them later via `SendMessage`.
- **Permission denied inside an agent** → it reports and stops; you don't perform it on its behalf. Collect the leftovers (e.g. undeletable worktree files) for the final report.

## Decisions that are the user's

Ask (with a recommended option first) when an item has two defensible behaviors, when a fix only swaps one failure for another, or when the scope of the next cycle changes. Record the answer in the tracker item's note (`st.mjs - --item-note "+…" ID`) so later agents follow it.

**Don't stall the loop on questions.** A planner that meets a product question proceeds with a flagged default — `PRODUCT Q — <question> — default used: <choice>` — and the plan stays executable. Collect those lines, note them on the item, and ask the user at the next gate; if the answer differs from the default, it's a plan revision (and, if the fix already merged, a new item). The exception: when the default would be destructive or irreversible (data deletion, migration, public API/behavior users rely on), the planner stops and says so, and you ask first.

## Cycle boundary — at the end of every cycle, and after any wave that merged items named in the area rules

0. Run `node <tooling>/boundary.mjs`: it lists every item id in the project's `.claude/rules/*.md` and the handoff memory file(s) (`rules`, `handoffMemory` in `qa.config.json`) with its tracker status and flags the merged, verified and unknown ones — those lines are what to refresh.

1. **Area rules**: refresh the project's own area rules (e.g. `.claude/rules/*.md` lines that name open IDs — "N168 is open here") so they match the tracker: drop what is verified, add what is open or deferred. Don't hand-write new invariants there; verified invariants come from the plans.
2. **Handoff memory**: update the project memory (cycle, verified count, open IDs, queue, tooling folder, user decisions).
3. **Tracker**: republish it. Then `sweep.mjs`, `reap.sh --all-merged` (dry run first), and the next-cycle gate with the user.

## Resume after a restart

A restart (or a compaction) loses every running agent's context and may wipe the scratchpad. Rebuild the picture from durable state before launching anything:

1. **Tracker** — read `tracker.html`/the published artifact: counts by status, items `fixing`/`failed`, anything `fixed` awaiting verification. This is the truth about work, not your memory of it.
2. **agents.txt** — subagents never survive a session restart, so `agents.mjs restart [--note t]` marks every `running` row `stopped` (note `session restart`) under the agents lock; a leftover `running` row blocks `merge.sh` for good. Then check each stopped row's worktree/sandbox and, for one that had handed back, `agents.mjs set <id> done`. Marking a row never changes an item's status: set `open`/`failed` on the items of a stopped fixer yourself (`st.mjs`). (`agents.mjs stale [hours]` only lists old `running` rows; it has no process check, because `ps` can't see subagents.)
3. **Worktrees** — `git worktree list` and `git -C <wt> status --short` for each stopped fixer: committed work on the branch → resume or hand to a fresh fixer with the branch; uncommitted work → say where it stopped; merged → `reap.sh`. `git branch --no-merged main` shows unmerged work.
4. **Ports and processes** — `lsof -nP -iTCP -sTCP:LISTEN` in the loop's port ranges, cwd under a sandbox/worktree → stop leftovers by PID (resource sweep). Re-run `mkbox.sh` for interrupted verifiers; confirm `SANDBOX_SHA` is current main.
5. **Plans** — `plans/` holds each planner's output with its BASE; re-check BASE against main (stale-plan guard) before handing one to a fixer, and note which revision a fixer was executing.
6. **Memory** — read the project memory for the loop (cycle, tooling folder, queue, user decisions) and update it at the end of this step; the scratchpad is not durable, so confirm `scratch` in `qa.config.json` still exists.

Then log the restart in `agents.txt` (`# restart <date>`), rebuild the queue with `agents.mjs queue`, and relaunch within the load budget.
