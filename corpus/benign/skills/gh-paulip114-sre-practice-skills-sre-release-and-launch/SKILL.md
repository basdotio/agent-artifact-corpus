---
name: sre-release-and-launch
description: Use when designing how code and config reach production (hermetic builds, progressive rollouts, canary analysis, rollback, config validation, reliability testing) or preparing a service or feature for launch (launch checklist, production readiness review, SRE engagement). Based on Google SRE practice.
---

# Releases, Canarying and Launch Readiness

Change is the biggest source of outages. Make each change small, gradual, observable and reversible, and make launches repeatable and boring.

## Releases, Canarying and Configuration

Change is the biggest source of outages. Make change small, gradual, observable and reversible.

### Release engineering principles

- **Self-service** — teams release on their own cadence through a shared, automated pipeline.
- **High velocity** — frequent small releases are easier to debug and roll back than big ones.
- **Hermetic, reproducible builds** — same inputs give the same binary regardless of machine; pinned toolchains and dependencies.
- **Enforced policy** — code review, who may release, which tests must pass; all audited.
- Every release is identifiable (version visible in monitoring) and **rollback is one command**, tested regularly.

### Canarying procedure

A canary exposes a small part of production to the change and compares it against a control before going further.

1. **Choose the population**: small enough to limit damage, big enough to give signal. Representative of real traffic (regions, client types).
2. **Run a control** of the same size on the old version at the same time, so traffic patterns affect both equally. Comparing against the rest of the fleet or against "yesterday" gives noisy results.
3. **Choose evaluation metrics**: SLIs (errors, latency) plus a few health signals (crashes, CPU/memory). Prefer few, well-understood metrics; too many guarantee false alarms. Metrics should be attributable to the canary population.
4. **Choose duration**: long enough to cover warm-up and representative load; consider time-of-day effects. Faster stages for low-risk changes, slower for high-risk.
5. **Define pass/fail before starting** (e.g. canary error ratio not worse than control by more than a set margin).
6. **Stage the rollout**: e.g. 1% → 10% → 50% → 100%, with evaluation at each stage; don't spread to many failure domains at once.
7. **Automate the decision** where possible, with automatic rollback on failure.
8. **One change per canary.** Don't canary multiple changes together; you won't know which caused a regression.

Why it matters for tight SLOs: a 1% canary that breaks everything it touches burns budget ~100× slower than a full rollout, buying time to react.

Also canary **configuration pushes, flag flips, schema changes and infrastructure changes**, not just binaries.

### Configuration design

- Separate **configuration philosophy** (what the user is asked to decide) from **mechanics** (language, storage, delivery).
- Ask users for as little as possible; provide good **defaults** and make the simple case simple.
- Treat config as code: version control, review, tests, staged rollout, rollback.
- **Validate** syntactically and semantically before push (types, ranges, references exist, would this drop capacity below N?). Validation must reject empty/missing values rather than treat them as "all".
- Prefer config languages that support abstraction and checks (e.g. Jsonnet, CUE) over sprawling copy-pasted YAML once complexity grows; keep evaluation hermetic and side-effect free.
- Make the effective config **observable** at runtime (introspection endpoint), and diffable against last known good.
- Guard against catastrophic edits: caps on % of fleet or capacity a single push can affect.

### Testing for reliability

- **Unit and integration tests** in CI; **system tests** (smoke, performance, regression) before release.
- **Production tests**: probers that continuously exercise critical journeys; config tests that verify production config matches what's checked in.
- **Load/stress tests** to find breaking points (`sre-capacity-and-system-design`).
- **Disaster and failure-injection tests** to prove failover and recovery work.
- Test the **rollback** path, not just roll-forward.

### Review checklist for a release process

- [ ] Builds hermetic and reproducible; artifacts versioned and signed?
- [ ] Rollout progressive with automated canary analysis and a control?
- [ ] Rollback one step, tested, fast?
- [ ] Config changes go through the same pipeline and validation?
- [ ] Releases avoided at times with poor coverage (weekends/holidays) unless on-call is staffed?
- [ ] Version and config visible in monitoring and annotated on dashboards?

## Launch and Production Readiness

