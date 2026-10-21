# Production best practices (audit list)

A condensed audit list of practices that make services robust in production. Use it for
PRRs and periodic health reviews.

## Fail sanely
- Invalid or missing configuration: keep running with the last known good config, alert,
  and refuse to apply the bad one.
- Treat empty inputs to destructive operations as errors, never as "apply to all".
- Prefer fail-open vs fail-closed decisions made deliberately per component (security
  controls usually fail closed; content serving often fails open with degraded results).

## Progressive rollouts
- Every change (binary, config, data, schema) rolls out in stages with health checks.
- Rollback is fast, automated and practised.

## Define SLOs like a user
- Measure availability and latency as close to the user as practical.
- Agree on SLOs and an error budget policy with product.

## Error budgets
- Use the budget to balance reliability and velocity; freeze risky changes when it's gone.

## Monitoring
- Alert only on conditions that need immediate human action; everything else is a ticket
  or dashboard.
- Each alert has a runbook; review pages regularly.

## Postmortems
- Blameless, quantified, with tracked action items, widely shared.

## Capacity planning
- Provision for peak plus redundancy for planned and unplanned outages (e.g. N+2).
- Validate forecasts with load tests; plan for launches and organic growth.

## Overloads and failure
- Serve degraded responses under overload rather than failing.
- Bounded retries with backoff and jitter; retry budgets.
- Deadlines on all requests.
- Clients and servers both protect themselves (throttling, load shedding).

## SRE team practice
- Ops work ≤ 50%; the rest is engineering.
- On-call load bounded (a few incidents per shift at most).
- Dedicated interrupt handling; protect project time.
