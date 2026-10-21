/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {assertBrowserUrlAllowed} from '../LocalFileAccess.js';
import {zod} from '../third_party/index.js';
import {normalizeToolError, ToolError} from '../ToolError.js';

import {ToolCategory} from './categories.js';
import {
  createToolOutputSchema,
  defineTool,
  PAGINATION_OUTPUT_SCHEMA,
  timeoutSchema,
} from './ToolDefinition.js';

// Default navigation timeout in milliseconds (10 seconds)
const DEFAULT_NAV_TIMEOUT = 10000;
const PAUSE_POLL_INTERVAL_MS = 50;

export type NavigationWaitResult<T = unknown> =
  | {status: 'completed'; value: T}
  | {status: 'paused'}
  | {status: 'error'; error: unknown};

interface PauseStateReader {
  isEnabled(): boolean;
  isPaused(): boolean;
}

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function throwNavigationFailure(error: unknown): never {
  const normalized = normalizeToolError(error);
  if (normalized.code !== 'INTERNAL') {
    throw normalized;
  }
  throw new ToolError('CDP_ERROR', `Navigation failed: ${normalized.message}`, {
    cause: error,
    retryable: true,
  });
}

export async function waitForNavigationOrPause<T>(
  navigation: Promise<T>,
  debugger_: PauseStateReader,
  stopNavigation: () => Promise<void>,
): Promise<NavigationWaitResult<T>> {
  const navigationResult = navigation.then(
    value => ({status: 'completed', value}) as const,
    error => ({status: 'error', error}) as const,
  );

  if (!debugger_.isEnabled()) {
    return navigationResult;
  }

  let stopped = false;
  const pauseResult = (async (): Promise<NavigationWaitResult<T>> => {
    while (!stopped) {
      if (debugger_.isPaused()) {
        return {status: 'paused'};
      }
      await delay(PAUSE_POLL_INTERVAL_MS);
    }
    // The loop only stops after another raced branch has resolved. This value
    // is never selected, but keeps the polling task finite.
    return {status: 'completed', value: undefined as T};
  })();

  const result = await Promise.race([navigationResult, pauseResult]);
  stopped = true;
  if (result.status === 'paused') {
    await stopNavigation().catch(() => undefined);
    // Page.stopLoading normally settles the Playwright navigation immediately.
    // Even if it fails, goto/reload carries its own bounded timeout. Drain it so
    // the tool mutex is never released while the navigation is still running.
    await navigationResult;
  }
  return result;
}

async function rebuildScriptsAfterNavigationFailure(
  context: {reinitDebugger(): Promise<void>},
  debugger_: PauseStateReader,
): Promise<void> {
  if (debugger_.isEnabled()) {
    await context.reinitDebugger();
  }
}

export const selectPage = defineTool({
  name: 'select_page',
  description: `Lists or selects open browser pages. Use it without pageIdx to identify the active page or choose the correct tab before inspecting network traffic, scripts, frames, or console output; pass pageIdx to make one listed page the shared target for later tools. It does not navigate or create pages: use navigate_page to change the selected page's URL and new_page when a separate tab is required. listPageIdx only paginates the page listing and never changes selection.`,
  annotations: {
    title: 'Select Page',
    category: ToolCategory.NAVIGATION,
    readOnlyHint: false,
  },
  outputSchema: createToolOutputSchema({
    pages: zod
      .array(
        zod.object({
          pageIdx: zod.number().int(),
          url: zod.string(),
          selected: zod.boolean(),
        }),
      )
      .optional(),
    pagination: PAGINATION_OUTPUT_SCHEMA.optional(),
  }),
  schema: {
    pageIdx: zod
      .number()
      .optional()
      .describe(
        'Snapshot index from the latest page listing. Pass it to make that page the target for later tools; omit it to list pages without changing selection. Re-list after pages open or close because indices can shift.',
      ),
    pageSize: zod
      .number()
      .int()
      .positive()
      .optional()
      .describe('Maximum pages to list per response. Defaults to 20.'),
    listPageIdx: zod
      .number()
      .int()
      .min(0)
      .optional()
      .describe(
        'Zero-based pagination index for the page listing only. This is not the pageIdx used to select a browser page. Defaults to 0.',
      ),
  },
  handler: async (request, response, context) => {
    if (request.params.pageIdx === undefined) {
      // List mode
      response.setIncludePages(true, {
        pageSize: request.params.pageSize,
        pageIdx: request.params.listPageIdx,
      });
      return;
    }

    // Select mode
    const page = context.getPageByIdx(request.params.pageIdx);
    assertBrowserUrlAllowed(page.url());
    await page.bringToFront();
    await context.selectPage(page);
    response.setIncludePages(true, {
      pageSize: request.params.pageSize,
      pageIdx:
        request.params.listPageIdx ??
        Math.floor(request.params.pageIdx / (request.params.pageSize ?? 20)),
    });
  },
});

