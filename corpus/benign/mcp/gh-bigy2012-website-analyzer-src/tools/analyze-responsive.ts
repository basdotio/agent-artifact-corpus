import path from 'node:path';
import { analyzeResponsive, responsiveOutputDir } from '../analyzers/responsive.js';
import { resolveOutputDir } from '../lib/paths.js';
import { viewportWidthsFromConfig } from '../config.js';
import type { WebsiteData } from '../types/website.js';
import { inspectPage } from './inspect.js';

export async function analyzeResponsiveTool(
  urlOrData: string | WebsiteData,
  options?: { captureScreenshots?: boolean; outputDir?: string; widths?: number[] },
) {
  const data = typeof urlOrData === 'string' ? (await inspectPage(urlOrData)).data : urlOrData;
  const outputDir = resolveOutputDir(options?.outputDir);
  const widths = options?.widths?.length ? options.widths : viewportWidthsFromConfig();

  const responsive = await analyzeResponsive(data, {
    captureScreenshots: options?.captureScreenshots ?? false,
    outputDir: responsiveOutputDir(outputDir, new URL(data.url).host),
    widths,
  });

  return {
    url: data.url,
    title: data.title,
    responsive,
    screenshotDir: options?.captureScreenshots
      ? path.join(outputDir, new URL(data.url).host.replace(/[^a-z0-9._-]+/gi, '-').toLowerCase(), 'screenshots')
      : undefined,
  };
}