Launches are where new failure modes enter production. A repeatable checklist and a clear engagement model make them boring.

### Launch coordination

Assign a **launch coordinator** (Google calls them Launch Coordination Engineers) who owns the checklist, involves the right teams early, and has authority to delay launches that aren't ready. Size the process to the risk: a small UI change doesn't need the full review a new service does.

Work through `references/launch-checklist.md` with the owning team. Typical areas:

- **Architecture and dependencies** — request flow, every dependency, what happens when each one fails or is slow; no hidden single points of failure.
- **Capacity** — expected load at launch and growth, load tests, provisioning for peak plus loss of a failure domain, quota with dependencies.
- **Failure modes** — behavior under overload, partial failure, bad input; graceful degradation path.
- **Client behavior** — retries with backoff and jitter, no synchronized polling, rate limits.
- **Processes and automation** — deploy, rollback, scaling and failover automated; manual steps documented.
- **Development process** — code review, tests, canarying (*Canarying procedure* above).
- **External dependencies** — third parties with SLAs, fallback if they fail.
- **Monitoring and alerting** — SLIs/SLOs defined, alerts routed, dashboards built, runbooks written (`sre-slos-and-error-budgets`, `sre-monitoring-and-alerting`).
- **Security and privacy** — reviews done, data handling, abuse prevention.
- **Rollout plan** — gradual (feature flags, staged %), dark launch where useful, a tested rollback and a kill switch.

### Launch techniques that reduce risk

- **Gradual, staged rollouts** with go/no-go evaluation at each stage.
- **Feature flags** to decouple deploying code from enabling behavior.
- **Dark launches**: send real traffic to the new path without showing results to users, to test load and correctness.
- **Plan for overload and "thundering herds"** at launch time (marketing events, client auto-updates hitting simultaneously).

### Production Readiness Review (PRR)

Before SRE (or any ops-owning team) takes on a service, review it against production standards:

1. **Engage early** — ideally in design, when changes are cheap. Late engagement means retrofitting reliability.
2. **Scope** the service: purpose, architecture, dependencies, traffic, SLOs, current ops burden.
3. **Assess** against the checklist and the best-practice list in `references/production-best-practices.md`: monitoring, alerting, capacity, change management, failure handling, documentation, toil.
4. **Produce a gap list** with owners and priorities; the development team fixes blocking gaps before handover.
5. **Onboard** gradually: shadow on-call, then joint on-call, then full ownership.
6. **Keep an exit path**: if a supported service's operational load grows unacceptable (ops > 50%, repeated SLO misses without fixes), hand pager responsibility back to developers until it's fixed.

### Engagement models

Not every service needs full SRE ownership. Options range from:
- Consulting and design reviews only.
- Shared frameworks/platforms that are reliable by default (the most scalable way to spread practice).
- Embedded SRE for a period to fix specific problems.
- Full ownership of on-call and operations for critical services.

Choose based on criticality, SLO, operational load, and team capacity; review periodically.

## Sources

- SRE book ch. 8 Release Engineering — https://sre.google/sre-book/release-engineering/
- SRE book ch. 17 Testing for Reliability — https://sre.google/sre-book/testing-reliability/
- Workbook ch. 14 Configuration Design and Best Practices — https://sre.google/workbook/configuration-design/
- Workbook ch. 15 Configuration Specifics — https://sre.google/workbook/configuration-specifics/
- Workbook ch. 16 Canarying Releases — https://sre.google/workbook/canarying-releases/
- SRE book ch. 27 Reliable Product Launches at Scale — https://sre.google/sre-book/reliable-product-launches/
- SRE book ch. 32 The Evolving SRE Engagement Model — https://sre.google/sre-book/evolving-sre-engagement-model/
- SRE book Appendix B Best Practices for Production Services — https://sre.google/sre-book/service-best-practices/
- SRE book Appendix E Launch Coordination Checklist — https://sre.google/sre-book/launch-checklist/
- Workbook ch. 18 SRE Engagement Model — https://sre.google/workbook/engagement-model/
- Workbook ch. 19 SRE: Reaching Beyond Your Walls — https://sre.google/workbook/reaching-beyond/
