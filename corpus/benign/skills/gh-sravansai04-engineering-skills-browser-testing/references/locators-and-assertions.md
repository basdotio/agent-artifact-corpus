# Locators and Assertions Cheat Sheet

Read this whenever you write or review a locator or an assertion. Examples are TypeScript (`@playwright/test`) with the Python (`pytest-playwright`, sync API) spelling alongside. Java and .NET use the same method names in their own casing (`getByRole`, `GetByRoleAsync`).

## Contents

1. Locator priority
2. Implicit ARIA roles
3. `getByRole` options and text matching
4. Narrowing: filter, chain, combine
5. Frames, shadow DOM, test ids
6. Auto-retrying assertions
7. Assertion helpers: timeouts, soft, poll, toPass, waiting for responses
8. Anti-pattern rewrites
9. Other frameworks

## 1. Locator priority

Pick the first one that uniquely and stably identifies the element.

| Rank | TypeScript | Python | Use for |
|---|---|---|---|
| 1 | `page.getByRole('button', { name: 'Save' })` | `page.get_by_role("button", name="Save")` | Anything interactive or structural: buttons, links, headings, form controls, dialogs, rows |
| 2 | `page.getByLabel('Email')` | `page.get_by_label("Email")` | Form fields with a `<label>`, `aria-label`, or `aria-labelledby` |
| 3 | `page.getByPlaceholder('Search')` | `page.get_by_placeholder("Search")` | Inputs with no label (also a finding for `frontend:accessibility-review`) |
| 3 | `page.getByText('Order placed')` | `page.get_by_text("Order placed")` | Non-interactive text: messages, paragraphs, list content |
| 3 | `page.getByAltText('Company logo')` | `page.get_by_alt_text("Company logo")` | Images |
| 3 | `page.getByTitle('Close')` | `page.get_by_title("Close")` | Elements identified only by a `title` |
| 4 | `page.getByTestId('cart-total')` | `page.get_by_test_id("cart-total")` | No stable user-facing handle exists (canvas widgets, repeated icon buttons, numbers that change) |
| 5 | `page.locator('css=...')` / `page.locator('xpath=...')` | `page.locator("...")` | Last resort. Add a comment explaining why nothing above works |

Why roles first: users and assistive technology perceive the page through role and accessible name. A role-based locator keeps working when classes, markup nesting, or the CSS framework change, and it breaks when the control stops being operable by a screen reader - which is a regression you want to hear about.

## 2. Implicit ARIA roles

Native elements carry roles without any `role=` attribute.

| HTML | Role | Notes |
|---|---|---|
| `<button>`, `<input type="button" / "submit" / "reset">` | `button` | |
| `<a href="...">` | `link` | An `<a>` **without** `href` has no link role |
| `<h1>` ... `<h6>` | `heading` | Filter with `level: 2` |
| `<input type="text" / "email" / "tel" / "url">`, `<textarea>` | `textbox` | |
| `<input type="search">` | `searchbox` | |
| `<input type="number">` | `spinbutton` | |
| `<input type="range">` | `slider` | |
| `<input type="checkbox">` | `checkbox` | `checked: true` |
| `<input type="radio">` | `radio` | |
| `<select>` (single, no `size` > 1) | `combobox` | Use `selectOption()` |
| `<select multiple>` | `listbox` | |
| `<option>` | `option` | `selected: true` |
| `<img alt="...">` | `img` | Empty `alt=""` makes it presentational |
| `<table>`, `<tr>`, `<td>`, `<th>` | `table`, `row`, `cell`, `columnheader` / `rowheader` | |
| `<ul>` / `<ol>`, `<li>` | `list`, `listitem` | |
| `<nav>`, `<main>`, `<aside>` | `navigation`, `main`, `complementary` | |
| `<header>` / `<footer>` (not inside article or section) | `banner` / `contentinfo` | |
| `<form>` with an accessible name | `form` | |
| `<section>` with an accessible name | `region` | |
| `<dialog>` | `dialog` | |
| `<progress>` | `progressbar` | |

Custom widgets need explicit roles (`role="tab"`, `role="switch"`, `role="menuitem"`, `role="alert"`). If the role you expect is not there, check the accessibility snapshot (`await page.locator('body').ariaSnapshot()`, or the MCP snapshot tool) to see what the browser actually exposes.

## 3. `getByRole` options and text matching

```ts
page.getByRole('heading', { name: 'Billing', level: 2 });
page.getByRole('checkbox', { name: 'Remember me', checked: true });
page.getByRole('button', { name: 'Menu', expanded: false });
page.getByRole('tab', { name: 'Usage', selected: true });
page.getByRole('button', { name: 'Submit', disabled: true });
page.getByRole('button', { name: 'Bold', pressed: true });
page.getByRole('button', { name: /^Delete/ });          // regex
page.getByRole('link', { name: 'Docs', exact: true });  // exact, case-sensitive
page.getByRole('dialog', { includeHidden: true });      // include aria-hidden / hidden elements
```

