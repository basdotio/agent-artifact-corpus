/**
 * @license
 * Copyright 2025 Google LLC
 * SPDX-License-Identifier: Apache-2.0
 */

import {zod} from '../third_party/index.js';

import {ToolCategory} from './categories.js';
import {defineTool} from './ToolDefinition.js';

export const screenshot = defineTool({
  name: 'take_screenshot',
  description: `Captures the visual state of the currently selected page. Use it to verify page layout, visible UI state, selector targets, in-page dialogs/modals, or the effect of a navigation/click; it is not a substitute for DOM values, network evidence, or script inspection. By default it returns the visible viewport, while fullPage=true captures the whole document; oversized captures may be saved as a temporary artifact instead of attached. Pass filePath for a reusable local artifact; existing files require confirmOverwrite=true and remain subject to --allowedRoots.`,
  annotations: {
    title: 'Take Screenshot',
    category: ToolCategory.DEBUGGING,
    // Not read-only due to filePath param.
    readOnlyHint: false,
  },
  schema: {
    format: zod
      .enum(['png', 'jpeg'])
      .default('png')
      .describe(
        'Image format for the attachment or saved file. Defaults to png; use jpeg when smaller lossy output is preferred.',
      ),
    quality: zod
      .number()
      .min(0)
      .max(100)
      .optional()
      .describe(
        'Compression quality for JPEG format (0-100). Higher values mean better quality but larger file sizes. Ignored for PNG format.',
      ),
    fullPage: zod
      .boolean()
      .optional()
      .describe(
        'Capture the entire scrollable document when true; leave false or omit it for the currently visible viewport.',
      ),
    filePath: zod
      .string()
      .optional()
      .describe(
        'Optional absolute or working-directory-relative path for a reusable screenshot artifact. Omit it to attach the image directly. Subject to --allowedRoots when configured.',
      ),
    confirmOverwrite: zod
      .boolean()
      .default(false)
      .describe(
        'Must be true when filePath already exists. New files do not require confirmation.',
      ),
  },
  handler: async (request, response, context) => {
    const page = context.getSelectedPage();

    const format = request.params.format;
    const quality = format === 'png' ? undefined : request.params.quality;

    const screenshot = await page.screenshot({
      type: format,
      fullPage: request.params.fullPage,
      quality,
    });

    if (request.params.fullPage) {
      response.appendResponseLine(
        'Took a screenshot of the full current page.',
      );
    } else {
      response.appendResponseLine(
        "Took a screenshot of the current page's viewport.",
      );
    }

    if (request.params.filePath) {
      const file = await context.saveFile(screenshot, request.params.filePath, {
        confirmOverwrite: request.params.confirmOverwrite,
      });
      response.appendResponseLine(`Saved screenshot to ${file.filename}.`);
      response.setStructuredContent({
        format,
        fullPage: request.params.fullPage ?? false,
        byteLength: screenshot.length,
        filename: file.filename,
      });
    } else if (screenshot.length >= 2_000_000) {
      const {filename} = await context.saveTemporaryFile(
        screenshot,
        `image/${request.params.format}`,
      );
      response.appendResponseLine(`Saved screenshot to ${filename}.`);
      response.setStructuredContent({
        format,
        fullPage: request.params.fullPage ?? false,
        byteLength: screenshot.length,
        filename,
      });
    } else {
      response.attachImage({
        mimeType: `image/${request.params.format}`,
        data: Buffer.from(screenshot).toString('base64'),
      });
      response.setStructuredContent({
        format,
        fullPage: request.params.fullPage ?? false,
        byteLength: screenshot.length,
        attached: true,
      });
    }
  },
});
