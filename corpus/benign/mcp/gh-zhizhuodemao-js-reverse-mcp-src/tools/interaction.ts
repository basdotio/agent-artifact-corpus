/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {zod} from '../third_party/index.js';
import {ToolError} from '../ToolError.js';

import {ToolCategory} from './categories.js';
import {
  createToolOutputSchema,
  defineTool,
  timeoutSchema,
} from './ToolDefinition.js';

const MODIFIERS = ['Alt', 'Control', 'ControlOrMeta', 'Meta', 'Shift'] as const;

/**
 * A deliberately small interaction primitive: one verified element, one click.
 * It does not accept arbitrary JavaScript or silently choose among matches.
 */
export const clickElement = defineTool({
  name: 'click_element',
  description:
    'Performs one verified, auditable click in the currently selected frame. Use it when the task requires activating a known button, link, or control after selecting the correct page/frame and identifying a CSS selector; it is the preferred minimal interaction primitive over arbitrary evaluate_script code. It does not discover elements, type text, or silently guess among matches: the selector must resolve to exactly one element unless index is explicit, and the chosen element must be visible. A click can submit data, navigate, or trigger external effects, so confirm=true is required and the result reports the exact resolved element.',
  annotations: {
    title: 'Click Element',
    category: ToolCategory.NAVIGATION,
    readOnlyHint: false,
    destructiveHint: true,
    openWorldHint: true,
  },
  outputSchema: createToolOutputSchema({
    action: zod.literal('click').optional(),
    selector: zod.string().optional(),
    index: zod.number().int().optional(),
    matchedCount: zod.number().int().optional(),
    element: zod
      .object({
        tagName: zod.string(),
        id: zod.string().nullable(),
        role: zod.string().nullable(),
        text: zod.string(),
        ariaLabel: zod.string().nullable(),
      })
      .optional(),
  }),
  schema: {
    confirm: zod
      .boolean()
      .default(false)
      .describe(
        'Must be true to authorize this specific click because it can submit data, navigate, or trigger external side effects.',
      ),
    selector: zod
      .string()
      .trim()
      .min(1)
      .describe(
        'CSS selector evaluated only in the currently selected frame. Use select_frame first when the target is inside an iframe.',
      ),
    index: zod
      .number()
      .int()
      .min(0)
      .optional()
      .describe(
        'Explicit zero-based match index. Required when the selector matches more than one element.',
      ),
    button: zod
      .enum(['left', 'middle', 'right'])
      .default('left')
      .describe('Mouse button. Defaults to left.'),
    modifiers: zod
      .array(zod.enum(MODIFIERS))
      .optional()
      .describe('Optional keyboard modifiers held during the click.'),
    ...timeoutSchema,
  },
  handler: async (request, response, context) => {
    if (!request.params.confirm) {
      throw new ToolError(
        'CONFIRMATION_REQUIRED',
        'click_element requires confirm=true because clicking can trigger external side effects.',
      );
    }
    const frame = context.getSelectedFrame();
    const matches = frame.locator(`css=${request.params.selector}`);
    // Resolve one snapshot of handles. Counting and then acting through a
    // Locator would resolve the selector twice and could silently choose a
    // replacement node after a DOM update.
    const elements = await matches.elementHandles();
    const count = elements.length;
    const index = request.params.index ?? 0;
    let metadata: {
      tagName: string;
      id: string | null;
      role: string | null;
      text: string;
      ariaLabel: string | null;
    };
    try {
      if (count === 0) {
        throw new ToolError(
          'NOT_FOUND',
          `No element matches selector: ${request.params.selector}`,
        );
      }
      if (request.params.index === undefined && count !== 1) {
        throw new ToolError(
          'CONFLICT',
          `Selector matched ${count} elements. Pass index explicitly to choose one.`,
        );
      }
      if (index >= count) {
        throw new ToolError(
          'INVALID_ARGUMENT',
          `index ${index} is out of range for ${count} matched elements.`,
        );
      }

      const element = elements[index]!;
      if (!(await element.isVisible())) {
        throw new ToolError(
          'PRECONDITION_FAILED',
          `Matched element at index ${index} is not visible.`,
        );
      }

      metadata = await element.evaluate(node => {
        const domElement = node as Element;
        return {
          tagName: domElement.tagName.toLowerCase(),
          id: domElement.id || null,
          role: domElement.getAttribute('role'),
          text: (domElement.textContent ?? '').trim().slice(0, 200),
          ariaLabel: domElement.getAttribute('aria-label'),
        };
      });
      // Keep the exact verified node pinned. A Locator would resolve again and
      // could click a replacement element if the DOM changed after metadata
      // collection; an ElementHandle instead fails if that node detaches.
      await element.click({
        button: request.params.button,
        modifiers: request.params.modifiers,
        timeout: request.params.timeout,
      });
    } catch (error) {
      if (error instanceof ToolError) {
        throw error;
      }
      if (
        error instanceof Error &&
        /timed?\s*out|timeout/i.test(error.message)
      ) {
        throw error;
      }
      throw new ToolError(
        'CONFLICT',
        'The verified element changed or detached before the click completed. Inspect the current page and retry.',
        {cause: error, retryable: true},
      );
    } finally {
      await Promise.allSettled(elements.map(element => element.dispose()));
    }

    response.appendResponseLine(
      `Clicked ${metadata.tagName} matched by ${request.params.selector} at index ${index}.`,
    );
    response.setStructuredContent({
      action: 'click',
      selector: request.params.selector,
      index,
      matchedCount: count,
      element: metadata,
    });
  },
});