```python
page.get_by_role("heading", name="Billing", level=2)
page.get_by_role("checkbox", name="Remember me", checked=True)
page.get_by_role("button", name=re.compile(r"^Delete"))
page.get_by_role("link", name="Docs", exact=True)
```

Text matching for `name`, `getByText`, `getByLabel`, and the other text-based locators: a string matches **case-insensitively as a substring** after whitespace normalization; `exact: true` requires a case-sensitive whole-string match; a regex gives full control. Substring matching is why `getByRole('button', { name: 'Save' })` also matches "Save draft" - add `exact: true` or scope it when that matters.

## 4. Narrowing: filter, chain, combine

```ts
// Scope by containing text, then find within the match.
const row = page.getByRole('row').filter({ hasText: 'Ada Lovelace' });
await row.getByRole('button', { name: 'Edit' }).click();

// Scope by a descendant locator, or exclude.
page.getByRole('listitem').filter({ has: page.getByRole('heading', { name: 'Pro plan' }) });
page.getByRole('listitem').filter({ hasNot: page.getByText('Sold out') });
page.getByRole('listitem').filter({ hasNotText: 'Archived' });
page.getByRole('button', { name: 'Close' }).filter({ visible: true });

// Match two conditions at once, or either of two.
page.getByRole('button').and(page.getByTitle('Subscribe'));
const newEmail = page.getByRole('button', { name: 'New' });
const dialog = page.getByText('Confirm security settings');
await expect(newEmail.or(dialog).first()).toBeVisible();

// Position - only when order IS the behavior under test.
page.getByRole('listitem').first();
page.getByRole('listitem').last();
page.getByRole('listitem').nth(2);   // zero-based
```

```python
row = page.get_by_role("row").filter(has_text="Ada Lovelace")
row.get_by_role("button", name="Edit").click()
page.get_by_role("listitem").filter(has=page.get_by_role("heading", name="Pro plan"))
```

**Strictness.** Any action or assertion on a locator that resolves to more than one element throws a strict-mode violation. That error is useful: it means the locator is ambiguous. Fix it by scoping (filter, chain from a container) rather than `.first()`, which silently starts acting on whichever element happens to come first.

## 5. Frames, shadow DOM, test ids

```ts
// iframes: enter the frame, then locate as usual
const card = page.frameLocator('iframe[title="Payment"]');
await card.getByLabel('Card number').fill('4242 4242 4242 4242');
// or from an existing locator to the <iframe> element
await page.getByTitle('Payment').contentFrame().getByLabel('Card number').fill('4242 4242 4242 4242');
```

- Open shadow roots are pierced automatically by Playwright locators (XPath does not pierce shadow roots).
- Test ids default to the `data-testid` attribute. Change it once in config: `use: { testIdAttribute: 'data-test' }`. Test ids are a contract with the app: name them for meaning (`cart-total`), not position (`div-3`).

## 6. Auto-retrying assertions

These re-check until they pass or the assertion timeout (5 s by default) expires. Always `await` them.

| Assertion (TypeScript) | Python | Passes when |
|---|---|---|
| `toBeVisible()` / `toBeHidden()` | `to_be_visible()` / `to_be_hidden()` | Rendered and visible / absent or hidden |
| `toBeAttached()` | `to_be_attached()` | Present in the DOM, visible or not |
| `toBeEnabled()` / `toBeDisabled()` | `to_be_enabled()` / `to_be_disabled()` | |
| `toBeEditable()` | `to_be_editable()` | |
| `toBeChecked()` | `to_be_checked()` | Pass `{ checked: false }` for unchecked |
| `toBeFocused()` | `to_be_focused()` | |
| `toBeEmpty()` | `to_be_empty()` | No text and no children, or empty input |
| `toBeInViewport()` | `to_be_in_viewport()` | Intersects the viewport |
| `toHaveText(t)` | `to_have_text(t)` | Full text matches (string, regex, or array for a list of elements) |
| `toContainText(t)` | `to_contain_text(t)` | Text contains `t` |
| `toHaveValue(v)` / `toHaveValues([...])` | `to_have_value` / `to_have_values` | Input value / selected options of a multi-select |
| `toHaveCount(n)` | `to_have_count(n)` | Locator resolves to exactly `n` elements |
| `toHaveAttribute(name, value)` | `to_have_attribute` | |
| `toHaveClass(c)` / `toContainClass(c)` | `to_have_class` / `to_contain_class` | Prefer user-visible state over classes |
| `toHaveCSS(prop, value)` | `to_have_css` | Computed style |
| `toHaveId(id)` / `toHaveJSProperty(k, v)` | `to_have_id` / `to_have_js_property` | |
| `toHaveRole(r)` | `to_have_role(r)` | |
| `toHaveAccessibleName(n)` | `to_have_accessible_name(n)` | |
| `toHaveAccessibleDescription(d)` | `to_have_accessible_description(d)` | |
| `toHaveAccessibleErrorMessage(m)` | `to_have_accessible_error_message(m)` | Field's `aria-errormessage` content |
| `toMatchAriaSnapshot(yaml)` | `to_match_aria_snapshot(yaml)` | Accessibility tree matches a template |
| `toHaveScreenshot()` | (no Python equivalent) | Visual comparison against a stored baseline |
| `expect(page).toHaveURL(u)` | `expect(page).to_have_url(u)` | |
| `expect(page).toHaveTitle(t)` | `expect(page).to_have_title(t)` | |
| `expect(response).toBeOK()` | `expect(response).to_be_ok()` | API response status 2xx |

