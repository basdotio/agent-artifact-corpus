# Scripted static recipe

Date rule: [ASK DATE and source evidence](../../playbooks/research-and-memory.md#ask-date-rule).
Use this recipe only after accepted research and a named visual mockup selection.
Example commands and host/runtime support are UNVERIFIED until executed or sourced
for the chosen project. Save actual results; never claim this recipe was deployed.

Use when many pages share structure and must derive metadata from the same records.

## File responsibilities

```text
src/data/                 Authored records and route registry.
src/render/               Shared escaping, URL, JSON and state helpers.
templates/                Page and component rendering.
scripts/build.ts          Validate, render, derive discovery, report omissions.
scripts/images.ts         Deterministic authorized image transformations.
public/                   Approved static files copied to output.
test/                     Data boundaries, rendered adverse cases, route parity.
dist/                     Generated deployable output, never hand edited.
package.json              Exact project scripts and declared dependencies.
package-lock.json         Reproducible dependency resolution when npm is selected.
SITE_OPERATIONS.md        Content, build, release, verify and recovery in one file.
```

Builder owns implementation and generated output.
Graphics supplies versioned assets; Optimizer supplies versioned discovery inputs.
Do not let integrations overwrite their authored sources.

## Define the command contract

```text
npm ci             Install the project's reviewed locked dependencies.
npm run build      Validate -> images -> render -> discovery -> inspect/report.
npm test           Run meaningful boundary and generated-output checks.
npm run preview    Serve the built output for local browser verification.
```

These commands are a proposed project contract, not scripts supplied by this skill.
Builder must implement and verify the scripts and document the actual TypeScript runtime.
Use the chosen runtime's supported compilation/execution path after a current-source check.
Vite is optional when bundling or development behavior serves a named requirement.
Sharp is a build dependency when the image transformation pipeline needs it.
Do not introduce a client framework merely to map records to HTML.

## Build deterministically

Validate required fields, route uniqueness, URLs, dates, and relations before rendering.
Compute publication state once with an explicit clock/timezone and named rebuild trigger.
Generate HTML, metadata, social inputs, schema, sitemap, and llms.txt from validated records.
Omit absent optional provider controls and report the omission.
Sort output and use stable content/transformation asset identities.
Exclude site-work, originals not intended for publication, credentials, and scratch files.

## Prove the next-item workflow

Add one invented valid record in a disposable copy, run the clean command chain,
and inspect the new route and every derived surface.
Confirm no template or separate metadata list needed manual edits.
Remove the demonstration record before the real release and rebuild its exact candidate.
Keep adverse cases for quotes, script terminators, unsafe schemes, empty IDs,
duplicate slugs, missing assets, long copy, and publication boundaries.
Apply checklists/build.md and the remaining QA/security/ship gates.

## When to move to a bigger stack

A generated page changes only when rebuilt and promoted.
A browser interaction cannot keep a private server credential.
Move to a justified endpoint or framework when request-time/authenticated state needs it.
Keep records and pure rendering helpers separable so the content is portable.

## Research starting points

Read current runtime, template library, sharp, optional bundler, and selected host docs.
Inspect actual build/helper/test files in reference repositories at recorded revisions.
Use playbooks/data-and-templates.md and image-pipeline.md for acceptance contracts.
