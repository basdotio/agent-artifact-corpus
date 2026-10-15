# Field Format

All field labels are fixed English strings, regardless of what language the source
documentation is written in. Field content is also written in English.

## Full format (used in `docs/test-cases/<feature>.md`)

```markdown
### TC-<FEATURE>-<NNN>
- **Title**: Short, specific description of the scenario
- **Source**: written spec (docs/path.md §section) OR inferred (checklist: category)
- **Type**: happy-path | error-handling | edge-case
- **Priority**: P0 | P1 | P2
- **Status**: active | needs-review | superseded-by: TC-xxx
- **Precondition**: State the system must be in before Steps begin
- **Steps**:
  1. Concrete, literal action
  2. Concrete, literal action
- **Expected**: Observable outcome, stated as fact
- **Level test**: unit | integration | snapshot | ui-single-screen | e2e-multi-screen
- **Smoke**: true | false
```

If `Status` is `needs-review`, add one line directly under it explaining why, e.g.:
```markdown
- **Status**: needs-review
  > New SSO flow adds a second auth path; confirm this network-failure case still
  > covers it, not just password login.
```

## Short index format (used only in `_index.md`, auto-generated)

```markdown
- [ ] TC-003 (P1, integration) ⚠️needs-review: Short title
- [x] TC-007 (P0, e2e-multi-screen, 🔥smoke): Short title
```

Checked box means `Status: active` or `superseded-by`. Unchecked means
`needs-review`. This file is fully regenerated every time, never hand-edited.

## ID rules

- Format: `TC-<FEATURE>-<NNN>`, zero-padded to 3 digits, starting at 001.
- In a monorepo covering more than one platform, prefix with the platform too:
  `TC-IOS-LOGIN-003`.
- Numbers are never reused and never reset, even across separate invocations or
  after a file split (Step 6 in SKILL.md). If `login.md` is split into `login.md`
  and `login-sso.md`, the SSO test cases keep whatever numbers they already had.

## Priority decision rule

Apply top to bottom; stop at the first match.

1. Failure causes a crash, data loss/corruption, or a security/auth bypass → **P0**,
   no exceptions.
2. This is the happy path of a core flow (see `core-flows.md`) and it fails
   entirely → **P0**.
3. This is an error-handling path within a core flow → **P1**.
4. This is the happy path of a non-core (peripheral) feature → **P1**.
5. Everything else (peripheral edge case, cosmetic, low-traffic path) → **P2**.

## Level test decision rule

Derive this from what the test case's own Steps actually require, not from a guess
about how important the feature is.

| Steps require... | Level test |
|---|---|
| Only calling a function/method with given input and checking output; no UI, no OS | `unit` |
| Network or storage I/O, but it can be mocked; no real UI navigation | `integration` |
| Rendering a single view and comparing it to a reference image | `snapshot` |
| Real UI/OS interaction confined to one screen (tap, permission dialog, form input) | `ui-single-screen` |
| Real UI/OS interaction that crosses multiple screens (a journey) | `e2e-multi-screen` |

Default toward the cheapest level that can actually verify the behavior. Don't mark
something `e2e-multi-screen` just because the feature feels important - only mark it
that way if the Steps genuinely can't be verified without crossing screens.

A platform pack may add extra `Level test` values scoped to that platform (for
example, a `contract` level for backend/API work) when none of the five above fit.
It may also declare some of the five not applicable on that platform. Check the
loaded platform pack before assuming the full list above always applies.

## Smoke flag

`Smoke: true` is not a sixth level test value. It's a flag layered on top of a test
case that is already all three of: `Priority: P0`, part of a core flow, and
`Type: happy-path`. Everything else gets `Smoke: false`.
