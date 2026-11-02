/**
 * browser-scraper: Playwright scraper using real Chrome + user profiles.
 *
 * Usage:
 *   node scrape.mjs <url> [css_selector] [options]
 *
 * Options:
 *   --profile <name>   Use profiles/<name>/ under the skill dir instead of the system default
 *   --headless         Run in headless mode (faster, higher block risk)
 *   --wait <ms>        Extra wait time after DOMContentLoaded (default: 3000)
 *
 * If no selector is provided, dumps page title + body text preview.
 * If selector is provided, returns matched elements' text/attributes.
 *
 * Key approach:
 *   - Uses launchPersistentContext with a real Chrome/Chromium profile
 *   - channel: 'chrome' so it launches actual Chrome when available
 *   - --disable-blink-features=AutomationControlled to avoid bot detection
 *   - navigator.webdriver patched via addInitScript
 *   - Shares cookies/auth from the target profile session
 */

import { chromium } from 'playwright';
import { homedir } from 'os';
import { execSync } from 'child_process';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { existsSync, unlinkSync } from 'fs';

// Resolve skill directory (scripts/ is one level under the skill root)
const __dirname = dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = join(__dirname, '..'); // go up from scripts/ to skill root

// Platform detection
const isMac = process.platform === 'darwin';
const isLinux = process.platform === 'linux';
const isWin = process.platform === 'win32';

function getDefaultProfileDir() {
  if (isMac) return join(homedir(), 'Library/Application Support/Google/Chrome/Default');
  if (isLinux) return join(homedir(), '.config/google-chrome/Default');
  if (isWin) return join(process.env.LOCALAPPDATA || '', 'Google/Chrome/User Data/Default');
  throw new Error(`Unsupported platform: ${process.platform}`);
}

function getNamedProfileDir(name) {
  return join(SKILL_DIR, 'profiles', name);
}

// Clean up stale Chrome singleton lock files, crash recovery state,
// and session restore tabs from a previous unclean exit
function cleanupStaleLocks(profileDir) {
  const staleFiles = [
    'SingletonLock', 'SingletonCookie', 'SingletonSocket',
  ];
  for (const f of staleFiles) {
    try {
      const path = join(profileDir, f);
      if (existsSync(path)) {
        unlinkSync(path);
        console.error(`Removed stale ${f}`);
      }
    } catch {}
  }

  // Clear session restore tabs — these trigger the "Restore pages?" popup
  try {
    const sessionsDir = join(profileDir, 'Default', 'Sessions');
    const files = require('fs').readdirSync(sessionsDir);
    for (const f of files) {
      if (f.startsWith('Session_') || f.startsWith('Tabs_')) {
        unlinkSync(join(sessionsDir, f));
        console.error(`Cleared session file ${f}`);
      }
    }
  } catch {}
}

// Parse arguments properly — flags with values consume the next positional arg
const rawArgs = process.argv.slice(2);
const FLAGS_WITH_VALUE = ['--profile', '--wait'];

const namedFlags = {};
const positional = [];

for (let i = 0; i < rawArgs.length; i++) {
  const arg = rawArgs[i];
  if (arg.startsWith('--')) {
    if (FLAGS_WITH_VALUE.includes(arg) && i + 1 < rawArgs.length && !rawArgs[i + 1].startsWith('--')) {
      namedFlags[arg] = rawArgs[i + 1];
      i++; // skip the value
    } else {
      namedFlags[arg] = true;
    }
  } else {
    positional.push(arg);
  }
}

const url = positional[0];
const selector = positional[1] || null;
const profileName = namedFlags['--profile'] || null;
const headless = namedFlags['--headless'] === true;
const keepOpen = namedFlags['--keep-open'] === true;
const extraWait = namedFlags['--wait'] ? parseInt(namedFlags['--wait'], 10) : 3000;

