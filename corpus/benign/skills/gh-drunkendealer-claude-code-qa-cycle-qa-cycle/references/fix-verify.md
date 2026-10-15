# Fix and verify (steps 5–8)

## Workstreams and waves

- Group fix-now items by **file scope** into workstreams (server integrity, uploads, render, billing, CLI, editor persistence, layout…). A workstream's scope list is in the tracker; fixers stay inside it.
- Items that depend on another stream's change go in a later **wave** (e.g. editor fixes after the server routes they call).
- One fixer per item or per root-cause group — never one fixer per workstream with 20 items.

## Plan first when the fix is a design problem

Route each item before spawning a fixer:

| Item | Flow |
|---|---|
| Simple and local — a guard, copy, a deterministic test, a small layout rule | `qa-fixer` straight from your brief |
| Touches state, undo/redo history, ordering, concurrency, persisted data, or spans several files | `qa-planner` → plan → `qa-fixer` executes it |
| Failed verification | the **planner** revises the plan with the verifier's findings, then a fixer executes the revision on a fresh branch from main — never straight back to a fixer without the revision |
| Fixer reports `PLAN GAP` | send the gap and its evidence to the planner, then the revised plan to a fixer |
| Fixer reports `PARTIAL` or `NOT FIXED` | back to `qa-planner` with what the fixer did and found, then a fixer on the revised plan — never straight to another fixer |

Which fixer: a fresh agent with the full brief by default; resume the previous one (`SendMessage`) only when its context is the point — it holds hard-won state a new agent would have to rebuild.

The planner's brief is the item (as below) plus: the prior verifier findings, the project skills/rules that cover the area, and "write ROOT CAUSE / INVARIANT / APPROACH / CASES / TESTS / RISKS". Pass the plan verbatim into the fixer's brief and its INVARIANT into the verifier's.

Planners don't stop on product questions: they proceed with a flagged default, `PRODUCT Q — <question> — default used: <choice>`, unless the default would be destructive or irreversible (then they stop). Relay the PRODUCT Q lines to the user at the next gate and record them in the item's note. Every plan starts with `BASE: main <sha> [+ assumes <ITEM> merged]` (e.g. `+ assumes N170 merged`). `merge.sh` cherry-picks, so a branch's own shas never reach main; the assumed item is identified by ID and its merged shas live in the tracker's `commit` field. The stale check is a script: `node <tooling>/stale.mjs <plan.md>` parses the BASE line, verifies the assumed items' tracker shas are ancestors of main, and prints the diff stat from the earliest one's parent (or BASE) limited to the files APPROACH names; it exits 2 with `PLAN GAP — stale: …` when an assumption doesn't hold (orchestration.md › Scheduling). Nobody does that arithmetic by hand.

## Fixer brief (`qa-fixer`)

Spawn with worktree isolation. The brief contains:
1. "Read and follow `<tooling>/FIXRULES.md`" (the filled template — hard rules live there, not repeated per brief). With a plan: its path and the revision to execute, and "run `node <tooling>/stale.mjs <plan>` first".
2. Branch: `git switch -c <id> main`, current main's short SHA, its port range.
3. The item verbatim: ID, severity, title, where, repro steps and script paths, expected behavior, any user decision recorded on it.
4. Pointers: the functions/files involved, related earlier fixes, other fixers working nearby (to keep diffs small).
5. Proof required: a test that fails before and passes after; suite + lint + build clean; the headless repro before → after.
6. Report format: branch, BASE, commit list, one `ID FIXED|PARTIAL|NOT FIXED|NOT A BUG|PLAN GAP — what — commit — evidence` line per item, plus residuals/trade-offs stated as before → after.

## Merge (orchestrator)

