/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import './polyfill.js';

import * as fs from 'node:fs';
import * as path from 'node:path';

import {
  closeBrowser,
  ensureBrowserConnected,
  ensureBrowserLaunched,
} from './browser.js';
import type {BrowserResult} from './browser.js';
import {parseArguments} from './cli.js';
import {
  assertBrowserUrlAllowed,
  configureAllowedRoots,
  getAllowedRoots,
} from './LocalFileAccess.js';
import {
  formatLogValue,
  formatToolErrorLog,
  logger,
  saveLogsToFile,
  warnAboutUnsafeDebugLogging,
} from './logger.js';
import {McpContext} from './McpContext.js';
import {McpResponse} from './McpResponse.js';
import {Mutex} from './Mutex.js';
import {
  McpServer,
  StdioServerTransport,
  type CallToolResult,
  SetLevelRequestSchema,
} from './third_party/index.js';
import {runAbortableOperation} from './ToolCallRunner.js';
import {normalizeToolError} from './ToolError.js';
import * as consoleTools from './tools/console.js';
import * as debuggerTools from './tools/debugger.js';
import * as frameTools from './tools/frames.js';
import * as interactionTools from './tools/interaction.js';
import * as networkTools from './tools/network.js';
import * as pagesTools from './tools/pages.js';
import * as screenshotTools from './tools/screenshot.js';
import * as scriptTools from './tools/script.js';
import * as siteDataTools from './tools/siteData.js';
import {
  TOOL_OUTPUT_SCHEMA,
  type ToolDefinition,
} from './tools/ToolDefinition.js';
import * as websocketTools from './tools/websocket.js';

// Read the version from package.json at runtime so it never drifts from the
// published package. Releases here are driven by `npm version` + a git tag, not
// release-please, so a hardcoded constant would go stale.
const VERSION = (
  JSON.parse(
    fs.readFileSync(
      path.join(import.meta.dirname, '../../package.json'),
      'utf8',
    ),
  ) as {version: string}
).version;

const SERVER_INSTRUCTIONS = `Use purpose-built tools for network, source, debugger, and browser-state evidence. Use evaluate_script directly for requested DOM/page state, web storage, page-defined globals, paused-frame expressions, or browser-side local-file processing when no narrower tool applies. Reuse returned IDs only within each tool's documented lifetime; prefer a script URL because scriptId expires on reload, navigation, or debugger frame/target change.

For captured HTTP/API traffic, redirects, HTTP authentication flows, or cookie provenance, start with list_network_requests. To find where an exact cookie was created, refreshed, rotated, overwritten, or deleted—including HttpOnly, Secure, and SameSite cookies—call list_network_requests with cookieName. Then inspect the returned reqid or export outputPart="responseHeaders" for complete Set-Cookie values and attributes. Use get_request_initiator on a captured reqid to locate client-side JavaScript that initiated that request, if any. Initiator CDP data is not retroactive: if an older reqid has no initiator, reproduce the action after network capability is active and inspect the new reqid, or set break_on_xhr before reproduction. If runtime arguments or local variables are still needed, set break_on_xhr with a narrow URL substring, reproduce the request, inspect get_paused_info, optionally evaluate in the paused frame, and explicitly resume execution.

For code discovery, use search_in_sources when you know text and list_scripts when you do not; read a bounded region with get_script_source or save a complete/minified source with save_script_source. Use get_websocket_messages for WebSocket frames rather than the HTTP upgrade request. WebSocket frame capture is not retroactive: call get_websocket_messages once before reloading or reproducing an already-finished socket flow because earlier frames cannot be recovered. Select the correct page before page-scoped work. Select a frame for iframe-specific source, debugger, evaluate, or click work; network and cookie evidence is page-scoped and does not require frame selection. Prefer click_element for one known interaction. For code evaluation, clicks, deletion of state/evidence, or breakpoint removal, set confirm=true only when the user explicitly authorizes that specific effect; otherwise request confirmation.`;

export const args = parseArguments(VERSION);
configureAllowedRoots(args.allowedRoots);
warnAboutUnsafeDebugLogging();

const logFile = args.logFile ? saveLogsToFile(args.logFile) : undefined;

