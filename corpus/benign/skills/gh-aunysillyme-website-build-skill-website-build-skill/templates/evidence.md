# Claim and source evidence contract

Date rule: [ASK DATE and evidence provenance](../playbooks/research-and-memory.md#ask-date-rule).
This is a blank artifact contract. Fill it from actual inputs and evidence at runtime.
Unresolved required fields keep the relevant gate BLOCKED; never prefill a PASS.

## Library opening and scope

Every completed research Markdown file begins with Research as of the exact stored ASK DATE.
Apply the full derived-floor wording when only a lower bound is available.
This reusable contract is not a runtime research receipt.
Record the scope link, library revision, engagement identifier, producer role and actual family.

## Per-claim record

| Field | Required value and evidence |
| --- | --- |
| claim_id | Stable identifier referenced by decisions, checks and findings. |
| domain | One of the fourteen research domains, with additional scoped concerns as needed. |
| statement | Exact bounded claim, including relevant version, tier, consumer or use. |
| kind | Evidence, inference, proposed default, measurement, or UNVERIFIED. |
| source_url | Opened authoritative URL; a search snippet does not satisfy this field. |
| published | Source publication/update date and kind if visible, otherwise unknown. |
| source_date_proof | Supporting date text/location; never infer a date from footer, URL or HTTP header. |
| accessed | Actual opening date on or after ASK DATE within this engagement, or qualified derived floor. |
| opening_receipt | `research/library/receipts/<CLAIM-ID>.md` relative to `site-work/`, written at fetch time with the fields below. |
| precision | Exact date/timezone supplied, or exact access unavailable plus opening sequence and lower bound. |
| applicability | Brief, version, tier, jurisdiction or content scope that makes this relevant. |
| status | OPENED with a fetch receipt, otherwise UNVERIFIED. Record disputes and supersession separately. |
| dependents | Decision IDs, checklist IDs, role outputs and gate receipts relying on this claim. |

Preserve observations separately from interpretations.
A familiar fact without URL and actual access evidence fails AD03/AD04.

## Fetch receipt and ledger

For each cited claim, write `site-work/research/library/receipts/<CLAIM-ID>.md`
when fetching the page itself, never after the fact. Search snippets and memory
cannot support OPENED. Begin with the dated library opener, then plain fields:

```text
url: <exact claim row URL>
fetched_at: <environment UTC timestamp, YYYY-MM-DDTHH:MM:SSZ>
tool: <fetch tool actually used>
result: <HTTP status or tool outcome>
published: <date copied verbatim from excerpt text, or unknown>
excerpt: |
  <verbatim supporting page text, at least 80 characters>
```

Indent every excerpt line by two spaces. Optional fractional seconds use three
digits before Z. If a publication date appears elsewhere in quoted page text,
include that text in the excerpt too; absent date evidence means `unknown`.
Missing UTC timestamp evidence leaves the claim UNVERIFIED, never guessed.
Use this header in `sources.md` and stable `CLAIM-` IDs containing only letters,
digits, underscores and hyphens. Escape literal cell pipes with a backslash.

```text
| Claim ID | Domain | Statement | URL | Published | Accessed | Status | Dependents |
| --- | --- | --- | --- | --- | --- | --- | --- |
```

Published matches the receipt's published field exactly. Status is OPENED or
UNVERIFIED; `Verified` without a receipt is a gate failure. Use this checker ladder;
the five-rule manual equivalent is in checklists/research.md:

1. `website-build-skill check-library <root>/site-work`, when that command is on PATH.
2. Otherwise `npx -y website-build-skill@<packageVersion> check-library <root>/site-work`, where `<packageVersion>` is read from the installed `manifest.json`. Never write the literal version into prose, or it goes stale on every bump.
3. From a repository checkout: `node bin/website-build-skill.mjs check-library <site-work-dir>`.
4. When no rung can run, meaning no shell, no PATH command and npx fails or has no network: Reviewer records the five-rule manual equivalent. Also record each rung tried, with its command, exit code and output, as the reason.

For every rung that runs, save the command, exit code and output. PASS still needs exit 0 from a mechanical rung, or a recorded manual equivalent for rung 4. Acted-on UNVERIFIED claims still keep research acceptance BLOCKED.

## Reuse and expiry record

| Field | Required value |
| --- | --- |
| original_accessed | Historical opening date, never overwritten by a new stamp. |
| original_scope | Previous engagement ASK DATE and library revision. |
| window | Applicable domain/subclaim freshness window and earlier change triggers. |
| decision | Rechecked, reused within window, superseded, or blocked. |
| reason | Current applicability and why that decision fits the evidence. |
| current_access | Actual current-engagement opening receipt and access date. |
| revalidation | Result, revision/version, check date and method. |
| next_check | Concrete due date plus ASK DATE-relative expression computed with date tooling. |
| owner | Role responsible for refresh and downstream receipts to invalidate. |

## Disagreement record

Name competing claim IDs and opened sources, their dates and differences in scope.
Record the affected choice, evidence needed to resolve it, current disposition and owner.
Do not average contradictory claims or call an unresolved relied-on claim verified.

## Measurement record

Record artifact digest, route/state, environment, tool/version, exact inputs,
command/action, raw output, computed result, applicable criterion and limitation.
Keep external standard source evidence separate from the site's observed measurement.

## Gate result

Apply research AD01 through AD08; Reviewer later applies AD09 independently.
No web access means BLOCKED, including an old or freshly restamped library.
UNVERIFIED claims stay in unresolved-claims.md with a named next check and blocked decisions.
