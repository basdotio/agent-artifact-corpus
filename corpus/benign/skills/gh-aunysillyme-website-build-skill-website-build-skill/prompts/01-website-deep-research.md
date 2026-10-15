ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Deep Research prompt to make your agent good at building websites:

Become good at full-stack website building for this user's actual request.
Act as Researcher, the first job in both TEAM and SOLO. Research, then learn,
ingest, then execute. No other role works until your research library gate passes.
Use web search and opened sources current as of the ASK DATE, not this package's
publication date. This prompt is your primary instrument; own the graphics archive
as a research source too, never as an active instruction to its historical path.

STANDARDS
- Search for every dated claim. Never answer one from training memory.
- Every claim carries a source URL, a publication/update date (unknown if absent),
  and an actual access date on or after the ASK DATE inside this engagement.
- Every output file opens with "Research as of <ASK DATE>".
- Where sources disagree, record the disagreement. Never average it.
- Mark anything unverified as UNVERIFIED.
- Write `site-work/research/library/receipts/<CLAIM-ID>.md` at page fetch time,
  never afterward. Follow templates/evidence.md for every field and the verbatim
  supporting excerpt of at least 80 characters. Never mark a claim OPENED from
  memory or a search snippet; only a fetched page with a receipt qualifies.
- Open each cited source. Prefer standards, official docs, original research, and
  real code. Record source publication/update date and the actual access date separately.
- Separate evidence, inference, proposed defaults, and observed project measurements.
- Research outputs are Markdown. All paths below are relative to
  site-work/research/library/ in the user's agreed project, never this skill package.

RESEARCH THESE 14 AREAS
1. Reference codebases and real implementations.
   Questions: open real repositories and read the entrypoints, routes, templates,
   data models, build scripts, tests, and deploy configuration. Which patterns recur
   in well-built sites as of the ASK DATE? What is minimal for this brief, and what is over-built?
   Compare a no-build site, a scripted static site, and an application where useful.
   Record repository URL, inspected revision, exact file links, license, and the
   behavior the code actually implements. Reading a README alone is not inspection.
   Artifact: 01-codebases-and-stacks.md, domain 1 implementation comparison and
   inspected-file ledger; checklists/01-codebases.md with reuse and complexity checks.
2. Stacks and frameworks.
   Questions: which current versions and APIs fit this brief? What changed recently,
   what is deprecated, what are the browser/runtime support and upgrade costs, and
   what does each stack actually do well? When is no framework the right answer?
   Include data-plus-template publishing, tests, content ownership, localization if
   needed, integrations, and maintenance. Do not select a stack before a mockup.
   Artifact: 01-codebases-and-stacks.md, domain 2 dated comparison and migration
   notes; checklists/02-stacks.md mapping every proposed layer to a requirement.
3. Design.
   Questions: inspect award-winning sites from the last two to three years relative
   to the ASK DATE, the award criteria, and the actual live work. What wins and
   why does it work for its audience? Study grids, whitespace, type pairing/scales,
   color systems, tokens, message hierarchy, and copy-visual relationships.
   Look past the generic AI template; visit threejs.org examples to see what a browser
   can really do. Evaluate capability, interaction cost, and a simpler alternative.
   Go deepest on translating a brief into concrete visual choices. Go deep on taste
   and critique, and on brand-kit extraction: observed, inferred, and approved rules.
   Artifact: 02-design-and-experience.md, domain 3 case studies and decision rubric;
   how-to-read-a-brand-kit.md; checklists/03-design.md with brand and mockup tests.
4. Graphics skills.
   Questions: what can current image tools actually create or edit, at what pricing,
   and with which COMMERCIAL RIGHTS PER TIER? Verify the exact product/tier's terms,
   inputs, outputs, attribution, redistribution, and relevant exclusions separately.
   What are the social/link-preview sizes and safe zones as of the ASK DATE? Study
   formats, vector versus raster, compression, responsive crops, export hygiene,
   icon consistency, font embedding/subsetting, and stock licensing. Inspect output.
   Use archive/graphics-design-original.md as the archived source of this domain;
   learn its standards and deep areas without executing its historical SAVE paths.
   Artifact: 03-graphics-and-rights.md, domain 4 tool/tier/rights matrix and format
   specifications; checklists/04-graphics.md with export, crop, and rights gates.
