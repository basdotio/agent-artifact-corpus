/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {
  type NetworkExportPart,
  exportNetworkRequestPart,
} from '../formatters/networkFormatter.js';
import {zod} from '../third_party/index.js';
import {ToolError} from '../ToolError.js';

import {ToolCategory} from './categories.js';
import {
  createToolOutputSchema,
  defineTool,
  PAGINATION_OUTPUT_SCHEMA,
} from './ToolDefinition.js';

// Resource types as string literals (Playwright returns string from resourceType())
const FILTERABLE_RESOURCE_TYPES = [
  'document',
  'stylesheet',
  'image',
  'media',
  'font',
  'script',
  'texttrack',
  'xhr',
  'fetch',
  'prefetch',
  'eventsource',
  'websocket',
  'manifest',
  'signedexchange',
  'ping',
  'cspviolationreport',
  'preflight',
  'other',
] as const;

// HTTP request methods for filtering (matched case-insensitively against
// request.method()).
const HTTP_METHODS = [
  'GET',
  'POST',
  'PUT',
  'DELETE',
  'PATCH',
  'HEAD',
  'OPTIONS',
] as const;

const NETWORK_EXPORT_PARTS = [
  'all',
  'responseHeaders',
  'responseBody',
  'requestBody',
  'queryParams',
] as const;

export const listNetworkRequests = defineTool({
  name: 'list_network_requests',
  description: `Inspect captured HTTP(S) traffic for the currently selected page. Use this for API calls, request or response headers and bodies, redirects, authentication/session flows, replay or signing inputs, and determining which response created, refreshed, rotated, overwritten, or deleted a cookie. Without reqid it lists and filters requests; with cookieName it traces exact response Set-Cookie updates oldest-first, including cookies with HttpOnly, Secure, or SameSite attributes that page JavaScript cannot fully inspect; with reqid it returns bounded request details; with reqid plus outputFile it exports exact data. To inspect complete Set-Cookie values and attributes, export outputPart="responseHeaders" for a reqid returned by cookieName mode. cookieName never searches outbound Cookie request headers. Use get_websocket_messages for WebSocket frame payloads; this tool only represents the HTTP upgrade request. Capture begins when this MCP attaches and is not retroactive, so reload or reproduce traffic that occurred earlier. Captures then survive navigation in a 5000-request FIFO queue. List and cookie-flow modes default to 20 items per page; filters combine with AND and multiple values inside one filter combine with OR.`,
  annotations: {
    title: 'Inspect Network Requests',
    category: ToolCategory.NETWORK,
    // Not read-only due to outputFile export support.
    readOnlyHint: false,
  },
  capabilities: ['network', 'devtools-ui'],
  outputSchema: createToolOutputSchema({
    requests: zod.array(zod.record(zod.string(), zod.unknown())).optional(),
    cookieFlow: zod.array(zod.record(zod.string(), zod.unknown())).optional(),
    request: zod.record(zod.string(), zod.unknown()).optional(),
    export: zod.record(zod.string(), zod.unknown()).optional(),
    reqid: zod.number().optional(),
    pagination: PAGINATION_OUTPUT_SCHEMA.optional(),
  }),
  schema: {
    reqid: zod
      .number()
      .optional()
      .describe(
        'Inspect one captured request by the reqid returned by request-list or cookie-flow mode. Omit it to list/filter requests or trace cookie setters. Add outputFile when exact, complete, or large data is needed.',
      ),
    pageSize: zod
      .number()
      .int()
      .positive()
      .optional()
      .describe(
        'Maximum requests or Set-Cookie updates per page in list or cookie-flow mode. Defaults to 20.',
      ),
    pageIdx: zod
      .number()
      .int()
      .min(0)
      .optional()
      .describe(
        'Zero-based page to return in request-list or cookie-flow mode. Omit it for the first page.',
      ),
    methods: zod
      .array(zod.enum(HTTP_METHODS))
      .optional()
      .describe(
        'Filter requests by HTTP method (the request verb). Matched case-insensitively. Pass one or more of GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS; multiple values are OR-ed (e.g. ["POST"] shows only POSTs, ["GET","POST"] shows both). Use this to hunt for submissions (POST/PUT/PATCH) versus reads (GET). This is the HTTP verb, distinct from resourceTypes which filters by resource category (xhr, document, ...). When omitted or empty, methods are not filtered.',
      ),
    resourceTypes: zod
      .array(zod.enum(FILTERABLE_RESOURCE_TYPES))
      .optional()
      .describe(
        'Filter requests to only return requests of the specified resource types (xhr, fetch, document, script, ...). This is the resource category, NOT the HTTP verb — use methods for GET/POST filtering. When omitted or empty, returns all requests.',
      ),
    urlFilter: zod
      .string()
      .optional()
      .describe(
        'Filter request-list results to URLs containing this substring. Use an endpoint path, host, query fragment, or other known URL text; combine with methods/resourceTypes to narrow an API flow.',
      ),
    cookieName: zod
      .string()
      .trim()
      .min(1)
      .optional()
      .describe(
        'Trace an exact cookie name in response Set-Cookie headers. Use this when asked where, when, or by which response a cookie was created, refreshed, rotated, overwritten, or deleted, including HttpOnly cookies and cookies carrying Secure or SameSite attributes. Matching setter responses are returned oldest-first with reqids and use pageSize/pageIdx. Export outputPart="responseHeaders" for a returned reqid to inspect the complete value and Path, Domain, HttpOnly, Secure, SameSite, Expires, or Max-Age attributes. This mode does not search outbound Cookie request headers.',
      ),
    outputFile: zod
      .string()
      .optional()
      .describe(
        'With reqid, save selected network data to a local file. Use export instead of bounded inline details for complete Set-Cookie headers, exact bytes, large or binary bodies, long query payloads, replay/signature inputs, or external decoding. Absolute paths and paths relative to the current working directory are supported. The response reports the resolved absolute path; use it with evaluate_script localFilePath for browser-side processing. Subject to --allowedRoots when configured.',
      ),
    confirmOverwrite: zod
      .boolean()
      .default(false)
      .describe(
        'Must be true when outputFile already exists. New files do not require confirmation.',
      ),
    outputPart: zod
      .enum(NETWORK_EXPORT_PARTS)
      .default('all')
      .describe(
        'Select what outputFile receives for the chosen reqid. Use "responseHeaders" for complete cookie attributes and repeated Set-Cookie headers, "responseBody" for raw response bytes, "requestBody" for captured request bytes, "queryParams" for parsed URL parameters, or "all" for a JSON bundle of metadata, headers, query parameters, and body content/metadata. Defaults to "all".',
      ),
  },
  handler: async (request, response, context) => {
    if (request.params.outputFile && request.params.reqid === undefined) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        'outputFile requires reqid. First call list_network_requests without outputFile to find the request id, then re-run with reqid and outputFile.',
      );
    }

    if (request.params.reqid !== undefined) {
      if (request.params.outputFile) {
        const networkRequest = context.getNetworkRequestById(
          request.params.reqid,
        );
        const outputPart = request.params.outputPart as NetworkExportPart;
        const exported = await exportNetworkRequestPart(
          networkRequest,
          outputPart,
        );
        const file = await context.saveFile(
          exported.data,
          request.params.outputFile,
          {confirmOverwrite: request.params.confirmOverwrite},
        );
        response.appendResponseLine(
          `${exported.summary} Saved ${outputPart} to ${file.filename}.`,
        );
        response.setStructuredContent({
          reqid: request.params.reqid,
          export: {
            outputPart,
            filename: file.filename,
            byteLength: exported.data.length,
          },
        });
        return;
      }

      response.attachNetworkRequest(request.params.reqid);
      return;
    }
    const data = await context.getDevToolsData();
    const reqid = data?.cdpRequestId
      ? context.resolveCdpRequestId(data.cdpRequestId)
      : undefined;
    response.setIncludeNetworkRequests(true, {
      pageSize: request.params.pageSize,
      pageIdx: request.params.pageIdx,
      methods: request.params.methods,
      resourceTypes: request.params.resourceTypes,
      urlFilter: request.params.urlFilter,
      cookieName: request.params.cookieName,
      networkRequestIdInDevToolsUI: reqid,
    });
  },
});

