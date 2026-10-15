# Make repeated pages data changes

Date rule: [establish ASK DATE and revalidate claims](research-and-memory.md#ask-date-rule).
Source status: external facts and example commands are UNVERIFIED until checked for the chosen version and engagement.
Record opened URLs, source dates or unknown, actual access dates, and supporting evidence.

Question: how can another author add the tenth item without copying a page?

## Separate responsibilities

- Data: authored content and stable identities, owned independently of layout.
- Validation: required fields, types, uniqueness, URLs, dates, and relationships.
- Rendering: shared templates and context-specific serialization.
- Output: generated pages and discovery artifacts, never edited as source.
- Deployment: an allowlist of checked output, with private work files excluded.

## Define the record contract

Name an immutable record ID and a unique normalized route slug.
Require title, useful body, and publication state inputs needed for that content type.
Mark optional provider IDs and assets explicitly optional.
Define the accepted identifier grammar from the provider's current official source.
Trim before validating. Whitespace-only identifiers are absent, not valid values.
Reject malformed required fields with record ID and field name before rendering.
Omit missing optional controls and list omissions in the build report.

## Compute state once

Define publicationState(record, clock, timezonePolicy) as a pure decision.
Use its result for page headings, badges, buttons, indexes, feeds, and discovery output.
Use an explicit clock and timezone policy; do not infer dates from the build machine.
Test immediately before, at, and after each release boundary.
A static page changes state only after rebuilding. Name the rebuild trigger or human owner.

## Keep helpers narrow

| Helper | Contract | Adverse input |
| --- | --- | --- |
| esc | Escape text or quoted attribute metacharacters after string normalization. | Quotes, ampersands, angle brackets. |
| jsonLd | Serialize valid JSON and escape literal less-than characters for a script element. | Script-terminator text followed by markup. |
| safeUrl | Parse, normalize, and allow only schemes/origins appropriate to the URL role. | A script URL, control characters, or an unexpected origin. |
| publicationState | Return one state and its allowed actions using the explicit clock. | A release boundary with an absent provider ID. |

Use structural DOM/template APIs when available; do not concatenate untrusted attributes.
Escaping is not URL validation, and safe JSON is not HTML sanitization.
For rich HTML, use a reviewed sanitizer with a narrow allowlist or render text instead.

## Work a small example

```text
record: workshop-introduction
slug: workshop-introduction
state: published
provider_id: empty
expected page: visible article, no provider link, no player, omission in build report
expected discovery: the article route only if it satisfies the public-content rules
```

Validate the ID before constructing a URL, not after interpolating it into a suffix.
Never render an empty href, a fragment stand-in, or an empty provider URL as recovery.
A valid optional ID enables its control only when the shared state permits it.

## Derive related outputs

Generate route HTML, titles, descriptions, canonical URLs, social metadata,
structured data, sitemap, and llms.txt from the same validated records.
Sort deterministically. Use content or transformation identities for generated asset names.
Exclude drafts and private records consistently from navigation and discovery.
Keep Optimizer's authored inputs immutable when Builder integrates a revision.

## Verify the generated artifact

Run checklists/build.md B02 through B07 on rendered HTML.
Exercise quotes, ampersands, angle brackets, script terminators, rejected schemes,
empty and whitespace IDs, duplicate slugs, long copy, missing assets, and boundary dates.
Prove hostile text stays text, valid JSON parses, and unsafe actions are absent.
Add one representative record and inspect every derived surface.
Rebuild unchanged inputs twice and investigate output differences.

## Failure modes and sources

- Late validation: malformed data reaches templates before a meaningful error.
- Split state: badges and buttons each implement a separate date condition.
- Safe-looking source: only the template is checked while generated HTML is broken.
- Quiet omission: optional data disappears without an author-visible report.

Open the chosen template engine's escaping documentation, the URL API documentation,
and https://html.spec.whatwg.org/multipage/scripting.html for script parsing context.
Record source-opening evidence before relying on an implementation detail.
