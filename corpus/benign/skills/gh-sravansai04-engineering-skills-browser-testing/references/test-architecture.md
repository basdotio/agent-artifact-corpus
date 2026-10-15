# Test Architecture: Config, Auth, Fixtures, Mocking, CI

Read this when setting up Playwright in a project or when adding or changing config, authentication, fixtures, page objects, network mocking, time control, visual comparisons, parallelism, or CI. Match the project's existing patterns where they exist; these are defaults for when they do not.

## Contents

1. Installing
2. A baseline config
3. Authentication with a setup project
4. Fixtures
5. Page objects (when, and how small)
6. Network mocking
7. Time, randomness, and animation
8. Visual and structural snapshots
9. Parallelism, sharding, and tags
10. CI essentials
11. Python (pytest-playwright) equivalents

## 1. Installing

```bash
npm init playwright@latest            # scaffolds config, example spec, optional CI workflow
npx playwright install --with-deps    # browsers plus OS libraries (use in CI and fresh Linux boxes)
```

Python: `pip install pytest-playwright` then `playwright install --with-deps chromium`.

Using an installed branded browser instead (`use: { channel: 'chrome' }`) skips the browser download, but video recording still needs Playwright's own ffmpeg build: `npx playwright install ffmpeg`. Without it, every test fails at `newPage` once `video` is enabled.

## 2. A baseline config

```ts
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.PORT ?? 3000);

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,                       // tests must be independent - SKILL.md step 12, rule 3
  forbidOnly: !!process.env.CI,              // a stray test.only fails CI instead of skipping the suite
  retries: process.env.CI ? 2 : 0,           // retries surface flakes in the report; locally you want to see them fail
  workers: process.env.CI ? 2 : undefined,   // tune to the CI machine; undefined = half the cores
  reporter: process.env.CI ? [['blob'], ['github']] : [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: `http://localhost:${PORT}`,     // lets tests call page.goto('/settings')
    trace: 'on-first-retry',                 // 'retain-on-failure' if you run without retries
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // testIdAttribute: 'data-test',         // only if the app does not use data-testid
  },
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.ts/ },
    { name: 'chromium', use: { ...devices['Desktop Chrome'], storageState: 'playwright/.auth/user.json' }, dependencies: ['setup'] },
    { name: 'mobile-safari', use: { ...devices['iPhone 13'], storageState: 'playwright/.auth/user.json' }, dependencies: ['setup'] },
  ],
  webServer: {
    command: 'npm run start',                // a production-like server is less flaky than a dev server with HMR;
                                             // it serves the last build, so run `npm run build` first (the CI job below does)
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,    // locally, reuse the server you already have running
    timeout: 120_000,
  },
});
```

Timeouts worth knowing: the test timeout (30 s default, `timeout` in config), the assertion timeout (5 s default, `expect: { timeout }`), and `use.actionTimeout` / `use.navigationTimeout` (no limit by default, so actions are bounded by the test timeout). Raise the one that matches the slow thing, locally (`{ timeout }` on a single assertion or `test.slow()` on a test), rather than inflating everything.

## 3. Authentication with a setup project

Sign in once, save the browser state, reuse it in every test.

```ts
// e2e/auth.setup.ts
import { test as setup, expect } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

setup('sign in', async ({ page }) => {
  const { E2E_USER, E2E_PASSWORD } = process.env;
  // Fail loudly here; otherwise the form gets "undefined" and every dependent test runs signed out.
  if (!E2E_USER || !E2E_PASSWORD) throw new Error('E2E_USER / E2E_PASSWORD are not set');

  await page.goto('/login');
  await page.getByLabel('Email').fill(E2E_USER);
  await page.getByLabel('Password').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('button', { name: 'Account menu' })).toBeVisible(); // proof the session exists
  await page.context().storageState({ path: authFile });
});
```

```bash
mkdir -p playwright/.auth && echo 'playwright/.auth' >> .gitignore   # the file holds live session cookies
```

- **Faster:** sign in through the API with the `request` fixture and save `request.storageState({ path })`, if the app issues cookies from an API endpoint.
- **Several roles:** one setup test per role writing `admin.json`, `member.json`; select per file with `test.use({ storageState: 'playwright/.auth/admin.json' })`, or open both in one test with `browser.newContext({ storageState })` for "admin changes it, member sees it" flows.
- **Signed-out tests:** `test.use({ storageState: { cookies: [], origins: [] } })`.
- **Tests that change account-level state** (password, preferences, plan): give each worker its own account, keyed by `test.info().parallelIndex`, in a worker-scoped fixture, so parallel workers never fight over one user.
- **Apps that keep auth in IndexedDB:** `storageState({ path, indexedDB: true })`.
- Credentials come from environment variables or CI secrets, never from the repository.

## 4. Fixtures

Fixtures give a test exactly what it needs and clean up even when it fails. Prefer them to `beforeEach` chains.

```ts
// e2e/fixtures.ts
import { test as base, expect } from '@playwright/test';

