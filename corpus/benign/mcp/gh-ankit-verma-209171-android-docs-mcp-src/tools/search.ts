/**
 * MCP Tool: search_android_docs
 * Search Android developer documentation by query.
 */

import { z } from "zod";
import { fetchPage } from "../lib/fetcher.js";
import { parseSearchResults } from "../lib/parser.js";
import { getSearchUrl } from "../lib/url-resolver.js";

export const searchToolName = "search_android_docs";

export const searchToolDescription =
    "Search the official Android developer documentation (developer.android.com). " +
    "Returns matching API reference classes and developer guide articles. " +
    "Use this to find relevant documentation pages for any Android topic.";

export const searchToolSchema = {
    query: z.string().describe("Search query (e.g., 'jetpack compose navigation', 'RecyclerView', 'Room database')"),
    max_results: z
        .number()
        .min(1)
        .max(30)
        .optional()
        .default(10)
        .describe("Maximum number of results to return (default: 10)"),
};

export async function searchToolHandler(args: {
    query: string;
    max_results?: number;
}): Promise<string> {
    const { query, max_results = 10 } = args;

    const url = getSearchUrl(query);
    const html = await fetchPage(url);
    const results = parseSearchResults(html, query);

    // Build markdown response
    const lines: string[] = [];
    lines.push(`# Search Results for "${query}"\n`);

    // API Reference results
    const apiSlice = results.apiResults.slice(0, max_results);
    if (apiSlice.length > 0) {
        lines.push(`## API Reference (${apiSlice.length} matches)\n`);
        for (const r of apiSlice) {
            lines.push(`- [${r.name}](${r.url})`);
        }
        lines.push("");
    }

    // Guide results
    const guideSlice = results.guideResults.slice(0, max_results);
    if (guideSlice.length > 0) {
        lines.push(`## Guides & Tutorials (${guideSlice.length} matches)\n`);
        for (const r of guideSlice) {
            lines.push(`- [${r.title}](${r.url})`);
            if (r.snippet) {
                lines.push(`  ${r.snippet}`);
            }
        }
        lines.push("");
    }

    if (apiSlice.length === 0 && guideSlice.length === 0) {
        lines.push("No results found. Try a different search query.");
    }

    lines.push(`\n*Source: ${url}*`);

    return lines.join("\n");
}
