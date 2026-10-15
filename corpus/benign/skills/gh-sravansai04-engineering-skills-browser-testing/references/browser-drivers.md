# Browser Drivers: MCP Setup and CLI Fallback

Read this in Mode A when choosing how to drive the browser, when no browser MCP is connected, or when the user asks how to set one up. Commands were checked against Playwright 1.64, `@playwright/mcp` 0.0.83, and `chrome-devtools-mcp` 1.10. Flags drift, so confirm with `--help` on the installed version.

## Contents

1. Detecting what is connected
2. Optional one-line setup (ask first)
3. Using an MCP driver well
4. CLI fallback ladder
5. Saving and reusing a login
6. Throwaway flow script (Node and Python)
7. Handling evidence

## 1. Detecting what is connected

- Scan your available tools for browser verbs: navigate, snapshot, click, screenshot, console, network. Playwright MCP tools are named `browser_*`; Chrome DevTools MCP uses names such as `navigate_page`, `take_snapshot`, `list_console_messages`. Clients usually prefix them with the server name, e.g. `mcp__playwright__browser_snapshot`.
- If the client lists MCP tools without schemas (a "deferred" or "load on demand" list), load the browser tools first. Their absence from the initial schema list does not mean they are unavailable.
- In Claude Code the user can run `claude mcp list` to see configured servers and whether each one connects; other clients show the same in their MCP settings or status view. A server that is configured but failing to connect is a setup problem to report, not a reason to silently switch tools.
- More than one browser server? Prefer the one with an isolated or temporary profile for verification. A server attached to a personal browser profile carries that person's cookies and sessions.

## 2. Optional one-line setup (ask first)

Only offer these; installing or changing a user's client configuration needs their consent. The `claude mcp add` commands are the Claude Code form; other MCP clients take the same server command in their own configuration, usually as JSON (example below).

**Playwright MCP** (official, from the Playwright team):

```bash
claude mcp add playwright npx @playwright/mcp@latest
```

To pass server flags, put them after `--` so the client does not try to parse them. A typical verification setup - headless, nothing persisted, signed in from a saved state, request mocking enabled:

```bash
claude mcp add playwright -- npx @playwright/mcp@latest --headless --isolated \
  --storage-state /tmp/pw-verify/auth.json --caps network
```

Other MCP clients take the same command as JSON:

```json
{ "mcpServers": { "playwright": { "command": "npx", "args": ["@playwright/mcp@latest"] } } }
```

Playwright 1.62 and later also bundle the server as `npx playwright mcp`, which takes the same flags and uses the project's own Playwright version.

Useful flags:

- `--headless` (headed is the default) and `--isolated` (profile kept in memory, nothing persisted). Without `--isolated` the server reuses a persistent profile under the Playwright cache directory, so cookies from an earlier session can leak into this one.
- `--storage-state <file>` loads cookies and local storage **only together with `--isolated`**. On its own it is silently ignored and you will not be signed in - a bounce to the login page then looks like an auth bug that does not exist.
- `--browser chrome|firefox|webkit|msedge`, `--device "iPhone 15"` or `--mobile`, `--viewport-size 1280x720`. Device emulation is fixed at startup; there is no tool to switch devices mid-session.
- `--console-level error|warning|info|debug`, `--test-id-attribute <attr>`, `--output-dir <dir>` (where automatically named screenshots land).
- `--caps <list>` turns on opt-in tool groups:

  | Cap | Adds |
  |---|---|
  | `network` | `browser_route`, `browser_route_list`, `browser_unroute` (mock responses), `browser_network_state_set` (offline) |
  | `storage` | cookie, localStorage, and sessionStorage tools; `browser_storage_state` / `browser_set_storage_state` |
  | `testing` | `browser_verify_*` assertions, `browser_generate_locator` |
  | `devtools` | tracing, video, recording, element highlighting |
  | `pdf` | `browser_pdf_save` |
  | `vision` | coordinate-based mouse tools |
  | `config` | `browser_get_config` |

  `--help` may list only some of these, and a misspelled cap is ignored without an error. After a restart, confirm the tools you need actually appear.
- Pin a version (`@playwright/mcp@0.0.83`) in shared or CI configuration so a new release cannot change tool behavior underneath you.

**Chrome DevTools MCP** (from the Chrome DevTools team; adds performance traces, Lighthouse, CSS inspection):

```bash
claude mcp add chrome-devtools --scope user npx chrome-devtools-mcp@latest
```

