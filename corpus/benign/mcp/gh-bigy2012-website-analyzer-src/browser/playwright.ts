import { chromium, type Browser, type BrowserContext, type Page } from 'playwright';
import { config } from '../config.js';

let browser: Browser | null = null;

export async function getBrowser(): Promise<Browser> {
  if (!browser || !browser.isConnected()) {
    browser = await chromium.launch({
      headless: true,
      args: ['--disable-dev-shm-usage', '--no-sandbox'],
    });
  }
  return browser;
}

export async function withPage<T>(
  fn: (page: Page, context: BrowserContext) => Promise<T>,
  options?: { viewport?: { width: number; height: number }; userAgent?: string },
): Promise<T> {
  const b = await getBrowser();
  const context = await b.newContext({
    viewport: options?.viewport ?? { width: 1440, height: 900 },
    userAgent: options?.userAgent ?? config.userAgent,
  });
  const page = await context.newPage();
  try {
    return await fn(page, context);
  } finally {
    await context.close();
  }
}

export async function closeBrowser(): Promise<void> {
  if (browser) {
    await browser.close();
    browser = null;
  }
}