if (!url) {
  console.error('Usage: node scrape.mjs <url> [css_selector] [options]');
  console.error('Options:');
  console.error('  --profile <name>  Use profiles/<name>/ instead of system default');
  console.error('  --headless         Run headless (faster, higher block risk)');
  console.error('  --wait <ms>        Extra wait after load (default: 3000)');
  console.error('  --keep-open        Leave browser open after scraping');
  process.exit(1);
}

const profileDir = profileName
  ? getNamedProfileDir(profileName)
  : getDefaultProfileDir();

console.error(`Using profile: ${profileDir}`);
if (profileName) console.error(`  (skill-local profile: ${profileName})`);
else console.error('  (system default Chrome profile)');

// Clean up any stale singleton locks from a previous crash/unclean exit
cleanupStaleLocks(profileDir);

const STEALTH_SCRIPT = `
Object.defineProperty(navigator, 'webdriver', {
  get: () => undefined
});
`;

const USER_AGENT = (
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ' +
  'AppleWebKit/537.36 (KHTML, like Gecko) ' +
  'Chrome/131.0.0.0 Safari/537.36'
);

// Build launch args
// Use channel:'chrome' on macOS when Chrome is installed (real Chrome shares the user's profile).
// When Chrome isn't installed or on other platforms, omit channel to use Playwright's
// bundled Chromium (the profile dir will be created/used by the bundled browser).
const launchOptions = {
  headless,
  channel: isMac && hasChrome() ? 'chrome' : undefined,
  userAgent: USER_AGENT,
  viewport: { width: 1280, height: 900 },
  args: [
    '--no-sandbox',
    '--disable-blink-features=AutomationControlled',
  ],
};

// Check if Chrome is available on macOS
function hasChrome() {
  try {
    execSync('ls "/Applications/Google Chrome.app" 2>/dev/null', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

// Check if Chrome is currently running (macOS)
function isChromeRunning() {
  try {
    execSync('pgrep -x "Google Chrome" 2>/dev/null', { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

// Warn if Chrome is running and we're trying to use it with the default profile
if (launchOptions.channel === 'chrome' && !profileName && isChromeRunning()) {
  console.error('WARNING: Chrome is currently running. Close Chrome first to avoid crashes,');
  console.error('         or use --profile <name> to use a separate profile directory.');
  console.error('         (Ctrl+C to abort, or close Chrome and run again)');
  // Give user a moment to see the warning before proceeding anyway
  await new Promise(r => setTimeout(r, 2000));
}

let context;
try {
  context = await chromium.launchPersistentContext(profileDir, launchOptions);
} catch (err) {
  // Fallback: if Chrome was requested but failed, retry with bundled Chromium
  if (launchOptions.channel === 'chrome') {
    console.error('Chrome launch failed, falling back to bundled Chromium...');
    launchOptions.channel = undefined;
    context = await chromium.launchPersistentContext(profileDir, launchOptions);
  } else {
    throw err;
  }
}

await context.addInitScript(STEALTH_SCRIPT);

const page = await context.newPage();
await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
await page.waitForTimeout(extraWait);

let result;

if (selector) {
  await page.waitForSelector(selector, { timeout: 15000 }).catch(() => null);
  result = await page.evaluate((sel) => {
    return [...document.querySelectorAll(sel)].slice(0, 10).map(el => ({
      text: el.textContent?.trim(),
      attrs: Object.fromEntries([...el.attributes].map(a => [a.name, a.value])),
    }));
  }, selector);
} else {
  result = await page.evaluate(() => ({
    title: document.title,
    url: location.href,
    preview: document.body.innerText.slice(0, 1000),
  }));
}

console.log(JSON.stringify(result, null, 2));

// Screenshot
await page.screenshot({ path: '/tmp/browser-scraper-last.png' });
console.error('Screenshot saved to /tmp/browser-scraper-last.png');

if (keepOpen) {
  console.error('Keeping browser open (Ctrl+C to close)...');
  await new Promise(() => {}); // hang forever
} else {
  await context.close();
}
