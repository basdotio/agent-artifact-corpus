---
name: auth-for-browser-tests
description: Establish authenticated session for browser-based E2E: register/login via API (curl with cookie jar), then load cookie/state into browser context if supported, or document manual login / test-only bypass and use API verification. Include fallback when cookie/state injection is not supported; revert mocks and document. Use when verifying protected pages in browser tests.
---

# Auth for Browser Tests (Session / Cookie Injection)

When browser tests need to hit **protected pages**, establish auth in a consistent way instead of ad-hoc bypasses.

## Steps

1. **Create or reuse a test user via API**: Register and/or login with curl, save cookies (e.g. cookie jar).
2. **Check the browser tool's docs** for loading cookies or session state into the browser context.
3. **If supported**: Load state, then open the protected URL and run the flow.
4. **If not supported**: Document that "browser tests require manual login or a test-only route" and use API verification for the protected endpoints; optionally add a test-only "login as test user" that sets a cookie.
5. **When using mocks** for verification because the backend is down: **revert all mock/bypass changes** and document in progress what was done.

## Fallbacks

- Document clearly when cookie/state injection is not supported.
- Prefer API verification + documented limitation over leaving temporary auth bypass in code.

## Why This Matters

Multiple frontend tasks could not verify protected pages because login in the browser failed (network, CORS, or cookie handling). A single documented flow reduces ad-hoc bypasses and clarifies fallbacks.