logger(`Starting Chrome DevTools MCP Server v${VERSION}`);
const server = new McpServer(
  {
    name: 'js-reverse',
    title: 'JS Reverse Engineering MCP Server',
    description: `Agent-oriented JavaScript reverse engineering through Chrome DevTools (v${VERSION}): inspect HTTP and WebSocket evidence, trace Set-Cookie provenance and request initiators, search scripts, debug breakpoints, and perform controlled page interactions. Patchright provides the supporting anti-detection browser layer.`,
    version: VERSION,
  },
  {
    capabilities: {logging: {}},
    instructions: SERVER_INSTRUCTIONS,
  },
);
server.server.setRequestHandler(SetLevelRequestSchema, () => {
  return {};
});

let context: McpContext | undefined;

// No JS-level init scripts — Patchright's protocol-layer stealth handles
// automation signal suppression. JS patches (Error.prepareStackTrace, screen
// property overrides, fake chrome.runtime) actually CAUSE detection because
// anti-bot systems check for Object.defineProperty tampering. Source-level
// fingerprint patches (canvas/WebGL/GPU) are opt-in via --cloak.

async function getContext(): Promise<McpContext> {
  let result: BrowserResult;
  if (args.browserUrl) {
    result = await ensureBrowserConnected({
      browserURL: args.browserUrl,
    });
  } else {
    result = await ensureBrowserLaunched({
      isolated: args.isolated,
      logFile,
      cloak: args.cloak,
    });
  }

  if (!context || context.browserContext !== result.context) {
    context?.dispose();
    context = await McpContext.from(result.context, logger);
  }
  return context;
}

const logDisclaimers = () => {
  const roots = getAllowedRoots();
  console.error(
    `js-reverse-mcp exposes content of the browser instance to the MCP clients allowing them to inspect,
debug, and modify any data in the browser or DevTools.
Avoid sharing sensitive or personal information that you do not want to share with MCP clients.

Some tools can read from and write to the local filesystem. ${
      roots
        ? `Access is restricted to: ${roots.join(', ')}`
        : 'No allowed roots are configured, so local-file access is unrestricted. Use --allowedRoots to restrict it.'
    }`,
  );
};

const toolMutex = new Mutex();
const DEFAULT_TOOL_TIMEOUT_MS = 35_000;
const SHUTDOWN_TIMEOUT_MS = 5_000;
const PAGE_RECOVERY_TOOLS = new Set([
  'new_page',
  'navigate_page',
  'select_page',
]);

function getErrorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function errorResult(toolName: string, error: unknown): CallToolResult {
  const normalized = normalizeToolError(error);
  return {
    content: [
      {
        type: 'text',
        text: `[${normalized.code}] ${normalized.message}`,
      },
    ],
    structuredContent: {
      ok: false,
      tool: toolName,
      summary: normalized.message,
      error: {
        code: normalized.code,
        message: normalized.message,
        retryable: normalized.retryable,
      },
    },
    isError: true,
  };
}

function registerTool(tool: ToolDefinition): void {
  const {category, ...annotations} = tool.annotations;
  server.registerTool(
    tool.name,
    {
      description: tool.description,
      inputSchema: tool.schema,
      outputSchema: tool.outputSchema ?? TOOL_OUTPUT_SCHEMA,
      annotations,
      _meta: {'io.github.zhizhuodemao/category': category},
    },
    async (params, extra): Promise<CallToolResult> => {
      let guard: InstanceType<typeof Mutex.Guard>;
      try {
        guard = await toolMutex.acquire({
          timeoutMs: DEFAULT_TOOL_TIMEOUT_MS,
          signal: extra.signal,
        });
      } catch (error) {
        return errorResult(tool.name, error);
      }

      try {
        logger(`${tool.name} request: ${formatLogValue(params)}`);
        // Browser startup is shared across callers and can legitimately take
        // longer than an ordinary tool call (notably the first cloak setup).
        // Keep the mutex until the shared start settles, then apply the tool's
        // execution budget to the actual operation.
        const context = await getContext();
        logger(`${tool.name} context: resolved`);

        const timeoutMs = tool.timeoutMs ?? DEFAULT_TOOL_TIMEOUT_MS;
        return await runAbortableOperation(
          async signal => {
            signal.throwIfAborted();

            if (!PAGE_RECOVERY_TOOLS.has(tool.name)) {
              assertBrowserUrlAllowed(context.getSelectedPage().url());
            }
            await context.ensureCapabilities(tool.capabilities ?? []);
            const response = new McpResponse();
            await tool.handler(
              {
                params,
                signal,
              },
              response,
              context,
            );

            if (!PAGE_RECOVERY_TOOLS.has(tool.name)) {
              assertBrowserUrlAllowed(context.getSelectedPage().url());
            }

            const content = await response.handle(tool.name, context);
            return {
              content,
              structuredContent: response.createStructuredContent(tool.name),
            };
          },
          {
            timeoutMs,
            timeoutMessage: `Tool "${tool.name}" timed out after ${timeoutMs}ms`,
            signal: extra.signal,
          },
        );
      } catch (err) {
        const normalized = normalizeToolError(err);
        logger(formatToolErrorLog(tool.name, normalized));
        return errorResult(tool.name, normalized);
      } finally {
        guard.dispose();
      }
    },
  );
}

