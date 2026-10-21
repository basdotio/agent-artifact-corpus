import type { Page } from 'playwright';
import type { ScrapedElement, WebsiteData } from '../types/website.js';
import { withPage } from './playwright.js';
import { config } from '../config.js';

const STYLE_PROPS = [
  'color',
  'background-color',
  'background-image',
  'font-family',
  'font-size',
  'font-weight',
  'line-height',
  'letter-spacing',
  'margin-top',
  'margin-right',
  'margin-bottom',
  'margin-left',
  'padding-top',
  'padding-right',
  'padding-bottom',
  'padding-left',
  'gap',
  'display',
  'flex-direction',
  'justify-content',
  'align-items',
  'grid-template-columns',
  'max-width',
  'width',
  'height',
  'border-radius',
  'border',
  'box-shadow',
  'position',
  'overflow',
] as const;

export async function scrapeWebsite(url: string): Promise<WebsiteData> {
  return withPage(
    async (page) => {
      await page.goto(url, { waitUntil: 'networkidle', timeout: config.requestTimeout });
      await page.waitForTimeout(500);

      const title = await page.title();
      const description = await page.evaluate(() => {
        const el = document.querySelector('meta[name="description"]');
        return el?.getAttribute('content') ?? '';
      });
      const html = await page.content();

      const cssVariables = await extractCssVariables(page);
      const stylesheets = await extractStylesheets(page);
      const elements = await extractElements(page);

      return {
        url,
        title,
        description,
        html,
        cssVariables,
        stylesheets,
        elements,
        inspectedAt: new Date().toISOString(),
      };
    },
    { userAgent: config.userAgent },
  );
}

async function extractCssVariables(page: Page): Promise<Record<string, string>> {
  return page.evaluate(() => {
    const vars: Record<string, string> = {};
    const root = getComputedStyle(document.documentElement);
    for (let i = 0; i < root.length; i++) {
      const prop = root[i];
      if (prop.startsWith('--')) {
        vars[prop] = root.getPropertyValue(prop).trim();
      }
    }

    for (const sheet of Array.from(document.styleSheets)) {
      try {
        for (const rule of Array.from(sheet.cssRules ?? [])) {
          if (!(rule instanceof CSSStyleRule)) continue;
          if (rule.selectorText !== ':root' && rule.selectorText !== 'html') continue;
          for (let i = 0; i < rule.style.length; i++) {
            const prop = rule.style[i];
            if (prop.startsWith('--')) {
              vars[prop] = rule.style.getPropertyValue(prop).trim();
            }
          }
        }
      } catch {
        // cross-origin stylesheets
      }
    }
    return vars;
  });
}

async function extractStylesheets(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const texts: string[] = [];
    for (const sheet of Array.from(document.styleSheets)) {
      try {
        const rules = Array.from(sheet.cssRules ?? [])
          .map((r) => r.cssText)
          .join('\n');
        if (rules) texts.push(rules);
      } catch {
        if (sheet.href) texts.push(`/* external: ${sheet.href} */`);
      }
    }
    return texts;
  });
}

async function extractElements(page: Page): Promise<ScrapedElement[]> {
  return page.evaluate((props) => {
    const selectors = [
      'header',
      'nav',
      'main',
      'footer',
      'section',
      'article',
      'aside',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'p',
      'a',
      'button',
      'input',
      'textarea',
      'select',
      'form',
      'img',
      '[role]',
      '[class*="btn"]',
      '[class*="button"]',
      '[class*="card"]',
      '[class*="nav"]',
      '[class*="hero"]',
      '[class*="container"]',
    ];

    const seen = new Set<Element>();
    const results: Array<{
      tag: string;
      id: string;
      className: string;
      text: string;
      href?: string;
      role?: string;
      styles: Record<string, string>;
      rect: { x: number; y: number; width: number; height: number };
    }> = [];

    for (const sel of selectors) {
      for (const el of Array.from(document.querySelectorAll(sel))) {
        if (seen.has(el)) continue;
        seen.add(el);

        const cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;

        const styles: Record<string, string> = {};
        for (const p of props) {
          styles[p] = cs.getPropertyValue(p);
        }

        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;

        results.push({
          tag: el.tagName.toLowerCase(),
          id: el.id || '',
          className: typeof el.className === 'string' ? el.className : '',
          text: (el.textContent ?? '').trim().slice(0, 200),
          href: el instanceof HTMLAnchorElement ? el.href : undefined,
          role: el.getAttribute('role') ?? undefined,
          styles,
          rect: {
            x: Math.round(rect.x),
            y: Math.round(rect.y),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
          },
        });

        if (results.length >= 400) return results;
      }
    }
    return results;
  }, [...STYLE_PROPS]);
}
