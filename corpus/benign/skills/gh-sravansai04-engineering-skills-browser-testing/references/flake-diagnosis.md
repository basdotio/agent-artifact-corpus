# Flake Diagnosis

Read this when a browser test fails intermittently, fails only in CI, fails only alongside other tests, or passes only on retry. A flaky test is a race you have not found yet - either in the test or in the app. Both are worth finding: a fair share of "flaky tests" are real bugs that users hit on slow networks.

## Contents

1. Workflow
2. Reading a failure: error context, trace, report
3. Symptom -> cause -> fix
4. "Passes locally, fails in CI"
5. Order and parallelism problems
6. What is not a fix
7. Quarantine without losing the test

## 1. Workflow

1. **Reproduce.** Run the single test many times under pressure:
   ```bash
   npx playwright test e2e/cart.spec.ts:42 --repeat-each=20 --workers=4 --retries=0
   ```
   `--retries=0` overrides config retries, so every bad run counts as a failure. A `test.describe.configure({ retries })` in the spec still wins over the flag, so remove it while reproducing. If it only fails alongside other tests, run the whole file or project (section 5).

   To expose timing bugs, make the machine slower in a way you can repeat. Watching a headed run is not an option for an agent, and a browser MCP cannot reach the browser the test runner launches, so slow the test's own browser with an opt-in fixture (Chromium only - it uses the DevTools protocol):

   ```ts
   // e2e/fixtures.ts - add to your existing test.extend; does nothing unless SLOW_CPU is set
   import { test as base } from '@playwright/test';

   export const test = base.extend<{ slowMachine: void }>({
     slowMachine: [async ({ page, browserName }, use) => {
       if (process.env.SLOW_CPU && browserName === 'chromium') {
         const cdp = await page.context().newCDPSession(page);
         await cdp.send('Emulation.setCPUThrottlingRate', { rate: Number(process.env.SLOW_CPU) || 4 });
         await cdp.send('Network.enable');
         await cdp.send('Network.emulateNetworkConditions', {
           offline: false, latency: 300, downloadThroughput: 200 * 1024, uploadThroughput: 100 * 1024,
         });
       }
       await use();
     }, { auto: true }],
   });
   ```

   ```bash
   SLOW_CPU=4 npx playwright test e2e/cart.spec.ts:42 --project=chromium --repeat-each=20 --retries=0
   ```

   More workers and a CI-like `CI=1` add load too. A test that only fails under throttling has a real race - often one your slowest users hit.
2. **Capture.** Make sure a failure leaves evidence: `--trace=retain-on-failure` on the command line overrides the config. Each run clears `test-results/`, so copy the evidence out before re-running.
3. **Read** the error context and trace (section 2) before forming a theory.
4. **Classify** with the table in section 3. Decide whether the race is in the test (wrong wait, shared data) or in the app (double submit, hydration gap, stale cache). App races are bugs: report or fix them, do not just teach the test to tolerate them.
5. **Fix the cause** and prove it: the same `--repeat-each=20` run passes, and the test still fails when you break the behavior it checks.

## 2. Reading a failure

- **Error context.** Recent Playwright versions write `error-context.md` next to each failure in `test-results/<test-dir>/`. It holds the error, the assertion's call log (every value the locator resolved to while retrying), an ARIA snapshot of the page at the moment of failure, and the test source. Read it first - it often answers the question without opening anything else.
- **Call log.** In the assertion message, lines such as `4 x locator resolved to <p role="status"></p> - unexpected value ""` followed by `17 x ... "Your card was declined"` tell you the element existed and what it contained over time. "Waiting for getByRole(...)" with no resolution means the element never appeared under that role and name.
- **Trace in the terminal** (1.59 and later; check `npx playwright trace --help`) - the agent's trace viewer, and every command exits on its own:
  ```bash
  npx playwright trace open test-results/<test-dir>/trace.zip
  npx playwright trace actions --errors-only      # which step failed; note its action id
  npx playwright trace action <action-id>         # parameters, timing, and the error for that step
  npx playwright trace snapshot <action-id> --phase before   # the page just before the failing step
  npx playwright trace requests --failed          # responses with status >= 400
  npx playwright trace console --errors-only
  npx playwright trace errors                     # every error with its stack trace
  npx playwright trace close
  ```
  Check what the page looked like *just before* the failing action - an overlay, a spinner, an old list.
- **CI artifacts:** download the HTML or merged blob report. The HTML report keeps each failure's trace zip and error context under its `data/` folder, so you can read them with the commands above without opening a browser.
- **Graphical viewers (human only):** `npx playwright show-trace <trace.zip>` and `npx playwright show-report <dir>` open a window or a local server and wait until someone closes it. Offer them to the user; do not run them from an agent shell.

## 3. Symptom -> cause -> fix