Useful flags: `--headless` (headed is the default), `--isolated` (temporary profile, deleted when the browser closes), `--viewport 1280x720`, `--browser-url http://127.0.0.1:9222` (attach to a Chrome you started with remote debugging), `--no-usage-statistics`. Avoid `--slim` for verification: it leaves only navigation, script execution, and screenshots, with no snapshot, console, or network tools. Its `emulate` tool sets a device viewport (`375x667x2,mobile,touch`), color scheme, network throttling or offline, and CPU throttling at runtime; it has no request mocking. The server exposes everything in the attached browser to the client, so do not point it at a profile holding personal accounts.

After adding either server, start a new session and confirm it connects: in Claude Code with `claude mcp list` (or `/mcp` inside a session), elsewhere with the client's own MCP status view or tool list.

## 3. Using an MCP driver well

- **Snapshot first, screenshot second.** The accessibility snapshot lists roles, names, states, and element references. Choose click targets from it; use screenshots for layout and visual evidence.
- **References expire.** An element reference from a snapshot is only valid for the DOM it was taken from. After any click, navigation, or async update, take a new snapshot before the next action.
- **Wait on content, not time.** Use the wait tool with text that should appear or disappear.
- **Read console and network after each flow.** Filter console to errors and warnings; in the network list look for status >= 400, failed requests, and duplicate mutations. Open the full request for the mutation you triggered and check its payload.
- **Resize for widths, emulate for devices.** Resizing changes only the viewport; device emulation also sets touch, pixel ratio, and user agent.
- **Forcing states.** Error and empty responses need a route tool (Playwright MCP `--caps network`). Loading and offline states can come from network throttling (Chrome DevTools MCP `emulate`) or `browser_network_state_set`. With neither, switch to the CLI (`npx playwright cli route <pattern> --status 500 --body '{...}'`) or a flow script with `page.route` (section 6) - do not overwrite `fetch` through script evaluation.
- **Long pages.** Snapshots of huge pages are expensive. Navigate to the specific route, scope your reading to the region that changed, and prefer the find or search tool when the server offers one.
- **Dialogs and uploads.** Native `alert` / `confirm` dialogs block the page until handled - use the dialog tool. File inputs need the upload tool, not typing a path.
- **Finish cleanly.** Close the browser with the close tool when you are done.

## 4. CLI fallback ladder

Work from a scratch directory so verification adds nothing to the user's project:

```bash
mkdir -p /tmp/pw-verify && cd /tmp/pw-verify
npm init -y && npm i -D playwright
npx playwright install chromium      # or skip and pass --channel chrome to use an installed Chrome
```

If the project already has Playwright, you can reuse its install instead - but run rung 2 from the scratch directory either way, because it writes files into the current directory.

**Rung 1 - multi-width health check.** The bundled script resolves Playwright from the current directory. `${CLAUDE_SKILL_DIR}` below is not a shell variable: replace it with this skill's directory, the folder that contains SKILL.md (in Claude Code, the path SKILL.md shows for `scripts/page-smoke.mjs`).

```bash
node "${CLAUDE_SKILL_DIR}/scripts/page-smoke.mjs" http://localhost:3000/settings \
  --widths 375,768,1280 --out /tmp/pw-verify/shots \
  --wait-for-text "Settings" --storage-state /tmp/pw-verify/auth.json
```

Output is JSON. Per width: the final URL, status, and title (check the title - it tells you which app actually answered), a `problems` count, `consoleErrors`, `consoleWarnings`, `pageErrors` (uncaught exceptions), `failedRequests` (network failures; aborted requests are listed separately and not counted), `httpErrors` (responses >= 400), `horizontalOverflow`, `overflowCulprits`, `notes`, the screenshot path, and `error` if navigation failed.

- `overflowCulprits` lists where the overflow *starts* - elements whose own box sticks out while their parent fits - widest first, each with a CSS `selector`, `right` and `width` in pixels, and a `text` snippet. Content that is clipped or scrolls inside its own container (carousels, `overflow-x: auto` table wrappers) and `position: fixed` off-canvas panels are skipped because they cannot widen the page.
- A missing `/favicon.ico` goes to `notes` and is not counted; browsers request it on their own, often at one width only.
- One defect counts once: a 404 document is not counted again as an HTTP error, and a failed navigation is not counted again as a failed request.
- Exit 0 = clean, 1 = problems, 2 = could not run (bad arguments, Playwright or browser missing, or the URL did not load at any width - verdict `unreachable`, usually a server that is down).
- `--ignore <regex>` (repeatable) drops other known noise. It only loads a page; it does not click through flows.

**Rung 2 - drive the flow from the terminal, no code** (Playwright 1.62 and later; check that `npx playwright --help` lists `cli`):

