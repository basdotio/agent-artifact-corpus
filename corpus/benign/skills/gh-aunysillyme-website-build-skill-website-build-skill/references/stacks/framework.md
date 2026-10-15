# Framework recipe

Date rule: [ASK DATE and source evidence](../../playbooks/research-and-memory.md#ask-date-rule).
Use this recipe only after accepted research and a named visual mockup selection.
Example commands and host/runtime support are UNVERIFIED until executed or sourced
for the chosen project. Save actual results; never claim this recipe was deployed.

Use when named application requirements earn a server/client framework.

## Justify the runtime

Compare a small endpoint with a full application for each server requirement.
Name authentication state, server secrets, request-time behavior, integration needs,
content authoring, deployment runtime, and maintenance owner.
Select supported versions from current official documentation and actual source inspection.
MDX or payments may support this decision but do not mandate a particular framework.

## Map responsibilities

```text
routes/                   Framework-native route files after version verification.
server/                   Authorized secrets, validation, integrations, access checks.
components/               Shared presentation and bounded client interactions.
content/                  Validated authored data and owner-approved entity facts.
public/                   Approved images, local fonts, discovery/static assets.
test/                     Server boundaries, rendering, state and primary journeys.
framework configuration   Verified runtime, output, routing and security behavior.
dependency lock           Reproducible chosen toolchain.
SITE_OPERATIONS.md        One complete run/release/verify/recovery document.
```

These are responsibility names, not invented vendor directory requirements.
Use the actual framework's versioned directory and API contracts.
Keep server secrets out of public environment variables, serialized props, and client bundles.
Authorize each private action on the server; hiding a button is not access control.

## Establish the command contract

Record exact dependency installation, development, type-check, test, production build,
production preview/start, deploy and rollback commands for the chosen host/version.
Do not paste generic commands as successful runs.
Require a clean production build and the same output/runtime class used for release.
Record environment variable names, purpose, scope, and injection mechanism without values.
Verify build-time versus request-time behavior, caching, route fallback and error handling.

## Render safely and usefully

Keep useful initial HTML and truthful per-route metadata.
Validate data, URL schemes and required identifiers before rendering controls.
Use safe script-bound JSON serialization even if the framework escapes normal text.
Test server/client state parity and boundary dates with an explicit timezone policy.
Keep client work small; add it for actual interaction rather than all page content.

## Verify the application surface

- Access: test unauthenticated and wrong-authority requests on each protected action.
- Inputs: test malformed bodies, rejected URLs, uploads and third-party responses where applicable.
- Rendering: run build B04/B05 and discovery parity against actual production output.
- CSP: inspect emitted inline content and test an exact hash or per-response nonce design.
- Responses: check normal, redirect, error, asset and dynamic/function headers separately.
- Journey: complete mobile/desktop, keyboard, failure/retry and reduced-motion paths.
- Release: freeze a candidate, obtain different-family read-only review, reproduce findings,
  verify fixes, then promote the checked artifact within existing authorization.

## When to move to a bigger stack

More runtime means more dependency, patching, secret, and operational responsibility.
Record the upgrade cadence, watchers, failure recipient, and tested recovery commands.
Keep content portable and isolate external integrations behind narrow interfaces.
A supported framework name does not prove that a selected host tier runs its features.

## Research starting points

Open the chosen framework's current routing, rendering, security, environment, and CSP docs.
Open the target host's current runtime/plan constraints and deployment/recovery docs.
Compare a real application repository at an inspected revision, with its license recorded.
