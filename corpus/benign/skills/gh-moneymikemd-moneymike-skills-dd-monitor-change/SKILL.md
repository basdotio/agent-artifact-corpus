---
name: dd-monitor-change
description: "Rename, retag, reprioritise, retune, reroute or rewrite the message of a Datadog monitor without breaking anything that references it. Use for any monitor edit, alert hygiene ticket, threshold change, synthetics monitor edit, notification routing change, or before removing a span or tag that a monitor might query. Also use when a monitor reads OK and you suspect it is silent rather than healthy."
license: MIT
---

# Change a Datadog monitor

Read `~/.claude/skill-context/dd-monitor-change.md` first if it exists. It holds this org's routing handles, team tag, dashboards and research files, and wins over anything general here.

Also read `memory.md` and `research.md` from that directory if they exist: they say how this environment recalls and stores memories and where its research files live. With no memory store set up anywhere, skip the recall and store steps below and tell the user what was not stored; with no research directory, do the same for research-file appends.

Every rule here was paid for on a real batch of production monitors. Read the research files the context file names before starting.

## Recall

Recall from the memory store before anything else (how: `memory.md`): query `datadog monitor <id or name>`, limit 10.

## 1. Save before-state

Audit Trail usually needs an admin-granted permission, so assume a saved GET is the only rollback and verification record that will exist.

```bash
curl -s "https://api.datadoghq.com/api/v1/monitor/$ID" -H "DD-API-KEY: $DD_API_KEY" -H "DD-APPLICATION-KEY: $DD_APP_KEY" > before-$ID.json
```

## 2. Sweep the four reference surfaces

Renaming is safe because references are by id. **Retagging is the risky one**: a tag-scoped downtime silently widens or breaks and nothing warns you.

1. Dashboards: `GET /api/v1/dashboard` to list, then GET each; widget contents are only in the per-dashboard GET. Check match context, note widgets produce false positives.
2. SLOs: `GET /api/v1/slo`, `type:monitor` with `monitor_ids`. Metric SLOs cannot reference a monitor.
3. Composite monitors: `GET /api/v1/monitor`, filter `.type=="composite"`, ids are in `.query`.
4. Downtimes: `GET /api/v2/downtime`, read `monitor_identifier.monitor_tags`.

Also evaluate the org notification rules (`GET /api/v2/monitor/notification_rule`): filters are tags-only, ANDed, and rules ADD recipients to message handles. Removing a tag can drop a channel; adding one can double-deliver.

## 3. Pick the write path

| Target | Path |
|---|---|
| Metadata only (name, tags, priority, message) | `PUT /api/v1/monitor/{id}` with ONLY those keys. It is a partial update; omit `options` and thresholds survive. |
| Thresholds | Rebuild the ENTIRE `options` object from a fresh GET, then send. `update_datadog_monitor` (MCP) replaces `options` wholesale; passing `{thresholds:{critical:2}}` dropped a warning threshold once. Pass only `query` when thresholds are not changing. |
| Synthetics monitor | Read-only via the monitor API (400 "use Synthetics API"). `PATCH /api/v1/synthetics/tests/{public_id}` with `{"data":[{"op":"add","path":"/options/monitor_priority","value":1}]}`. Name is `[Synthetics] ` + test name; the prefix cannot be removed. |

A `500` with an empty body is a clean no-op: re-GET, confirm, retry. Do not start repairing fields. Verify on one low-priority monitor first, diff before/after, then batch.

## 4. Message template

Chosen by the user after editing three drafts:

```
**<service>** · <env> · P<n> · <signal>
{{#is_alert}} 🚨 <what a user of the product cannot do now> {{/is_alert}}
{{#is_warning}} ⚠️ <same, not-yet-broken> {{/is_warning}}
{{#is_recovery}} ✅ <it is back> {{/is_recovery}}
Links
- 2-4 ABSOLUTE https://app.datadoghq.com links, most specific first, the team's overview dashboard last
<handles, one line, OUTSIDE all conditionals>
```

No `##` headings. No engineering notes about migrations or baselines; those live in tickets. `is_warning` only where a warning threshold exists. Service name dropped where it is an adjective ("requests"), kept where it is the subject. Link text says "service" generically unless the link points at a different service than the header.

Route by handles in the message, per the context file's priority table, unless the org routes by tag.

## 5. Thresholds

Measure at least 14 days; 7-day maxima ran 36% low. Group by `http.status_class` to discover which values exist before concluding a query is broken: a status-filtered APM metric returning no series means the service has none, not that the wildcard failed. Measure the request floor before accepting a small-denominator argument. State on the ticket which other ticket would invalidate the baseline.

## 6. Verify from GETs, not write responses

The PUT response shows mid-re-evaluation state. Compare `overall_state` from GETs before and after. A synthetics message PATCH bumps `check_version` and forces an off-schedule run, so No Data for a minute or more is correct; confirm on `/api/v1/synthetics/tests/browser/{id}/results` (the segment is the test TYPE, `api` returns an empty list rather than an error).

Monitor search grammar: `tag:team:<team> AND priority:p1`. `priority:1` is a parse error that returns HTTP 200 with `total_count: null`. Assert the count is a number.

## Before removing a span or tag anywhere

Check which monitors query it. Suppressing an http client integration once killed a monitor silently: it reads OK forever because there is no data. Green is not healthy.

Where to read options without keys: the Export Monitor button, or `source:monitor_audit_event` in `search_datadog_events`, which also shows the BEFORE values.

## Memory and research file

Store the change and any new product behaviour, then append a dated refinement to the Datadog research file (see `research-file-update`).
