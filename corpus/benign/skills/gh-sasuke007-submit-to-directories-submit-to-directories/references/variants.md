# Positioning variants by directory category

Adapt each description to the directory's audience and field limits. Rotate the opening
sentence and feature emphasis without inventing facts. Omit any placeholder the product
profile cannot support.

Use profile fields and verified site facts to fill relevant placeholders. Omit
unsupported sections. `{url_with_utm}` means a URL with
`utm_source=<directory-host>&utm_medium=directory&utm_campaign=listings` when accepted.

Pick the variant by the catalog entry's `category` field:

| category | variant | lead with |
|---|---|---|
| launch, startup | A — Launch | Outcome + origin energy |
| saas, general | B — SaaS | Category and use case; mention alternatives only when supported |
| ai | C — AI tool | AI-first architecture |
| agent | D — Agent/MCP | agent/MCP capabilities |
| review | E — B2B review | Use case and verified outcomes |
| dev | F — Dev / technical | technical depth, architecture, API |
| content, local, other | G — Neutral | short factual blurb, no hype |

---

## Variant A — Launch / startup directories

**Use for:** `category` in (launch, startup)

> {name} — {tagline}.
>
> {long_description_opening}
>
> What you get:
> • {feature_1}
> • {feature_2}
> • {feature_3}
>
> {founder_story}
>
> Try it: {url_with_utm}

**Launch-day first comment (ask for feedback, never upvotes):**
> Hey — we kept seeing {audience_pain}. {name} does {core_job}. Would love your take on
> {specific_question} — sample here, no signup: {proof_asset_url}

## Variant B — SaaS / alternative directories

**Use for:** `category` in (saas, general) and directories with an "alternatives to" field. Use competitor framing only when verified alternatives exist.

> {name} helps {audience} {core_job}. {short_description}
>
> • {benefit_1}
> • {benefit_2}
> • {benefit_3}
> • {benefit_4}
>
> {pricing_model} — {url_with_utm}

If the directory has an alternatives field and verified competitors are in the
profile, add them there. Do not insert competitor claims into the description
merely to fill this template.

## Variant C — AI tool directories

**Use for:** `category` == ai

> {name} is an AI-powered {category_keyword} for {audience}. {one_liner}
>
> What makes it AI-first:
> • {ai_capability_1}
> • {ai_capability_2}
> • {ai_capability_3}
>
> Use cases: {use_case_list}.
> {compliance_or_safety_line_if_applicable}

## Variant D — Agent / MCP registries

**Use for:** `category` == agent (skip if your product is not an agent/MCP — check `profile.not`)

> {name} — {tagline}.
>
> Capabilities: {capability_list}
> Auth: {auth_mechanism} · Transport: {transport} · Install: {install_command_or_url}
>
> Tools exposed: {tool_count_or_list}
> {url_with_utm}

## Variant E — B2B review platforms

**Use for:** `category` == review. A profile can be submitted before customer reviews; do not fabricate reviews or quantitative outcomes.

> {name} helps {audience} {core_job} without {pain_without_product}.
>
> Key benefits:
> • {outcome_1_if_verified}
> • {outcome_2}
> • {outcome_3}
> • {pricing_model} — {pricing_note}
>
> Best for {segment_list}, and for teams evaluating {alternatives}.

## Variant F — Dev / technical directories

**Use for:** `category` == dev

> {name} ({tagline}) — built for engineers.
>
> • Architecture: {architecture_note}
> • API / CLI / SDK: {api_note}
> • Open source / self-host: {oss_note_or_na}
> • Install: {install_snippet}
>
> Docs: {docs_url} · Repo: {repo_url} · Demo: {url_with_utm}

## Variant G — Neutral (content, local, everything else)

**Use for:** `category` in (content, local, other)

> {name} — {tagline}. {short_description}
>
> {one_liner}
>
> {url_with_utm}

---

## Tag pools (rotate; never repeat the exact 5–8 set twice in a row)

- **Job-to-be-done:** pull from `profile.tags`
- **Category:** your market keywords (e.g. recruiting automation, CRM, analytics)
- **Audience:** who it's for (e.g. SMB, enterprise, creators, developers)
- **Comparison:** "{competitor} alternative" tags where the directory allows them

## Do / Don't

- DO rotate the opening sentence every submission within the same variant.
- DO vary which 3 bullets appear.
- DON'T include anything from `profile.forbidden_claims`.
- DON'T claim categories in `profile.not`.
- DON'T claim reviews, ratings, or outcomes that have not been verified.
- DO verify the backlink after going live: `scripts/verify_backlink.sh <listing_url> <your-domain>`.
