# Choose the smallest stack

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: what is the least machinery that meets the approved brief?

## Establish requirements

Require accepted research, a confirmed brief, and a named mockup selection.
List routes, content editor, publishing frequency, repeated structures, state,
authentication, secrets, integration needs, localization, and maintenance owner.
Separate request-time requirements from operations that can happen during a build.
A framework preference is a preference, not proof of a runtime requirement.

## Follow the decision tree

```text
Server secrets, authenticated state, or request-time behavior?
  Compare a small separate endpoint with an application framework.
  Select a framework only if the remaining application requirements earn it.
Otherwise, repeated pages with shared structure or derived metadata?
  Yes: scripted static builder with validated records and shared templates.
  No: static HTML, CSS, and only the JavaScript the approved experience uses.
Before adding another layer, name the requirement still unmet.
```

- Static HTML: load references/stacks/static-html.md for files, preview, and checks.
- Scripted static: load references/stacks/scripted-static.md for data-derived routes.
- Framework: load references/stacks/framework.md for server/client and runtime boundaries.

## Compare costs and exits

For each candidate, name its dependency, supported version, build/runtime needs,
host constraints, upgrade path, editor workflow, and removal path.
Evaluate APIs against official documentation opened in this engagement.
Payments may use a hosted checkout. MDX may compile to static pages.
Neither capability universally requires a particular framework.
Do not add a CMS, analytics service, or paid dependency without an approved need.

## Work a small example

An invented workshop has a home page, visit page, and quarterly article series.
Repeated articles share title, summary, image, and canonical metadata.
A scripted static builder can derive articles and discovery files from one record.
A private member area would add a server-state requirement that needs a new comparison.
Do not silently extend the original stack decision to cover the member area.

## Record and verify

Write site-work/stack.md with requirements, rejected alternatives and reasons,
selected recipe, dependencies, host, source claim IDs, and exact editing/build commands.
Have another author add a representative next item from those instructions.
Verify the new route, navigation, canonical, sitemap, and discovery entry together.
Apply checklists/build.md B01 and B03 before accepting the decision.

## Failure modes

- Familiarity: choosing a framework before reading requirements or selecting a mockup.
- Hidden server: static output depends on an undocumented secret-bearing process.
- Editorial duplication: each new record needs manual changes in multiple metadata lists.
- Unsupported API: copying a remembered version without a current source check.

## Source starting points

Open the selected framework and host's official versioned documentation.
Inspect real source files at a recorded repository revision and check its license.
The three local stack references are recipes to validate, not platform support claims.