// Default referer for anti-detection (matches Scrapling's google_search=True behavior)
const DEFAULT_REFERER = 'https://www.google.com/';

export const newPage = defineTool({
  name: 'new_page',
  description: `Opens a separate browser page for a URL, reusing an existing about:blank startup tab when available. Use this when the task needs another tab or should preserve the currently selected page; use navigate_page to change the URL in the existing selected page instead. It waits for DOMContentLoaded, not every background resource, and then makes the opened page the target for later tools. It preserves cookies, storage, cache, and other browser state; use clear_site_data separately when a clean replay is required.`,
  annotations: {
    title: 'New Page',
    category: ToolCategory.NAVIGATION,
    readOnlyHint: false,
  },
  schema: {
    url: zod
      .string()
      .describe(
        'Absolute URL to load in a separate or reusable blank page. Use navigate_page instead when the current selected page should be reused.',
      ),
    ...timeoutSchema,
  },
  handler: async (request, response, context) => {
    assertBrowserUrlAllowed(request.params.url);
    // launchPersistentContext opens an initial about:blank tab on startup.
    // If a blank tab is still around (either the startup one or an explicitly
    // requested one), navigate it in place instead of opening another tab —
    // avoids the "two about:blank" UX on first MCP tool call.
    const existingBlank = context
      .getPages()
      .find(p => p.url() === 'about:blank');
    const page = existingBlank ?? (await context.newPage());
    if (existingBlank) {
      await context.selectPage(existingBlank);
    }

    // Use plain goto without waitForEventsAfterAction to avoid creating
    // a CDP session during navigation. Anti-bot systems detect the extra
    // CDP session that WaitForHelper creates (Page.frameStartedNavigating listener).
    await page.goto(request.params.url, {
      timeout: request.params.timeout ?? DEFAULT_NAV_TIMEOUT,
      waitUntil: 'domcontentloaded',
      referer: DEFAULT_REFERER,
    });
    assertBrowserUrlAllowed(page.url());

    response.setIncludePages(true);
  },
});

