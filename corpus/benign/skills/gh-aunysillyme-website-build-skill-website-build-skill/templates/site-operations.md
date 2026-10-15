# Site operations

Date rule: [ASK DATE and evidence provenance](../playbooks/research-and-memory.md#ask-date-rule).
This is a blank artifact contract. Fill it from actual inputs and evidence at runtime.
Unresolved required fields keep the relevant gate BLOCKED; never prefill a PASS.

## What and why

Record audience, primary action, public destination, implementation source and current artifact.
Name the operational owner by approved role or contact mechanism, never by invented identity.

## Trigger

State what starts content updates, scheduled publication, builds and release promotion.
Name the actual scheduler or manual owner. If nothing is scheduled, say manual.
A date in a template does not create a rebuild trigger.

## Invocation chain

Write the exact sequence from content edit through validation, image generation, build,
preview, checks, promotion and live verification. Include working directories and commands
as project-relative paths. Record the operator and failure stop at each step.
Do not require a second document to reconstruct the procedure.

## Dependencies

List verified runtime/tool versions, dependency lock, host plan, integrations and access roles.
Name credential storage/injection mechanisms and environment variable names only.
Do not include secret values, authenticated links or personal machine paths.

## Reads

List content records, assets, brand tokens, approved discovery inputs, configuration,
external resources, and authority needed to read each.

## Writes

List generated output, deployment target, logs, analytics/event side effects,
and any runtime persistence with owners and retention constraints.
Keep private research, raw brand sources, scratch artifacts and credentials out of uploads.

## The closed loop

Name what watches the site, including nothing when no watcher exists.
For each watcher record check, cadence, expected signal, recipient and response procedure.
State how missed instrumentation or a broken watcher becomes visible.
If manual only, name the responsible role and the concrete manual verification trigger.

## Failure modes

| Symptom | Diagnostic command/action | Expected evidence | Recovery | Responsible role |
| --- | --- | --- | --- | --- |

Cover failed builds, bad routes/assets, CSP breakage, form/integration failure,
stale scheduled content, invalid discovery data, unavailable credentials and failed deploys.
Record rollback identity, retention limits and safe recovery for an initial release.

## Run-and-verify by hand

Provide exact content editing, clean build, tests, preview, promotion and rollback commands.
For each command include environment requirements, observed success evidence and failure response.
Include live HTTPS, route, error, asset, primary journey, header and metadata checks.
Include verification after rollback, not only the restoration command.
Mark every untested procedure UNVERIFIED with the exact settling test.

## Source of truth

Identify maintained source, content owner, approved research/brand/design revisions,
current deployed artifact, build recipe, configuration authority and release receipt.
Explain which generated files must not be edited and how future changes reopen affected gates.
Keep this document updated with the deployed artifact and actual watcher state.
