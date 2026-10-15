# Target levels

Stored in the profile frontmatter as `target_levels` (one or more keys below) and `target_roles` (exact titles). The `target` operation shows them; `target staff director` replaces them (see the README for agent-specific invocation). With no level given, ask using the agent's question tool or plain text, allowing multiple selections. When the user has two targets (e.g. Staff IC and Eng Manager), each application uses the level that matches its JD, and the summary and bullet ordering change accordingly.

| Key | Pages | Summary leads with | Bullets lead with |
|---|---|---|---|
| `senior` | 1-2 | specialty and the systems built | what you built, scale, result |
| `staff` | 2 | specialty and cross-team scope | decisions that spanned teams, who adopted them |
| `principal` | 2 | the technical direction set across an org | org-wide strategy, standards, external standing |
| `manager` | 2 | team size and the product/area owned | team outcomes, hiring, delivery, people growth |
| `director` | 2 | org size, number of managers, business area | org outcomes, business metrics, the org you built |
| `vp` | 2 | org scale, budget, business results | company-level outcomes, strategy, exec partnership |
| `architect` | 2 | domain and the systems shaped | architecture decisions, platform adoption, cost/reliability |

## senior
Shows independent ownership of significant systems. Evidence: features or services owned end to end, production scale, on-call and reliability work, mentoring juniors, design docs written. Keep the stack visible in bullets.

## staff
Reviewers check four things: technical scope and impact, architectural direction across teams, leadership through influence (people mentored or promoted, standards set), and external signals (talks, OSS, patents). A resume strong only on the first reads as senior regardless of title. Bullet shape: scope + decision + measurable outcome + who adopted it ("Wrote the service-mesh design adopted by 6 teams; cut cross-service p99 by 35%"). Older roles compress to 1-2 bullets.

## principal
Staff signals at org or company scale, plus long-horizon bets: multi-year technical strategy, build-vs-buy calls with dollar impact, industry-facing work. A short "Selected technical initiatives" block under the summary is acceptable if the work spans several roles (still a standard heading-safe name: use it as a `## Projects` section).

## manager
Lead each role with scope: headcount, teams, product area, budget if owned. Then team outcomes (delivery, reliability, quality), hiring and retention numbers, people growth (promotions, new leads developed), process changes and their measured effect, and one or two bullets that prove technical credibility. Avoid "I built" for work the team built; "The team shipped X under my lead" or "Led the team that..." is honest and still strong.

## director
Number of managers and engineers, multi-team outcomes, the business metric the org moved (revenue, cost, uptime SLA, security posture, time to market), org design (what you reorganized and why), budget/vendor ownership, partnership with product, sales, and executives. Fewer technical details per bullet; still name the domain and stack in the summary or skills.

## vp
Org scale, budget, and company-level results first. Strategy that changed direction, building the org (from N to M, leadership hires), board or exec-level communication, M&A or major platform bets, security/compliance programs. Two pages; roles older than ~12 years get title lines only. Skills section can be short (domains plus key platforms).

## architect
For architect, platform, DevOps, and SRE roles: infrastructure scale (clusters, regions, nodes, rps, data volume), reliability (SLOs, incident rates, MTTR), cost (cloud spend cut, unit economics), platform adoption (teams onboarded, golden paths), security and compliance outcomes. The skills section matters more here; group it by Cloud, Orchestration, IaC, Observability, Security.
