# Author and replay diagnostic rules

Use a collector AlertRule for a single aggregated metric threshold. JSON fields:
id, metric, comparison (> or >=), threshold (nonnegative integer), forWindows (>=1).
Threshold units follow the metric: nanoseconds, bytes or counts. Supported paths:
eventLoop.max/p99/mean; memory.heapUsedLast/heapUsedMax/rssLast/rssMax;
gc.count/totalPause/maxPause; backpressure.events/totalStall/maxStall.

```json
[
  {
    "id": "sustained-lag",
    "metric": "eventLoop.max",
    "comparison": ">",
    "threshold": 50000000,
    "forWindows": 3
  }
]
```

The evaluator emits firing once when enough successive input windows breach, then
resolved on the first nonbreaching window. Equality differs for > and >=. forWindows
counts input windows; gaps do not automatically reset the upstream evaluator. Check
window continuity before describing the condition as a continuous wall-clock duration.

Replay the rule on separate normal and incident data with rules --mode alerts. Choose
a threshold from the symptom and observed normal range, not from an arbitrary default.
Inspect alert timing, resolution and false alarms before wiring the JSON into
createCollector({ windowMs, capacity, alerts: rules }). Agent config does not configure
collector alerts. --rules on the collect helper loads that collector JSON.

Alerts without a sink stay in the collector's ring buffer and the dashboard; nobody is
notified. Deliver them with createCollector({ ..., alerts, sinks, onSinkError }), where
sinks are { type: 'file', path } (append NDJSON), { type: 'webhook', url } (POST, with
optional timeoutMs, retries, backoffMs) or { type: 'stdout' }. The collect helper takes
--sinks pointing at a JSON array of file or webhook sinks; it refuses stdout because its
own result is JSON on stdout. Sink failures appear on stderr and as sinkErrors. Keep a
webhook URL with credentials out of version control; the helper never echoes it. Include
the sink in the activation recipe and confirm one delivered alert before relying on it.

Use sandbox rules for multi-metric or trend logic. Each .js file in the rule directory
is a FUNCTION BODY with windows in scope; return an array of { windowStart, message }.
Do not export a module, use require/import, or evaluate the source in the host.

```js
const findings = [];
for (const w of windows) {
  if (w.eventLoop.max > 50000000 && w.gc.totalPause > 10000000) {
    findings.push({ windowStart: w.start, message: 'Lag coincided with GC activity' });
  }
}
return findings;
```

Rules run in Phargus's child-process isolated-vm sandbox with memory/time/result caps.
The optional isolated-vm peer must be installed for the target Node version. Missing
peer, compile errors, timeouts and ok: false results are failed executions, not zero
findings. Close the runner after replay. Built-in eventLoopLagRule, gcPauseShareRule
and heapGrowthRule are available; heapGrowthRule detects rising heap, not a proven leak.

Deliver the rule, rationale, replay results on both datasets, and how to activate it.
Keep findings faithful to observable signals rather than declaring unproven causes.
