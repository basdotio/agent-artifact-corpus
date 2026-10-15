# Other E2E Frameworks: Applying the Rules Outside Playwright

Read this in Mode B when the repo's end-to-end suite already uses Cypress, WebdriverIO, Selenium, or TestCafe. Extend that suite. Adding Playwright next to it doubles the CI time, the flake surface, and the conventions a reviewer has to know, so do it only when the user asks for a migration.

The six test-writing rules (SKILL.md step 12) and the proof steps (SKILL.md step 13) are framework-neutral. This file translates them. Commands were checked against each project's current documentation; confirm against the versions in the lockfile, because these APIs move.

## Contents

1. Spotting the framework
2. The six rules, translated
3. The proof steps, translated
4. Framework-specific traps

## 1. Spotting the framework

| Signal in the repo | Framework |
|---|---|
| `cypress.config.{js,ts}`, a `cypress/` folder, specs named `*.cy.{js,ts}` | Cypress |
| `wdio.conf.{js,ts}`, `@wdio/*` packages | WebdriverIO |
| `selenium-webdriver` (Node), `selenium` (Python), `org.seleniumhq.selenium` (Java) dependencies | Selenium |
| `.testcaferc.{json,js}`, `testcafe` package, `fixture` / `test` with tagged templates | TestCafe |

Read the existing support files (custom commands, page objects, hooks) before writing anything: most of the house rules live there.

## 2. The six rules, translated

| Rule | Cypress | WebdriverIO | Selenium | TestCafe |
|---|---|---|---|---|
| **1. Locate like a user** | `cy.findByRole('button', { name: 'Save' })` via `@testing-library/cypress` (import `@testing-library/cypress/add-commands` in the support file); otherwise `cy.contains('button', 'Save')`, then a test-id attribute such as `data-cy` | `$('role/button[name="Save"]')` on recent versions, `$('aria/Save')` (accessible name), then a test-id attribute | No role locator: prefer a test-id attribute or an accessible attribute (`By.css('[aria-label="Close"]')`); XPath on text only as a last resort | `Selector('button').withText('Save')`, or `screen.getByRole` via `@testing-library/testcafe` |
| **2. Retrying assertions, no sleeps** | Chain `.should('be.visible')` / `.should('have.text', 'Saved')` on a query - queries and `.should` retry, `.then()` does not. Wait on a request with `cy.intercept(...).as('save')` + `cy.wait('@save')`, never `cy.wait(2000)` | `await expect($('...')).toBeDisplayed()`, `toHaveText(...)` - `expect-webdriverio` matchers wait. Never `browser.pause(ms)` | `WebDriverWait` with `ExpectedConditions` (Java) / `expected_conditions` (Python). Never `Thread.sleep` / `time.sleep`, and **never mix implicit and explicit waits** - the timeouts compound unpredictably | `await t.expect(Selector('#status').innerText).eql('Saved')` - assertions on selector properties retry. Never `t.wait(ms)` |
| **3. Isolate every test** | `testIsolation` (on by default) clears the page, cookies, and storage between tests; cache sign-in with `cy.session()`; create data with `cy.request()` in a hook | Each spec file gets a fresh session; within a file, clear state yourself (`browser.reloadSession()` or delete cookies and storage); sign in through the API and set cookies | A new driver session per test, or clear cookies and storage in teardown; set an auth cookie with `addCookie` after visiting the domain | `Role(url, async t => {...})` + `t.useRole(role)` caches sign-in; `Role.anonymous()` signs out |
| **4. Control what you do not own** | `cy.intercept(url, { statusCode: 500, body: {...} })`; `cy.clock()` / `cy.tick()` for time | `const mock = await browser.mock('**/api/items')` then `mock.respond([...], { statusCode: 500 })` - needs WebDriver BiDi (local Chromium or Firefox, or a grid that supports it) | No built-in mocking in classic WebDriver; use the BiDi network interception in recent bindings, or a stub server / proxy in front of the app | `RequestMock().onRequestTo(url).respond(body, 500)`, attached with `fixture.requestHooks(mock)` or `test.requestHooks(mock)` |
| **5. Structure** | Custom commands (`Cypress.Commands.add`) for repeated multi-step actions; keep assertions in the spec | Page objects with getters returning `$()`; keep `expect` in the spec | Page objects with locators and user-level methods | Page models exporting `Selector`s; keep assertions in the test |
| **6. Debuggable failures** | `cypress run` saves screenshots on failure by default; video is off by default in recent versions (`video: true`) | `afterTest` hook calling `browser.saveScreenshot()` on failure; the reporters you have configured | Screenshot in teardown on failure (`TakesScreenshot` / `save_screenshot`), plus browser logs where the driver exposes them | `--screenshots path=artifacts,takeOnFails=true`, `--video artifacts` |

