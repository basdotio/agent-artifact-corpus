# Core Flows

Whether a feature counts as a "core flow" drives its `Priority` classification (see
`field-format.md`). This is a product decision, not something to infer from code, so
it's kept as an explicit, user-maintained list below.

## How to use this file

1. Check the list under "Core flows" for the feature in scope.
2. Listed → treat it as a core flow. This is final; don't second-guess it.
3. Not listed → you may infer core-flow status from signals in the spec (words like
   "MVP", "must-have", or the feature's position in primary navigation), but every
   test case that relies on this inference must record `core-flow: inferred` next to
   its `Source` field, not be treated as settled.
4. If you infer a feature is a core flow but it isn't on the list below, say so to
   the user when you report results - don't just silently add it to this file
   yourself. The user updates this list by hand.

## Core flows

<!--
List one feature per line, matching the names used under docs/test-cases/.
Example:
- Login
- Checkout
-->

(empty - fill in as features are defined)
