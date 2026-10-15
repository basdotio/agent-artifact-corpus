import { existsSync } from 'node:fs';
import { defineConfig, devices } from '@playwright/test';

/**
 * TVideo recorder. Every knob is an env var so one template serves any app:
 *
 *   TV_BASE_URL   app root, e.g. https://staging.example.com/app/  (required)
 *   TV_LOCALE     browser locale for the UI language, e.g. th-TH, en-US (default en-US)
 *   TV_USERNAME / TV_PASSWORD   if set, auth.setup.ts logs in once and every clip
 *                 starts already signed in (the login itself isn't filmed).
 *                 Or save a session by hand into .auth/state.json (SSO/captcha logins).
 *   TV_VIEWPORT   "WIDTHxHEIGHT" of the page and the video (default 1280x800)
 *   TV_REHEARSE=1 dry run: no video, no pauses — proves every selector first
 *
 * Clip specs live in clips/*.spec.ts and navigate with RELATIVE paths
 * ("orders/new", not "/orders/new") so a base path like /app/ is kept.
 */
const REHEARSE = process.env.TV_REHEARSE === '1';
const base = process.env.TV_BASE_URL ?? '';
if (!base) throw new Error('Set TV_BASE_URL (the app root the clips will open).');
const baseURL = base.endsWith('/') ? base : `${base}/`;
const hasLogin = Boolean(process.env.TV_USERNAME && process.env.TV_PASSWORD);
// A session saved by hand (`npx playwright codegen --save-storage=.auth/state.json <url>`)
// is used too — the route for SSO / captcha logins that automation can't pass.
const hasSession = hasLogin || existsSync('.auth/state.json');
const vp = /^(\d+)x(\d+)$/.exec(process.env.TV_VIEWPORT ?? '1280x800');
if (!vp) throw new Error(`TV_VIEWPORT must look like 1280x800, got "${process.env.TV_VIEWPORT}".`);
const viewport = { width: Number(vp[1]), height: Number(vp[2]) };

export default defineConfig({
  outputDir: './test-results',
  // Copies takes out of test-results before the next run wipes it.
  globalTeardown: './teardown.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 240_000,
  expect: { timeout: 20_000 },
  reporter: [['list']],
  use: {
    baseURL,
    viewport,
    locale: process.env.TV_LOCALE ?? 'en-US',
    timezoneId: process.env.TV_TIMEZONE,
    video: REHEARSE ? 'off' : { mode: 'on', size: viewport },
    trace: 'retain-on-failure',
    // Slowed so clicks and typing are followable on screen.
    launchOptions: { slowMo: REHEARSE ? 0 : 250 },
  },
  projects: [
    // The login itself is never part of a tutorial — don't film it.
    { name: 'setup', testMatch: /auth\.setup\.ts/, use: { video: 'off' } },
    {
      name: 'clips',
      testMatch: /clips\/.*\.spec\.ts/,
      dependencies: hasSession ? ['setup'] : [],
      use: {
        ...devices['Desktop Chrome'],
        viewport,
        ...(hasSession ? { storageState: '.auth/state.json' } : {}),
      },
    },
  ],
});
