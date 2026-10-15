---
name: no-false-flags
description: Use when a response was "stopped by a safety classifier" or "withheld", when a notice says "safeguards flagged this session" and another model "is answering instead", when legitimate work keeps getting flagged, before reading a long document or a whole folder of docs, or before acting on a short request that touches servers, credentials, data or people.
---

# No False Flags

The safety check reads the **whole conversation**, and everything read or pasted
stays in it for the session. Keep in it only what the task needs; state the task
plainly. Nothing here bypasses a check or guarantees zero stops.

## 1. When a response is stopped

A new message in the same session usually re-triggers the check, and so does
`--continue` / `--resume`. Recovery means removing content, not insisting.

**Stops that recur across sessions on legitimate work, or a request to "make it
stop happening":** recovery alone treats the symptom. Do section 5 now, then
recover the current session.

1. Tell the user in one line: it was the safety check, not a tool error.
2. **Say what was cut:** the step or tool call that did not finish; the withheld
   text cannot be recovered. For an interrupted tool call, check its effect (does
   the file or change exist, whole or partial) by name, size or git status, and
   say so.
3. **Hand back the stopped step:** if it was legitimate work, give the user a
   ready-to-paste request for it, in their language: the same action stated
   plainly, plus what it is, whose it is and what it is for. Mark any fact the
   user did not give as `[COMPLETE: ...]`; never fill it in.
4. Find material the task does not need (a document from another task, long
   pastes). Refer to it **by file name only**; describing it puts it back in.
5. **Turn identifiable:** ask the user for Esc twice or `/rewind` to before it.
6. **Not identifiable, or second stop:** stop working here. Write a handoff (goal,
   decisions, state, pending; file pointers, never content; files NOT to open).
   Ask for `/clear` or a new session without `--continue`. Do not keep going here.
   A hook that loads the previous session at start (a saved session summary)
   brings the stop back after `/clear`: move that file aside or turn the hook off
   first. The fallback hook detects it and tells the user.
7. **Stop on the first request of a session:** the request usually lacked
   context; step 3 is the answer. If complete requests still stop,
   always-loaded context may be the trigger; `claude --safe-mode` confirms.
8. **After an automatic fallback:** once clean, `/model` returns to the original.
9. **Still stopped in a clean session:** suggest `/feedback`; for legitimate
   security work, Anthropic's Cyber Verification Program.

Never reword, use euphemisms, or obfuscate to get past the check. If asked, decline
and offer the clean path and section 3 instead.

## 2. Bringing material in

For a long document, or one from another task: Grep headings (`^#`) and task
keywords with line numbers, then Read only those sections with `offset`/`limit`.
Quote only the lines you act on. "It fits in one read" is not the test: every
section read stays in the conversation.

Asked to read a whole folder first (CLAUDE.md and all of `Brain/`, say): read
CLAUDE.md, Grep each doc's headings, Read only what the first task needs, and say
in one line that the rest is read when a step needs it.

## 3. Delivering the request

If a short or ambiguous request touches a sensitive domain (servers, remote
access, migrations, credentials; deleting data; accounts and access control;
licensing; automation on third-party sites; security testing; monitoring people;
financial, health or legal data; bulk actions on people), restate it first, in
the user's language, as one confirmable line:

> Task: <action> on <object>, which is <whose>, for <purpose>.
> Safeguards: <backup / dry-run / confirmation / audit log / rollback>.

Use the domain's professional terms, not euphemisms. Whose it is and what it is
for are facts the user supplies: if unstated, ask; never assume them. The user's own work is stated too ("my own app").
Read-only exploration can proceed; nothing irreversible runs before confirmation.

## 4. Shaping the response

Answer at the scope asked, in the task's own domain. No unrequested background or
tutorials; no material from an earlier, unrelated task.

## 5. Clean from the start (the cause)

What loads every session (rules, CLAUDE.md, memory indexes such as MEMORY.md) is
the usual cause of recurring stops. One alarming line in an index is paid every
session, even when its file loads on demand. So are the project docs read at
every start (`Brain/`, plans) and the kickoff prompt pasted each session.

**The request carries its own context.** Measured: a short request was stopped
even with its context in CLAUDE.md; the same request stating what the work is,
whose it is and what it is for was not. Keep that line in the kickoff prompt the
user pastes, not only in CLAUDE.md.

1. **Measure without dumping:** list those files and find flagged lines with
   `grep -il` / `grep -c` (names and counts only). Never Read them whole or paste them.
2. **Rewrite by purpose:** each flagged line says what the work is for, in the
   domain's professional terms.
3. **Demote** long or single-domain material to on-demand references.
4. **Edit without re-exposing:** Read only the flagged line (`offset` on it,
   `limit` 1) and change it with Edit.

See [loading layers](references/loading-layers.md),
[surface audit](references/surface-audit.md), [demotion](references/demotion.md),
[intent lines](references/framing-intent.md), [limits](references/false-positives.md).
Sources: [errors](https://code.claude.com/docs/en/errors),
[model fallback](https://code.claude.com/docs/en/model-config).
