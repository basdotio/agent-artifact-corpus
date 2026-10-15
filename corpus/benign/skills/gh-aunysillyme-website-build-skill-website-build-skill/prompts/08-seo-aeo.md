ASK DATE prerequisite: follow playbooks/research-and-memory.md#ask-date-rule.
Researcher establishes it before intake or research; later roles read scope.md.
Never ask the user for the date or infer it from model knowledge. Apply the
same source, two-date, freshness, reuse, and blocked-gate rules to this stage.

Research and implement discoverability for this site's actual audience and content.
First require accepted research and read site-work/research/library/README.md,
05-search-and-answers.md, 07-measurement-and-operations.md, and their domain checklists.
Use the areas below only to top up Optimizer's questions against that library; send
stale or wrong claims back to Researcher before dependent decisions.
Use SEO and answer-engine practices with evidence, not guarantees about ranking.

STANDARDS
- Search the web for every dated claim (tool capabilities, pricing, licensing, trends,
  platform specs). Never answer those from training memory.
- Every claim gets a source URL, publication/update date (unknown if absent), and
  an actual access date on or after the ASK DATE. Open every output file with
  "Research as of <ASK DATE>".
- Where sources disagree, record the disagreement - never average it.
- Mark anything you could not verify as UNVERIFIED.

RESEARCH THESE 8 AREAS
1. Audience questions and page intent - what someone should learn or do on each route.
   Go deepest here. Do not make keyword lists substitute for useful answers.
2. Crawlability - initial HTML, robots rules, status codes, canonical URLs, sitemap,
   redirects, pagination if relevant, and intentional exclusions.
3. Entity modeling - truthful identities, stable IDs, ownership, and page relationships.
   Go deep here too. Pick schema types that fit the site rather than copying a graph.
4. Answer extraction - standalone answer-first sections, clear headings, attribution,
   dates where meaningful, and visible evidence behind factual claims.
5. Structured data - current vocabularies, current consumer support, and exact parity
   between visible content and markup. Never equate valid schema with rich-result eligibility.
6. Discovery files - a data-derived sitemap and llms.txt; IndexNow only where supported
   and authorized. Identify what each consumer actually documents.
7. Social previews - per-route initial metadata, stable image URLs, actual dimensions,
   and the difference between an origin response and a third-party cache.
8. Measurement - indexing evidence, search-console access if provided, CWV, and what
   cannot yet be measured on a new site. Separate traffic from crawler availability.

SAVE THE RESULTS - two places, both required:
A. site-work/research/optimizer/:
   - README.md - current findings and decisions
   - sources.md - claims, URLs, dates, disagreements, unresolved items
   - route-map.md - intent, canonical URL, status, schema, sitemap membership
   - qa-checklist.md - checks that run against rendered HTML and live responses
   - memory-receipt.md - durable save result or pending manual save
B. Your memory: save the durable rules and research location through an authorized,
   supported mechanism. Remember truthful schema, generated discovery files,
   answer-first copy, and re-verification of dated search claims.
   If memory is unavailable, write site-work/research/optimizer/memory-proposal.md
   for Coordinator to consolidate into site-work/MEMORY.md for saving or reattachment. Never claim automatic persistence.

APPLY
- Test intended-public routes and deliberate exclusions against the route map.
- Use Person, Organization, and ProfilePage only where the visible facts fit.
- Add FAQPage only for actual visible questions and answers when appropriate.
- Do not promise Google FAQ rich results; verify current Google support first.
- Treat llms.txt as navigation assistance, not a proven ranking requirement.
- Do not add AI-blocking metadata by default; respect an explicit owner policy.
- Own site-work/optimization/route-map.json, metadata.json, structured-data.json,
  answers.md, llms.txt, and sitemap.xml as the discovery inputs. Validate them.
- Builder alone integrates these inputs into implementation paths and generates the
  deployable HTML, sitemap, and llms.txt. Request changes through a handoff, never
  edit Builder's source directly. Revalidate the actual rendered candidate afterward.
- Save implementation evidence to site-work/qa/seo-aeo.md.

When done, report the most surprising findings and ask for any missing owner-approved
identity, audience questions, canonical domain, or content needed to make the graph true.

EVIDENCE
Never report a measured, saved, installed, or deployed result without evidence.
Apply the stage route and named checks in manifest.json before handing off.
