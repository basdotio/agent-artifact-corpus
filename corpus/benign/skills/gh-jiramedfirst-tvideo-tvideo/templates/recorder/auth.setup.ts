import { test as setup, expect } from '@playwright/test';
import { existsSync, mkdirSync } from 'node:fs';

/**
 * Logs in once and saves the session to .auth/state.json, so every clip starts
 * already signed in and the video doesn't open on a login form. Skipped when
 * TV_USERNAME/TV_PASSWORD are unset (public apps, or a clip that films login).
 *
 * The defaults match most login forms; override per app with
 *   TV_LOGIN_PATH (default "login"), TV_USER_SELECTOR, TV_PASS_SELECTOR, TV_SUBMIT_SELECTOR.
 * TV_LOGGED_IN_SELECTOR (optional): success = this selector is visible, for apps
 * that stay on a /login-like URL after sign-in.
 * With no credentials but a saved .auth/state.json, it only checks the session is
 * still valid, so an expired one fails here with a clear message, not mid-clip.
 * Credentials come from the environment only — never write them into a file.
 */
setup('sign in', async ({ page, browser }) => {
  const user = process.env.TV_USERNAME;
  const pass = process.env.TV_PASSWORD;
  const loggedIn = process.env.TV_LOGGED_IN_SELECTOR;
  if (!user || !pass) {
    setup.skip(!existsSync('.auth/state.json'), 'No TV_USERNAME/TV_PASSWORD or saved session — clips run signed out.');
    const baseURL = setup.info().project.use.baseURL!;
    const ctx = await browser.newContext({ storageState: '.auth/state.json', baseURL });
    const p = await ctx.newPage();
    await p.goto('');
    await p.waitForLoadState('networkidle').catch(() => {});
    // Expired = bounced to another origin (an SSO / IdP page) or to the app's own
    // login path. Matching the word "login" anywhere would fail an app whose base
    // URL contains it and pass an IdP at /signin.
    const at = new URL(p.url());
    const loginPath = new URL(process.env.TV_LOGIN_PATH ?? 'login', baseURL).pathname;
    const ok = loggedIn
      ? await expect(p.locator(loggedIn).first()).toBeVisible({ timeout: 15_000 }).then(() => true, () => false)
      : at.origin === new URL(baseURL).origin && !at.pathname.startsWith(loginPath);
    await ctx.close();
    if (!ok) throw new Error('Saved session expired — delete .auth/state.json and log in again (or rerun codegen --save-storage).');
    return;
  }

  mkdirSync('.auth', { recursive: true });
  await page.goto(process.env.TV_LOGIN_PATH ?? 'login');
  const userField = page.locator(process.env.TV_USER_SELECTOR ?? 'input[name="username"], input[name="email"], input[type="email"]').first();
  const passField = page.locator(process.env.TV_PASS_SELECTOR ?? 'input[type="password"]').first();
  await userField.fill(user!);
  await passField.fill(pass!);
  await page.locator(process.env.TV_SUBMIT_SELECTOR ?? 'button[type="submit"]').first().click();
  // Signed in = we left the login page. Apps with a second factor need a clip-level step instead.
  if (loggedIn) await expect(page.locator(loggedIn).first()).toBeVisible({ timeout: 60_000 });
  else await expect(page).not.toHaveURL(/login/i, { timeout: 60_000 });
  await page.context().storageState({ path: '.auth/state.json' });
});
