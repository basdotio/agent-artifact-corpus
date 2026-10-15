#!/usr/bin/env bun
/**
 * Report the remote-debugging state of installed Chromium browsers WITHOUT
 * connecting, so it never triggers the "Allow remote debugging?" dialog.
 */

import { parseArgs } from "node:util";
import { customBrowser, knownBrowsers } from "./src/browsers.ts";
import { discover, explain, type Inspection } from "./src/discovery.ts";

const HELP = `Usage: bun scripts/find-endpoint.ts [options]

Probes local Chromium browsers (reads files + TCP connect). Never opens a CDP
connection, so it is safe to run repeatedly.

Options:
  --browser <id>         Only this browser (chrome, chrome-beta, chrome-dev, chrome-canary,
                         chromium, edge, edge-beta, edge-dev, edge-canary, brave, vivaldi, opera)
  --user-data-dir <dir>  Inspect a custom profile dir instead of the known ones
  --text                 Human-readable lines instead of JSON
  -h, --help             Show this help

Output (JSON on stdout): [{ id, name, state, toggleEnabled, port, endpoint, inspectUrl, hint }]
  state: "listening" | "not-listening" | "no-port-file"

Exit codes: 0 at least one (or the requested) browser is listening
            1 nothing listening (see "hint")
            2 invalid arguments`;

let values;
try {
  ({ values } = parseArgs({
    args: process.argv.slice(2),
    options: {
      browser: { type: "string" },
      "user-data-dir": { type: "string" },
      text: { type: "boolean", default: false },
      help: { type: "boolean", short: "h", default: false },
    },
  }));
} catch (error) {
  console.error(`${(error as Error).message}\n\n${HELP}`);
  process.exit(2);
}

if (values.help) {
  console.log(HELP);
  process.exit(0);
}

let browsers = values["user-data-dir"] ? [customBrowser(values["user-data-dir"])] : knownBrowsers();
if (values.browser) {
  browsers = browsers.filter((b) => b.id === values.browser);
  if (browsers.length === 0) {
    console.error(`Unknown browser id "${values.browser}" for this OS. Run with --help for the list.`);
    process.exit(2);
  }
}

const inspections = await discover(browsers);

const summarize = (i: Inspection) => ({
  id: i.browser.id,
  name: i.browser.name,
  state: i.state,
  toggleEnabled: i.toggleEnabled ?? null,
  port: i.activePort?.port ?? null,
  endpoint: i.endpoint ?? null,
  inspectUrl: i.browser.inspectUrl,
  hint: explain(i),
});

if (values.text) {
  if (inspections.length === 0) console.log("No installed Chromium-based browser profile found.");
  for (const i of inspections) console.log(explain(i));
} else {
  console.log(JSON.stringify(inspections.map(summarize), null, 2));
}

process.exit(inspections.some((i) => i.state === "listening") ? 0 : 1);
