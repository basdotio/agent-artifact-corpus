import path from 'node:path';
import fs from 'node:fs/promises';
import { captureScreenshot, captureResponsiveScreenshots, DEFAULT_VIEWPORT_WIDTHS } from '../browser/screenshot.js';
import { resolveOutputDir } from '../lib/paths.js';
import { viewportWidthsFromConfig, config } from '../config.js';
import { guardUrl } from './inspect.js';

function hostDir(base: string, url: string): string {
  const host = new URL(url).host.replace(/[^a-z0-9._-]+/gi, '-').toLowerCase();
  return path.join(base, host, 'screenshots');
}

export async function captureScreenshotsTool(
  url: string,
  options?: {
    outputDir?: string;
    widths?: number[];
    fullPage?: boolean;
  },
): Promise<{ outputDir: string; files: Array<{ name: string; width: number; path: string }> }> {
  if (!config.screenshot && options?.widths === undefined) {
    // still allow explicit capture via tool
  }

  const safeUrl = await guardUrl(url);
  const base = resolveOutputDir(options?.outputDir);
  const outDir = hostDir(base, safeUrl);
  await fs.mkdir(outDir, { recursive: true });

  const widths = options?.widths?.length ? options.widths : viewportWidthsFromConfig();
  const effective = widths.length ? widths : DEFAULT_VIEWPORT_WIDTHS;

  const named: Array<{ name: string; width: number; path: string }> = [];

  // Named aliases matching docs examples
  const aliases: Record<number, string> = {
    375: 'mobile.png',
    768: 'tablet.png',
    1440: 'desktop.png',
  };

  const shots = await captureResponsiveScreenshots(safeUrl, outDir, effective);
  for (const shot of shots) {
    const alias = aliases[shot.width];
    if (alias) {
      const aliasPath = path.join(outDir, alias);
      await fs.copyFile(shot.path, aliasPath);
      named.push({ name: alias, width: shot.width, path: aliasPath });
    }
    named.push({ name: path.basename(shot.path), width: shot.width, path: shot.path });
  }

  // Ensure a primary desktop.png even if 1440 not in list
  if (!named.some((f) => f.name === 'desktop.png') && effective.includes(1920)) {
    const desktop = named.find((f) => f.width === 1920);
    if (desktop) {
      const aliasPath = path.join(outDir, 'desktop.png');
      await fs.copyFile(desktop.path, aliasPath);
      named.push({ name: 'desktop.png', width: desktop.width, path: aliasPath });
    }
  }

  // Single full capture convenience
  if (options?.fullPage !== false && !named.some((f) => f.name === 'full.png')) {
    const fullPath = path.join(outDir, 'full.png');
    await captureScreenshot(safeUrl, fullPath, {
      width: effective.includes(1440) ? 1440 : effective[effective.length - 1],
      fullPage: true,
    });
    named.push({ name: 'full.png', width: 1440, path: fullPath });
  }

  return { outputDir: outDir, files: named };
}