export const navigatePage = defineTool({
  name: 'navigate_page',
  description: `Navigates, reloads, or moves through history in the currently selected page. Use it to reproduce requests, trigger configured breakpoints, refresh scripts, or continue a workflow in the same tab; use new_page when a separate tab is required. It does not clear cookies, storage, cache, or site data, so call clear_site_data first only when a clean replay is intended. It waits for DOMContentLoaded rather than every background resource; if a breakpoint pauses loading, use get_paused_info and then pause_or_resume(action="resume"). Navigation invalidates old script IDs, while tracked URL and XHR/Fetch breakpoints are restored when possible.`,
  annotations: {
    title: 'Navigate Page',
    category: ToolCategory.NAVIGATION,
    readOnlyHint: false,
  },
  schema: {
    type: zod
      .enum(['url', 'back', 'forward', 'reload'])
      .optional()
      .describe(
        'Navigation action for the selected page: url, back, forward, or reload. Use type=url together with url; omit type only when url is provided.',
      ),
    url: zod
      .string()
      .optional()
      .describe(
        'Target URL for type=url. Do not pass it for back, forward, or reload.',
      ),
    ...timeoutSchema,
  },
  handler: async (request, response, context) => {
    const page = context.getSelectedPage();
    const options = {
      timeout: request.params.timeout ?? DEFAULT_NAV_TIMEOUT,
    };

    if (!request.params.type && !request.params.url) {
      throw new Error('Either URL or a type is required.');
    }

    if (!request.params.type) {
      request.params.type = 'url';
    }
    if (request.params.type === 'url') {
      if (!request.params.url) {
        throw new ToolError(
          'INVALID_ARGUMENT',
          'A URL is required for navigation of type=url.',
        );
      }
      assertBrowserUrlAllowed(request.params.url);
    }

    const debugger_ = context.debuggerContext;
    const urlBeforeNavigation = page.url();

    // Clear stale script IDs BEFORE navigation. The scriptParsed listener
    // remains active and will capture new scripts as the page loads.
    // We intentionally do NOT call reinitDebugger() here — that would send
    // Debugger.disable which wipes ALL breakpoints (URL, XHR, DOM) and
    // implicitly resumes paused state. clearScripts() only clears cached
    // script IDs without touching the debugger or breakpoints.
    //
    // Note: Debugger.setBreakpointByUrl breakpoints survive navigation, but
    // DOMDebugger XHR breakpoints are reset by Chrome on navigation — we
    // restore them after navigation completes.
    if (debugger_.isEnabled()) {
      debugger_.clearScripts();
    }

    // Use plain navigation without waitForEventsAfterAction to avoid creating
    // a CDP session during navigation. Anti-bot systems detect the extra
    // CDP session that WaitForHelper creates (Page.frameStartedNavigating listener).
    let navigationCompleted = false;

    switch (request.params.type) {
      case 'url':
        {
          const targetUrl = request.params.url!;
          const result = await waitForNavigationOrPause(
            page.goto(targetUrl, {
              ...options,
              waitUntil: 'domcontentloaded',
              referer: DEFAULT_REFERER,
            }),
            debugger_,
            () => context.stopPageLoading(page),
          );
          if (result.status === 'completed') {
            if (result.value === null) {
              // Successful same-document and non-HTTP navigations can return
              // null without replaying scriptParsed for existing scripts.
              await rebuildScriptsAfterNavigationFailure(context, debugger_);
            }
            navigationCompleted = true;
            response.appendResponseLine(
              `Successfully navigated to ${targetUrl}.`,
            );
            response.appendResponseLine(
              'Note: Any previously obtained script IDs are now invalid. Use script URLs instead.',
            );
          } else if (result.status === 'paused' || debugger_.isPaused()) {
            response.appendResponseLine(
              `Navigation to ${targetUrl} started but execution is paused at a breakpoint. Use get_paused_info to inspect, then resume to continue loading.`,
            );
          } else {
            await rebuildScriptsAfterNavigationFailure(context, debugger_);
            throwNavigationFailure(result.error);
          }
        }
        break;
      case 'back':
        {
          const result = await waitForNavigationOrPause(
            page.goBack({
              ...options,
              waitUntil: 'domcontentloaded',
            }),
            debugger_,
            () => context.stopPageLoading(page),
          );
          if (result.status === 'completed') {
            if (result.value === null) {
              await rebuildScriptsAfterNavigationFailure(context, debugger_);
              if (page.url() === urlBeforeNavigation) {
                throw new ToolError(
                  'PRECONDITION_FAILED',
                  'The page has no previous history entry to navigate to.',
                );
              }
            }
            navigationCompleted = true;
            response.appendResponseLine(
              `Successfully navigated back to ${page.url()}.`,
            );
            response.appendResponseLine(
              'Note: Any previously obtained script IDs are now invalid. Use script URLs instead.',
            );
          } else if (result.status === 'paused' || debugger_.isPaused()) {
            response.appendResponseLine(
              `Navigation back started but execution is paused at a breakpoint. Use get_paused_info to inspect, then resume to continue loading.`,
            );
          } else {
            await rebuildScriptsAfterNavigationFailure(context, debugger_);
            throwNavigationFailure(result.error);
          }
        }
        break;
      case 'forward':
        {
          const result = await waitForNavigationOrPause(
            page.goForward({
              ...options,
              waitUntil: 'domcontentloaded',
            }),
            debugger_,
            () => context.stopPageLoading(page),
          );
          if (result.status === 'completed') {
            if (result.value === null) {
              await rebuildScriptsAfterNavigationFailure(context, debugger_);
              if (page.url() === urlBeforeNavigation) {
                throw new ToolError(
                  'PRECONDITION_FAILED',
                  'The page has no next history entry to navigate to.',
                );
              }
            }
            navigationCompleted = true;
            response.appendResponseLine(
              `Successfully navigated forward to ${page.url()}.`,
            );
            response.appendResponseLine(
              'Note: Any previously obtained script IDs are now invalid. Use script URLs instead.',
            );
          } else if (result.status === 'paused' || debugger_.isPaused()) {
            response.appendResponseLine(
              `Navigation forward started but execution is paused at a breakpoint. Use get_paused_info to inspect, then resume to continue loading.`,
            );
          } else {
            await rebuildScriptsAfterNavigationFailure(context, debugger_);
            throwNavigationFailure(result.error);
          }
        }
        break;
      case 'reload':
        {
          const result = await waitForNavigationOrPause(
            page.reload({
              ...options,
              waitUntil: 'domcontentloaded',
            }),
            debugger_,
            () => context.stopPageLoading(page),
          );
          if (result.status === 'completed') {
            if (result.value === null) {
              await rebuildScriptsAfterNavigationFailure(context, debugger_);
            }
            navigationCompleted = true;
            response.appendResponseLine(`Successfully reloaded the page.`);
            response.appendResponseLine(
              'Note: Any previously obtained script IDs are now invalid. Use script URLs instead.',
            );
          } else if (result.status === 'paused' || debugger_.isPaused()) {
            response.appendResponseLine(
              `Page reload started but execution is paused at a breakpoint. Use get_paused_info to inspect, then resume to continue loading.`,
            );
          } else {
            await rebuildScriptsAfterNavigationFailure(context, debugger_);
            throwNavigationFailure(result.error);
          }
        }
        break;
    }

    assertBrowserUrlAllowed(page.url());

    // Restore XHR breakpoints after navigation — Chrome resets
    // DOMDebugger state on page navigation.
    if (navigationCompleted && debugger_.isEnabled()) {
      await debugger_.restoreXHRBreakpoints();
    }

    response.setIncludePages(true);
  },
});
