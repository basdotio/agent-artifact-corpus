/**
 * MCP Tool: get_android_doc_page
 * Fetch any Android developer documentation page and return it as clean markdown.
 */

import { z } from "zod";
import { fetchPage } from "../lib/fetcher.js";
import { parsePage, detectPageType } from "../lib/parser.js";

export const getDocToolName = "get_android_doc_page";

export const getDocToolDescription =
    "Fetch and read any page from the official Android developer documentation (developer.android.com). " +
    "Provide a full URL and get back clean markdown content. " +
    "Automatically detects whether it's an API reference, guide, release notes, or other page and applies the best parser. " +
    "Use this when you already have a specific URL from search results or a known documentation page.";

export const getDocToolSchema = {
    url: z
        .string()
        .url()
        .describe(
            "Full URL of the Android documentation page (e.g., 'https://developer.android.com/guide/navigation/get-started')",
        ),
};

export async function getDocToolHandler(args: { url: string }): Promise<string> {
    const { url } = args;

    // Validate it's a developer.android.com URL
    const parsed = new URL(url);
    if (!parsed.hostname.endsWith("developer.android.com")) {
        return `Error: URL must be from developer.android.com. Got: ${parsed.hostname}`;
    }

    const html = await fetchPage(url);
    const pageType = detectPageType(url);
    const markdown = parsePage(html, url);

    if (!markdown || markdown.trim().length === 0) {
        return `No content could be extracted from ${url}. The page may not exist or may have an unexpected format.`;
    }

    const lines: string[] = [];
    lines.push(`*Page type: ${pageType} | Source: ${url}*\n`);
    lines.push(markdown);

    return lines.join("\n");
}
