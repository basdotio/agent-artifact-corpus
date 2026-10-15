#!/usr/bin/env bun
/**
 * End-to-end reference for attach mode. Read it as the canonical flow; run it
 * to verify a machine is ready.
 *
 *   discover (no dialog) → connect ONCE (dialog) → list tabs → work in an own
 *   background tab → close only that tab → disconnect (browser stays open)
 */

import { parseArgs } from "node:util";
import { knownBrowsers } from "./src/browsers.ts";
import { CdpClient, CdpClosedError } from "./src/cdp-client.ts";
import { discover, explain, pickEndpoint } from "./src/discovery.ts";
import { evaluate, listPages, navigate, openBackgroundTab } from "./src/targets.ts";

const HELP = `Usage: bun scripts/example-attach.ts [--browser <id>] [--url <url>]

Attaches to the running browser (shows ONE "Allow remote debugging?" dialog),
lists the user's tabs, opens <url> in a background tab, prints its title,
closes that tab and disconnects.

Exit codes: 0 ok · 1 not ready (see message) · 3 user denied the dialog · 4 other error`;

const { values } = parseArgs({
  args: process.argv.slice(2),
  options: {
    browser: { type: "string" },
    url: { type: "string", default: "https://example.com/" },
    help: { type: "boolean", short: "h", default: false },
  },
});
if (values.help) {
  console.log(HELP);
  process.exit(0);
}

// 1. Discover without connecting.
const inspections = await discover(knownBrowsers());
const target = pickEndpoint(inspections, values.browser);
if (!target) {
  const relevant = values.browser ? inspections.filter((i) => i.browser.id === values.browser) : inspections;
  for (const i of relevant) console.error(explain(i));
  process.exit(1);
}

// 2. Connect once. No connect timeout: the handshake completes when the user clicks Allow.
console.error(`Connecting to ${target.browser.name}. Click "Allow" in the browser dialog.`);
let cdp: CdpClient;
try {
  cdp = await CdpClient.connect(target.endpoint!);
} catch (error) {
  // Chrome answers the upgrade with HTTP 403 when the user clicks Cancel / "Turn off in settings".
  if (error instanceof CdpClosedError) {
    console.error("Connection refused: the user denied the dialog, or the browser closed.");
    process.exit(3);
  }
  throw error;
}
const offLost = cdp.onClose((e) => console.error(`Connection lost (${e.code}). Toggle turned off or browser closed.`));

try {
  // 3. Read-only look at the user's tabs.
  const pages = await listPages(cdp);
  const result: Record<string, unknown> = {
    browser: (await cdp.send("Browser.getVersion")).product,
    userTabs: pages.map((p) => ({ targetId: p.targetId, title: p.title, url: p.url })),
  };

  // 4. Work in an own background tab; the user's tabs stay untouched.
  const tab = await openBackgroundTab(cdp);
  try {
    await navigate(cdp, tab.sessionId, values.url);
    result.ownTab = { url: values.url, title: await evaluate<string>(cdp, tab.sessionId, "document.title") };
  } finally {
    await tab.close(); // only the tab we created
  }

  console.log(JSON.stringify(result, null, 2));
} catch (error) {
  console.error((error as Error).message);
  process.exitCode = 4;
} finally {
  // 5. Disconnect. Never Browser.close: this is the user's browser.
  offLost(); // our own close is not a lost connection
  cdp.close();
}