type Project = { id: string; name: string };

export const test = base.extend<{ project: Project; failOnPageErrors: void }>({
  // Create test data through the API, hand it to the test, delete it afterwards.
  project: async ({ request }, use, testInfo) => {
    const name = `e2e-${testInfo.workerIndex}-${Date.now()}`;          // unique per test, safe in parallel
    const res = await request.post('/api/projects', { data: { name } });
    expect(res.ok()).toBeTruthy();
    const project = (await res.json()) as Project;
    await use(project);
    await request.delete(`/api/projects/${project.id}`);              // runs even if the test failed
  },

  // Automatic fixture: any uncaught exception in the page fails the test.
  failOnPageErrors: [async ({ page }, use) => {
    const errors: string[] = [];
    page.on('pageerror', (e) => errors.push(e.message));
    await use();
    expect(errors, 'uncaught errors in the page').toEqual([]);
  }, { auto: true }],
});

export { expect };
```

```ts
// e2e/projects.spec.ts
import { test, expect } from './fixtures';

test('renaming a project updates the sidebar', async ({ page, project }) => {
  await page.goto(`/projects/${project.id}/settings`);
  await page.getByLabel('Project name').fill(`${project.name} renamed`);
  await page.getByRole('button', { name: 'Save' }).click();
  await expect(page.getByRole('navigation').getByRole('link', { name: `${project.name} renamed` })).toBeVisible();
});
```

Worker-scoped fixtures (`{ scope: 'worker' }`) run once per worker - use them for expensive shared setup such as a per-worker account, never for state that one test mutates and another reads.

## 5. Page objects (when, and how small)

Add a page object when the same multi-step interaction appears in several spec files. Keep it thin: locators plus user-level actions. Leave assertions in the test so each spec still reads as the behavior it checks.

```ts
// e2e/pages/checkout-page.ts
import type { Page, Locator } from '@playwright/test';

export class CheckoutPage {
  readonly cardNumber: Locator;
  readonly payButton: Locator;
  readonly status: Locator;

  constructor(private readonly page: Page) {
    this.cardNumber = page.getByLabel('Card number');
    this.payButton = page.getByRole('button', { name: /^Pay/ });
    this.status = page.getByRole('status');
  }

  async goto() {
    await this.page.goto('/checkout');
  }

  async payWith(card: string) {
    await this.cardNumber.fill(card);
    await this.payButton.click();
  }
}
```

```ts
test('declined card shows an error and keeps the cart', async ({ page }) => {
  const checkout = new CheckoutPage(page);
  await checkout.goto();
  await checkout.payWith('4000 0000 0000 0002');
  await expect(checkout.status).toHaveText(/declined/i);
  await expect(page).toHaveURL(/\/checkout$/);
});
```

Expose page objects through a fixture (`checkoutPage: async ({ page }, use) => use(new CheckoutPage(page))`) once several specs use them. Avoid deep inheritance trees and "god" page objects that wrap every element on a page.

## 6. Network mocking

Mock what you do not own and states you cannot easily produce. Keep your own backend real on the main journeys.

```ts
// Replace a response entirely
await page.route('**/api/items', (route) => route.fulfill({ json: [] }));            // empty state

// Force an error state
await page.route('**/api/items', (route) => route.fulfill({ status: 500, json: { error: 'boom' } }));

// Patch a real response
await page.route('**/api/items', async (route) => {
  const response = await route.fetch();
  const json = await response.json();
  await route.fulfill({ response, json: [...json, { id: 'extra', name: 'Injected item' }] });
});

// Block noisy third parties for every page in the context
await context.route(/(analytics|tracking)\./, (route) => route.abort());

// Slow a request to test loading UI (the one legitimate in-test delay: it shapes the network, not the test)
await page.route('**/api/report', async (route) => {
  await new Promise((r) => setTimeout(r, 2_000));
  await route.continue();
});
```

- Register routes **before** the navigation or action that triggers the request.
- Assert on the request your UI sent, not only on what it rendered: `const req = page.waitForRequest('**/api/signup'); ... expect((await req).postDataJSON()).toEqual({ email: 'a@b.co' })`.
- Record and replay a whole API surface with a HAR: `await page.routeFromHAR('e2e/hars/items.har', { url: '**/api/**', update: true })` once against a real backend, then `update: false` in tests. Re-record when the API changes.
- Service workers can intercept requests before `page.route` sees them; set `use: { serviceWorkers: 'block' }` when mocking apps with an active service worker.
- WebSockets: `page.routeWebSocket(url, (ws) => { ... })`.

## 7. Time, randomness, and animation

```ts
await page.clock.setFixedTime(new Date('2026-03-01T09:00:00Z'));   // Date.now() and new Date() are frozen; timers still run

