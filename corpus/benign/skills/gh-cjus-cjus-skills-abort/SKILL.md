---
name: abort
description: Abandon a branch that will never merge. Closes its issue as not planned, closes any open PR, removes the worktree, and deletes the branch locally and on the remote. Permanent, so it only runs when the user invokes it explicitly. Use when the user says "/pr:abort <reason>".
disable-model-invocation: true
allowed-tools: Bash(node:*), Bash(git:*), Bash(gh:*), Bash(grep:*), Bash(rmdir:*), Bash(ls:*), Bash(jq:*), Bash(date:*)
argument-hint: "[ticket-number] <reason>"
---

# /pr:abort

Abandon a branch. Closes the parent issue as **not planned**, removes the worktree, and deletes the branch both locally and on the remote.

The ticket is derived from the current branch when the session is inside a feature worktree, so the usual invocation is just `/pr:abort <reason>`.

**This is the terminal counterpart to `/pr:cleanup`.** Cleanup ends a branch that **merged**; abort ends one that **never will**. They are not interchangeable, and step 2 refuses to let one stand in for the other.

## This is the most destructive skill here

A full abort deletes the worktree, the local branch and the remote branch. **The branch's plan folder lives only on that branch, so `PLAN.md` and `CHANGELOG.md` go with it.** Nothing is copied anywhere and nothing is archived.

**Recovery is weaker than "the reflog will have it", and saying otherwise would be a false reassurance.** The commits were made in the worktree, so they were only ever in that worktree's `HEAD` reflog, which `git worktree remove` deletes along with the rest of its administrative directory. `git branch -D` then deletes the branch's own reflog. What survives is dangling objects in the main repo, findable with `git fsck --unreachable` and only until `git gc` prunes them, two weeks by default. **Treat an abort as permanent.**

That is why **the reason is required while the ticket number is not**: the closing comment on the issue becomes the only surviving record of what was attempted and why.

## When NOT to recommend this skill

`disable-model-invocation: true` means it only runs when the **user** invokes it, so *suggesting* it is the only way it can fire prematurely.

**Never recommend it for:**

- A branch that is merely blocked, stalled or waiting on someone. That is an open ticket with a comment on it.
- A branch whose PR merged. That is `/pr:cleanup`.
- A branch you believe is redundant. Say why you believe it and let the operator decide.

**The only honest trigger is the operator stating the work is abandoned.**

## Arguments

- **ticket number** *(optional)*. Derive it from context where possible; accept it as an argument only where it is not. A leading all-digits token is the ticket; anything else means the whole argument string is the reason.
- **reason (required)**, in the operator's words. **If absent, ask and stop.** Do not invent one and do not proceed with a generic placeholder.

**Explicit beats derived.** A number typed on the command line wins over the current branch, since the operator may be standing in one worktree while aborting another.

## All verification precedes all destruction

Steps 0 through 4 read and verify. Steps 5 through 9 destroy. **The boundary is absolute.** Never begin a destructive step while an earlier one is unresolved, and never reorder across it.

This differs from `/pr:cleanup`, which can afford a non-halting bookkeeping step because the merge already happened and the content is safe. **Here nothing is safe anywhere, so every gate halts.**

## Step 0. Resolve the target from context

Work down this list and stop at the first rule that resolves, setting the ticket, the branch and the worktree path.

1. **An explicit ticket number was passed.** Resolve it to its branch by `${CLAUDE_PLUGIN_ROOT}/reference/config.md § Resolving a ticket number to its branch`:

   ```bash
   git for-each-ref --format='%(refname:lstrip=2)%09%(worktreepath)' refs/heads \
     | grep -iE '^(<branchPrefix>)?([^/[:space:]]+/)*(<ticketPrefix>-)?<ticket>-'
   ```

   Match the branch name, never the worktree path: `12-` is a substring of `…/feature/112-…`. Set `MAIN_CHECKOUT` to the first `worktree` entry of `git worktree list --porcelain`; a row whose second field equals it is checked out in the main checkout. Multiple rows list and stop. One row resolves, and its second field decides the worktree:
   - **A worktree of its own** → that is the worktree path.
   - **Empty** → the worktree is gone; see below.
   - **The main checkout** → **stop.** The branch is checked out there, and step 8 cannot delete a checked-out branch, so the abort would close the PR and the issue and then fail on the branch. Ask the operator to switch the main checkout to the default branch and run the abort again. Do not switch it for them: a switch carries uncommitted changes with it.

   No row at all → see below.
2. **No number, and this session is inside a feature worktree.** The common case, needing no argument: if the current branch matches the configured ticket pattern, that capture **is** the ticket. Derive all three and move on. **Do not ask for a number you already have.**
3. **No number, and the session is in the main checkout on the default branch.** There is no branch context, so list the feature worktrees with their numbers and full slugs and ask which to abort. **Do not auto-select a single match**: a lone worktree is evidence about what exists on disk, not about what the operator meant, and this skill deletes three things.
4. **Nothing resolves.** Report what was checked and ask. **Never guess a number from a recent conversation.**

