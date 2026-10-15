# Tested Phargus contract

Tested against [pharn-dev/phargus](https://github.com/pharn-dev/phargus) release tag
v0.1.0 (commit 819a795875fc547e7daeccc0f0b50846ba642286), package @pharn-dev/phargus
version 0.1.0, on Node >=22.18.0. The package is published on npm. The helpers accept
installed versions >=0.1.0 <0.2.0; 0.1.0 is the tested release, and a later 0.1.x
patch is accepted without having been tested here.

Install the tested release from npm in the application:
npm install @pharn-dev/phargus@0.1.0. Without registry access, build the tag from
source (see setup) and install its tarball. The tools take --project pointing to that
application and optionally --phargus-package for an explicitly installed package alias.
Resolve modules there, not in the skill checkout. Doctor resolves exports without
importing @pharn-dev/phargus/agent.

Phargus exports agent, collector, analyzer, dashboard, plugin-runner and otel.
Importing @pharn-dev/phargus/agent starts monitoring the importing process. Use it only in the
application being observed; importing it in a helper does not attach to another PID.

Collector: createCollector({ windowMs, capacity, alerts? }); consume(parsedRecords),
windows.snapshot(), spans.snapshot(), alerts.snapshot(), close().
Dashboard: createDashboardServer({ collector, host, port, token? }); close().
Analyzer: summarizeHeapSnapshot(path), diffHeapSnapshots(before, after).
Plugin runner: createPluginRunner(), loadRulesDirectory(dir), runRules(runner, rules, windows).

The agent never starts a server. There is no snapshot, profiler or metrics REST API.
The dashboard offers GET /events (SSE), not an MCP endpoint. Incoming HTTP/HTTPS
requests are traced; outgoing requests, database calls, queue jobs and HTTP/2 have
no separate spans. Worker and process boundaries require explicit trace propagation.

isolated-vm is an optional peer dependency needed only for sandbox rules. Allocation
sampling and snapshots are library operations inside the monitored process.
createDeoptParser parses supplied node --trace-deopt output; it does not capture it.

Runtime checks establish version and required exports, not the source commit of an
installed package. The report says sourceCommitVerified: false and names the tested
version, tag and commit; the release integration suite establishes compatibility with
the tagged source separately.
