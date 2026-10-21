import path from 'node:path';
import fs from 'node:fs/promises';
import { withPage } from './playwright.js';
import { config } from '../config.js';

export const DEFAULT_VIEWPORT_WIDTHS = [375, 768, 1024, 1440, 1920];

export async function captureScreenshot(
  url: string,
  outputPath: string,
  options?: { width?: number; height?: number; fullPage?: boolean },
): Promise<string> {
  const width = options?.width ?? 1440;
  const height = options?.height ?? 900;

  await fs.mkdir(path.dirname(outputPath), { recursive: true });

  await withPage(
    async (page) => {
      await page.goto(url, { waitUntil: 'networkidle', timeout: config.requestTimeout });
      await page.waitForTimeout(400);
      await page.screenshot({
        path: outputPath,
        fullPage: options?.fullPage ?? true,
        type: 'png',
      });
    },
    { viewport: { width, height }, userAgent: config.userAgent },
  );

  return outputPath;
}

export async function captureResponsiveScreenshots(
  url: string,
  outputDir: string,
  widths: number[] = DEFAULT_VIEWPORT_WIDTHS,
): Promise<Array<{ width: number; path: string }>> {
  await fs.mkdir(outputDir, { recursive: true });
  const results: Array<{ width: number; path: string }> = [];

  for (const width of widths) {
    const filePath = path.join(outputDir, `viewport-${width}.png`);
    await captureScreenshot(url, filePath, {
      width,
      height: heightForWidth(width),
      fullPage: true,
    });
    results.push({ width, path: filePath });
  }

  return results;
}

function heightForWidth(width: number): number {
  if (width <= 375) return 812;
  if (width <= 768) return 1024;
  return 900;
}
