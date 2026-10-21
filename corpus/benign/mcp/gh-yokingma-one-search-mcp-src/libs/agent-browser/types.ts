/**
 * Types for agent-browser integration
 */

export interface AgentBrowserOptions {
  /**
   * Session name for the browser instance
   */
  sessionName?: string;
  /**
   * Headless mode
   */
  headless?: boolean;
  /**
   * Navigation timeout in milliseconds
   */
  timeout?: number;
  /**
   * Ignore HTTPS/TLS certificate errors for this browser context
   */
  ignoreHttpsErrors?: boolean;
}

export interface ScrapeResult {
  success: boolean;
  markdown?: string;
  html?: string;
  rawHtml?: string;
  links?: string[];
  screenshot?: string;
  error?: string;
}

export interface MapResult {
  success: boolean;
  links?: string[];
  error?: string;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  content?: string;
}

export type SearchEngine = 'bing' | 'google' | 'baidu' | 'sogou';

export interface SearchOptions {
  query: string;
  engine: SearchEngine;
  limit?: number;
}

export type ScrapeAction =
  | {
    type: 'wait';
    milliseconds: number;
  }
  | {
    type: 'click';
    selector: string;
  }
  | {
    type: 'write';
    selector: string;
    text: string;
  }
  | {
    type: 'press';
    key: string;
  }
  | {
    type: 'scroll';
    direction: 'up' | 'down';
  }
  | {
    type: 'executeJavascript';
    script: string;
  };

/**
 * Supported scrape options exposed by the wrapper
 */
export interface ScrapeOptions {
  formats?: Array<'markdown' | 'html' | 'rawHtml' | 'links' | 'screenshot' | 'screenshot@fullPage'>;
  waitFor?: number;
  timeout?: number;
  skipTlsVerification?: boolean;
  actions?: ScrapeAction[];
}

/**
 * Options for mapping URLs
 */
export interface MapOptions {
  search?: string;
  includeSubdomains?: boolean;
  limit?: number;
}
