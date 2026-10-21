/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {zod} from '../third_party/index.js';

import {ToolCategory} from './categories.js';
import {
  createToolOutputSchema,
  defineTool,
  PAGINATION_OUTPUT_SCHEMA,
} from './ToolDefinition.js';
// Playwright's ConsoleMessage.type() returns a string union directly
type ConsoleResponseType = string;

const FILTERABLE_MESSAGE_TYPES: [
  ConsoleResponseType,
  ...ConsoleResponseType[],
] = [
  'log',
  'debug',
  'info',
  'error',
  'warn',
  'dir',
  'dirxml',
  'table',
  'trace',
  'clear',
  'startGroup',
  'startGroupCollapsed',
  'endGroup',
  'assert',
  'profile',
  'profileEnd',
  'count',
  'timeEnd',
  'verbose',
];

export const listConsoleMessages = defineTool({
  name: 'list_console_messages',
  description:
    'Inspects console messages and uncaught page errors captured for the selected page. Use it to diagnose runtime failures, warnings, application logs, or values already emitted by page code; use search_in_sources for source text and list_network_requests for HTTP evidence instead. Without msgid it lists messages 20 per page by default, optionally filtered by type or retained navigation history. With msgid it returns one message by its stable ID for focused inspection. Capture begins when this MCP attaches and is not retroactive, so reload or reproduce code that logged before attachment.',
  annotations: {
    title: 'List Console Messages',
    category: ToolCategory.DEBUGGING,
    readOnlyHint: true,
  },
  outputSchema: createToolOutputSchema({
    messages: zod.array(zod.record(zod.string(), zod.unknown())).optional(),
    message: zod.record(zod.string(), zod.unknown()).optional(),
    pagination: PAGINATION_OUTPUT_SCHEMA.optional(),
  }),
  schema: {
    msgid: zod
      .number()
      .optional()
      .describe(
        'Stable message ID returned by list mode. Pass it to inspect one captured console message; omit it to list messages.',
      ),
    pageSize: zod
      .number()
      .int()
      .positive()
      .optional()
      .describe('Maximum number of messages to return. Defaults to 20.'),
    pageIdx: zod
      .number()
      .int()
      .min(0)
      .optional()
      .describe(
        'Page number to return (0-based). When omitted, returns the first page.',
      ),
    types: zod
      .array(zod.enum(FILTERABLE_MESSAGE_TYPES))
      .optional()
      .describe(
        'Console levels/types to include in list mode, such as error, warn, log, or trace. Values are OR-ed; omit or pass an empty array for all types.',
      ),
    includePreservedMessages: zod
      .boolean()
      .default(false)
      .optional()
      .describe(
        'Include retained console messages from the last 3 navigations. Leave false when only the current page load is relevant.',
      ),
  },
  handler: async (request, response) => {
    if (request.params.msgid !== undefined) {
      response.attachConsoleMessage(request.params.msgid);
      return;
    }
    response.setIncludeConsoleData(true, {
      pageSize: request.params.pageSize,
      pageIdx: request.params.pageIdx,
      types: request.params.types,
      includePreservedMessages: request.params.includePreservedMessages,
    });
  },
});