5. UI and UX.
   Questions: what interaction and navigation patterns fit the site's main task?
   Research forms, validation, empty/error/loading/success states, recovery, motion
   and when it hurts, mobile/touch behavior, content hierarchy, and localization.
   What do observed users actually do versus designer assumptions? Distinguish
   usability evidence from taste and hypotheses; specify tests for unknown behavior.
   Artifact: 02-design-and-experience.md, domain 5 journey/state matrix and evidence
   limits; checklists/05-ui-ux.md with primary-task and recovery scenarios.
6. Accessibility.
   Questions: what is the current WCAG version and applicable target level? Which
   criteria cover this project's content and controls? Compute contrast instead of
   eyeballing it; identify thresholds by actual text/control context. Research
   keyboard paths, visible/restored focus, screen-reader semantics, reduced motion,
   touch targets, reflow, media alternatives, and manual versus automated testing.
   Artifact: 04-accessibility-and-performance.md, domain 6 criteria/test matrix;
   checklists/06-accessibility.md naming calculator inputs and manual journeys.
7. Performance.
   Questions: what are the current Core Web Vitals thresholds, measurement windows,
   device segmentation, and lab-versus-field limits? Which image formats, responsive
   sizing, loading priorities, font strategy, caching, and third-party costs affect
   this site? What interventions have measured effects rather than score folklore?
   Include network/CPU constraints, realistic route budgets, and repeatable runs.
   Artifact: 04-accessibility-and-performance.md, domain 7 dated measurement plan
   and budget proposals; checklists/07-performance.md with tools and evidence fields.
8. SEO.
   Questions: what is the current documented indexing/ranking behavior relevant to
   these pages? Which structured-data types are supported by which consumers and
   validators? Research crawlable HTML, canonical/redirect behavior, robots rules,
   sitemaps, internal linking, search intent, content quality, and site migrations.
   What can a small site realistically win? Distinguish documented eligibility,
   observed indexing, and speculative ranking claims; promise none as guaranteed.
   Artifact: 05-search-and-answers.md, domain 8 route/discovery requirements and
   validator map; checklists/08-seo.md with rendered-page and live-response checks.
9. AEO and AI citation.
   Questions: as of the ASK DATE, how do answer engines select and cite sources, and which parts
   are documented, experimentally observed, or unknown? Study answer-first and
   standalone-quotable structure, provenance, entity graphs, and source freshness.
   What is the current state of the llms.txt proposal, actual adoption evidence,
   and AI crawler behavior? Separate training, search, and user-triggered retrieval
   where sources distinguish them. Do not infer citation from crawler access.
   Artifact: 05-search-and-answers.md, domain 9 evidence/uncertainty table, entity
   guidance, and crawler policy options; checklists/09-aeo.md with parity tests.
10. Security.
    Questions: what headers and exact CSP syntax does each candidate host use for
    static, dynamic, redirect, and error responses? Which current attack classes
    apply to this site's inputs, dependencies, forms, auth, payments, or uploads?
    Study context-safe rendering of fallible data, script-bound JSON, URL schemes,
    secret boundaries, authorization, supply-chain exposure, and scanner grading.
    Record what a grade cannot prove; verify functionality with the policy enforced.
    Artifact: 06-security-and-delivery.md, domain 10 threat/surface matrix and dated
    host syntax; checklists/10-security.md with adverse cases and response checks.
11. Hosting, deploy and DNS.
    Questions: which current platforms fit, with what configuration/header syntax,
    build commands, preview isolation, rollback, runtime limits, and free-versus-paid
    conditions? Research custom domains, DNS records/TTL/propagation, HTTPS, redirects,
    caching, environment separation, monitoring, backups, and recovery where needed.
    Include commercial-use restrictions and ongoing maintenance costs. Do not create
    accounts, alter DNS, incur charges, or deploy while researching these options.
    Artifact: 06-security-and-delivery.md, domain 11 host comparison and release/
    recovery plan; checklists/11-hosting.md with domain, preview, and rollback tests.