`toHaveText` normalizes whitespace and matches the full text; `toContainText` matches a substring. Both accept an array to check every element of a list in order:

```ts
await expect(page.getByRole('listitem')).toHaveText(['Apples', 'Pears', 'Plums']);
```

Negation retries too: `await expect(spinner).not.toBeVisible()` and `await expect(spinner).toBeHidden()` both wait for the spinner to go away.

**Generic matchers do not retry.** `expect(value).toBe(...)`, `toEqual`, `toContain` evaluate once. Use them only on values that are already final (a parsed API body, a number you computed), never on something you just read from a page that may still be changing.

## 7. Assertion helpers

```ts
// Per-assertion timeout for a known-slow outcome (prefer this to raising the global timeout)
await expect(page.getByText('Report ready')).toBeVisible({ timeout: 30_000 });

// Custom message shown on failure
await expect(page.getByRole('alert'), 'save confirmation should appear').toHaveText('Saved');

// Soft assertion: record the failure, keep running, fail the test at the end
await expect.soft(page.getByTestId('total')).toHaveText('$42.00');

// Poll a non-DOM condition
await expect.poll(async () => (await page.request.get('/api/jobs/123')).status(), {
  timeout: 15_000,
}).toBe(200);

// Retry a whole block until it passes
await expect(async () => {
  const res = await page.request.get('/api/health');
  expect(res.status()).toBe(200);
}).toPass({ timeout: 20_000 });

// Wait for a specific response caused by an action: start waiting BEFORE the action
const saved = page.waitForResponse((r) => r.url().endsWith('/api/profile') && r.request().method() === 'PUT');
await page.getByRole('button', { name: 'Save' }).click();
expect((await saved).status()).toBe(200);
```

```python
with page.expect_response(lambda r: r.url.endswith("/api/profile") and r.request.method == "PUT") as info:
    page.get_by_role("button", name="Save").click()
assert info.value.status == 200
```

## 8. Anti-pattern rewrites

| Instead of | Write | Why |
|---|---|---|
| `expect(page.getByText('Saved')).toBeVisible()` (no `await`) | `await expect(page.getByText('Saved')).toBeVisible()` | Without `await` the assertion does not gate the next step and may pass on a later page state; failures arrive out of order. Lint with `missing-playwright-await` |
| `await page.waitForTimeout(2000)` | `await expect(page.getByText('Saved')).toBeVisible()` | Sleeps are too short on slow CI and waste time everywhere else |
| `expect(await el.isVisible()).toBe(true)` | `await expect(el).toBeVisible()` | One-shot read races the render |
| `expect(await el.textContent()).toBe('3 items')` | `await expect(el).toHaveText('3 items')` | Same race |
| `page.locator('.btn-primary.mt-2')` | `page.getByRole('button', { name: 'Checkout' })` | Styling classes change for unrelated reasons |
| `page.locator('#root > div:nth-child(3) > button')` | Scope from a meaningful container, then role | Structural paths break on any layout change |
| `page.getByRole('button').nth(4)` | `row.getByRole('button', { name: 'Edit' })` | Index depends on everything else on the page |
| `.first()` to silence strict mode | A narrower locator | `.first()` hides ambiguity instead of fixing it |
| `click({ force: true })` | Find out what covers or disables the element | Forcing skips the actionability checks a user would hit |
| `await page.waitForLoadState('networkidle')` | Assert the element or response you need | "No requests for 500 ms" is unrelated to readiness and never settles on apps that poll |
| `page.$('...')` / `page.$$eval(...)` | Locators | Element handles do not auto-wait or re-resolve |
| Logging in through the UI in every test | Setup project + `storageState` | Slow, and every test then also tests login |

## 9. Other frameworks

The principles transfer even when the repo is not on Playwright: Testing Library's `findByRole` / `findByText` queries already retry and rank roles first (use them for component tests, see `implementation:tdd`). Follow the existing e2e framework rather than introducing Playwright alongside it unless the user asks. `other-e2e-frameworks.md` maps every rule here to Cypress, WebdriverIO, Selenium, and TestCafe.