const tools = [
  ...Object.values(consoleTools),
  ...Object.values(debuggerTools),
  ...Object.values(frameTools),
  ...Object.values(interactionTools),
  ...Object.values(networkTools),
  ...Object.values(pagesTools),
  ...Object.values(screenshotTools),
  ...Object.values(scriptTools),
  ...Object.values(siteDataTools),

  ...Object.values(websocketTools),
].filter(tool => {
  return (
    typeof tool === 'object' &&
    tool !== null &&
    'name' in tool &&
    'handler' in tool &&
    'schema' in tool &&
    'annotations' in tool
  );
}) as unknown as ToolDefinition[];

tools.sort((a, b) => {
  return a.name.localeCompare(b.name);
});

let shuttingDown = false;

function requestShutdown(reason: string, exitCode: number): void {
  void shutdown(reason, exitCode);
}

async function shutdown(reason: string, exitCode: number): Promise<void> {
  if (shuttingDown) {
    return;
  }
  shuttingDown = true;
  logger(`Shutdown requested: ${reason}`);

  await withShutdownTimeout(
    (async () => {
      context?.dispose();
      context = undefined;

      await closeBrowser(reason);

      await server.close().catch(error => {
        logger('Failed to close MCP server during shutdown', error);
      });

      await closeLogFile();
    })(),
    reason,
  );

  process.exit(exitCode);
}

async function withShutdownTimeout(
  promise: Promise<void>,
  reason: string,
): Promise<void> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<void>(resolve => {
    timeoutId = setTimeout(() => {
      logger(
        `Shutdown cleanup timed out after ${SHUTDOWN_TIMEOUT_MS}ms: ${reason}`,
      );
      resolve();
    }, SHUTDOWN_TIMEOUT_MS);
  });

  await Promise.race([promise, timeout]);
  if (timeoutId) {
    clearTimeout(timeoutId);
  }
}

function closeLogFile(): Promise<void> {
  if (!logFile || logFile.destroyed || logFile.writableEnded) {
    return Promise.resolve();
  }

  return new Promise(resolve => {
    logFile.end(resolve);
  });
}

function getStreamErrorCode(error: unknown): string | undefined {
  return typeof error === 'object' && error !== null && 'code' in error
    ? String(error.code)
    : undefined;
}

process.on('SIGINT', () => requestShutdown('SIGINT', 130));
process.on('SIGTERM', () => requestShutdown('SIGTERM', 143));
process.on('SIGHUP', () => requestShutdown('SIGHUP', 129));
process.on('disconnect', () => requestShutdown('process disconnect', 0));

process.stdin.on('end', () => requestShutdown('stdin end', 0));
process.stdin.on('close', () => requestShutdown('stdin close', 0));
process.stdin.on('error', error => {
  requestShutdown(`stdin error: ${getErrorText(error)}`, 1);
});

process.stdout.on('error', error => {
  const code = getStreamErrorCode(error);
  requestShutdown(
    code === 'EPIPE' || code === 'ECONNRESET'
      ? `stdout ${code}`
      : `stdout error: ${getErrorText(error)}`,
    code === 'EPIPE' || code === 'ECONNRESET' ? 0 : 1,
  );
});

for (const tool of tools) {
  registerTool(tool);
}

const transport = new StdioServerTransport();
await server.connect(transport);
logger('Chrome DevTools MCP Server connected');
logDisclaimers();