```bash
cd /tmp/pw-verify                                  # it writes snapshots and logs to ./.playwright-cli/
npx playwright cli open http://localhost:3000/signup   # headless unless you add --headed
npx playwright cli snapshot                        # roles, names, and [ref=eN] handles
npx playwright cli click e12                       # act on a ref from the latest snapshot
npx playwright cli fill e7 "ada@example.com"
npx playwright cli console                         # console messages so far
npx playwright cli requests                        # network log (add --static for assets)
npx playwright cli resize 375 800
npx playwright cli screenshot
npx playwright cli close                           # the browser stays alive until you close it
```

Other useful commands: `state-load <file>` / `state-save <file>` for sign-in, `route <pattern> --status 500 --body '...'` for mocking (register it before the action that fires the request), `set-color-scheme dark`, `eval "() => document.documentElement.scrollWidth"` to read state. `npx playwright cli --help` lists the current set. Refs expire after the page changes, exactly as in an MCP snapshot.

**Rung 3 - a flow script** for the claims you wrote, when you need several devices or signed-in roles in one run, or a check you can repeat exactly (template in section 6).

**Rung 4 - quick visuals:**

```bash
npx playwright screenshot --full-page http://localhost:3000/ home-desktop.png
npx playwright screenshot --device "iPhone 13" --full-page http://localhost:3000/ home-phone.png
npx playwright screenshot --viewport-size "768, 1024" --color-scheme dark --wait-for-selector "main" http://localhost:3000/ home-tablet-dark.png
npx playwright screenshot --load-storage /tmp/pw-verify/auth.json http://localhost:3000/account account.png
```

## 5. Saving and reusing a login

Save the session to a file outside the repository, reuse it everywhere, and delete it when you are done. It holds live session cookies.

**Agent, no display - script the login** with a test account whose credentials come from the environment. Use a script rather than `npx playwright cli fill`: the CLI echoes every value it types into its output, which would put the password in your transcript and in `.playwright-cli/` logs.

```js
// save-auth.mjs - throwaway; run from /tmp/pw-verify. Credentials are read from the environment and never printed.
import { chromium } from 'playwright';

const { BASE_URL = 'http://localhost:3000', E2E_USER, E2E_PASSWORD } = process.env;
if (!E2E_USER || !E2E_PASSWORD) throw new Error('E2E_USER / E2E_PASSWORD are not set');

const browser = await chromium.launch();
try {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`${BASE_URL}/login`);
  await page.getByLabel('Email').fill(E2E_USER);
  await page.getByLabel('Password').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByRole('button', { name: 'Account menu' }).waitFor();   // a signed-in signal - adjust to the app
  await context.storageState({ path: '/tmp/pw-verify/auth.json' });
  console.log('saved /tmp/pw-verify/auth.json');
} finally {
  await browser.close();
}
```

**Human at the keyboard** - the user signs in by hand:

```bash
# Opens a headed browser and waits until the window is closed. Never run this from an agent shell.
npx playwright open --save-storage /tmp/pw-verify/auth.json http://localhost:3000/login
```

Then pass the file as:

- `--storage-state /tmp/pw-verify/auth.json` to `page-smoke.mjs`;
- `--isolated --storage-state /tmp/pw-verify/auth.json` to the Playwright MCP server (both flags; see section 2);
- `state-load /tmp/pw-verify/auth.json` to `npx playwright cli` (after `open`);
- `--load-storage` to `screenshot` / `codegen` / `open`;
- `storageState` to `browser.newContext()`.

Sessions expire. If pages bounce to the login screen, capture a fresh one before suspecting the app.

## 6. Throwaway flow script

Write one claim per block, assert on what a user would see, and collect console and network problems along the way. A failing claim is recorded, not thrown, so the remaining widths still run and the evidence still prints. Run it from the scratch directory with `node verify-flow.mjs`.

