import { chromium as rebrowserChromium } from 'rebrowser-playwright'
import { addExtra } from 'playwright-extra'
import StealthPlugin from 'puppeteer-extra-plugin-stealth'
import type { Browser, BrowserContext } from 'rebrowser-playwright'

// addExtra wraps rebrowser-playwright's chromium so stealth plugin runs on top of
// rebrowser's CDP patches — NOT on standard playwright chromium
const chromium = addExtra(rebrowserChromium)
chromium.use(StealthPlugin())

const STEALTH_LAUNCH_ARGS = [
  '--disable-blink-features=AutomationControlled',
  '--disable-infobars',
  '--no-sandbox',
  '--disable-setuid-sandbox',
  '--disable-dev-shm-usage',
  '--lang=zh-CN',
]

const STEALTH_CONTEXT_OPTIONS = {
  // Keep in sync with installed rebrowser-playwright Chromium version
  userAgent:
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
  viewport: { width: 1280, height: 800 },
  locale: 'zh-CN',
  timezoneId: 'Asia/Shanghai',
}

export class BrowserFactory {
  static async launch(headless = false, options?: { timeout?: number }): Promise<Browser> {
    return chromium.launch({
      headless,
      args: STEALTH_LAUNCH_ARGS,
      ...(options?.timeout !== undefined && { timeout: options.timeout }),
    }) as Promise<Browser>
  }

  static async newStealthContext(browser: Browser): Promise<BrowserContext> {
    return browser.newContext(STEALTH_CONTEXT_OPTIONS)
  }
}
