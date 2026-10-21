import { z } from 'zod/v3';

// Search Schema
export const SearchSchema = z.object({
  query: z.string().describe('Search query string'),
  limit: z.number().optional().describe('Maximum number of results to return (default: 10)'),
  language: z.string().optional().describe('Language code for search results (default: auto)'),
  categories: z.enum([
    'general',
    'news',
    'images',
    'videos',
    'it',
    'science',
    'map',
    'music',
    'files',
    'social_media',
  ]).optional().describe('Categories to search for (default: general)'),
  timeRange: z.enum([
    'all',
    'day',
    'week',
    'month',
    'year',
  ]).optional().describe('Time range for search results (default: all)'),
});

export type SearchInput = z.infer<typeof SearchSchema>;

// Map Schema
export const MapSchema = z.object({
  url: z.string().describe('Starting URL for URL discovery'),
  search: z.string().optional().describe('Optional search term to filter URLs'),
  includeSubdomains: z.boolean().optional().describe('Include URLs from subdomains in results'),
  limit: z.number().optional().describe('Maximum number of URLs to return'),
}).strict();

export type MapInput = z.infer<typeof MapSchema>;

const ActionSchema = z.discriminatedUnion('type', [
  z.object({
    type: z.literal('wait'),
    milliseconds: z.number().describe('Time to wait in milliseconds'),
  }),
  z.object({
    type: z.literal('click'),
    selector: z.string().describe('CSS selector for the target element'),
  }),
  z.object({
    type: z.literal('write'),
    selector: z.string().describe('CSS selector for the target element'),
    text: z.string().describe('Text to write'),
  }),
  z.object({
    type: z.literal('press'),
    key: z.string().describe('Key to press'),
  }),
  z.object({
    type: z.literal('scroll'),
    direction: z.enum(['up', 'down']).describe('Scroll direction'),
  }),
  z.object({
    type: z.literal('executeJavascript'),
    script: z.string().describe('JavaScript code to execute'),
  }),
]);

// Scrape schema exposed to MCP clients and inspector forms
export const ScrapeToolInputSchema = z.object({
  url: z.string().describe('The URL to scrape'),
  formats: z.array(z.enum([
    'markdown',
    'html',
    'rawHtml',
    'screenshot',
    'links',
    'screenshot@fullPage',
  ])).optional().describe("Content formats to extract (default: ['markdown'])"),
  waitFor: z.number().optional().describe('Time in milliseconds to wait for dynamic content to load'),
  timeout: z.number().optional().describe('Maximum time in milliseconds to wait for the page to load'),
  skipTlsVerification: z.boolean().optional().describe('Skip TLS certificate verification'),
  allowExecuteJavascript: z.boolean().optional().describe('Must be true when actions contain executeJavascript. Use only for advanced page-side scripting.'),
  actions: z.array(ActionSchema).optional().describe('List of pre-scrape actions to run before content capture. Standard actions are bounded; executeJavascript requires allowExecuteJavascript: true.'),
}).strict();

// Scrape schema with cross-field runtime validation
export const ScrapeSchema = ScrapeToolInputSchema.superRefine((value, ctx) => {
  const usesExecuteJavascript = value.actions?.some((action) => action.type === 'executeJavascript') ?? false;

  if (usesExecuteJavascript && value.allowExecuteJavascript !== true) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['allowExecuteJavascript'],
      message: 'allowExecuteJavascript must be true when using executeJavascript actions',
    });
  }
});

export type ScrapeInput = z.infer<typeof ScrapeToolInputSchema>;

// Extract Schema
export const ExtractSchema = z.object({
  urls: z.array(z.string()).describe('List of URLs to extract information from'),
}).strict();

export type ExtractInput = z.infer<typeof ExtractSchema>;
