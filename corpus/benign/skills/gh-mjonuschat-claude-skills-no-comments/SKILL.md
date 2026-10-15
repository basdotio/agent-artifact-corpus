---
name: no-comments
description: Use when the user asks to clean up comments, run a comment audit, or invokes /no-comments — spawns a fresh, comment-hating subagent to flag unjustified comments and unproven lint suppressions in a diff or file set, then fixes what the audit confirms.
---

# No comments

Spawn Comment Sicko fresh. Act on what it confirms.

The agent that wrote a comment will defend it. A fresh subagent with no
stake in the code and no conversation history has no such bias — that's why
this spawns a subagent instead of reviewing inline.

Requires subagent support: built in for the Agent tool in Claude Code; in
Codex, needs `multi_agent = true` in `~/.codex/config.toml`.

## Scope

Use the caller's named files or diff. Otherwise use the current diff against
the base branch (`main` in this repo), including the uncommitted working
tree.

## Steps

1. Spawn a fresh subagent with a clean context — no prior conversation
   history. In Claude Code, the Agent tool (subagent_type `general-purpose`
   or omitted); in Codex, `spawn_agent {fork_turns: "none"}`. Its prompt is
   `references/comment-sicko-prompt.md` verbatim, plus the scope from above.
   Pass nothing else — no priming, no restating rules.
2. Inspect its report against the actual diff. Reject:
   - edits to application code (it may only flag comments, never change
     them itself),
   - flags outside the given scope,
   - a deletion of a comment that matches one of the persona's five keep
     exceptions,
   - a `MUST KILL` whose stated reason doesn't hold once you read the code,
   - a flag that treats a genuine our-code surprise as a foreign-dependency
     "keep" — that's a `MUST KILL` the persona missed; add it to the accepted
     set instead.
   Do not restore a comment you reject for the last two reasons — a keep
   survives only with proof it describes something outside this codebase's
   control.
   For thin `IMPORTANT` / `do not remove` justifications: before accepting
   either a kill or a keep, read the named symbol's actual callers and usages
   directly. An ambiguous kill stays killed. A keep that's refuted or still
   ambiguous after checking gets deleted.
   If you reject a report, respawn once with the specific failure named in
   the prompt. Reject the second report too, and stop: report the audit as
   open and leave the comments as they are rather than guessing a third time.
3. Fix trivial accepted flags directly: delete a dead path, drop an unused
   parameter, call the real API instead of narrating around it. If a fix
   needs an actual design decision, work out that shape yourself before
   touching code — don't paper over the decision with a quick patch.
4. For each accepted `MUST KILL`, implement the smallest root-cause fix:
   rename, extract, retype, or rearchitect so the behavior is obvious without
   prose. Remove the workaround the comment was narrating, not just the
   comment. If the root cause is out of scope for this pass, land the
   smallest in-scope fix and report the rest as open — this never justifies
   widening the file/diff scope from step 1.
5. A surviving keep that names a real constraint (`do not remove`, `do not
   change wording`, `talk to X before changing`) stays as a comment. Offer to
   encode it more cheaply instead: a type, a runtime assertion, a test, or a
   CI lint, whichever is smallest. Wait for the user to approve before
   encoding it — in an unattended or scheduled run, only act on constraints
   the user pre-approved. If approved, encode it and delete the comment.
   Otherwise leave the comment, report the constraint as open, and describe
   the encoding you'd apply if asked.
6. Report: deletion count, any comments restored and why, rerun attempts,
   fixes made, encoding offers/results, and any constraint left as a plain
   comment.
