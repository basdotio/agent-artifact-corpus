import { DocCache, type CachedPage } from "./cache.js";

const LLMS_TXT_URL = "https://sbox.game/llms.txt";
const WIKI_BASE_URL = "https://sbox.game";
const WIKI_DOC_PREFIX = "/dev/doc/";
const REQUEST_DELAY_MS = 150;
const REQUEST_TIMEOUT_MS = 15000;

interface LlmsEntry {
    title: string;
    path: string; // e.g. /dev/doc/scene/components.md
}

function delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Parse an llms.txt file and return all /dev/doc/ entries. */
function parseLlmsTxt(raw: string): LlmsEntry[] {
    const entries: LlmsEntry[] = [];
    const linkPattern = /^-\s+\[(.+?)\]\((.+?)\)/;
    for (const line of raw.split("\n")) {
        const match = line.match(linkPattern);
        if (!match) continue;
        const title = match[1]!;
        const path = match[2]!;
        if (!path.startsWith(WIKI_DOC_PREFIX)) continue;
        entries.push({ title, path });
    }
    return entries;
}

/** Extract a category label from the /dev/doc/{category}/... path. */
function extractCategory(path: string): string {
    const stripped = path.replace(WIKI_DOC_PREFIX, "").replace(/\.md$/, "");
    const parts = stripped.split("/").filter(Boolean);
    return parts.length > 0 ? parts[0]! : "general";
}

/** Canonical page URL (without .md) used as the cache key and shown to users. */
function pageUrlFromPath(path: string): string {
    return `${WIKI_BASE_URL}${path.replace(/\.md$/, "")}`;
}

/** Raw Markdown URL used to fetch content. */
function markdownUrlFromPath(path: string): string {
    const mdPath = path.endsWith(".md") ? path : `${path}.md`;
    return `${WIKI_BASE_URL}${mdPath}`;
}

async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { signal: controller.signal });
        clearTimeout(timeout);
        return res;
    } catch (e) {
        clearTimeout(timeout);
        throw e;
    }
}

async function fetchLlmsTxt(): Promise<LlmsEntry[] | null> {
    try {
        const res = await fetchWithTimeout(LLMS_TXT_URL, REQUEST_TIMEOUT_MS);
        if (!res.ok) return null;
        const raw = await res.text();
        return parseLlmsTxt(raw);
    } catch {
        return null;
    }
}

async function fetchMarkdown(url: string): Promise<string | null> {
    try {
        const res = await fetchWithTimeout(url, REQUEST_TIMEOUT_MS);
        if (!res.ok) return null;
        return await res.text();
    } catch {
        return null;
    }
}

export interface CrawlStats {
    crawled: number;
    failed: number;
    fromCache: number;
    total: number;
}

export class DocCrawler {
    private cache: DocCache;
    private llmsEntries: LlmsEntry[] = [];

    // --- Self-Test (pure functions only, no network) ---
    static runSelfTest(): { passed: string[]; failed: string[] } {
        const passed: string[] = [];
        const failed: string[] = [];

        function assert(name: string, condition: boolean) {
            (condition ? passed : failed).push(name);
        }

        // Test: parseLlmsTxt
        const sample = [
            "# S&box Documentation",
            "",
            "## Scene",
            "- [Components](/dev/doc/scene/components.md): Learn about components",
            "- [GameObjects](/dev/doc/scene/gameobjects.md)",
            "## Networking",
            "- [RPC Messages](/dev/doc/networking/rpc-messages.md): Remote procedure calls",
            "- [Ignore this](https://example.com/other): Not a wiki page",
            "  Not a list item",
        ].join("\n");

        const entries = parseLlmsTxt(sample);
        assert("parseLlmsTxt returns 3 wiki entries", entries.length === 3);
        assert("parseLlmsTxt first entry title", entries[0]?.title === "Components");
        assert("parseLlmsTxt first entry path", entries[0]?.path === "/dev/doc/scene/components.md");
        assert("parseLlmsTxt skips non-/dev/doc/ links", !entries.some((e) => e.path.startsWith("https")));

        // Test: extractCategory
        assert("extractCategory scene/components.md", extractCategory("/dev/doc/scene/components.md") === "scene");
        assert("extractCategory networking/rpc.md", extractCategory("/dev/doc/networking/rpc.md") === "networking");
        assert("extractCategory top-level.md", extractCategory("/dev/doc/top-level.md") === "top-level");
        assert("extractCategory empty suffix", extractCategory("/dev/doc/") === "general");

        // Test: pageUrlFromPath
        assert(
            "pageUrlFromPath strips .md",
            pageUrlFromPath("/dev/doc/scene/components.md") === "https://sbox.game/dev/doc/scene/components"
        );
        assert(
            "pageUrlFromPath no-op without .md",
            pageUrlFromPath("/dev/doc/scene/components") === "https://sbox.game/dev/doc/scene/components"
        );

        // Test: markdownUrlFromPath
        assert(
            "markdownUrlFromPath adds .md",
            markdownUrlFromPath("/dev/doc/scene/components") === "https://sbox.game/dev/doc/scene/components.md"
        );
        assert(
            "markdownUrlFromPath no double .md",
            markdownUrlFromPath("/dev/doc/scene/components.md") === "https://sbox.game/dev/doc/scene/components.md"
        );

        return { passed, failed };
    }

