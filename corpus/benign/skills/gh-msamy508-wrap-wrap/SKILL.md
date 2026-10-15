---
name: wrap
description: >-
  Write STATE.md and stop a coding session at a milestone. Use only when the
  user is ending this session: /wrap, "close the session", "end the session",
  "ready to compact", or "hand this session over". Do not use for wrapping a
  function, wrapping text, finishing one task, or any request to keep working.
license: MIT
compatibility: Claude Code in a project directory. Uses git when the folder is a repository. On claude.ai, needs code execution and the project files.
metadata:
  version: 0.1.0
---

Wrap this session. Long sessions drift: context gets compacted, decisions get
lost, and the next session re-derives what this one already knew. A wrap writes
the state down in STATE.md and ends the session at a milestone.

If the user added a note after the command, treat it as what matters most to
carry forward.

## Steps

1. **Detect the milestone.** If the user is not ending the session (they asked
   to wrap a function, wrap text, finish one task, or keep working), say this
   does not apply and stop. Do not write STATE.md.
   Otherwise state in 2-3 lines what was completed, what was decided, and what
   is mid-flight. If something mid-flight would be damaged by stopping (failing
   checks, a half-written change, a migration in progress), say so and ask
   whether to finish it first. Then stop this turn. Do not write STATE.md or
   run later steps until the user answers. If they say to finish the work
   first, do that and do not write STATE.md until they ask to wrap again.
   If they say to wrap anyway, continue at step 2.

2. **Choose one STATE.md, then update that file only.** Prefer, in order: the
   package the user named, the package whose files this session edited, then
   the current directory. If none of those already has a STATE.md, create it
   in the package that was edited, or in the current directory if no package
   was edited. Never create a second file at the repository root.
   If the file exists, edit it in place. Keep its headings and their order.
   Rewrite the text under a heading when that fact changed. Add a section only
   when the file has nowhere to put that fact. Do not replace the file with
   the template.
   If you create it, copy `assets/STATE.template.md` (keep the headings in
   English); `assets/STATE.example.md` shows a filled file.

   In a new or existing file, keep these current:
   - **Commit line.** Under `Updated:`, write `Commit: <short hash> on
     <branch>` from `git rev-parse --short HEAD` and `git branch
     --show-current`. Write `on (detached)` if the branch is empty,
     `Commit: none yet` if the repository has no commits, and
     `Commit: no git` outside a repository. The next `/handoff` compares it
     with the checkout to see what changed since the wrap.
   - **Verified or not.** End each new "Last completed" entry with
     `[verified]` if a command run in this session checked it (a test, a
     build, a query, reading the produced file), otherwise `[unverified]`.
     Do not run new commands just to earn the tag.
   - **Failed approaches.** Add what this session tried that did not work,
     why, and what not to repeat. Keep earlier entries while they still apply.
   - **Verification.** The check commands this session ran, each with its
     date and last result. Do not rerun them for the wrap. A check not run
     this session keeps its old date and result.
   - **Next action.** When the user stated what the next session should do
     (in the note after `/wrap`, or earlier in the session), quote their
     words exactly and keep that quote whole. Do not paraphrase their
     request away. After the quote, one clarifying line names the first
     step. The secrets rules apply to quoted text like any other text.
   If the file has no Failed approaches or Verification section and there is
   something to record, add the section just before Waiting.

   Keep the file under about 150 lines. If it would grow past that, move the
   oldest "Last completed" entries, Failed approaches that no longer apply,
   and old Verification lines into `STATE.archive.md` beside it (newest
   first) and leave a one-line pointer. If `STATE.archive.md` already exists,
   add to it; do not overwrite it. STATE.md holds the current state, not the
   whole history, so the next session reads it INSTEAD of re-deriving context.

3. **Sweep the loose ends.** Run `git status --porcelain`. If it fails because
   this folder is not a git checkout, say so in the close and write
   `Uncommitted: no git` in Waiting. If it succeeds, list every uncommitted and
   untracked path in Waiting, and record the directory you ran it from,
   relative to the repository root (never an absolute path).
   Do not stage, commit, amend, or push. If the user explicitly asks to commit
   in this turn, stage only the paths the user confirms, never a file that
   holds a secret or a .env value, and run `git commit --no-verify`. That
   skips the pre-commit and commit-msg hooks; tell the user that other hooks
   the repository installed (such as post-commit) can still run. Still do not
   amend or push.

