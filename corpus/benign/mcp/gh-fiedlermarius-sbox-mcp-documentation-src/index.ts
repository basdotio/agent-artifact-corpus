#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { DocCache } from "./cache.js";
import { DocCrawler } from "./crawler.js";
import { DocSearch } from "./search.js";
import { ApiCache } from "./api-cache.js";
import { ApiCrawler } from "./api-crawler.js";
import { ApiSearch } from "./api-search.js";
import { z } from "zod";
import {
    SearchDocsInput,
    GetDocPageInput,
    ListCategoriesInput,
    SearchApiInput,
    GetApiTypeInput,
} from "./schemas.js";
import { handleSearchDocs } from "./tools/searchDocs.js";
import { handleGetDocPage } from "./tools/getDocPage.js";
import { handleListCategories } from "./tools/listCategories.js";
import { handleSearchApi } from "./tools/searchApi.js";
import { handleGetApiType } from "./tools/getApiType.js";

const cache = new DocCache();
const crawler = new DocCrawler(cache);
const search = new DocSearch();
const apiCache = new ApiCache();
const apiCrawler = new ApiCrawler(apiCache);
const apiSearch = new ApiSearch();

const server = new McpServer({
    name: "sbox-docs-mcp",
    version: "0.1.0",
});

// --- Tool: sbox_search_docs ---
server.tool(
    "sbox_search_docs",
    "Search s&box documentation for guides, tutorials, and concepts. Returns matching pages with titles, URLs, and relevant snippets.",
    SearchDocsInput.shape,
    async (params) => {
        await ensureIndexed();
        return handleSearchDocs(search, params);
    }
);

// --- Tool: sbox_get_doc_page ---
server.tool(
    "sbox_get_doc_page",
    "Fetch a specific s&box documentation page and return its content as Markdown. Supports chunked reading for large pages via start_index and max_length.",
    GetDocPageInput.shape,
    async (params) => {
        await ensureIndexed();
        return handleGetDocPage(search, crawler, params);
    }
);

// --- Tool: sbox_list_doc_categories ---
server.tool(
    "sbox_list_doc_categories",
    "List all available s&box documentation categories with page counts. Use this to discover what documentation is available before searching.",
    ListCategoriesInput.shape,
    async () => {
        await ensureIndexed();
        return handleListCategories(search);
    }
);

// --- Tool: sbox_search_api ---
server.tool(
    "sbox_search_api",
    "Search the s&box API reference for classes, structs, interfaces, and their members. Returns matching types with descriptions and member names. Use sbox_get_api_type to get full details for a specific type.",
    SearchApiInput.shape,
    async (params) => {
        await ensureApiIndexed();
        return handleSearchApi(apiSearch, params);
    }
);

// --- Tool: sbox_get_api_type ---
server.tool(
    "sbox_get_api_type",
    "Get full API reference for a specific s&box type: all public methods, properties, fields, and their signatures and descriptions. Accepts short names (e.g. 'Component') or fully-qualified names (e.g. 'Sandbox.Component').",
    GetApiTypeInput.shape,
    async (params) => {
        await ensureApiIndexed();
        return handleGetApiType(apiSearch, params);
    }
);

// --- Tool: sbox_cache_status ---
server.tool(
    "sbox_cache_status",
    "Show the current status of the documentation cache and search index. Use this to verify the MCP server is running and has indexed documentation.",
    z.object({}).shape,
    async () => {
        const cacheCount = cache.getPageCount();
        const indexCount = search.pageCount;
        const isFresh = cache.isFresh();
        const apiTypeCount = apiCache.getTypeCount();
        const apiIndexCount = apiSearch.typeCount;
        const apiIsFresh = apiCache.isFresh();
        const lines = [
            `## S&box Docs MCP — Cache Status\n`,
            `### Documentation`,
            `- **Index ready:** ${indexReady ? "Yes" : "No (still crawling...)"}`,
            `- **Pages in cache:** ${cacheCount}`,
            `- **Pages in search index:** ${indexCount}`,
            `- **Cache fresh:** ${isFresh ? "Yes" : "No (will re-crawl on next use)"}`,
            ``,
            `### API Reference`,
            `- **Index ready:** ${apiIndexReady ? "Yes" : "No (still loading...)"}`,
            `- **Types in cache:** ${apiTypeCount}`,
            `- **Types in search index:** ${apiIndexCount}`,
            `- **Cache fresh:** ${apiIsFresh ? "Yes" : "No (will re-fetch on next use)"}`,
            `- **Schema URL:** ${apiCache.getSchemaUrl() || "(not yet fetched)"}`,
        ];
        return { content: [{ type: "text" as const, text: lines.join("\n") }] };
    }
);