await page.clock.install({ time: new Date('2026-03-01T09:00:00Z') }); // full control: call before page scripts run
await page.goto('/session');
await page.clock.fastForward('30:00');                                 // jump 30 minutes, e.g. to trigger an idle timeout
await expect(page.getByRole('dialog', { name: 'Session expired' })).toBeVisible();
```

- Pin `timezoneId` and `locale` in `use` so date and number formatting do not depend on the CI machine.
- Seed or stub randomness the UI depends on (shuffled lists, generated names) or assert on properties that do not depend on it.
- Use `reducedMotion: 'reduce'` in `use` when animations get in the way, and `animations: 'disabled'` for screenshots.

## 8. Visual and structural snapshots

```ts
await expect(page).toHaveScreenshot('dashboard.png', {
  fullPage: true,
  mask: [page.getByTestId('last-updated')],   // hide volatile regions
  maxDiffPixelRatio: 0.01,
  animations: 'disabled',
});

await expect(page.getByRole('navigation')).toMatchAriaSnapshot(`
  - navigation:
    - link "Home"
    - link "Projects"
    - link "Settings"
`);
```

- Screenshot baselines are per browser and per OS (the file name carries both). Generate and update them in the same environment CI uses - typically the official Playwright Docker image - with `npx playwright test --update-snapshots`. Baselines from a laptop will not match Linux CI.
- Visual tests are expensive to maintain. Reserve them for layout-critical surfaces; for "the right things are on the page", an ARIA snapshot is cheaper and survives restyling.

## 9. Parallelism, sharding, and tags

- `fullyParallel: true` runs tests within a file in parallel too. It requires independent tests and gives sharding even load.
- `test.describe.configure({ mode: 'serial' })` only for steps that genuinely cannot be split (a multi-page wizard against a backend you cannot seed). A serial group retries as a whole and hides which step is broken.
- Shard across machines: `npx playwright test --shard=2/4`. Each shard writes a `blob` report; merge them with `npx playwright merge-reports --reporter html ./all-blob-reports`.
- Tag tests and filter by tag:

```ts
test('checkout with a saved card', { tag: ['@smoke', '@payments'] }, async ({ page }) => { /* ... */ });
```

```bash
npx playwright test --grep @smoke
npx playwright test --grep-invert @slow
npx playwright test --only-changed=origin/main   # local fast loop: spec files changed since main
npx playwright test --last-failed                # re-run just what failed last time
```

## 10. CI essentials

GitHub Actions with four shards and a merged report. It pairs with the section 2 config (production-like `webServer`) and the section 3 setup project (credentials from secrets). Action versions follow Playwright's own sharding guide at the time of writing; pin whatever majors are current.

```yaml
jobs:
  e2e:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        shardIndex: [1, 2, 3, 4]
        shardTotal: [4]
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with: { node-version: lts/* }
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run build                     # webServer runs `npm run start`, which serves this build
      - run: npx playwright test --shard=${{ matrix.shardIndex }}/${{ matrix.shardTotal }}
        env:
          E2E_USER: ${{ secrets.E2E_USER }}
          E2E_PASSWORD: ${{ secrets.E2E_PASSWORD }}
      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: blob-report-${{ matrix.shardIndex }}
          path: blob-report
          retention-days: 7

  merge-reports:
    if: ${{ !cancelled() }}
    needs: [e2e]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with: { node-version: lts/* }
      - run: npm ci
      - uses: actions/download-artifact@v5
        with:
          path: all-blob-reports
          pattern: blob-report-*
          merge-multiple: true
      - run: npx playwright merge-reports --reporter html ./all-blob-reports
      - uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report
          retention-days: 14
```

- Upload artifacts even when tests fail (`!cancelled()`), or there is nothing to debug.
- Cache `node_modules` if you like, but let `npx playwright install` manage browsers so their version always matches the installed Playwright.
- Keep the flaky count visible. A retry that passes is reported as "flaky", not "passed"; add `--fail-on-flaky-tests` once the suite is clean, so new flakes cannot slip in.

## 11. Python (pytest-playwright) equivalents

```python
# conftest.py
import pytest

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {**browser_context_args, "viewport": {"width": 1280, "height": 800}, "locale": "en-US", "timezone_id": "UTC"}
```

```python
# test_signup.py
import re
from playwright.sync_api import Page, expect

def test_empty_email_shows_validation(page: Page):
    page.goto("/signup")
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_role("alert")).to_have_text("Email is required")
    expect(page).to_have_url(re.compile(r"/signup$"))

def test_empty_state_when_no_items(page: Page):
    page.route("**/api/items", lambda route: route.fulfill(json=[]))
    page.goto("/items")
    expect(page.get_by_text("No items yet")).to_be_visible()
```

```bash
pytest --base-url http://localhost:3000 --browser chromium --browser webkit \
  --tracing retain-on-failure --screenshot only-on-failure --video retain-on-failure
pytest --numprocesses auto     # parallel, requires pytest-xdist
playwright trace open test-results/<test-dir>/trace.zip   # then trace actions --errors-only, trace errors, ...
playwright show-trace test-results/<test-dir>/trace.zip   # graphical viewer - human at the keyboard only
```
