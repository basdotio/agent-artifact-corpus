/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type {DebuggerContext} from '../DebuggerContext.js';
import type {TrafficSummary} from '../formatters/websocketFormatter.js';
import type {RequestInitiator} from '../PageCollector.js';
import {zod} from '../third_party/index.js';
import type {Dialog, Frame, HTTPRequest, Page} from '../third_party/index.js';
import {TOOL_ERROR_CODES} from '../ToolError.js';
import type {PaginationOptions} from '../utils/types.js';
import type {WebSocketData} from '../WebSocketCollector.js';

import type {ToolCategory} from './categories.js';

export const TOOL_CAPABILITIES = [
  'debugger',
  'network',
  'websocket',
  'devtools-ui',
] as const;

export type ToolCapability = (typeof TOOL_CAPABILITIES)[number];

export const TOOL_OUTPUT_SCHEMA = {
  ok: zod.boolean().describe('Whether the tool completed successfully.'),
  tool: zod.string().describe('Stable MCP tool name.'),
  summary: zod.string().describe('Concise human-readable outcome.'),
  data: zod
    .record(zod.string(), zod.unknown())
    .optional()
    .describe('Machine-readable result payload.'),
  error: zod
    .object({
      code: zod.enum(TOOL_ERROR_CODES).describe('Stable error code.'),
      message: zod.string(),
      retryable: zod.boolean(),
    })
    .optional(),
};

export const PAGINATION_OUTPUT_SCHEMA = zod.object({
  pageIdx: zod.number().int(),
  pageSize: zod.number().int(),
  totalItems: zod.number().int(),
  totalPages: zod.number().int(),
  hasNextPage: zod.boolean(),
  hasPreviousPage: zod.boolean().optional(),
});

export function createToolOutputSchema(dataSchema: zod.ZodRawShape) {
  return {
    ...TOOL_OUTPUT_SCHEMA,
    data: zod.object(dataSchema).optional(),
  };
}

export interface ToolDefinition<
  Schema extends zod.ZodRawShape = zod.ZodRawShape,
> {
  name: string;
  description: string;
  annotations: {
    title?: string;
    category: ToolCategory;
    /**
     * If true, the tool does not modify its environment.
     */
    readOnlyHint: boolean;
    destructiveHint?: boolean;
    idempotentHint?: boolean;
    openWorldHint?: boolean;
  };
  /** Override the default end-to-end execution timeout for this tool. */
  timeoutMs?: number;
  /** CDP collectors/domains that must be active before this tool runs. */
  capabilities?: readonly ToolCapability[];
  /** Typed structured-content envelope for this tool. */
  outputSchema?: zod.ZodRawShape;
  schema: Schema;
  handler: (
    request: Request<Schema>,
    response: Response,
    context: Context,
  ) => Promise<void>;
}

export interface Request<Schema extends zod.ZodRawShape> {
  params: zod.output<zod.ZodObject<Schema>>;
  signal?: AbortSignal;
}

export interface ImageContentData {
  data: string;
  mimeType: string;
}

export interface DevToolsData {
  cdpRequestId?: string;
  cdpBackendNodeId?: number;
}

export interface Response {
  appendResponseLine(value: string): void;
  setStructuredContent(value: Record<string, unknown>): void;
  setIncludePages(value: boolean, options?: PaginationOptions): void;
  setIncludeNetworkRequests(
    value: boolean,
    options?: PaginationOptions & {
      methods?: string[];
      resourceTypes?: string[];
      urlFilter?: string;
      cookieName?: string;
      networkRequestIdInDevToolsUI?: number;
    },
  ): void;
  setIncludeConsoleData(
    value: boolean,
    options?: PaginationOptions & {
      types?: string[];
      includePreservedMessages?: boolean;
    },
  ): void;
  attachImage(value: ImageContentData): void;
  attachNetworkRequest(reqid: number): void;
  attachConsoleMessage(msgid: number): void;
  // WebSocket methods
  setIncludeWebSocketConnections(
    value: boolean,
    options?: PaginationOptions & {
      urlFilter?: string;
      includePreservedConnections?: boolean;
    },
  ): void;
  attachWebSocket(wsid: number): void;
}

/**
 * Only add methods required by tools/*.
 */
