/**
 * Nia tools for the AI agent
 * Search pickup lines, contextual knowledge, and web search
 */

import { tool } from "ai";
import { z } from "zod";
import { config } from "../config";

const API = config.niaApiBase;

// Helper for Nia API calls
async function niaFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  if (!config.niaApiKey) {
    throw new Error("NIA_API_KEY is not configured");
  }

  const url = `${API}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      Authorization: `Bearer ${config.niaApiKey}`,
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Nia API error: ${error}`);
  }

  return response.json();
}

// Types
interface SearchResult {
  content: string;
  source?: string;
  path?: string;
  url?: string;
  score?: number;
}

interface SearchResponse {
  results?: SearchResult[];
  answer?: string;
  sources?: any[];
}

// Tools

export const searchPickupLines = tool({
  description: `Search your indexed pickup lines and conversation knowledge base using semantic search. Use this to find relevant pickup lines, flirty responses, conversation starters, or dating advice based on context. THIS IS YOUR MAIN TOOL FOR RELATIONSHIP ADVICE.`,
  inputSchema: z.object({
    query: z
      .string()
      .describe(
        "What to search for. Be specific about the context, mood, or topic (e.g., 'funny coffee pickup line', 'romantic response to good morning', 'witty comeback when she teases me')"
      ),
  }),
  execute: async ({ query }) => {
    const sourceId = config.niaCodebaseSource;

    if (!sourceId) {
      return {
        error: "NIA_CODEBASE_SOURCE not configured. Please set the pickup lines source ID.",
        suggestion: "Index your pickup lines with Nia first, then add the source ID to .env",
      };
    }

    // Determine if sourceId is a repository (owner/repo format) or data source UUID
    const isRepository = sourceId.includes("/") && !sourceId.includes("-");

    // Use Nia query endpoint with the specific source
    const response = await niaFetch<SearchResponse>("/query", {
      method: "POST",
      body: JSON.stringify({
        messages: [{ role: "user", content: query }],
        ...(isRepository 
          ? { repositories: [sourceId] }
          : { data_sources: [sourceId] }
        ),
        search_mode: "sources",
        include_sources: true,
      }),
    });

    // Extract and format results
    if (response.sources && response.sources.length > 0) {
      return {
        results: response.sources.slice(0, 5).map((s: any) => ({
          content: s.content || s.text,
          path: s.path,
          score: s.score,
        })),
        answer: response.answer,
      };
    }

    return {
      results: [],
      message: "No pickup lines found for this query. Try a different search term.",
    };
  },
});

export const niaSearch = tool({
  description: `General semantic search across all your indexed Nia data sources (documentation, repos, etc). Use for broader context when pickup lines search doesn't have what you need.`,
  inputSchema: z.object({
    query: z.string().describe("Search query - ask a natural language question"),
  }),
  execute: async ({ query }) => {
    const response = await niaFetch<SearchResponse>("/query", {
      method: "POST",
      body: JSON.stringify({
        messages: [{ role: "user", content: query }],
        search_mode: "sources",
        include_sources: true,
      }),
    });

    if (response.sources && response.sources.length > 0) {
      return {
        results: response.sources.slice(0, 5).map((s: any) => ({
          content: s.content || s.text,
          source: s.source_type,
          path: s.path,
          url: s.url,
        })),
        answer: response.answer,
      };
    }

    return { results: [], message: "No results found" };
  },
});

export const webSearch = tool({
  description: `Search the web for real-time information. Use sparingly - only when you need current information not available in the knowledge base.`,
  inputSchema: z.object({
    query: z.string().describe("Web search query"),
    num_results: z.number().min(1).max(10).default(5).describe("Number of results"),
    category: z
      .enum(["github", "company", "research paper", "news", "tweet", "pdf"])
      .optional()
      .describe("Filter by content category"),
  }),
  execute: async ({ query, num_results, category }) => {
    const response = await niaFetch<any>("/web-search", {
      method: "POST",
      body: JSON.stringify({
        query,
        num_results,
        ...(category && { category }),
      }),
    });

    return {
      results: response.results?.slice(0, num_results) || [],
    };
  },
});

// Export all Nia tools
export const niaTools = {
  searchPickupLines,
  niaSearch,
  webSearch,
};
