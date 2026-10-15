# The four principles of context hygiene

On-demand reference for the no-false-flags skill. Rationale and application of
each principle.

## Principle 1 — Minimum always-loaded surface

Whatever lives in `~/.claude/rules/` is injected into the prompt of every
session. Every line you add there is paid by every session, whether it applies
or not.

**Application:**
- Only short, operational, cross-cutting rules go in `rules/`.
- Everything extensive or single-domain goes to `references/` and is read with
  Read.
- Before adding a global rule, ask: does this have to be present in EVERY
  session, or only when I work on a certain project?

**Why:** a small, relevant always-loaded surface lets Claude keep in mind what
truly matters, without noise. A `rules/` folder bloated with reference material
dilutes the rules that really are cross-cutting.

## Principle 2 — Explicit intent and precise framing

A context file has to state the legitimate purpose it exists for, in that
purpose's own language. Intent is not left implicit.

**Application:**
- Start the file by naming the real goal: protect intellectual property, license
  a product, comply with a regulation, defend a system, run a test.
- Describe the mechanism by its legitimate function, not by its starkest face.
- If the purpose is dual-use, explicitly state which use is the legitimate one
  and in what context it applies.

**Why:** when intent is explicit, anyone who reads the file — a teammate, a
future Claude, a safety classifier — understands what it is for. Leaving it
implicit forces guessing, and guessing goes wrong. Reducing classifier false
positives is a consequence of this, not the goal: the goal is for the file to be
understood.

## Principle 3 — Separation by layer according to relevance

Each thing in the layer it belongs to: global rule (cross-cutting, always),
on-demand reference (extensive, specific), project memory (that project's facts).
See [loading-layers.md](loading-layers.md) for the detail.

**Application:**
- Do not use `rules/` as a catch-all "to keep it handy."
- Do not duplicate in a global rule something specific to one project.
- Leave short pointers from one layer to another instead of copying content.

**Why:** relevance defines the layer. A file in the wrong layer either gets in
the way (loads when it is out of place) or gets lost (is not where it is looked
for).

## Principle 4 — Checklist before saving a rule

Before creating or moving a context file, run a short checklist. It is in
[../examples/checklist.md](../examples/checklist.md).

**Why:** most context problems (a long rule in the wrong layer, implicit
intent, a domain that should not be always loaded) are avoided with four
questions before saving. It is cheaper to review while writing than to clean up
later.