## 3. The proof steps, translated

| Step | Cypress | WebdriverIO | Selenium | TestCafe |
|---|---|---|---|---|
| Run one spec headless (exits on its own) | `npx cypress run --spec cypress/e2e/checkout.cy.ts` | `npx wdio run wdio.conf.ts --spec ./test/specs/checkout.e2e.ts` | Your runner's single-test filter: `pytest tests/test_checkout.py::test_declined`, `mvn test -Dtest=CheckoutTest#declined` | `npx testcafe chrome:headless tests/checkout.test.ts` |
| Lint | `eslint-plugin-cypress` (`no-unnecessary-waiting`, `unsafe-to-chain-command`, `no-assigning-return-values`) | `eslint-plugin-wdio`, plus `@typescript-eslint/no-floating-promises` - every command must be awaited | Your language's linter; ban sleeps in review | `@typescript-eslint/no-floating-promises` - every `t.*` chain must be awaited |
| See it fail | Break the behavior, confirm the failing `.should` names what is wrong | Same, with the failing matcher | Same, with the failing wait or assert | Same, with the failing `t.expect` |
| Shake out flake, retries off | `@cypress/grep` burn mode: `npx cypress run --spec <file> --expose grep="declined card",burn=10 --config retries=0` (older Cypress and `@cypress/grep` versions take `--env` instead of `--expose`) | `npx wdio run wdio.conf.ts --spec <file> --repeat 10` with `specFileRetries` and `mochaOpts.retries` at 0 | `pytest tests/test_checkout.py --count=10` with `pytest-repeat`, and no `--reruns`; JUnit 5 `@RepeatedTest(10)` | Loop the run in the shell (`for i in $(seq 10); do npx testcafe ... || break; done`) without `--quarantine-mode` |
| Run like CI | Every configured browser, headless, with CI env vars | Every capability in the config | Against the same grid or driver versions as CI | Every browser in the CI command |

## 4. Framework-specific traps

- **Cypress commands are not promises.** Do not `await` them and do not assign their return values (`const btn = cy.get(...)` is a chainer, not an element); use `.then()` or aliases. This is the reverse of the Playwright rule, and mixing the two styles is a common bug in repos that have both.
- **`cypress open`, `wdio`'s `browser.debug()`, and TestCafe's `--debug-mode` / `t.debug()` wait for a human** - offer them to the user, never run them from an agent shell. The same applies to any headed run you cannot watch.
- **Retries hide flakes everywhere.** Cypress `retries: { runMode, openMode }`, WebdriverIO `specFileRetries` / `mochaOpts.retries`, `pytest-rerunfailures`, and TestCafe `--quarantine-mode` all turn a flaky test green. Turn them off for the stability run and report the flaky count.
- **Selenium's implicit wait is global.** If the suite already sets one, do not add explicit waits on top without removing it first - talk to the user, because changing it affects every test.
- **WebdriverIO mocks need BiDi.** On a cloud grid without WebDriver BiDi support, `browser.mock` fails; check the provider before relying on it.
