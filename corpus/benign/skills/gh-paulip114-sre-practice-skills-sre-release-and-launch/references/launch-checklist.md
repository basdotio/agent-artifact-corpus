# Launch readiness checklist

Answer each question in writing; link evidence. Mark N/A with a reason.

## Architecture and dependencies
- [ ] Architecture diagram with request flow, data flow and every dependency.
- [ ] For each dependency: SLO, owner, what happens when it is down or slow, timeout and retry settings.
- [ ] No single points of failure (or they are documented and accepted).
- [ ] Data stores: replication, backups, restore tested (see `sre-data-reliability`).

## Capacity
- [ ] Expected launch traffic and 6–12 month growth estimate (incl. marketing events, client update waves).
- [ ] Load test result: per-task and per-cluster capacity, limiting resource.
- [ ] Provisioned for peak + loss of largest failure domain (e.g. N+2).
- [ ] Quotas reserved with downstream dependencies.
- [ ] Autoscaling min/max and signals reviewed; downstream impact of scaling considered.

## Failure modes
- [ ] Behavior under overload: sheds load / degrades gracefully, doesn't collapse.
- [ ] Deadlines set and propagated; retries bounded with backoff + jitter.
- [ ] Request criticality defined; batch traffic sheddable.
- [ ] Behavior on bad input / corrupt data defined.
- [ ] Failover tested.

## Client behavior
- [ ] Clients back off and jitter; no synchronized polling or wake-ups.
- [ ] Mobile/client releases can be throttled or killed server-side.

## Processes and automation
- [ ] Deploy, rollback, scaling, failover automated.
- [ ] Remaining manual procedures documented in runbooks.
- [ ] On-call rotation staffed and trained; escalation contacts listed.

## Development process
- [ ] Code review and CI tests required.
- [ ] Release pipeline with canary + control and automated rollback.
- [ ] Config changes reviewed, validated and canaried.

## External dependencies
- [ ] Third-party services: SLA known, fallback defined, contacts listed.

## Monitoring and alerting
- [ ] SLIs and SLOs documented and agreed.
- [ ] Burn-rate alerts configured (page + ticket).
- [ ] Golden-signal dashboards; deploys annotated.
- [ ] Black-box probes for critical user journeys.
- [ ] Every alert has a runbook.

## Security, privacy, abuse
- [ ] Security review complete.
- [ ] Privacy/data-handling review complete.
- [ ] Abuse and rate-limiting controls in place.

## Rollout plan
- [ ] Staged rollout plan with go/no-go criteria per stage.
- [ ] Feature flag / kill switch tested.
- [ ] Dark launch considered.
- [ ] Rollback tested end to end.
- [ ] Launch time chosen when the team is available (not before weekends/holidays).
- [ ] Communication plan (status page, support team briefed).
