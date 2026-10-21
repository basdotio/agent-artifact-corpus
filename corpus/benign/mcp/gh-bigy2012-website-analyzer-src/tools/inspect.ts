import { scrapeWebsite } from '../browser/scrape.js';
import { inspectPageFromHtml } from '../lib/dom.js';
import { assertSafeUrl } from '../security/ssrf.js';
import { checkRobotsTxt } from '../crawler/robots.js';
import type { PageInspectResult, WebsiteData } from '../types/website.js';

export async function guardUrl(url: string): Promise<string> {
  const safe = await assertSafeUrl(url);
  const robots = await checkRobotsTxt(safe.toString());
  if (!robots.allowed) {
    throw new Error(`Blocked by robots.txt: ${robots.reason}`);
  }
  return safe.toString();
}

export async function inspectPage(url: string): Promise<{
  inspect: PageInspectResult;
  data: WebsiteData;
}> {
  const safeUrl = await guardUrl(url);
  const data = await scrapeWebsite(safeUrl);
  const inspect = inspectPageFromHtml(data.html, {
    url: data.url,
    title: data.title,
    description: data.description,
    inspectedAt: data.inspectedAt,
  });
  return { inspect, data };
}