// --- Tool: sbox_run_tests ---
server.tool(
    "sbox_run_tests",
    "Run built-in self-tests for the cache, search index, and crawler. Returns pass/fail results for each test case.",
    z.object({}).shape,
    async () => {
        const results = [
            { module: "DocCache", ...DocCache.runSelfTest() },
            { module: "DocSearch", ...DocSearch.runSelfTest() },
            { module: "DocCrawler", ...DocCrawler.runSelfTest() },
            { module: "ApiCache", ...ApiCache.runSelfTest() },
            { module: "ApiSearch", ...ApiSearch.runSelfTest() },
            { module: "ApiCrawler", ...ApiCrawler.runSelfTest() },
        ];

        const lines = [`## Self-Test Results\n`];
        let totalPassed = 0;
        let totalFailed = 0;

        for (const r of results) {
            totalPassed += r.passed.length;
            totalFailed += r.failed.length;
            const icon = r.failed.length === 0 ? "\u2705" : "\u274c";
            lines.push(`### ${icon} ${r.module} — ${r.passed.length} passed, ${r.failed.length} failed\n`);
            for (const p of r.passed) lines.push(`- \u2705 ${p}`);
            for (const f of r.failed) lines.push(`- \u274c ${f}`);
            lines.push("");
        }

        lines.push(`---\n**Total: ${totalPassed} passed, ${totalFailed} failed**`);

        return { content: [{ type: "text" as const, text: lines.join("\n") }] };
    }
);

// --- Initialization ---
let indexReady = false;
let indexPromise: Promise<void> | null = null;
let apiIndexReady = false;
let apiIndexPromise: Promise<void> | null = null;

async function ensureIndexed(): Promise<void> {
    if (indexReady) return;
    if (indexPromise) return indexPromise;
    indexPromise = doIndex();
    return indexPromise;
}

async function doIndex(): Promise<void> {
    await cache.init();

    const stats = await crawler.crawlAll((s) => {
        const done = s.crawled + s.failed + s.fromCache;
        if (done % 10 === 0 || done === s.total) {
            const pct = s.total > 0 ? Math.round((done / s.total) * 100) : 0;
            process.stderr.write(
                `[sbox-docs-mcp] Crawling... ${done}/${s.total} (${pct}%) — ${s.crawled} fetched, ${s.failed} skipped\n`
            );
        }
    });

    process.stderr.write(
        `\n[sbox-docs-mcp] Crawl complete: ${stats.crawled} fetched, ${stats.fromCache} cached, ${stats.failed} failed\n`
    );

    const pages = cache.getAllPages();
    search.buildIndex(pages);
    process.stderr.write(
        `[sbox-docs-mcp] Search index ready: ${pages.length} pages indexed\n`
    );
    indexReady = true;
}

async function ensureApiIndexed(): Promise<void> {
    if (apiIndexReady) return;
    if (apiIndexPromise) return apiIndexPromise;
    apiIndexPromise = doApiIndex();
    return apiIndexPromise;
}

async function doApiIndex(): Promise<void> {
    await apiCache.init();

    const stats = await apiCrawler.crawlAll((msg) => {
        process.stderr.write(`[sbox-docs-mcp] API: ${msg}\n`);
    });

    process.stderr.write(
        `[sbox-docs-mcp] API schema ready: ${stats.typeCount} types (${stats.fromCache ? "from cache" : "freshly downloaded"})\n`
    );

    const types = apiCache.loadTypes() ?? [];
    apiSearch.buildIndex(types);
    process.stderr.write(
        `[sbox-docs-mcp] API search index ready: ${apiSearch.typeCount} types indexed\n`
    );
    apiIndexReady = true;
}

// --- Start ---
async function main(): Promise<void> {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    process.stderr.write("[sbox-docs-mcp] Server started on stdio\n");

    // Begin crawling + indexing immediately so the first query doesn't return empty
    ensureIndexed().catch((err) => {
        process.stderr.write(`[sbox-docs-mcp] Background index error: ${err}\n`);
    });
    ensureApiIndexed().catch((err) => {
        process.stderr.write(`[sbox-docs-mcp] Background API index error: ${err}\n`);
    });
}

main().catch((err) => {
    process.stderr.write(`[sbox-docs-mcp] Fatal error: ${err}\n`);
    process.exit(1);
});
