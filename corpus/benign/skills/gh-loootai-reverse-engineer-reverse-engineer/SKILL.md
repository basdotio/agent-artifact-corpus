---
name: reverse-engineer
description: "Reverse engineer a product, feature, website, paid tool or go-to-market motion from the outside, from public evidence only, and explain how it works with every step tagged observed, inferred or unknown. Use when the user says: reverse engineer X, how does X work, how is X built, take X apart, what is X doing under the hood, figure out how they do it, how does this tool actually work, what does X need to work. Chains bounded-probe, site-teardown, evidence-research, competitor-diff and claims-audit, then lists what the mechanism needs as generic capabilities. For only a quick look at a site's pages, price and stack, use site-teardown."
---

# Reverse engineer

Take a product apart from the outside and write down how it works. Start small, read summaries first, keep what you saw apart from what you guessed, and list what is still unknown.

This is the orchestrator. It runs five other skills in a fixed order and adds two steps they do not cover: the mechanism, and a neutral list of what the mechanism needs. It stops at "how it works". The next skill, `rebuild-on-looot`, decides what to build.

## When to use

- "How does X really work", when the user wants the inside and not the sales page. X can be a paid tool, a feature or a data product.
- "What are they doing to get customers", when the target is a motion (a script, a list, a channel mix).
- Not for a quick look at one site. Use `site-teardown`.
- Not for a research brief on a company's size and stack. Use `evidence-research`.

`site-teardown` answers "how do they sell": pages, price, funnel, stack, ads. `reverse-engineer` answers "how does it function": a numbered mechanism and what it needs. It runs the teardown inside it.

## Inputs

- Target: a product name, domain, URL, feature name, or a description of the motion.
- The question: how does it work, or what are they doing to get customers. Default is how it works.
- Spend cap in USD. Default $0.50 for the whole run. Use 0 for a free-only run.
- Snapshot folder. Default `./reverse/<slug>-<YYYY-MM-DD>/` in the current project.

## Hard limits

Use public information only. If a step would need one of these, stop that step, say which limit blocks it, mark the step unknown and carry on.

- No logging in to an account you do not own, and no use of anyone else's credentials or tokens.
- No bypassing an access control, paywall, rate limit or bot block.
- No running untrusted code. Read public scripts as text. Never execute them and never load them in a live page.
- No scraping behind a login.
- Respect robots.txt and the terms of every page you fetch.
- No signing up, filling forms or sending anything to the target.
- No copying code, text, logos or screenshots into what you build. Facts and ideas are fine. Expression is not.
- No trademark confusion. Do not name or style the rebuild so it can pass as the original.
- No profiling of private individuals. Work facts about a company are fine.
- No paid looot calls when the user said no paid calls.

## The three tags

- observed: a source says it, or a looot run returned it. Cite the URL and the date read, or the run id.
- inferred: you concluded it from observed items. Name the items.
- unknown: nothing answers it. Say what would, and what it costs.

A third-party review, forum post or search summary never makes an item observed. Write it as unknown and add "reported by <source>". An absence (nothing found in a script, no ads in a library) is a miss, not proof.

## Phases

Run in order. After each phase, write its output to the snapshot folder (`00-scope.md`, `01-probe.md`, and so on) so a rerun skips what is done.

### Phase 0. Scope and budget (free)

1. Restate the target and the question in two lines.
2. Ask at most one clarifying question, and only if the target is ambiguous.
3. State the cap: "Cap $0.50, free reads first, I will ask before any step above $0.10."
4. Create the snapshot folder. If one exists for this slug, read it and resume.
5. Check `https://<domain>/robots.txt` and note what it disallows. Do not fetch disallowed paths.

Stop if the target is still unclear after one question, or the user declines the cap.

### Phase 1. Bounded probe (`bounded-probe`)

Pass in: the 3 to 5 cheapest looot calls that would show what data is reachable on the target (for example `job:web.site.map`, `job:web.scrape.markdown` on the pricing page, `job:company.technographics`, `job:company.enrich`), a probe cap of $0.05, and the success definition "returned usable text or fields".
Expect back: hit rate, cost per call, and a projected cost of phases 2 and 4.
Stop if the projection is above the cap. Report it and ask for a higher cap or a smaller scope.

### Phase 2. Site teardown (`site-teardown`)

Pass in: the domain, 40 percent of the cap, and "skip steps the probe already paid for".
Expect back: site map, positioning, pricing, tech stack, hiring, ads, search footprint, each tagged.
Stop if the teardown's own quote is above its share, or the site shows only a login wall.

### Phase 3. Mechanism (no other skill covers this)

Work out how the product functions from public evidence only. Read in this order, and stop when the flow is clear:

1. Public docs and API reference.
2. Help centre and changelog.
3. Pricing units (per seat, per credit, per resolution). The unit often names what the system counts.
4. Public client-side scripts, read as text, and only when the vendor serves them to every visitor.
5. Network endpoints named in the docs or in those scripts.
6. Integrations list.
7. Job ads that name the stack (reuse the phase 2 result).
8. Privacy policy and subprocessor list. These often name the data suppliers.
9. Status page components. Each component is often a subsystem.

Read pages with `job:web.scrape.markdown` or a plain GET. When a script is obfuscated, you may decode text encodings such as base64 with a tool that only transforms text. Do not run the script.

Output a numbered flow from input to output, one line per step:

