import path from 'node:path';
import type { ResponsiveAnalysis, WebsiteData } from '../types/website.js';
import { withPage } from '../browser/playwright.js';
import { captureResponsiveScreenshots, DEFAULT_VIEWPORT_WIDTHS } from '../browser/screenshot.js';
import { config } from '../config.js';

export const DEFAULT_RESPONSIVE_WIDTHS = DEFAULT_VIEWPORT_WIDTHS;

export async function analyzeResponsive(
  data: WebsiteData,
  options?: { captureScreenshots?: boolean; outputDir?: string; widths?: number[] },
): Promise<ResponsiveAnalysis> {
  const widths = options?.widths ?? DEFAULT_RESPONSIVE_WIDTHS;
  const mediaQueries = extractMediaQueries(data.stylesheets);
  const viewportMeta = extractViewportMeta(data.html);

  let screenshots: Array<{ width: number; path: string }> = [];
  if (options?.captureScreenshots && options.outputDir) {
    screenshots = await captureResponsiveScreenshots(data.url, options.outputDir, widths);
  }

  const breakpoints = await Promise.all(
    widths.map(async (width) => {
      const snapshot = await withPage(
        async (page) => {
          await page.goto(data.url, { waitUntil: 'networkidle', timeout: config.requestTimeout });
          await page.waitForTimeout(300);
          const sections = await page.evaluate(() =>
            Array.from(document.querySelectorAll('header, nav, main, section, footer'))
              .filter((el) => {
                const r = el.getBoundingClientRect();
                return r.width > 0 && r.height > 0;
              })
              .map((el) => el.tagName.toLowerCase() + (el.className ? '.' + String(el.className).split(/\s+/)[0] : ''))
              .slice(0, 20),
          );
          const hasMobileNav = await page.evaluate(() => {
            const btn = document.querySelector(
              'button[aria-label*="menu" i], button[aria-label*="nav" i], [class*="hamburger"], [class*="menu-toggle"], [class*="mobile-nav"]',
            );
            return Boolean(btn);
          });
          return { sections, hasMobileNav };
        },
        { viewport: { width, height: heightForWidth(width) } },
      );

      return {
        width,
        height: heightForWidth(width),
        screenshotPath: screenshots.find((s) => s.width === width)?.path,
        layoutShift: false,
        visibleSections: snapshot.sections,
        hasMobileNav: snapshot.hasMobileNav,
      };
    }),
  );

  const hasMobileNav = breakpoints.some((b) => b.hasMobileNav);
  const fluidImages = /max-width:\s*100%|img\s*\{[^}]*width:\s*100%/i.test(data.stylesheets.join('\n'));

  return {
    breakpoints: breakpoints.map(({ width, height, screenshotPath, layoutShift, visibleSections }) => ({
      width,
      height,
      screenshotPath,
      layoutShift,
      visibleSections,
    })),
    mediaQueries: mediaQueries.slice(0, 40),
    hasMobileNav,
    fluidImages,
    viewportMeta,
  };
}

function heightForWidth(width: number): number {
  if (width <= 375) return 812;
  if (width <= 768) return 1024;
  return 900;
}

function extractMediaQueries(stylesheets: string[]): string[] {
  const found = new Set<string>();
  const re = /@media[^{]+/gi;
  for (const css of stylesheets) {
    let m: RegExpExecArray | null;
    while ((m = re.exec(css))) {
      found.add(m[0].replace(/\s+/g, ' ').trim());
    }
  }
  return [...found];
}

function extractViewportMeta(html: string): string | null {
  const m = html.match(/<meta[^>]+name=["']viewport["'][^>]*>/i);
  return m?.[0] ?? null;
}

export function responsiveOutputDir(baseDir: string, host: string): string {
  return path.join(baseDir, sanitize(host), 'screenshots');
}

function sanitize(value: string): string {
  return value.replace(/[^a-z0-9._-]+/gi, '-').toLowerCase();
}