Order is always **merge → build → sandbox**. `merge.sh <branch> <IDs…> [--partial]` does the first two and fails closed: it first checks the configured test/lint/build commands exist, takes the repo lock (`mkbox.sh` takes it too), needs main on `main` with a clean tracked tree; it fast-forwards (else cherry-picks `merge-base..branch`), then runs test, lint and build, each under `gateTimeoutMs` — any failure, timeout or interrupt puts main back to the pre-merge sha with `git reset --keep`, marks nothing and exits 1. If `--keep` refuses it stops with exit 2 and leaves everything for you: look at the repo, restore it by hand, never force. On success it marks the items `fixed` and ADDS the merged short shas to their `commit` field (for a branch already cherry-picked earlier, the main shas carrying its patches; earlier shas — a partial's — stay). Sandboxes come after (`mkbox.sh`, below).

**A `PARTIAL` fix is not `fixed`.** Either leave the commit on its branch, or merge it with `merge.sh <branch> <IDs…> --partial`, which records the shas but keeps the items at `fixing`; the planner then plans the rest from there.

**The merge gate runs the full test suite**, so it is a medium (sometimes high) load item (orchestration.md › Load budget) that can take minutes: **run `merge.sh` in the background** (Bash `run_in_background`) and carry on with other work until it reports. It enforces the load rule itself: it refuses while `agents.txt` shows a `running` verifier or tester (`--force` overrides). Queue the merge instead (`agents.mjs queue "merge <branch> <IDs> after <verifier>"`) and run it when that agent ends.

**Crash recovery.** `merge.sh` writes `<tooling>/merge.journal.json` (pre-merge sha, branch, ids, pid) before it touches git and deletes it when main is back in a known state. If the process died (SIGKILL, reboot) the next run stops and prints the exact recovery command (`git reset --keep <pre>` after checking HEAD) — it never runs it; after restoring main by hand, `merge.sh --clear-journal`. The gate's process group is killed by a watchdog if the parent is SIGKILLed; a gate descendant that detached into its own group (a browser started with `setsid`) is outside it — the resource sweep catches those. On `CONFLICT` (main is already restored): resolve only trivial ones yourself (both sides adding independent lines) on a branch, then re-run; anything semantic goes back through the planner/fixer on a fresh branch. Never merge by hand around the gate.

## Verifier brief (`qa-verifier`)

1. "Read and follow `<tooling>/VERIFYRULES.md`."
2. Sandbox: `mkbox.sh <ID> <port>` after the merge — a copy made from the commit main points at (`git archive`, not the working tree), built in place, `SANDBOX_SHA` records the commit. Give its path, port range, other verifiers' ranges to avoid, and the fix's commit (the verifier checks it's an ancestor of `SANDBOX_SHA`).
3. Per item: the original finding, the fix's claim (mechanism in a sentence), and the fixer's stated residuals — to be reported back, not accepted.
4. Ask it to be adversarial: original repro, close variants, every frame/step not just the end state, what the fix could have broken nearby, and named earlier fixes in the same area to regression-check. It also runs the regression suite its plan's RISKS names (name the test files in the brief). **Cross-item verifier:** when several items merged in the same area in one wave, the orchestrator runs ONE extra verifier over the combined result (every item's invariant together, on the sandbox at the wave's last merge) — once per wave, not per item.
5. Point to existing scripts but say "measure yourself; don't trust the fixer's numbers" and name known harness artifacts so they aren't reported as bugs.
6. Cap the scenario count when load matters.
7. Repro scripts and evidence go in `<scratch>/verify-<ID>/` (VERIFYRULES says so), and the report names the paths. Report: `ID VERIFIED|FAILED|BLOCKED — evidence` per item; every residual (stated or found) as `RESIDUAL — what — evidence — suggested: accept|fix` — verifiers never accept a trade-off; then `NEW <sev B|M|m> — title — where — repro` for anything found.

## The loop

- **VERIFIED** → `st.mjs verified --by <verifier agentId> --verify "<evidence>" ID` (add `--commit <sha>` only to ADD a sha; the merge already recorded the commit). The script refuses `verified` without a commit and evidence, without `--by`, with a `--by` that is not a `verifier` row of `agents.txt`, doesn't list the item, or is a fixer listed for that item, with a commit that doesn't resolve or isn't an ancestor of main (checked for any `--commit`, not only on verify), with an unresolved residual, and from any status but `fixed`. `--commit` never replaces recorded shas without `--force`. `--force` is for historical backfill only. `--verify` is the evidence, `--item-note` the item's own note; `--note` no longer exists. Register the verifier in `agents.txt` (its real agent id, role `verifier`, the item IDs it verifies) before you need `--by`.
- **FAILED** → status `failed` with the verifier's repro and root cause (`--verify`); the planner revises the plan (ask for a sturdier invariant, not another patch), then a fixer executes it on a fresh branch from current main. After the second failure, the revising planner runs at high effort.
- **BLOCKED** → the environment, not the fix, stopped the check (server refused, sandbox older than the fix, permission denied). Status unchanged; fix the cause (re-run `mkbox.sh`, free the port) and re-dispatch a verifier. Don't treat it as a pass.
- **NEW** → `add` it to the tracker (from any agent: planner, fixer, verifier or tester). **Severity policy:** B or M → bucket `now`, queue a fixer. `m` → bucket `later` — `add.mjs` does this by default (`--now` overrides, only on the user's word); it waits for the user's gate and is not fixed in this loop. `later` reaches `now` only at that gate. A pre-existing bug found nearby is still logged; the loop runs until nothing fix-now is left.
- **PARTIAL / NOT FIXED** (fixer results) → to `qa-planner` for a revision, then a fixer; the item stays `fixing` (see Merge for a partial commit).
- **RESIDUAL** → record each line on the item (`st.mjs - --residual "<what — evidence>" ID`) and put it to the user with `AskUserQuestion` at the next gate (accept, or fix). **`verified` is refused while any residual is unresolved: the item stays `fixed`** (the simpler of the two options — a verified item never carries an open question), and the verifier's VERIFIED line waits in its evidence. After the user answers, the orchestrator records it: `st.mjs - --resolve-residual <n> accept|fix ID` (n is 1-based; `st.mjs show ID` counts them), then runs `verified`. "fix" also means a new item (`add.mjs`).
- **NOT A BUG** from a fixer → stays `fixed` until a verifier confirms it independently.
- **Trade-offs** are the user's call, never a verifier's: every `RESIDUAL` goes to the user at the next gate, with the verifier's suggestion.
- **Reap after verify.** Once an item is `verified` (or its fixer branch is merged and no failed round is pending), `reap.sh <ID|branch|agentId>` removes its worktree, its `wt-<ID>` scratch symlink and its branches (the fixer's own and the auto `worktree-agent-*` one). It refuses anything not fully merged into main (cherry-picks count as merged), locked, dirty, or with a process whose cwd is inside — so a refusal is information, not an error to force around; stop the process by PID or finish the work, then retry. Don't reap while a FAILED round may still need the branch's history. `reap.sh --all-merged` is the bulk form: a dry run listing every worktree/branch that is fully on main by patch-id (SAFE) or skipped with the reason (locked, in use, tracked changes, untracked files, a `running` agent's, no commit of its own = a fresh agent worktree, touched in the last 30 min); `--yes` reaps only the SAFE ones. `--include-empty` reaps the fresh ones, `--include-recent` (with `--yes` in bulk mode) the recently touched ones — only when you know nothing is about to use them.
- Republish the tracker after every batch of status changes.

Done when every fix-now item is `verified`, the suite is green on main, and the user has the list of trade-offs. Then the next test cycle starts only on the user's word.
