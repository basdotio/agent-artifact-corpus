# The three context-loading layers

On-demand reference for the no-false-flags skill. Detail of each layer, what
goes in each one, and how to decide.

## Why the layer matters

The cost of a context file is not just disk: it is how many times it loads and
in which sessions. A 200-line file in `~/.claude/rules/` is injected into the
prompt of EVERY session of EVERY project, whether it applies or not. The same
file in `~/.claude/references/` costs nothing until someone reads it with the
Read tool, and only when it is needed.

Choosing the layer well is what keeps the always-loaded surface small, relevant,
and clear.

## Layer 1 — Global rule (`~/.claude/rules/*.md`)

- **When it loads:** in every session, always, automatically.
- **What goes here:** short, operational, cross-cutting rules. Things that apply
  to any project and that Claude has to keep in mind without looking them up.
  Examples of the right kind: date format, time zone, do not fabricate, do not
  spend without permission, how to deliver text.
- **What does NOT go here:** long reference documents, single-domain or
  single-project material, anything only needed "once in a while."
- **Size rule:** if you have to scroll it a lot or it is mostly examples, it is
  probably not an operational rule but a reference.

## Layer 2 — On-demand reference (`~/.claude/references/*.md`)

- **When it loads:** never on its own. It is read explicitly with the Read tool
  when the project or task calls for it.
- **What goes here:** extensive material, full guides, architectures,
  specialized domain vocabulary (security, legal, medical, financial), any
  dual-use material that only applies to some projects.
- **How it is discovered:** from a short rule or from the project memory, leave a
  pointer ("for X, read `references/file.md`"). The pointer is short and always
  loaded; the heavy content stays out until asked for.
- **Benefit:** the material stays 100% available, but does not contaminate every
  session with vocabulary that is out of place there.

## Layer 3 — Project memory (`~/.claude/projects/<x>/memory/`)

- **When it loads:** in that project's sessions.
- **What goes here:** project facts not derivable from code or git, learned
  feedback, decisions made, work in progress.
- **What does NOT go here:** rules that apply to all projects (those are layer 1),
  nor extensive reference documents (those are layer 2).

## How to decide the layer (decision tree)

0. **Is it mechanically enforceable rather than knowledge?** If a hook or a
   permission rule could enforce it (a format, a ban, a path restriction), it is
   not documentation — put it in the hook/permission config, not in always-loaded
   text. Many bloated rules are really unimplemented hooks.
1. **Does it apply to all projects, and is it short and operational?**
   Yes -> Layer 1 (global rule).
   - **Only matters under a certain path/directory?** -> path-scoped rule (loads
     only for that path), not a fully global rule.
2. **Is it extensive, single-domain, or dual-use material only needed sometimes?**
   Yes -> Layer 2 (on-demand reference). Leave a short pointer where needed.
3. **Is it a fact, feedback, or decision for ONE specific project?**
   Yes -> Layer 3 (that project's memory).

If something seems like layer 1 but is long: it is almost always layer 2 with a
short pointer in layer 1.
