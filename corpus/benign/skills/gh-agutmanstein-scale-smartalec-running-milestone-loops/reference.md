# Milestone loop reference

## State files (in the loop dir)
| File | Contents |
|---|---|
| `LOOP.md` | The profile: sources of truth, authority, gates, conventions, people (`LOOP.template.md`). |
| `QUEUE.md` | One row per unit: `unit \| tickets \| done-when (short) \| § refs \| depends on \| files \| status \| next action`. Status is `todo`, `running <workflow run id>`, `pr <#n>`, `merged <sha>` or `blocked: <who/what>`. |
| `PRS.md` | One row per PR: `unit \| ticket \| branch \| #PR \| base branch \| state`. Below it: the current stack order, the tips recorded before each restack, a merge log (PR, merge sha, date) and a contact log (who was messaged, when, why). |
| `DECISIONS.md` | Each default you took without asking, with its citations (§, ticket line, comment). This keeps a decision from being re-made after a compaction. |
| `QUESTIONS.md` | Open questions for the user. Each has the unit it blocks, the proposed default and the date asked. Lead every status update with these. |
| `OWNER` | `session=<id> host=<host> pid=<pid> tmux=<session> heartbeat=<ISO time>`. Refresh it on every turn. |
| `RESUME.md` | The exact prompt a fresh session pastes to resume: read LOOP.md, then follow the skill's resume steps. |
| `units/<unit>/` | DESIGN.md, PR-BODY.md (first line `TITLE: …`), logs, patch files and the brief. |

## Ownership
- **Live owner:** the heartbeat is under 30 minutes old, or a process is running with the loop dir in its arguments.
- **Commands:**
  - `ps -eo pid,etime,args | grep "[c]laude"`;
  - `tmux ls`;
  - the newest transcript under `~/.claude/projects/*/`.
- **If tmux says "no server" but the process is alive,** its socket was deleted. Run `kill -USR1 <tmux server pid>` to recreate it. Don't start a second loop.
- **On a hand-off,** the old owner writes `released` to OWNER before the new one starts.

## Stacking
- **Choosing the shape.** List the files each queued unit touches. Units that overlap go in one linear stack, in queue order. The rest branch from a freshly fetched main. Always fetch first and branch from `origin/<main>`, never from a local main.
- **Restack after a lower layer changes:**
  1. Record every layer's current tip in PRS.md.
  2. For each layer from the bottom up, run `git -C <wt> rebase --onto <parent-branch> <recorded old parent tip>`.
  3. Stop at the first conflict and give that layer to one agent to resolve. It keeps both sides' intent, reruns the gates, and gives a stated reason for any re-pin.
  4. Run the gates on the top layer, and on every layer whose parent touched its code.
  5. Run `git push --force-with-lease` for each layer. PR bases are branch names, so they stay correct.
- **Generated fixtures, goldens and snapshots.** Never hand-merge them. Regenerate them at the conflicting commit. Then check every moved value against what the unit declares (in DESIGN.md or a divergence ledger). An unexplained move is a bug until shown otherwise.
- **Merge train,** when the Authority table allows merges: once the bottom PR is approved and every check is done, including non-required security scans, squash-merge it. The next PR auto-retargets to main. Rebase it `--onto origin/main <old parent tip>`, force-push it, wait for its checks, and repeat. Log every merge in PRS.md.

## Bot review loop (Greptile, CodeRabbit, …)
1. A fixing agent checks each thread against the code. A valid thread gets a fix plus a test that fails before and passes after. A deferred thread names an owner. An invalid thread is answered with file:line evidence.
2. Push, reply, resolve and re-request a review, where the Authority table allows each.
3. A fix to a lower layer means restacking every layer above it.
4. A PR is clean when its score is at the threshold and no threads are unresolved.

## Hand-off to another machine
- **Bundle:** the loop dir, the design docs, any local-only data, and a `setup.sh`. Write laptop paths as placeholders that `setup.sh` fills in.
- **`setup.sh`:**
  - checks the prerequisites (git and tracker auth, toolchains);
  - creates the worktrees from the pushed branches;
  - builds the environments.
- **Verify the new machine** by running the gates on one unit and comparing against the old machine's counts, including known-failing ones. Different counts mean an environment gap, not a code change.
- **Start the new session** with tmux, the loop dir added as a working directory, and a permission mode that won't stall on every command. Submit `/loop` with RESUME.md's prompt. Stop the old loop's wakeups.

## Long runs
- Anything that may take more than about 90 seconds goes in the background; wait for its notification, never a foreground sleep.
- Big local jobs (corpus runs, full ingests) run under a lock directory with an owner file. Remove stale locks only after confirming nothing is running.
- Subagents write their scratch output into `units/<unit>/`, not into tool config directories.
