# Using high-capability models without false positives on legitimate work

On-demand reference for the no-false-flags skill. The honest account of what
context hygiene can and cannot do about safety-related false positives on the most
capable models.

## The situation

More capable models run stricter safety checks. On legitimate work they sometimes
flag by mistake — a false positive — and the platform may answer with a less
capable model instead. That is real friction on honest work, and it is annoying.

## What actually causes the false positives

The check evaluates the **content present in the conversation**, not your stated
good intentions. It reacts to sensitive or dual-use vocabulary and material that
is loaded into the context. The more such material sits in the always-loaded layer
or gets dragged into the working conversation, the more surface there is to react
to — even when the task at hand is unrelated to it.

A concrete pattern: a reference document full of specialized vocabulary lives in
the always-loaded rules layer. It loads in every session. Now every session
carries that surface, and unrelated legitimate work can trip on it.

## What context hygiene does about it (real and effective)

Remove the unnecessary surface. Keep sensitive or dual-use material out of the
always-loaded layer and out of the working conversation, and state each file's
legitimate intent plainly. Then legitimate work trips far less often on the top
model. Concretely:

1. **Sensitive or extensive reference material lives in `references/`,** read on
   demand — never in always-loaded rules.
2. **Each file opens with its legitimate purpose in one line,** so intent is
   explicit rather than left to be inferred.
3. **Do not pull a sensitive document into the conversation** unless the current
   task truly needs it right now. When the task is done, a fresh session drops it
   from context.
4. **Keep one topic per session** so material from one task does not linger into
   an unrelated one.

## What it does NOT do (the honest ceiling)

A skill is instructions inside the prompt. Safety checks run **outside** the
prompt and cannot be turned off, reduced, or bypassed by any instruction, skill,
or choice of wording. Nothing here disables a check or guarantees the top model
never flags you. The realistic outcome is **far fewer false positives on
legitimate work**, not **zero blocks ever**. Anything that claims to switch the
check off is selling a lie — and writing a file as "how to get around the check"
would itself be exactly the kind of content that trips it.

## If you get flagged anyway on legitimate work

Follow section 1 of [../SKILL.md](../SKILL.md). The official recovery options it
builds on (Claude Code docs, [errors](https://code.claude.com/docs/en/errors) and
[model fallback](https://code.claude.com/docs/en/model-config)):

- The check evaluates the full conversation, so a new message in the same
  session, or reopening it with `--continue` / `--resume`, usually re-triggers it.
- Press Esc twice or run `/rewind` to step back to a checkpoint before the turn
  that triggered it; if you cannot identify the turn, run `/clear`.
- The first request of a session carries CLAUDE.md and git status; to check
  whether customizations are the trigger, start with `claude --safe-mode`.
- After an automatic model fallback, run `/model` to return to the original model.
- Report false positives with `/feedback`. For legitimate security work, the
  Cyber Verification Program is the official route to fewer interruptions.
