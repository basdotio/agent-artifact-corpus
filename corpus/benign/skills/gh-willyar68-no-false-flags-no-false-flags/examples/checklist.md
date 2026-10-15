# Checklist before saving a rule or memory

Example/template for the no-false-flags skill. Run these questions before
creating or moving any Claude context file.

## The four questions

1. **Is it short and operational?**
   If it is long or mostly examples/reference, it is not a rule: it is reference
   material. It goes to `references/`, not `rules/`.

2. **Is it cross-cutting (applies to all projects)?**
   If it only applies to one project or a specific domain, it does not go in
   `rules/`.
   - Project fact/decision -> that project's memory.
   - A domain document used sometimes -> `references/` with a pointer.

3. **Is the intent explicit?**
   Does the file state which legitimate purpose it exists for, in that purpose's
   own language? If intent is implicit or described by its starkest face, rewrite
   the heading naming the real goal (see
   [../references/framing-intent.md](../references/framing-intent.md)).

4. **Is it in the right layer?**
   Check against the decision tree in
   [../references/loading-layers.md](../references/loading-layers.md):
   global rule / on-demand reference / project memory.

## If any answer is "no"

- Not short / not operational -> move to `references/`, leave a short pointer.
- Not cross-cutting -> move to project memory or to `references/`.
- Implicit intent -> rewrite the heading with the legitimate purpose.
- Wrong layer -> move to the layer it belongs to by relevance.

## Mnemonic

Short + cross-cutting + explicit intent + right layer -> `rules/`.
Fails any of the four -> it does not belong in the always-loaded layer.