export type Context = Readonly<{
  getSelectedPage(): Page;
  getDialog(): Dialog | undefined;
  clearDialog(): void;
  getPages(): Page[];
  getPageByIdx(idx: number): Page;
  isPageSelected(page: Page): boolean;
  newPage(): Promise<Page>;
  closePage(pageIdx: number): Promise<void>;
  selectPage(page: Page): Promise<void>;
  stopPageLoading(page: Page): Promise<void>;
  reinitDebugger(): Promise<void>;
  saveTemporaryFile(
    data: Uint8Array<ArrayBufferLike>,
    mimeType: 'image/png' | 'image/jpeg' | 'image/webp',
  ): Promise<{filename: string}>;
  saveFile(
    data: Uint8Array<ArrayBufferLike>,
    filename: string,
    options?: {confirmOverwrite?: boolean},
  ): Promise<{filename: string}>;
  waitForEventsAfterAction(action: () => Promise<unknown>): Promise<void>;
  waitForTextOnPage(params: {
    text: string;
    timeout?: number | undefined;
  }): Promise<Element>;
  getDevToolsData(): Promise<DevToolsData>;
  /**
   * Returns a reqid for a cdpRequestId.
   */
  resolveCdpRequestId(cdpRequestId: string): number | undefined;
  /**
   * Get the debugger context for script/breakpoint management.
   */
  debuggerContext: DebuggerContext;
  /**
   * Get the initiator (call stack) for a network request.
   */
  getRequestInitiator(request: HTTPRequest): RequestInitiator | undefined;
  /**
   * Get the initiator by request ID.
   */
  getRequestInitiatorById(requestId: number): RequestInitiator | undefined;
  /**
   * Get network request by ID.
   */
  getNetworkRequestById(reqid: number): HTTPRequest;
  /**
   * Clear all collected network requests for the selected page, releasing the
   * cached response-body byte budget and initiator maps. Returns how much was
   * dropped so the caller can report it.
   */
  clearNetworkRequests(): {requestCount: number; reclaimedBytes: number};
  /**
   * Get all WebSocket connections for the selected page.
   */
  getWebSocketConnections(includePreservedData?: boolean): WebSocketData[];
  /**
   * Get a WebSocket connection by stable ID.
   */
  getWebSocketById(wsid: number): WebSocketData;
  /**
   * Get stable ID for a WebSocket connection.
   */
  getWebSocketStableId(ws: WebSocketData): number;
  /**
   * Cache traffic summary for a WebSocket connection.
   */
  cacheTrafficSummary(
    wsid: number,
    version: number,
    summary: TrafficSummary,
  ): void;
  /**
   * Get cached traffic summary for a WebSocket connection.
   */
  getCachedTrafficSummary(
    wsid: number,
    version: number,
  ): TrafficSummary | undefined;
  /**
   * Get the currently selected frame (or main frame if none selected).
   */
  getSelectedFrame(): Frame;
  /**
   * Select a specific frame for code execution.
   * Also reinitializes the debugger for the frame's CDP session.
   */
  selectFrame(frame: Frame): Promise<void>;
  /**
   * Reset frame selection back to the main frame.
   * Also reinitializes the debugger for the main page's CDP session.
   */
  resetSelectedFrame(): Promise<void>;
  ensureCapabilities(capabilities: readonly ToolCapability[]): Promise<void>;
}>;

export function defineTool<Schema extends zod.ZodRawShape>(
  definition: ToolDefinition<Schema>,
) {
  return {
    ...definition,
    annotations: {
      // MCP defaults destructiveHint to true when omitted. Make the ordinary
      // debugging/navigation tools explicitly non-destructive; tools that can
      // delete data or perform arbitrary page actions opt back into true and
      // require their own confirmation parameter.
      destructiveHint: false,
      ...definition.annotations,
    },
    outputSchema: definition.outputSchema ?? TOOL_OUTPUT_SCHEMA,
  };
}

export const CLOSE_PAGE_ERROR =
  'The last open page cannot be closed. It is fine to keep it open.';

export const timeoutSchema = {
  timeout: zod
    .number()
    .int()
    .optional()
    .describe(
      `Maximum wait time in milliseconds. If set to 0, the default timeout will be used.`,
    )
    .transform(value => {
      return value !== undefined && value <= 0 ? undefined : value;
    }),
};

export const paginationSchema = {
  pageSize: zod
    .number()
    .int()
    .positive()
    .optional()
    .describe('Maximum items per page. Defaults to 20.'),
  pageIdx: zod
    .number()
    .int()
    .min(0)
    .optional()
    .describe('Page number (0-based). Defaults to 0.'),
};
