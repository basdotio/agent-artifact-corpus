#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/server';
import { StdioServerTransport } from '@modelcontextprotocol/server/stdio';
import * as z from 'zod/v4';
import { closeBrowser } from './browser/playwright.js';
import { defaultOutputDir } from './lib/paths.js';
import { inspectPage } from './tools/inspect.js';
import { captureScreenshotsTool } from './tools/screenshot.js';
import { analyzeDesign } from './tools/analyze-design.js';
import { analyzeResponsiveTool } from './tools/analyze-responsive.js';
import { generateDocs } from './tools/generate-docs.js';

const server = new McpServer({
  name: 'website-analyzer-mcp',
  version: '0.1.0',
});

function textResult(payload: unknown) {
  return {
    content: [{ type: 'text' as const, text: typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2) }],
  };
}

function errorResult(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return {
    isError: true as const,
    content: [{ type: 'text' as const, text: `Error: ${message}` }],
  };
}

server.registerTool(
  'inspect_page',
  {
    title: 'Inspect Page',
    description:
      'Inspect a single URL: HTML/DOM summaries, headings, links, images, buttons, forms, and semantic landmarks. Returns structured JSON for the LLM (does not write markdown).',
    inputSchema: z.object({
      url: z.string().url().describe('Page URL to inspect'),
    }),
  },
  async ({ url }) => {
    try {
      const { inspect } = await inspectPage(url);
      return textResult(inspect);
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  'capture_screenshot',
  {
    title: 'Capture Screenshot',
    description:
      'Capture screenshots at mobile/tablet/desktop viewports (up to 5 widths). Writes PNG files under output/<host>/screenshots/.',
    inputSchema: z.object({
      url: z.string().url(),
      outputDir: z.string().optional().describe(`Base output directory (default: ${defaultOutputDir()})`),
      widths: z.array(z.number().int().positive()).optional().describe('Viewport widths in px'),
    }),
  },
  async ({ url, outputDir, widths }) => {
    try {
      const result = await captureScreenshotsTool(url, { outputDir, widths });
      return textResult(result);
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  'analyze_design',
  {
    title: 'Analyze Design',
    description:
      'Extract design system signals: colors, typography, spacing, border radius, shadows, layout, components. Returns structured JSON (tokens + design). Does not write markdown.',
    inputSchema: z.object({
      url: z.string().url(),
    }),
  },
  async ({ url }) => {
    try {
      return textResult(await analyzeDesign(url));
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  'analyze_responsive',
  {
    title: 'Analyze Responsive',
    description:
      'Analyze responsive behavior across Desktop / Tablet / Mobile viewports. Optionally capture screenshots.',
    inputSchema: z.object({
      url: z.string().url(),
      screenshots: z.boolean().optional().describe('Capture viewport screenshots (default: false)'),
      outputDir: z.string().optional(),
      widths: z.array(z.number().int().positive()).optional(),
    }),
  },
  async ({ url, screenshots, outputDir, widths }) => {
    try {
      return textResult(
        await analyzeResponsiveTool(url, {
          captureScreenshots: screenshots ?? false,
          outputDir,
          widths,
        }),
      );
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  'generate_docs',
  {
    title: 'Generate Docs',
    description:
      'Write deterministic template docs from structured analysis: design.md, rule.md, component.md, layout.md, content.md, README.md. No external LLM API required. Default output: <package>/docs/<host>/',
    inputSchema: z.object({
      url: z.string().url(),
      outputDir: z.string().optional().describe('Base output directory (default: ./docs under package root)'),
      documents: z
        .array(z.enum(['design', 'rule', 'component', 'layout', 'content', 'readme']))
        .optional()
        .describe('Which documents to generate'),
      screenshots: z.boolean().optional().describe('Include responsive screenshots (default from SCREENSHOT env)'),
    }),
  },
  async ({ url, outputDir, documents, screenshots }) => {
    try {
      const result = await generateDocs(url, { outputDir, documents, screenshots });
      return textResult({
        ok: true,
        message: `Wrote ${result.files.length} files`,
        outputDir: result.outputDir,
        files: result.files,
      });
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerPrompt(
  'analyze_website_design',
  {
    title: 'Analyze Website Design',
    description: 'Prompt template for turning website analyzer JSON into design docs / rebuild guidance.',
    argsSchema: {
      url: z.string().describe('Website URL being analyzed'),
    },
  },
  ({ url }) => ({
    messages: [
      {
        role: 'user' as const,
        content: {
          type: 'text' as const,
          text: `Analyze the website data for ${url} provided by the website-analyzer-mcp tools (inspect_page, analyze_design, analyze_responsive).

Identify:
1. Color system
2. Typography
3. Spacing
4. Layout
5. Components
6. Responsive behavior
7. UI patterns
8. Design rules

Do not invent values that cannot be inferred from the provided website data.
Prefer writing design.md, rule.md, component.md, layout.md, and README.md from the structured JSON.
If files should be written deterministically without interpretation, call generate_docs instead.`,
        },
      },
    ],
  }),
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('website-analyzer-mcp v0.1.0 running on stdio');
}

const shutdown = async () => {
  await closeBrowser();
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);

main().catch(async (error) => {
  console.error('Fatal:', error);
  await closeBrowser();
  process.exit(1);
});