```js
// verify-flow.mjs - throwaway; do not commit
import { chromium, devices } from 'playwright';

const BASE = process.env.BASE_URL ?? 'http://localhost:3000';
const browser = await chromium.launch(); // { channel: 'chrome' } to use installed Chrome
const problems = [];
const results = [];

async function claim(name, fn) {
  try { await fn(); results.push(`PASS  ${name}`); }
  catch (e) { results.push(`FAIL  ${name}\n      ${String(e.message).split('\n')[0]}`); }
}

try {
  for (const [label, options] of [['desktop', { viewport: { width: 1280, height: 800 } }],
                                  ['phone', devices['iPhone 13']]]) {
    const context = await browser.newContext(options); // add storageState: '/tmp/pw-verify/auth.json' if signed in
    try {
      const page = await context.newPage();
      page.on('pageerror', (e) => problems.push(`[${label}] uncaught: ${e.message}`));
      page.on('console', (m) => m.type() === 'error' && !m.location().url.endsWith('/favicon.ico') // browser-initiated; not the page's fault
        && problems.push(`[${label}] console: ${m.text()}`));
      page.on('response', (r) => r.status() >= 400 && problems.push(`[${label}] ${r.status()} ${r.request().method()} ${r.url()}`));
      page.on('requestfailed', (r) => problems.push(`[${label}] failed ${r.method()} ${r.url()} ${r.failure()?.errorText}`));

      // Optional: force a state you cannot reach otherwise - register before navigating.
      // await page.route('**/api/plans', (route) => route.fulfill({ status: 500, json: { error: 'boom' } }));

      await page.goto(`${BASE}/signup`);

      await claim(`[${label}] empty email shows a validation message`, async () => {
        await page.getByRole('button', { name: 'Create account' }).click();
        await page.getByText('Email is required').waitFor({ state: 'visible', timeout: 5000 });
        if (!page.url().endsWith('/signup')) throw new Error(`navigated to ${page.url()}`);
      });

      await page.screenshot({ path: `signup-${label}.png`, fullPage: true });
    } finally {
      await context.close();
    }
  }
} finally {
  await browser.close();
}

console.log(results.join('\n'));
console.log(problems.length ? `\nProblems:\n${problems.join('\n')}` : '\nNo console or network problems.');
process.exit(results.some((r) => r.startsWith('FAIL')) || problems.length ? 1 : 0);
```

Python equivalent (`pip install playwright && playwright install chromium`), with the same record-don't-throw shape:

```python
# verify_flow.py - throwaway; do not commit
import sys
from playwright.sync_api import sync_playwright, expect, Error as PlaywrightError

BASE = "http://localhost:3000"
problems, results = [], []

def claim(name, fn):
    try:
        fn()
        results.append(f"PASS  {name}")
    except (AssertionError, PlaywrightError) as e:
        results.append(f"FAIL  {name}\n      {str(e).splitlines()[0] if str(e) else type(e).__name__}")

with sync_playwright() as p:
    browser = p.chromium.launch()  # channel="chrome" to use installed Chrome
    try:
        for label, options in [("desktop", {"viewport": {"width": 1280, "height": 800}}),
                               ("phone", p.devices["iPhone 13"])]:
            context = browser.new_context(**options)  # storage_state="/tmp/pw-verify/auth.json" if signed in
            try:
                page = context.new_page()
                page.on("pageerror", lambda e, l=label: problems.append(f"[{l}] uncaught: {e}"))
                page.on("console", lambda m, l=label: m.type == "error"
                        and not m.location["url"].endswith("/favicon.ico")  # browser-initiated; not the page's fault
                        and problems.append(f"[{l}] console: {m.text}"))
                page.on("response", lambda r, l=label: r.status >= 400 and problems.append(f"[{l}] {r.status} {r.request.method} {r.url}"))
                page.on("requestfailed", lambda r, l=label: problems.append(f"[{l}] failed {r.method} {r.url} {r.failure}"))

                page.goto(f"{BASE}/signup")

                def empty_email_shows_message():
                    page.get_by_role("button", name="Create account").click()
                    expect(page.get_by_text("Email is required")).to_be_visible()
                    expect(page).to_have_url(f"{BASE}/signup")

                claim(f"[{label}] empty email shows a validation message", empty_email_shows_message)
                page.screenshot(path=f"signup-{label}.png", full_page=True)
            finally:
                context.close()
    finally:
        browser.close()

print("\n".join(results))
print("\nProblems:\n" + "\n".join(problems) if problems else "\nNo console or network problems.")
sys.exit(1 if problems or any(r.startswith("FAIL") for r in results) else 0)
```

Python's `expect` works outside a test runner and retries like the test version. In Node, use `locator.waitFor()` and explicit checks as above, or write the flow as a real spec and run it with `npx playwright test` to get traces for free.

## 7. Handling evidence

- Save screenshots and traces in a scratch directory, never in the repository, and name them by claim and width (`signup-empty-email-375.png`).
- Look at the screenshots you cite. A file existing is not the same as the UI being right.
- Before sharing screenshots, check them for tokens, personal data, or anything from a real account.
- When you finish, delete saved auth state and `.playwright-cli/` output you no longer need, and say in the report where the kept artifacts are.