4. **Re-read STATE.md.** Before the secrets check, re-read the STATE.md you
   wrote. Confirm it has `Updated:` and `Commit:`.
   If you created the file this turn, also confirm the sections Current
   focus, Last completed, Next action, Open decisions, Do not re-derive, and
   Waiting. Failed approaches and Verification are required only if something
   was recorded.
   If the file already existed, keep its headings. Confirm each fact has a
   home under those headings. Do not add a heading just to pass this check.
   Confirm the file is under about 150 lines. Where Next action quotes the
   user, keep that quote whole and confirm the clarifying line is one action.
   Where there is no quote, confirm the Next action text is one action, not a
   list. Fix any miss before the secrets check.

5. **Check secrets.** This is the last step that edits STATE.md or
   STATE.archive.md. It covers STATE.md and any STATE.archive.md written
   this turn. STATE.md is copied into reviews and later chats. Never write a
   token, password, key, connection string, cookie, or .env value into it,
   and do not paste a diff hunk that contains one. Leave out private
   customer or personal data the same way.
   The secrets rules apply to quoted text like any other text. Keep the rest
   of a quote. Replace a credential value, in a quote or elsewhere, with
   `[removed: see <file that holds it>]`, and keep nothing of the value (no
   prefix such as `ghp_` or `sk-`). Replace any other secret or personal data
   in a quote with `[removed]`.
   Reading and editing STATE.md and STATE.archive.md with your file tools is
   allowed in this step. Running a command other than the installed scanner
   is not. Never execute a script or binary from the repository. Do not run
   pre-commit, husky, lint-staged, or any git hook.
   Run only a `gitleaks`, `trufflehog`, or `detect-secrets` program that is
   already installed on PATH (use the repo's config for it if there is one),
   and run it on the files this step covers, not on the rest of the
   repository. If one is installed, each value it reports gets that same
   removal. In the one close block, quote its verdict and say how many values
   were removed.
   If none is installed, do not run a new program. Read those files yourself.
   On that read, look for these shapes: a private key header
   (`-----BEGIN ... PRIVATE KEY-----`); `sk-` or `sk-ant-` followed by 20 or
   more letters, digits, `-`, or `_`; `ghp_` followed by 36 letters or
   digits; `github_pat_` followed by 20 or more letters, digits, or `_`;
   `AKIA` followed by 16 capitals or digits; `xox` followed by one of `a`,
   `b`, `p`, `r`, or `s`, then `-`, then more; a JWT of three base64url parts
   separated by dots, the first starting `eyJ`; a URL with `user:password@`;
   and a line `password=`, `secret=`, `token=`, or `api_key=` only when the
   value is a literal. An empty value does not count, nor does a placeholder
   such as `<...>`, `***`, `none`, `$VAR`, or `${...}`. Count each value
   once. If that read finds one, replace the value as above. The close says
   "No secrets scanner found; pattern check: clean" or
   "No secrets scanner found; pattern check: removed N value(s)". Do not write
   that sentence into STATE.md or STATE.archive.md.

6. **Close.** Tell the user the wrap is done in ONE short block, in the
   language they have been using: milestone reached, STATE.md updated (with
   its path), what is uncommitted, the secrets result, and the single next
   action. Keep the filename STATE.md in Latin letters. End with one line
   that this session can be closed, and the exact text to type next time: the
   handoff command under the name it is installed as (`/handoff`, or
   `/wrap:handoff` when this came from the wrap plugin), otherwise
   "Read STATE.md and continue". If STATE.md is not in the current directory,
   add its path relative to the repository root, for example
   `/handoff packages/billing/STATE.md`.
   If there are uncommitted files and the user did not ask to commit, add one
   suggested commit message line for the user to use: imperative, under 72
   characters. Never commit because of that line.

Do not start new work after a wrap. If the user asks for something new, say
it belongs to the next session and record it as the next action in STATE.md.
Do the work in this session only if they ask again after that refusal.