export const clearNetworkRequests = defineTool({
  name: 'clear_network_requests',
  description: `Discard captured HTTP(S) evidence for the currently selected page after confirm=true. Use this immediately before reproducing an action when a clean network capture window is needed; do not use it to reset login, cookies, cache, or other browser state. It irreversibly clears the in-memory request queue, cached response bodies, and initiator maps only. Browser cookies, HTTP cache, origin storage, console messages, and WebSocket connections/messages are unchanged; use clear_site_data for cookie and storage reset. New captures continue above the previous reqid high-water mark because reqids are never reused.`,
  annotations: {
    title: 'Clear Network Requests',
    category: ToolCategory.NETWORK,
    readOnlyHint: false,
    destructiveHint: true,
    idempotentHint: true,
  },
  schema: {
    confirm: zod
      .boolean()
      .default(false)
      .describe(
        "Must be true to irreversibly delete the selected page's captured request history, response-body cache, and initiator evidence. This confirms capture cleanup, not browser-state cleanup.",
      ),
  },
  handler: async (request, response, context) => {
    if (!request.params.confirm) {
      throw new ToolError(
        'CONFIRMATION_REQUIRED',
        'clear_network_requests requires confirm=true because the captured request history cannot be restored.',
      );
    }
    const {requestCount, reclaimedBytes} = context.clearNetworkRequests();
    response.appendResponseLine(
      `Cleared ${requestCount} network request${
        requestCount === 1 ? '' : 's'
      } for the selected page.`,
    );
    response.appendResponseLine(
      `Released ${reclaimedBytes} bytes of cached response bodies.`,
    );
    response.appendResponseLine('Request initiator data cleared.');
    response.appendResponseLine(
      'reqids are not reused — newly collected requests continue from the previous high-water mark.',
    );
    response.setStructuredContent({requestCount, reclaimedBytes});
  },
});
