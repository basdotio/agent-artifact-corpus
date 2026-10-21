/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {zod} from '../third_party/index.js';
import {ToolError} from '../ToolError.js';

import {ToolCategory} from './categories.js';
import {defineTool} from './ToolDefinition.js';

function getHttpUrl(value: string): URL | undefined {
  try {
    const url = new URL(value);
    if (url.protocol === 'http:' || url.protocol === 'https:') {
      return url;
    }
  } catch {
    return;
  }
  return;
}

function formatValues(values: string[]): string {
  const uniqueValues = [...new Set(values)].sort();
  if (uniqueValues.length === 0) {
    return 'none';
  }

  return uniqueValues.join(', ');
}

function formatCookieScope(cookie: {
  name: string;
  domain: string;
  path: string;
}): string {
  return `${cookie.name} @ ${cookie.domain}${cookie.path}`;
}

export const clearSiteData = defineTool({
  name: 'clear_site_data',
  description: `Irreversibly clear browser state after confirm=true to create a clean replay environment for the selected page. Use this before replaying login, session creation, storage initialization, or other state-dependent flows; do not use it to inspect cookies or determine which response set one. For cookie provenance, including HttpOnly, Secure, and SameSite attributes, use list_network_requests with cookieName first. Cleanup covers cookies affecting the selected page's HTTP(S) frames—including HttpOnly and Secure cookies through the browser context—persistent storage for those frame origins, and each HTTP(S) frame's sessionStorage. It does not reload the page. The browser HTTP cache is global and is preserved by default; set clearBrowserCache=true only when that wider cross-page effect is explicitly intended.`,
  annotations: {
    title: 'Clear Site Data',
    category: ToolCategory.BROWSER_STATE,
    readOnlyHint: false,
    destructiveHint: true,
    idempotentHint: true,
  },
  schema: {
    confirm: zod
      .boolean()
      .default(false)
      .describe(
        "Must be true to irreversibly delete cookies affecting the selected page's HTTP(S) frames, persistent storage for those frame origins, and HTTP(S) frame sessionStorage. This confirms state reset for replay, not inspection.",
      ),
    clearBrowserCache: zod
      .boolean()
      .optional()
      .default(false)
      .describe(
        'Also clear the browser-wide HTTP cache. Leave false for site-scoped replay cleanup. Setting true has a wider global effect on every page and origin in this browser, not only the selected page or its frame origins.',
      ),
  },
  handler: async (request, response, context) => {
    if (!request.params.confirm) {
      throw new ToolError(
        'CONFIRMATION_REQUIRED',
        'clear_site_data requires confirm=true because cookies and site storage cannot be restored.',
      );
    }
    const debugger_ = context.debuggerContext;
    if (debugger_.isEnabled() && debugger_.isPaused()) {
      throw new ToolError(
        'PRECONDITION_FAILED',
        'Execution is paused at a breakpoint. clear_site_data needs page JavaScript to clear sessionStorage, which cannot complete while execution is paused. Resume with pause_or_resume(action="resume"), then retry clear_site_data.',
      );
    }

    const page = context.getSelectedPage();
    const pageUrl = page.url();
    const url = new URL(pageUrl);

    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new ToolError(
        'PRECONDITION_FAILED',
        `clear_site_data requires an http(s) selected page. Current URL is ${pageUrl}. Navigate to the target site first.`,
      );
    }

    const browserContext = page.context();
    const frameUrls = [
      ...new Map(
        page
          .frames()
          .map(frame => getHttpUrl(frame.url()))
          .filter((frameUrl): frameUrl is URL => Boolean(frameUrl))
          .map(frameUrl => [frameUrl.href, frameUrl]),
      ).values(),
    ];
    const frameOrigins = [
      ...new Map(
        frameUrls.map(frameUrl => [frameUrl.origin, frameUrl.origin]),
      ).values(),
    ];
    const warnings: string[] = [];
    let cookieCount: number | undefined;
    let cookieDomains: string[] = [];
    let cookieNames: string[] = [];
    let cookiesStatus = 'failed';
    let browserCacheStatus = 'no (not requested; browser-wide cache preserved)';
    let originStorageStatus = `failed`;
    let sessionStorageStatus = 'failed';
    const clearedStorageOrigins: string[] = [];
    const failedStorageOrigins: string[] = [];
    const clearedSessionStorageFrames: string[] = [];
    const failedSessionStorageFrames: string[] = [];
    const clearedCookieNames: string[] = [];
    const failedCookieNames: string[] = [];
    const clearedCookieScopes: string[] = [];
    const failedCookieScopes: string[] = [];

    try {
      const cookies = await browserContext.cookies(
        frameUrls.map(frameUrl => frameUrl.href),
      );
      cookieCount = cookies.length;
      cookieDomains = cookies.map(cookie => cookie.domain);
      cookieNames = cookies.map(cookie => cookie.name);

      const cookiesByKey = new Map(
        cookies.map(cookie => [
          `${cookie.name}\u0000${cookie.domain}\u0000${cookie.path}`,
          cookie,
        ]),
      );

      for (const cookie of cookiesByKey.values()) {
        try {
          await browserContext.clearCookies({
            name: cookie.name,
            domain: cookie.domain,
            path: cookie.path,
          });
          clearedCookieNames.push(cookie.name);
          clearedCookieScopes.push(formatCookieScope(cookie));
        } catch (error) {
          failedCookieNames.push(cookie.name);
          failedCookieScopes.push(formatCookieScope(cookie));
          warnings.push(
            `Failed to clear cookie ${formatCookieScope(cookie)}: ${error instanceof Error ? error.message : String(error)}`,
          );
        }
      }

      cookiesStatus = `${clearedCookieScopes.length}/${cookiesByKey.size} matching cookie scopes`;
      if (cookies.some(cookie => cookie.partitionKey)) {
        warnings.push(
          'Some matched cookies are partitioned. Patchright clearCookies filters by name/domain/path, so matching partitioned cookies may be cleared together.',
        );
      }
    } catch (error) {
      warnings.push(
        `Failed to inspect or clear cookies for current page frames: ${error instanceof Error ? error.message : String(error)}`,
      );
    }

    const session = await browserContext.newCDPSession(page).catch(error => {
      warnings.push(
        `Failed to create CDP session for cache/origin storage cleanup: ${error instanceof Error ? error.message : String(error)}`,
      );
      return undefined;
    });

    if (session) {
      if (request.params.clearBrowserCache) {
        try {
          await session.send('Network.clearBrowserCache');
          browserCacheStatus = 'yes (browser-wide)';
        } catch (error) {
          browserCacheStatus = 'failed';
          warnings.push(
            `Failed to clear browser HTTP cache: ${error instanceof Error ? error.message : String(error)}`,
          );
        }
      }

      try {
        for (const origin of frameOrigins) {
          try {
            await session.send('Storage.clearDataForOrigin', {
              origin,
              storageTypes: 'all',
            });
            clearedStorageOrigins.push(origin);
          } catch (error) {
            failedStorageOrigins.push(origin);
            warnings.push(
              `Failed to clear origin storage for ${origin}: ${error instanceof Error ? error.message : String(error)}`,
            );
          }
        }
        originStorageStatus = `${clearedStorageOrigins.length}/${frameOrigins.length} origins`;
      } catch (error) {
        warnings.push(
          `Failed to clear origin storage for current page frames: ${error instanceof Error ? error.message : String(error)}`,
        );
      } finally {
        await session.detach().catch(error => {
          warnings.push(
            `Failed to detach CDP session: ${error instanceof Error ? error.message : String(error)}`,
          );
        });
      }
    }

    for (const frame of page.frames()) {
      const frameUrl = getHttpUrl(frame.url());
      if (!frameUrl) {
        continue;
      }

      try {
        await frame.evaluate(() => {
          sessionStorage.clear();
        });
        clearedSessionStorageFrames.push(frameUrl.href);
      } catch (error) {
        failedSessionStorageFrames.push(frameUrl.href);
        warnings.push(
          `Failed to clear sessionStorage for frame ${frameUrl.href}: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }
    sessionStorageStatus = `${clearedSessionStorageFrames.length}/${frameUrls.length} frames`;

    response.appendResponseLine(
      `Browser state cleanup completed for ${url.origin}`,
    );
    response.appendResponseLine(`URL: ${pageUrl}`);
    response.appendResponseLine(
      `Frame origins targeted: ${formatValues(frameOrigins)}`,
    );
    response.appendResponseLine(`Cookies cleared: ${cookiesStatus}`);
    response.appendResponseLine(
      `Cookies found before clearing: ${cookieCount ?? 'unknown'}`,
    );
    response.appendResponseLine(
      `Cookie domains matched: ${formatValues(cookieDomains)}`,
    );
    response.appendResponseLine(
      `Cookie names matched: ${formatValues(cookieNames)}`,
    );
    response.appendResponseLine(
      `Cookie names cleared: ${formatValues(clearedCookieNames)}`,
    );
    response.appendResponseLine(
      `Cookie names failed: ${formatValues(failedCookieNames)}`,
    );
    response.appendResponseLine(
      `Cookie scopes cleared: ${formatValues(clearedCookieScopes)}`,
    );
    response.appendResponseLine(
      `Cookie scopes failed: ${formatValues(failedCookieScopes)}`,
    );
    response.appendResponseLine(
      `Browser HTTP cache cleared: ${browserCacheStatus}`,
    );
    response.appendResponseLine(
      `Origin storage cleared: ${originStorageStatus}`,
    );
    response.appendResponseLine(
      `Origin storage types attempted: all (localStorage, IndexedDB, Cache Storage, Service Workers, WebSQL, file systems, storage buckets, shared storage, and related CDP-supported data)`,
    );
    response.appendResponseLine(
      `Origin storage cleared for: ${formatValues(clearedStorageOrigins)}`,
    );
    response.appendResponseLine(
      `Origin storage failed for: ${formatValues(failedStorageOrigins)}`,
    );
    response.appendResponseLine(
      `Session storage cleared: ${sessionStorageStatus}`,
    );
    response.appendResponseLine(
      `Session storage cleared for frames: ${formatValues(clearedSessionStorageFrames)}`,
    );
    response.appendResponseLine(
      `Session storage failed for frames: ${formatValues(failedSessionStorageFrames)}`,
    );

    response.appendResponseLine(`Warnings:`);
    if (!warnings.length) {
      response.appendResponseLine(`none`);
    }
    for (const warning of warnings) {
      response.appendResponseLine(`- ${warning}`);
    }

    response.appendResponseLine(
      'The page was not reloaded. Use navigate_page({type:"reload"}) to replay cookie generation.',
    );
    response.setStructuredContent({
      origin: url.origin,
      url: pageUrl,
      cookieScopesCleared: clearedCookieScopes.length,
      cookieScopesFailed: failedCookieScopes.length,
      browserCacheCleared: browserCacheStatus.startsWith('yes'),
      storageOriginsCleared: clearedStorageOrigins,
      storageOriginsFailed: failedStorageOrigins,
      sessionStorageFramesCleared: clearedSessionStorageFrames,
      sessionStorageFramesFailed: failedSessionStorageFrames,
      warnings,
    });
  },
});
