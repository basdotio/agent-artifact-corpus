# Bundled tools

Find the absolute directory containing the loaded SKILL.md and invoke its
scripts/phargus.mjs with Node. All resource paths are relative to that skill directory;
the application working directory is a separate --project argument. No tool setup or
npm install is needed in an installed skill.

Examples below use /skill and /app placeholders. Replace them with actual absolute
paths, quote paths containing spaces and use the user's existing package alias if any.

```bash
node /skill/scripts/phargus.mjs doctor --project /app
node /skill/scripts/phargus.mjs capture --file /app/.phargus/raw.ndjson --out /app/.phargus/baseline --conditions /app/.phargus/conditions.json
node /skill/scripts/phargus.mjs capture --url http://127.0.0.1:7070/events --out /app/.phargus/live --duration-ms 30000
node /skill/scripts/phargus.mjs summarize --file /app/.phargus/baseline/events.ndjson --manifest /app/.phargus/baseline/manifest.json
node /skill/scripts/phargus.mjs compare --before /app/.phargus/before/events.ndjson --before-manifest /app/.phargus/before/manifest.json --after /app/.phargus/after/events.ndjson --after-manifest /app/.phargus/after/manifest.json
node /skill/scripts/phargus.mjs heap --project /app --file /captures/first.heapsnapshot
node /skill/scripts/phargus.mjs heap --project /app --before /captures/first.heapsnapshot --after /captures/second.heapsnapshot
node /skill/scripts/phargus.mjs rules --project /app --file /captures/windows.ndjson --mode alerts --rules /app/alerts.json
node /skill/scripts/phargus.mjs rules --project /app --file /captures/windows.ndjson --mode sandbox --rules /app/diagnostic-rules
```

Use --token-env PHARGUS_DASHBOARD_TOKEN to supply bearer authentication from that
environment variable. Never put the value in a command, report or checked-in file.
Capture refuses redirects. Prefer loopback or the user's authenticated tunnel for
remote dashboards; remote binding requires a Phargus dashboard token.

Capture reserves events.ndjson and manifest.json in --out, without overwriting prior
measurements. File reads by capture --file, summarize and compare have no event-count
cap unless --max-events is given. Live capture stops at 30 seconds or 10,000 events by
default; for a high-rate service pass a larger --max-events or a shorter --duration-ms.
Truncation is reported, and a truncated capture makes compare inconclusive.
Lines have a 1 MiB cap; SSE responses a 64 MiB cap. --allow-logs allows unrelated log
lines while continuing to report malformed Phargus records, including recognizable truncated
Phargus JSON. Collection fails on corrupt data in both file and --follow modes.
Invalid records are not zeros. rules buffers its input, so replay keeps a 10,000-event
default that rules --max-events raises.

Summarize and compare need no installed Phargus. doctor, collect, heap and rules load
the target application's tested Phargus installation. Every result is JSON with
schemaVersion: 1; logs/errors are stderr; execution failure has a nonzero exit code.
An inconclusive comparison is a valid result, not a command failure.

Doctor lists script names and the known agent configuration fields, without echoing
inline script credentials or arbitrary config values. Inspect the application's own
package.json locally when selecting its start command.

Raw sample interval precedence: explicit --interval-ms, then the intervalMs a capture
recorded in its manifest, then declared conditions intervalMs, then 1000.
coverage.samplingIntervalSource reports flag, manifest, conditions or default.
compare derives each side from its own manifest unless --interval-ms is passed.
--window-ms selects replay/collector aggregation, default 1000.
Capture conditions are user-supplied JSON, not an environment dump. Comparison expects
workload, concurrency, requests, warmupMs, durationMs, nodeVersion, machine, intervalMs
and windowMs to match. Actual duration and sample coverage must agree within 5%; the helper
also checks them against the declared duration and sampling interval. Record revision/config
labels too to explain the intended change. Summaries reject mixed sample/window input and
align request metrics with runtime coverage; requests reports excluded spans and their
separate overall period. requests.routes lists up to 20 method+path entries (count,
p50Ns, p99Ns, maxNs, serverErrors) from the same selected spans, ordered by count then
p99Ns; requests.distinctRoutes counts every selected pair, so truncation is visible.

collect --project /app --file /app/.phargus/raw.ndjson --follow serves the collector and
dashboard until SIGINT/SIGTERM. --duration-ms bounds a diagnostic run; --port 0 selects
an ephemeral test port. The ready event on stderr contains the URL. --rules loads
collector alert JSON; --sinks loads a JSON array of file/webhook alert sinks (stdout is
refused). --allowed-host NAME, repeatable, lets the dashboard answer a proxy's Host name.
The result lists sink types/names, sinkErrors and allowedHosts, never sink paths or URLs.
Rotation/truncation requires starting a fresh collection.
