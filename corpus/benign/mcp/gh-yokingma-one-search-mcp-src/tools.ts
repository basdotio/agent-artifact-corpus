import { SearchSchema, MapSchema, ScrapeToolInputSchema, ExtractSchema } from './schemas.js';

// Tool definitions following MCP SDK v1.25+ pattern
export const SEARCH_TOOL = {
  name: 'one_search',
  description: 'Search and retrieve content from web pages. Returns SERP results by default (url, title, description).',
  schema: SearchSchema,
} as const;

export const MAP_TOOL = {
  name: 'one_map',
  description: 'Discover URLs from a starting point by loading a page in the browser and extracting links from its HTML.',
  schema: MapSchema,
} as const;

export const SCRAPE_TOOL = {
  name: 'one_scrape',
  description: 'Scrape a single webpage and return markdown, HTML, links, or a screenshot. Supports navigation timeout, TLS verification control, full-page screenshots, bounded pre-scrape actions, and advanced executeJavascript only when allowExecuteJavascript is true.',
  schema: ScrapeToolInputSchema,
} as const;

export const EXTRACT_TOOL = {
  name: 'one_extract',
  description: 'Fetch and preprocess page content from one or more URLs. Returns cleaned text blocks that can be passed to downstream tools or models.',
  schema: ExtractSchema,
} as const;