    constructor(cache: DocCache) {
        this.cache = cache;
    }

    async crawlAll(
        onProgress?: (stats: CrawlStats) => void
    ): Promise<CrawlStats> {
        // If cache is fresh, skip crawling
        if (this.cache.isFresh()) {
            const count = this.cache.getPageCount();
            return { crawled: 0, failed: 0, fromCache: count, total: count };
        }

        const stats: CrawlStats = { crawled: 0, failed: 0, fromCache: 0, total: 0 };

        // Fetch and parse the llms.txt index
        const entries = await fetchLlmsTxt();
        if (!entries) {
            process.stderr.write(
                "\n[sbox-docs-mcp] ERROR: Could not fetch documentation index from sbox.game/llms.txt\n"
            );
            stats.fromCache = this.cache.getPageCount();
            return stats;
        }

        this.llmsEntries = entries;
        stats.total = entries.length;

        process.stderr.write(
            `\n[sbox-docs-mcp] Found ${entries.length} docs in llms.txt\n`
        );

        for (const entry of entries) {
            const pageUrl = pageUrlFromPath(entry.path);

            // Check page-level cache
            if (this.cache.isPageFresh(pageUrl)) {
                stats.fromCache++;
                onProgress?.(stats);
                continue;
            }

            const mdUrl = markdownUrlFromPath(entry.path);
            const markdown = await fetchMarkdown(mdUrl);

            if (!markdown) {
                stats.failed++;
                process.stderr.write(`\n[sbox-docs-mcp] Skipped (fetch failed): ${mdUrl}\n`);
                onProgress?.(stats);
                await delay(REQUEST_DELAY_MS);
                continue;
            }
            if (markdown.length < 10) {
                stats.failed++;
                process.stderr.write(`\n[sbox-docs-mcp] Skipped (too short): ${mdUrl}\n`);
                onProgress?.(stats);
                await delay(REQUEST_DELAY_MS);
                continue;
            }

            const page: CachedPage = {
                url: pageUrl,
                title: entry.title,
                category: extractCategory(entry.path),
                markdown,
                fetchedAt: Date.now(),
            };

            this.cache.setPage(page);
            stats.crawled++;
            onProgress?.(stats);
            await delay(REQUEST_DELAY_MS);
        }

        // Prune cached pages that are no longer in the llms.txt index
        const validUrls = new Set(entries.map((e) => pageUrlFromPath(e.path)));
        const pruned = this.cache.removePagesNotIn(validUrls);
        if (pruned > 0) {
            process.stderr.write(
                `\n[sbox-docs-mcp] Pruned ${pruned} stale page(s) from cache\n`
            );
        }

        this.cache.markFullCrawl();
        this.cache.save();
        return stats;
    }

    async crawlSinglePage(url: string): Promise<CachedPage | null> {
        // Normalize: strip trailing slash and ensure no .md suffix in the cache key
        let normalized = url.endsWith("/") ? url.slice(0, -1) : url;
        normalized = normalized.replace(/\.md$/, "");

        // Check cache first
        if (this.cache.isPageFresh(normalized)) {
            return this.cache.getPage(normalized) || null;
        }

        // Load the index if we haven't yet (needed for title + category lookup)
        if (this.llmsEntries.length === 0) {
            const entries = await fetchLlmsTxt();
            if (entries) this.llmsEntries = entries;
        }

        // Derive the /dev/doc/... path from the URL
        const docPath = normalized.replace(WIKI_BASE_URL, "");
        const mdUrl = docPath.endsWith(".md") ? `${WIKI_BASE_URL}${docPath}` : `${WIKI_BASE_URL}${docPath}.md`;

        const markdown = await fetchMarkdown(mdUrl);
        if (!markdown || markdown.length < 10) return null;

        // Try to find a matching entry for the title; fall back to path-derived title
        const entry = this.llmsEntries.find(
            (e) => pageUrlFromPath(e.path) === normalized
        );
        const title =
            entry?.title ||
            docPath.split("/").pop()?.replace(/\.md$/, "").replace(/-/g, " ") ||
            "Untitled";

        const page: CachedPage = {
            url: normalized,
            title,
            category: extractCategory(`${docPath}.md`),
            markdown,
            fetchedAt: Date.now(),
        };

        this.cache.setPage(page);
        this.cache.save();
        return page;
    }
}