| Symptom | Likely cause | Fix |
|---|---|---|
| An assertion passes on the wrong page state; the call log shows values from *after* the next step; "Test ended." or "Target page, context or browser has been closed" | A Playwright action or `expect(...)` without `await`: the promise runs loose while the test moves on or finishes | Add the `await`. Enforce it with `eslint-plugin-playwright`'s `missing-playwright-await` or `@typescript-eslint/no-floating-promises` |
| `Timeout ... waiting for getByRole(...)` | Element never rendered: wrong page, missing data, permission, or a different role or name than you assumed | Check the ARIA snapshot in the error context; fix the locator or the data setup. Do not raise the timeout first |
| `strict mode violation: ... resolved to 2 elements` | Ambiguous locator; or parallel tests created duplicate records, so a list contains two "Test project" rows | Scope the locator; give test data unique names |
| `element is not visible / not stable / not enabled` or `<div class="overlay"> intercepts pointer events` | Animation, toast, cookie banner, loading overlay, or disabled-until-valid button | Wait for the blocker to go away (`await expect(overlay).toBeHidden()`), dismiss it in a fixture, or fill the missing input. Do not `force: true` |
| Click "works" but nothing happens | Clicked before client-side hydration attached handlers (common with server-rendered frameworks) | Wait for a signal that the app is interactive, or better, have the app keep the control disabled until ready - users hit this too |
| Assertion sees the old value | One-shot read (`textContent()`, `isVisible()`, `count()`) instead of a retrying assertion | `await expect(locator).toHaveText(...)` / `toHaveCount(...)` |
| `waitForResponse` hangs | The promise was created after the action, so the response already happened | Create the promise before the click, then await it after |
| URL assertion fails right after a click | Read `page.url()` immediately | `await expect(page).toHaveURL(...)` |
| Fails around midnight, month-end, or on CI only | Time zone, locale, or real clock | Pin `timezoneId` / `locale`; control time with `page.clock` |
| Screenshot diff of a few pixels | Animation, caret, font loading, dynamic content, or different OS | `animations: 'disabled'`, mask volatile regions, generate baselines in the CI image |
| Passes alone, fails in the suite (or the reverse) | Shared state: same account, leftover data, a serial dependency | Isolate data per test; per-worker accounts; remove order dependence (section 5) |
| Fails only on retry | First attempt left server-side state the retry trips over | Make setup idempotent: create fresh data each attempt, clean up in fixtures |
| Times out only in CI | Too many workers for the machine, a cold server, slow third-party calls | Fewer CI workers, a `webServer` readiness URL, mock third parties |
| `net::ERR_CONNECTION_REFUSED` on the first test | Server not ready or wrong port/baseURL | Point `webServer.url` at a real readiness endpoint; verify `baseURL` |
| Randomly different list order | Unstable sort in the API or UI | Sort deterministically in the app, or assert as a set when order does not matter |

## 4. "Passes locally, fails in CI"

Go through the differences one at a time:

- **Headless vs headed**, and viewport: CI runs headless at the config's viewport; a local run someone watched with `--headed` may have used a larger window.
- **Speed:** CI machines are slower and share CPU; races that never show locally appear there. Reproduce with `--workers` equal to or greater than CI's and `--repeat-each`.
- **Environment:** time zone, locale, fonts, OS rendering (screenshots), environment variables, feature flags, seed data, secrets.
- **Server:** a dev server with hot reload locally vs a production build in CI (or the reverse); `reuseExistingServer` silently reusing a stale local server.
- **Auth:** expired or missing storage state; a setup project not declared as a dependency, so tests run signed out.
- **Browser versions:** browsers come from `npx playwright install`, matched to the installed Playwright. A lockfile drift between local and CI changes both.

Reproduce CI locally when possible: the official Playwright Docker image with the same Playwright version as `package.json`, `CI=1`, and the same `--project` and `--shard` arguments.

## 5. Order and parallelism problems

- Run the file in isolation, then the whole project, then the full suite with the CI worker count. Where it starts failing tells you the size of the shared state.
- `--shuffle` (recent versions) exposes hidden order dependence. Its seed is optional, so it swallows whatever comes next: `npx playwright test --shuffle e2e/cart.spec.ts` treats the file as the seed and shuffles the whole suite. Put filters first - `npx playwright test e2e/cart.spec.ts --shuffle` - and to replay an order, take the seed from the failing run's header line (`Running 12 tests using 4 workers, shuffle seed 444208114`) and pass it back: `npx playwright test e2e/cart.spec.ts --shuffle 444208114`. On versions without it, run suspect files in different combinations.
- Look for: one shared account whose settings tests change; records created with fixed names; tests that read "the first row"; `describe.serial` blocks that pass state through variables; global setup that mutates data mid-run.
- Fixes: unique data per test (`testInfo.workerIndex` plus a timestamp or random suffix), per-worker accounts, fixtures that clean up after themselves, and assertions scoped to the data the test created.

## 6. What is not a fix

- `page.waitForTimeout(...)` or any sleep: it moves the race, makes the suite slower, and fails again on a slower machine.
- Raising the global test or expect timeout to make one slow step pass. Set a per-assertion timeout for that genuinely slow step instead.
- `force: true`, script clicks, or `.first()` to get past an actionability or strictness error.
- Retries on their own. They keep the pipeline green while the flake rate grows. Keep the "flaky" count visible and add `--fail-on-flaky-tests` once the suite is clean.
- Waiting for `networkidle`: unrelated to what the user sees, and never settles on apps that poll or stream.

## 7. Quarantine without losing the test

When a fix cannot land right away, keep the signal:

```ts
test.fixme('applies coupon at checkout', async ({ page }) => { /* ... */ });   // skipped and reported as "fixme"
```

Link the tracking issue in a comment next to it, and give it an owner. Do not delete the test, and do not wrap it in `try/catch`. If the behavior is known to be broken in the app, `test.fail()` documents that and alerts you when it unexpectedly starts passing.