12. Measurement.
    Questions: how should analytics and search consoles be set up for this project?
    What primary action, event taxonomy, conversion path, and receiving property
    should be checked? Research delivery verification, consent/data minimization,
    retention, sampling, bots, attribution, small samples, and field-data lag.
    What can each number tell us, and what causal claim cannot follow from it?
    Include an owner and cadence for checking results and instrumentation failures.
    Artifact: 07-measurement-and-operations.md, event plan and interpretation limits;
    checklists/12-measurement.md with receiving-property proof and privacy checks.
13. Legal, kept light.
    Questions: which font and stock licenses cover the intended use and redistribution?
    What commercial rights and restrictions apply to the exact AI imagery tool/tier,
    and what remains uncertain about generated content or trademarks? Identify
    jurisdiction-specific privacy/consent or commerce questions only where the brief
    makes them relevant, cite authoritative sources, and refer unresolved legal
    determinations to the owner or qualified adviser. Do not claim legal clearance.
    Artifact: 03-graphics-and-rights.md, domain 13 rights ledger requirements and
    unresolved questions; checklists/13-legal.md with evidence and escalation paths.
14. Languages and coding practice.
    Questions: as of the ASK DATE, which current HTML semantics and elements fit
    this project? Which CSS layout features, container queries, cascade layers, and
    nesting patterns fit its browser targets, and what is each feature's Baseline
    status? Which JavaScript and TypeScript language features, module format, and
    build or bundling defaults suit the selected versions? What idioms, deprecated
    APIs, and upgrade notes apply to the chosen framework version? Research unit,
    integration, and end-to-end testing; linting, formatting, and type-checking;
    lockfiles, version pinning, dependency audits, and minimal dependencies; secure
    template and script escaping, URL validation, and keeping inline secrets out
    of code; and code organization and review. Use primary sources: MDN, web.dev
    Baseline status, WHATWG and W3C specifications, TC39 finished proposals,
    TypeScript release notes, and official runtime, tooling, and selected-framework
    documentation and changelogs. Verify support separately from proposal status.
    Artifact: 08-languages-and-code.md, domain 14 dated language/support matrix and
    coding guidance; checklists/14-code.md with version, quality, and secure-code checks.

SAVE THE RESULTS - two places, both required:
A. Markdown files in site-work/research/library/:
   - Write the eight grouped domain files named above, with all fourteen sections.
     Survey every domain; mark genuinely inapplicable project checks with reasons.
     Extend these domains for databases, auth, payments, content workflows,
     internationalization, testing, privacy, or operations when the brief needs them.
   - README.md: index, headline findings, reading order by role, and current revision.
   - scope.md: ASK DATE, ladder rung, raw evidence and precision first, then supplied
     request, audience/action, constraints, tool access, missing inputs and domain
     applicability. Research-only assumptions may describe scope, never the date.
   - coverage.md: each domain, group file, checklist, applicable questions, source
     coverage, exclusions with reasons, blockers, and downstream owners.
   - sources.md: use the exact Claim ID, Domain, Statement, URL, Published, Accessed,
     Status, Dependents table from templates/evidence.md. Status is OPENED with a
     receipt or UNVERIFIED without one. Keep applicability in the per-claim record.
     Unknown source dates say unknown; the actual access date is still required.
     Never invent a publication date. Each known date must appear in its receipt excerpt.
   - receipts/<CLAIM-ID>.md: one fetch-time receipt for each cited claim's opened
     source, with url, fetched_at, tool, result, published and excerpt.
   - disagreements.md: competing claims and dated sources, affected decision,
     evidence needed to settle it, and current disposition. Never average claims.
   - query-plan.md and unresolved-claims.md: searches, unanswered questions, missing
     sources/tools, affected decisions, and a named next verification action.
   - checklists/01-codebases.md through checklists/14-code.md: exact filenames
     named above. One checklist per domain, with criterion, method, expected evidence,
     source claim IDs, assigned downstream owner, PASS/FAIL/BLOCKED/NOT APPLICABLE,
     and a reason for exclusions. These are applied checks, not remembered prose.
   - website-qa-checklist.md: blockers first, then quality scoring; link every domain.
   - how-to-read-a-brand-kit.md: sources in, observed/inferred/approved rules and
     concrete type, color, spacing, imagery, and motion decisions out.
   - surprises.md: a short user-facing summary of the most surprising findings,
     each linked to a claim ID and its practical consequence for this site.
   - staleness.md: the canonical fourteen-domain freshness table from
     playbooks/research-and-memory.md, then claim/domain, ASK DATE, window, original
     access, last revalidation, next-check date, reason, owner and dependent receipts.
     Identify the earliest-expiring domain, its window, and its ASK DATE-relative due date.
     Recheck fast-moving pricing, rights, APIs, host syntax, crawler and search claims
     on the day they will be used. Older durable principles still need applicability.
   - learning.md: what you learned, source files opened, applicable checklist IDs,
     changed assumptions, and how you ingested the rules for this project's handoff.
   - memory-proposal.md and memory-receipt.md: the second save destination's proposal
     and actual result. A proposal is not a completed save.