### When the worktree is already gone

A worktree removed by hand leaves its branch behind, so rule 1 finds it as a row whose second field is empty. With no local row at all, check the remote by the same pattern:

```bash
git for-each-ref --format='%(refname:lstrip=3)' refs/remotes/origin \
  | grep -iE '^(<branchPrefix>)?([^/[:space:]]+/)*(<ticketPrefix>-)?<ticket>-'
```

A branch exists, locally or on the remote → set the worktree path empty and carry on; steps 7 and 9 skip themselves. One remote row resolves; several list and stop, as in rule 1. No branch either → run the no-match check in `config.md § Resolving a ticket number to its branch`. A hit names the branch this ticket most likely belongs to, so report it and stop. Otherwise report that only the issue remains and confirm the operator wants it closed on its own.

### Echo the resolution, always

Print it whether the ticket was typed or derived, with the **full slug** and never the bare number:

```
Ticket <N> resolved (from the current branch | from argument):
  Branch:   <branch>
  Worktree: <path> (or "none on disk")
```

Saying **which rule resolved it** is the other half: a derived target and a typed one fail differently, and the operator can only catch the wrong one if they know which they are looking at.

## Step 0b. Warn when the session is standing inside the target

True whenever rule 2 resolved, and possible under 1 and 3. When it holds, **every command must be redirected with `git -C "$MAIN_CHECKOUT"`**, because a worktree cannot remove itself.

```
This session is running inside the worktree being aborted.
Its working directory will be invalidated at step 7.
After the abort completes, run: cd <main checkout>
```

The skill cannot change the operator's shell directory for them, so it must say so plainly in the final report.

## Step 1. Resolve the issue and verify it is this branch's

```bash
ISSUE=$(gh issue view "$TICKET" --repo "$REPO" --json number,title,state,url,labels 2>/dev/null)
```

- **Not found** → **stop.** The ticket is half the point of this skill, and the number is probably wrong.
- **Found** → slugify the title and confirm it matches the branch's slug. **On mismatch, stop**, changing nothing.
- **Already `CLOSED`** → report it and ask whether to continue with the branch teardown alone. A closed ticket with a live branch is a normal state after a hand-close, not an error.

`/pr:cleanup` treats this same check as non-halting bookkeeping. It can, because by then the merge already happened. **Here a mismatch means the next command would close an unrelated ticket and delete an unrelated branch**, so it halts.

## Step 2. Check PR state, and refuse a merged branch

```bash
PR_STATE=$(gh pr view "$BRANCH" --repo "$REPO" --json state --jq '.state' 2>/dev/null || echo "NO_PR")
```

- **`MERGED`** → **stop. This is the wrong skill.** It would close the ticket as "not planned" and delete a branch whose work already shipped. **This is the one confusion that produces a silently wrong record**: a shipped feature whose ticket reads as abandoned, with nothing in the history to contradict it. Point at `/pr:cleanup`.
- **`OPEN`** → closed in step 5, before the branch goes.
- **`CLOSED` or `NO_PR`** → note it and continue.

## Step 3. Inventory what will be lost

Run all four and **show the operator the actual output, not a summary of it.** Skip the first two when there is no worktree.

```bash
git -C "$WORKTREE_PATH" status --porcelain
git -C "$WORKTREE_PATH" log --oneline @{u}..HEAD 2>/dev/null
git -C "$MAIN_CHECKOUT" log --oneline "origin/$DEFAULT_BRANCH..$BRANCH"
git -C "$MAIN_CHECKOUT" ls-tree -r --name-only "$BRANCH" -- "$CHANGELOG_ROOT/"
```

**Uncommitted changes are not a halt here**, unlike in cleanup. Abandoning work is the declared intent, so refusing to abandon dirty work would be refusing the request. They are shown so the confirmation is informed rather than blind.

**Say when all four come back empty**, because an abort of a branch with nothing on it usually means the number is wrong.

## Step 4. Confirmation gate

Print the inventory, then **require the operator to type the branch slug back.** A yes/no prompt is too cheap for an irreversible three-part deletion, and this skill has no second chance the way cleanup does.

```
ABORT ticket <N>. This is permanent.

  Branch:   <branch>
  Worktree: <path>
  Reason:   <reason>

Will be deleted:
  - the worktree directory
  - the local branch
  - the remote branch
  - N commits not on <default>
  - M uncommitted files
  - <changelogRoot>/<slug>/ (PLAN.md, CHANGELOG.md), which exists nowhere else

Will be closed:
  - PR #<n> (currently OPEN)        [omit when none]
  - Issue #<N> as "not planned"

After this point recovery means hunting dangling objects with `git fsck`, until gc prunes them.

Type the branch slug to confirm: <slug>
```

