/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import type {Frame} from '../third_party/index.js';
import {zod} from '../third_party/index.js';
import {ToolError} from '../ToolError.js';
import {paginate} from '../utils/pagination.js';

import {ToolCategory} from './categories.js';
import {
  createToolOutputSchema,
  defineTool,
  PAGINATION_OUTPUT_SCHEMA,
} from './ToolDefinition.js';

function getFrameDepth(frame: Frame): number {
  let depth = 0;
  let parent = frame.parentFrame();
  while (parent) {
    depth++;
    parent = parent.parentFrame();
  }
  return depth;
}

/**
 * List frames or select a frame for code execution.
 */
export const selectFrame = defineTool({
  name: 'select_frame',
  description:
    'Lists or selects frames, including iframes, within the current page. Use it when the target element, page-defined global, script, or execution context may live in an iframe: first list frames, then pass frameIdx before click_element or evaluate_script. Omitting frameIdx lists 20 frames per page without changing context; passing frameIdx changes the shared frame target, with 0 restoring the main frame. It does not switch browser tabs or navigate—use select_page or navigate_page for those actions—and listPageIdx only paginates this listing.',
  annotations: {
    title: 'Select Frame',
    category: ToolCategory.DEBUGGING,
    readOnlyHint: false,
  },
  capabilities: ['debugger'],
  outputSchema: createToolOutputSchema({
    frames: zod
      .array(
        zod.object({
          frameIdx: zod.number().int(),
          url: zod.string(),
          name: zod.string(),
          selected: zod.boolean(),
          depth: zod.number().int(),
        }),
      )
      .optional(),
    selectedFrame: zod
      .object({
        frameIdx: zod.number().int(),
        url: zod.string(),
        name: zod.string(),
        isMainFrame: zod.boolean(),
      })
      .optional(),
    pagination: PAGINATION_OUTPUT_SCHEMA.optional(),
  }),
  schema: {
    frameIdx: zod
      .number()
      .int()
      .min(0)
      .optional()
      .describe(
        'Frame index from the latest frame listing. Pass it to target later frame-aware tools; 0 restores the main frame. Omit it to list frames without changing context, and re-list after navigation or frame attachment/detachment because indices can shift.',
      ),
    pageSize: zod
      .number()
      .int()
      .positive()
      .optional()
      .describe('Maximum frames to list per response. Defaults to 20.'),
    listPageIdx: zod
      .number()
      .int()
      .min(0)
      .optional()
      .describe(
        'Zero-based pagination index for the frame listing only. This is not the frameIdx used to select a frame. Defaults to 0.',
      ),
  },
  handler: async (request, response, context) => {
    const page = context.getSelectedPage();
    const frames = page.frames();
    const currentFrame = context.getSelectedFrame();

    if (request.params.frameIdx === undefined) {
      // List mode
      if (frames.length === 0) {
        response.appendResponseLine('No frames found.');
        return;
      }

      const paginated = paginate(frames, {
        pageSize: request.params.pageSize,
        pageIdx: request.params.listPageIdx,
      });
      if (paginated.invalidPage) {
        throw new ToolError(
          'INVALID_ARGUMENT',
          `listPageIdx ${request.params.listPageIdx} is outside 0-${paginated.totalPages - 1}.`,
        );
      }
      response.appendResponseLine(
        `Frames (${frames.length} total), showing ${paginated.startIndex + 1}-${paginated.endIndex}:\n`,
      );

      for (let offset = 0; offset < paginated.items.length; offset++) {
        const frame = paginated.items[offset];
        const i = paginated.startIndex + offset;
        const isSelected = frame === currentFrame;
        const indent = getFrameDepth(frame);
        const prefix = '  '.repeat(indent);
        const marker = isSelected ? ' [selected]' : '';
        const name = frame.name() ? ` name="${frame.name()}"` : '';
        response.appendResponseLine(
          `${prefix}${i}: ${frame.url() || '(empty)'}${name}${marker}`,
        );
      }
      if (paginated.hasNextPage) {
        response.appendResponseLine(
          `Next page: listPageIdx=${paginated.currentPage + 1}`,
        );
      }
      response.setStructuredContent({
        frames: paginated.items.map((frame, offset) => ({
          frameIdx: paginated.startIndex + offset,
          url: frame.url(),
          name: frame.name(),
          selected: frame === currentFrame,
          depth: getFrameDepth(frame),
        })),
        pagination: {
          pageIdx: paginated.currentPage,
          pageSize: request.params.pageSize ?? 20,
          totalItems: frames.length,
          totalPages: paginated.totalPages,
          hasNextPage: paginated.hasNextPage,
        },
      });
      return;
    }

    // Select mode
    const {frameIdx} = request.params;

    if (frameIdx >= frames.length) {
      throw new ToolError(
        'INVALID_ARGUMENT',
        `Invalid frame index ${frameIdx}. Available: 0-${frames.length - 1}.`,
      );
    }

    const frame = frames[frameIdx];

    if (frameIdx === 0) {
      await context.resetSelectedFrame();
      response.appendResponseLine('Switched to main frame.');
    } else {
      await context.selectFrame(frame);
      const name = frame.name() ? ` (name: "${frame.name()}")` : '';
      response.appendResponseLine(
        `Switched to frame ${frameIdx}: ${frame.url()}${name}`,
      );
    }
    response.setStructuredContent({
      selectedFrame: {
        frameIdx,
        url: frame.url(),
        name: frame.name(),
        isMainFrame: frameIdx === 0,
      },
    });
  },
});