B. Your memory: propose durable rules and the library location, then save through
   the platform's supported memory or project-instruction mechanism only within
   existing user authorization. Include current-source research, computed contrast,
   three mockups, smallest justified stack, per-tier rights, independent review,
   and the refresh schedule. Keep volatile facts in the library, not timeless rules.
   Record the exact destination and read-back evidence in memory-receipt.md after
   a supported save. Otherwise record pending, unsupported, or declined; return the
   proposal for the user to save or reattach. Never call session context durable.
   Coordinator later consolidates authorized rules into site-work/MEMORY.md without
   changing your library. It cannot turn an unexecuted memory save into a success.

RESEARCH GATE
Apply checklists/research.md AD01 through AD08 and the canonical ASK DATE rule;
record allowed rung/raw evidence, two-date claim coverage, matching openers,
earliest expiry and per-claim reuse decisions. Use this checker ladder; the
five-rule manual equivalent is in checklists/research.md:

1. `website-build-skill check-library <root>/site-work`, when that command is on PATH.
2. Otherwise `npx -y website-build-skill@<packageVersion> check-library <root>/site-work`, where `<packageVersion>` is read from the installed `manifest.json`. Never write the literal version into prose, or it goes stale on every bump.
3. From a repository checkout: `node bin/website-build-skill.mjs check-library <site-work-dir>`.
4. When no rung can run, meaning no shell, no PATH command and npx fails or has no network: Reviewer records the five-rule manual equivalent. Also record each rung tried, with its command, exit code and output, as the reason.

For every rung that runs, save the command, exit code and output. PASS still needs exit 0 from a mechanical rung, or a recorded manual equivalent for rung 4. Acted-on UNVERIFIED claims still keep research acceptance BLOCKED.

Independent AD09 runs
before ship with live re-fetches of the required acted-on source sample.
The library exists on disk, every domain this project touches has a substantive
file and checklist, and every claim that will be acted on carries an opened source
URL, a publication/update date or explicit unknown, and an access date on or after the ASK DATE. Apply checklists/research.md from the skill and the coverage matrix.
UNVERIFIED actionable claims block their dependent decisions. Missing coverage or
unsaved library blocks all downstream work; do not replace a missing test with prose.
A pending optional memory save does not pretend to be done or erase a valid disk save.
If you cannot search, say so, produce the query plan and unresolved-claim ledger,
and leave current research BLOCKED. If you cannot write, return the named file bodies
for the user to save and reattach, then read them back before passing the disk gate.
Return a templates/handoff.yaml receipt to Coordinator; after its acceptance, every
other role reads its named library files first, learns the checklists, and tops up
only its own domain. Send stale/wrong claims back to Researcher for correction.

When done, report the most surprising findings and ask for still-missing audience,
main action, colors, fonts, and logo. If there is no brand kit, request profile-picture
and banner screenshots. Hand off the library; Designer later produces the three
mockups after learning it. Do not skip the learning step in SOLO.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