**Anything other than an exact match aborts the abort and changes nothing.**

---

*Everything above is read-only. Everything below destroys something.*

---

## Step 5. Close the PR, if one is open

```bash
gh pr close "$PR_NUMBER" --repo "$REPO" --comment "Abandoned via /pr:abort. Reason: $REASON"
```

**Do not pass `--delete-branch`.** It deletes both branches as a side effect of closing, and the local delete fails while the branch is still checked out in a worktree step 7 has not removed yet. Step 8 does both deletions explicitly, after the worktree is gone, so the ordering is visible rather than implied by a flag.

## Step 6. Close the issue as not planned, and drop its status label

```bash
gh issue close "$TICKET" --repo "$REPO" --reason "not planned" \
  --comment "Abandoned via /pr:abort on <date>.

Reason: $REASON

Branch \`$BRANCH\` was deleted locally and on the remote; its plan folder is not on <default>."
```

**`--reason "not planned"` is what distinguishes an abandoned ticket from a delivered one** in GitHub's own UI, which renders the two with different icons. A bare close marks it completed and makes an abort indistinguishable from a merge at a glance.

Then drop the status label, checking first because `--remove-label` errors on an absent one. Nothing goes in its place: the close reason carries the meaning.

Re-fetch and confirm before reporting success. **A failure here is reported and does not block the branch teardown**: an issue can be closed by hand, whereas a half-deleted worktree is harder to reason about than a fully deleted one.

## Step 7. Remove the worktree

Skip when there is no worktree. Run from the main checkout, never from inside the target.

Use the same attempt, retry with `--force`, verify-both-halves sequence as `/pr:cleanup` step 5, tracking the leftover-directory case.

`--force` is expected rather than exceptional here: the worktree holds build and dependency directories, and step 3 already established the dirty state the operator agreed to discard. **The hard exit on a still-registered worktree is the important line**, because deleting a branch still checked out somewhere leaves git in a state that is confusing to unpick.

`rm` is deliberately absent from `allowed-tools`. Directory deletion stays user-initiated.

## Step 8. Delete the branch, local and remote

```bash
git -C "$MAIN_CHECKOUT" branch -D "$BRANCH"
git -C "$MAIN_CHECKOUT" push origin --delete "$BRANCH"
```

`-D` rather than `-d`, because `-d` refuses an unmerged branch and **an aborted branch is unmerged by definition.** The safety `-d` would provide is step 4's confirmation, which is stronger and already happened.

**Report each half separately.** A remote delete can fail on a protected branch or a network error while the local one succeeded, and "branch deleted" would then be false.

## Step 9. Clean the empty parent directory

```bash
rmdir "$(dirname "$WORKTREE_PATH")" 2>/dev/null || true
```

## Step 10. Report

```
Abort complete, ticket <N>:
  Reason:    <reason>
  Issue:     closed as not planned | close failed (<error>), close by hand
  Label:     status:in-progress removed | none to remove
  PR:        #<n> closed | none | was already closed
  Worktree:  removed (metadata + disk) | partial, directory left on disk | none on disk
  Branch:    deleted local + remote | deleted local, remote failed (<error>)
  Lost:      N commits, M uncommitted files, <changelogRoot>/<slug>/

  If your shell is still in the removed worktree: cd <main checkout>
```

Never report an unqualified "removed" when the directory survived.

## Why the gates are shaped this way

**A branch deleted without checking PR status** cost work recoverable only through a reflog cherry-pick. Step 2 is that check, and step 4's inventory exists so the operator sees what a recovery would have to find. **That incident had a reflog to fall back on because the worktree was still there; a full abort removes the worktree first, so this one does not.**

**A ticket closed by the wrong number.** The close workflow once resolved a ticket by fuzzy title search and wrote a closing reference on an unrelated issue. Step 1 reuses the fix, and halts where cleanup merely reports, because here the same mismatch would also delete an unrelated branch.

**A guard that false-positives is worse than no guard.** That is why step 3 shows uncommitted changes instead of halting on them: halting would fire on the normal case, since abandoning work in progress is the entire point, and it would train the operator to click through the one gate that matters.

**`git worktree remove` reporting success while hundreds of megabytes stayed on disk.** Step 7 verifies both the registration and the directory rather than folding the result into a cheerful summary.

## Lifecycle position

**`/pr:abort` is an exit from the lifecycle, not a step on it.** It leaves the spine at any point after `/pr:start`, and the cycle does not resume.

Run the state check **before** step 4, from inside the worktree so it describes the branch being abandoned:

- Fold its `gaps` into step 3's inventory. A `close-incomplete` or `unpushed` gap tells the operator something real about what is being discarded.
- **Ignore its `next` field, and say so.** It will name a forward step such as `/pr:close`, which is the correct answer to a question this skill is not asking. **Every other skill here forwards `next`; this one deliberately does not, because there is no next.**