```
1. <what happens>. [observed] <URL, date read | run id>
2. <what happens>. [inferred from 1 and 4] <items>
3. <what happens>. [unknown] settled by <cheapest check, price>
```

Stop a step that needs a login, an access-control bypass or running code. Mark it unknown and move on.

### Phase 4. Evidence research (`evidence-research`)

Pass in: the unknown steps from phase 3 turned into questions, and 30 percent of the cap.
Expect back: a ledger row per question, tagged, with run ids and cost.
Cheapest call first. One call per question. Never repeat an identical call.

### Phase 5. Snapshot (`competitor-diff`)

Pass in: the domain and the watch items (pricing page text, home page headline, open roles, tech stack, ads, rank for up to 5 terms). Reuse phase 2 answers as the snapshot where they match, so nothing is paid twice.
Expect back: a dated snapshot. If an earlier one exists, a list of what changed. If not, say "baseline saved".

### Phase 6. Claims audit (`claims-audit`)

Pass in: the whole draft report, the audience, and 10 percent of the cap.
Expect back: each claim marked confirmed, contradicted or unknown.
Downgrade or remove any claim no source backs. Never keep an inferred item worded as observed. List the unknowns left, each with the cheapest call that would settle it.

### Phase 7. What the mechanism needs

For each mechanism step, name the kind of data or capability it depends on. State it generically and propose no solution. Examples: "IP to company lookup", "hashed email from a cookie network", "LinkedIn post engagers", "email verification".

One row per step: step number, capability, tag inherited from the step. Merge steps that need the same capability.

This list is the input to `rebuild-on-looot`. Checking the looot catalog against it is that skill's job. Do not recommend building anything here.

### Phase 8. Report

Write `<snapshot folder>/report.md` in this order:

1. One-page summary: what it is, how it works in five lines, what is observed versus unknown.
2. Mechanism flow, tagged.
3. Evidence ledger: claim, tag, source or run id, confidence.
4. What the mechanism needs.
5. Unknowns, each with the cheapest call to settle it and its price.
6. Spend: total against cap, calls made, split by phase.
7. Snapshot path.

Keep the summary to one page.

## Running only some phases

Say it in the request and follow it.

- "Mechanism only": phases 0, 3, 7 and 8. Free reads, no spend.
- "No paid calls" or a cap of 0: skip 1, 2, 4 and 5. Run 0, 3, 7 and 8 with plain GETs of public pages. Mark every step that needed a paid job as unknown and give its price.
- "What it needs only": needs a mechanism. If none is saved, run phase 3 first.
- "Just check what changed": phase 5 only.

Always keep phases 0 and 8. Keep phase 6 before 8 if any claim came from memory.

## The looot flow every paid call follows

1. Find the job. `search_catalog` (MCP) or `GET https://api.looot.ai/v1/public-catalog?q=<words>` (no sign-in) and confirm the job id.
2. Quote. `inspect` shows the exact input names, the price formula and the maximum cost. It is free and needs a sign-in. With no sign-in, use the public catalog price. There is no dry-run call. Inspect is the quote.
3. Tell the user the number. Ask for a yes above $0.10 or above 100 calls.
4. Run with a fresh `idempotencyKey` such as `<slug>-p<phase>-<n>-<date>`, `fallback: true` on a job id, and `maxCostUsd` at twice the quoted price. Retry the same call with the same key. The same key with a different input returns `409 idempotency_conflict`, so use a new key for a new input.
5. Read `status`, `outcome` and `actualCost`, not only the HTTP code. `queued`, `running`, `pending_provider` and `reconciliation_pending` mean pending, not failed.
6. Keep a running total and check it against the cap before each phase.

## Failure handling

- Miss or empty: say so, try `fallback` once, mark unknown. No retry loops.
- Two errors in a row in a phase: stop the phase, report the error text, continue with the next.
- Login wall, bot block, or terms that forbid the read: mark unknown, name the limit, do not work around it.
- Providers disagree: show both values with run ids, tag unknown, do not average.
- 402: show the top-up link (minimum $5). Never pay for the user.
- Over cap mid-run: stop, write what is done, list what is left and its price.
- Cost above the quoted maximum: stop and send `feedback` with the run id.
- Two sources conflict (two prices, two reviews): keep both, tag unknown, say which one is first-party.

## Example

Ask: "reverse engineer a website visitor identification tool, how does it identify visitors?" A free-only run read the vendor's pricing page, support pages and public script as text.

```
1. A visitor loads a page that carries the vendor's script. [observed] vendor home page source, read 2026-10-11
2. The script checks consent and location with a call to a geo lookup service. Visitors outside the US get no person-level attempt. [observed] script text
3. It asks three third-party services, with the visitor's own cookies, for a hashed email. The owners of two of them are unknown. [observed that it asks; owners unknown]
4. It posts the hashes, cookie ids and page URL to the vendor's server. [observed]
5. The server turns a hashed email into a name, LinkedIn URL and work email. [inferred] the server side is not public
```

What the mechanism needs: IP to country with a proxy flag (step 2, observed). Hashed email from a cookie network (step 3, observed). Hashed email to person and work email (step 5, inferred). The full write-up is in `examples/rb2b-to-looot-reveal.md`.

## Output rules

Plain words, sentence case, short sentences. No em dashes. No hype. Every number has a source or a run id.
