import { config } from '../config.js';
import { assertSafeUrl } from '../security/ssrf.js';
import { checkRobotsTxt } from './robots.js';
import { isSameOrigin, normalizeUrl, shouldSkipPath } from './url-filter.js';

/**
 * Stub crawler for v0.2+. v0.1 supports a single page only.
 * When called, returns the seed URL after safety checks (no multi-page crawl yet).
 */
export async function crawlWebsite(
  seedUrl: string,
  options?: { maxPages?: number; maxDepth?: number },
): Promise<{ urls: string[]; note: string }> {
  const url = await assertSafeUrl(seedUrl);
  const robots = await checkRobotsTxt(url.toString());
  if (!robots.allowed) {
    throw new Error(`Blocked by robots.txt: ${robots.reason}`);
  }

  const maxPages = options?.maxPages ?? config.maxPages;
  const maxDepth = options?.maxDepth ?? config.maxDepth;

  void maxDepth;
  void isSameOrigin;
  void normalizeUrl;
  void shouldSkipPath;

  return {
    urls: [url.toString()],
    note: `Crawler multi-page support lands in v0.2. Returning seed only (maxPages=${maxPages}).`,
  };
}
