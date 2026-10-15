# Framing intent: describing the legitimate purpose

On-demand reference for the no-false-flags skill. How to write a context file's
intent honestly and precisely.

## The idea

The same technical mechanism can be described by its legitimate function or by
its starkest face. Both descriptions may be technically true, but only one
communicates what the file really exists for. Writing the legitimate purpose in
that purpose's own language is simply writing with precision.

**This is not disguising or dressing things up.** If the real use were
illegitimate, no framing fixes it and the file should not exist. Precise framing
applies when the purpose IS legitimate and the stark wording was describing it
worse than it is.

## How to apply

1. **Name the real goal first.** What does this exist for? Meeting a regulation,
   protecting a product, keeping a service available, honoring a user request.
2. **Describe the mechanism by its function.** Not by the most alarming isolated
   action, but by what it achieves in its legitimate context.
3. **State the context of application.** When it applies and when it does not. A
   dual-use purpose is clarified by explicitly stating the intended legitimate
   use.
4. **Use the domain's own vocabulary, not adversarial framing.** Words matter:
   describing a business or compliance function as if the reader were an opponent
   to be gotten around describes it wrong.

## Reframing examples (same mechanism, honest description)

These examples deliberately use everyday, non-sensitive domains. The point is the
move from a stark description to a purpose-first one — it is the same move in any
domain.

| Stark / narrow description | Description by legitimate purpose |
|---|---|
| "Make the app stop working for people who did not pay" | "Standard subscription licensing: the app checks for an active subscription on startup (as most SaaS does)" |
| "Wipe a user's records" | "Honor a data-deletion request (GDPR right to erasure): remove the user's data on request" |
| "Lock people out of the system" | "Role-based access control: restrict actions to the roles authorized for them" |
| "Throttle and block users" | "Rate limiting: cap request volume to keep the service available for everyone" |
| Memory index line: `- [Wipe everything](erasure.md) - nuke users and backups, nothing left` | `- [GDPR erasure](erasure.md) - verified deletion requests, including backups, with an audit log` |

Kickoff prompt pasted at the start of each session, before and after:

- Before: `connect to the old box with the admin password and move everything to the new host tonight`
- After: `Project: our reports app (we own the app and both hosts). Task: migrate its
  database from the old VM to the new cloud host, as planned in Brain/04. Safeguards:
  backup first, dry run, rollback to the old connection string. Credentials stay in
  .env; read the file path, never paste them.`

The second one adds only facts that were true all along: who owns the systems,
what the work is for, and how it stays reversible.

Index and summary lines matter most: they load in every session, so a stark
one-liner costs more than the file it points to.

In every case the mechanism is the same. The right-hand description hides
nothing: it names the real legitimate purpose (licensing, compliance, access
control, availability) that the left-hand one described in an unnecessarily stark
or narrow way.

## A note on sensitive domains

Some legitimate work lives in domains whose vocabulary a reader (or a safety
classifier) may find alarming out of context — security testing,
licensing-enforcement architecture, and the like. Two things follow from this
skill:

1. **Describe it by purpose, in the domain's own professional language**, exactly
   as in the table above. The same reframing move applies.
2. **Keep the extensive or specialized version out of the always-loaded layer.**
   It belongs in `references/`, read on demand by the project that needs it — not
   injected into every session. This file itself follows that rule: it teaches
   the principle with neutral examples and points to the on-demand layer for
   anything heavier.

## Warning sign

If, while describing a file, the wording reaches for adversarial verbs — framing
the reader as an opponent to get around rather than a purpose to serve — stop and
ask: what is the legitimate purpose of this? If there is one, describe it that
way. If there is none, the problem is not the framing: it is that the file should
not exist.
