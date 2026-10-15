---
name: prometheus-alert-authoring
description: Write or change Prometheus alerting/recording rules the right way, with severity conventions, runbook links, SLO burn-rate patterns and promtool unit tests that prove each alert fires and stays quiet. Use when the user asks to "add an alert", "write a PromQL alert", "alert on X", "create an SLO alert", "fix a noisy/flapping alert", or "test my Prometheus rules".
---

# Prometheus alert authoring

An alert is only done when it has **(1)** a clear severity, **(2)** a runbook, and **(3)** a promtool test showing it fires on the real condition *and* stays quiet on the look-alikes.

## Conventions (apply unless the repo already has different ones; check first)

| Label / annotation | Rule |
|---|---|
| `severity: warning` | Awareness; act within business hours. Routes to a ticket or chat. |
| `severity: critical` | Service interruption or imminent impact; act now. Pages on-call. |
| `summary` | One line, templated with identifying labels: `"{{ $labels.instance }} ..."` |
| `runbook_url` | Always present. Points at a per-alert anchor. |
| Name | `PascalCase`, `<Component><Symptom>`, e.g. `NodeFilesystemFillingUp` |
| Recording rules | `level:metric:operations`, e.g. `job:http_errors_per_request:ratio_rate5m` |

Look for existing rule files, `promtool` tests, and an Alertmanager routing tree before inventing anything. Match whatever is already there.

## Design checklist

1. **Alert on symptoms users feel** (error rate, latency, saturation that is about to cause errors), not on every cause.
2. **`for:` duration.** Long enough to ride out scrapes and blips (usually 5-15m), short enough that critical alerts still matter. No `for:` only on burn-rate alerts whose short window already de-flaps them.
3. **Guard against noise.** Exclude the look-alikes (`fstype!~"tmpfs|overlay"`, read-only mounts, scaled-to-zero workloads, `job` filters). Combine predictive rules with a static guard: `predict_linear(...) < 0 and avail/size < 0.25`.
4. **Ratios over raw counts,** `rate()` over `irate()` for alerts, `sum by (...)` with the labels the routing and summary need. Never drop the labels the runbook uses.
5. **Two tiers when useful.** Warning at the early threshold, critical at the "it's happening" threshold, with separate `for:` values.
6. **SLOs: use multi-window, multi-burn-rate** (Google SRE Workbook ch. 5). For objective O and budget B = 1 − O:
   - page: `rate1h > 14.4·B and rate5m > 14.4·B` **or** `rate6h > 6·B and rate30m > 6·B`
   - ticket: `rate1d > 3·B and rate2h > 3·B` **or** `rate3d > B and rate6h > B`
   Record each window's error ratio first. For many SLOs, suggest Sloth or Pyrra instead of hand-writing them.

## Tests (required)

Write `tests/<file>.test.yml` next to the rules:

```yaml
rule_files: [../rules/node.rules.yml]
evaluation_interval: 1m
tests:
  - name: fires on the real condition
    interval: 1m
    input_series:
      - series: 'up{job="node", instance="h1:9100"}'
        values: '1 1 0x15'          # 1,1 then 0 for 15 samples
    alert_rule_test:
      - eval_time: 4m               # still pending: expect nothing
        alertname: NodeExporterDown
        exp_alerts: []
      - eval_time: 10m
        alertname: NodeExporterDown
        exp_alerts:
          - exp_labels: {severity: critical, job: node, instance: "h1:9100"}
            exp_annotations:          # must match exactly, rendered
              summary: "node_exporter on h1:9100 is unreachable"
              runbook_url: "https://.../runbooks#nodeexporterdown"
```

Every alert needs at least one **firing** case and one **not firing** case (a healthy neighbour, an excluded look-alike, or a recovered spike). Series notation: `a+bxN` = start at a, add b, N more samples. `_` = missing sample. `stale` = staleness marker.

When comparing computed floats in `promql_expr_test`, wrap them in `round(expr, 0.0001)` so the test doesn't break on float precision.

## Validate before finishing

```bash
promtool check rules rules/*.yml
promtool test rules tests/*.yml
```

Both must pass. Paste the summary into your reply. If `promtool` isn't installed, say so and give the install command. Don't claim the rules were tested when they weren't.

## Deliverable

- Rule diff + test diff
- A runbook entry (meaning, how to confirm, what to do) at the `runbook_url` anchor
- One line per alert: *what it catches, why this threshold, what it deliberately ignores*
