import * as fs from "node:fs";
import * as path from "node:path";
import * as os from "node:os";

export interface CachedPage {
    url: string;
    title: string;
    category: string;
    markdown: string;
    fetchedAt: number;
    lastUpdated?: string;
}

interface CacheManifest {
    version: number;
    pages: Record<string, CachedPage>;
    lastFullCrawl: number;
}

const CACHE_VERSION = 1;

export class DocCache {
    private cacheDir: string;
    private manifestPath: string;
    private manifest: CacheManifest;
    private ttlMs: number;

    constructor() {
        this.cacheDir =
            process.env["SBOX_DOCS_CACHE_DIR"] ||
            path.join(os.homedir(), ".sbox-docs-mcp", "cache");
        this.manifestPath = path.join(this.cacheDir, "manifest.json");
        this.ttlMs = parseInt(process.env["SBOX_DOCS_CACHE_TTL"] || "14400", 10) * 1000;
        this.manifest = { version: CACHE_VERSION, pages: {}, lastFullCrawl: 0 };
    }

    async init(): Promise<void> {
        fs.mkdirSync(this.cacheDir, { recursive: true });
        if (fs.existsSync(this.manifestPath)) {
            try {
                const raw = fs.readFileSync(this.manifestPath, "utf-8");
                const parsed = JSON.parse(raw) as CacheManifest;
                if (parsed.version === CACHE_VERSION) {
                    this.manifest = parsed;
                }
            } catch {
                // Corrupt cache — start fresh
            }
        }
    }

    isFresh(): boolean {
        if (this.manifest.lastFullCrawl === 0) return false;
        return Date.now() - this.manifest.lastFullCrawl < this.ttlMs;
    }

    isPageFresh(url: string): boolean {
        const page = this.manifest.pages[url];
        if (!page) return false;
        return Date.now() - page.fetchedAt < this.ttlMs;
    }

    getPage(url: string): CachedPage | undefined {
        return this.manifest.pages[url];
    }

    getAllPages(): CachedPage[] {
        return Object.values(this.manifest.pages);
    }

    getPageCount(): number {
        return Object.keys(this.manifest.pages).length;
    }

    setPage(page: CachedPage): void {
        this.manifest.pages[page.url] = page;
    }

    markFullCrawl(): void {
        this.manifest.lastFullCrawl = Date.now();
    }

    save(): void {
        fs.writeFileSync(this.manifestPath, JSON.stringify(this.manifest), "utf-8");
    }

    removePagesNotIn(validUrls: Set<string>): number {
        let removed = 0;
        for (const url of Object.keys(this.manifest.pages)) {
            if (!validUrls.has(url)) {
                delete this.manifest.pages[url];
                removed++;
            }
        }
        return removed;
    }

    clear(): void {
        this.manifest = { version: CACHE_VERSION, pages: {}, lastFullCrawl: 0 };
        this.save();
    }

    // --- Self-Test ---
    static runSelfTest(): { passed: string[]; failed: string[] } {
        const passed: string[] = [];
        const failed: string[] = [];

        function assert(name: string, condition: boolean) {
            (condition ? passed : failed).push(name);
        }

        // Use a temp directory so tests don't touch the real cache
        const tmpDir = path.join(os.tmpdir(), `sbox-docs-mcp-test-${Date.now()}`);
        process.env["SBOX_DOCS_CACHE_DIR"] = tmpDir;

        try {
            const cache = new DocCache();

            // Test: fresh cache should not be fresh
            assert("new cache is not fresh", !cache.isFresh());
            assert("new cache has 0 pages", cache.getPageCount() === 0);

            // Test: setPage + getPage round-trip
            const testPage: CachedPage = {
                url: "https://example.com/test",
                title: "Test Page",
                category: "Testing",
                markdown: "# Hello World\n\nThis is a test page.",
                fetchedAt: Date.now(),
            };
            cache.setPage(testPage);
            assert("setPage increments count", cache.getPageCount() === 1);

            const retrieved = cache.getPage(testPage.url);
            assert("getPage returns stored page", retrieved !== undefined);
            assert("getPage title matches", retrieved?.title === "Test Page");
            assert("getPage markdown matches", retrieved?.markdown === testPage.markdown);

            // Test: isPageFresh for recently stored page
            assert("recent page is fresh", cache.isPageFresh(testPage.url));
            assert("unknown page is not fresh", !cache.isPageFresh("https://example.com/nonexistent"));

            // Test: markFullCrawl + isFresh
            cache.markFullCrawl();
            assert("cache is fresh after markFullCrawl", cache.isFresh());

            // Test: save + init round-trip
            fs.mkdirSync(tmpDir, { recursive: true });
            cache.save();
            assert("manifest file exists after save", fs.existsSync(path.join(tmpDir, "manifest.json")));

            const cache2 = new DocCache();
            // cache2 reads from same tmpDir via env var
            // Need to call init synchronously-ish — but init is async, so test the sync parts
            fs.mkdirSync(tmpDir, { recursive: true });
            const raw = fs.readFileSync(path.join(tmpDir, "manifest.json"), "utf-8");
            const parsed = JSON.parse(raw) as { version: number; pages: Record<string, CachedPage> };
            assert("saved manifest has correct version", parsed.version === CACHE_VERSION);
            assert("saved manifest has 1 page", Object.keys(parsed.pages).length === 1);

            // Test: getAllPages
            const allPages = cache.getAllPages();
            assert("getAllPages returns 1 page", allPages.length === 1);
            assert("getAllPages first page title", allPages[0]?.title === "Test Page");

            // Test: removePagesNotIn
            cache.setPage(testPage);
            cache.setPage({
                url: "https://example.com/stale",
                title: "Stale Page",
                category: "Old",
                markdown: "This will be pruned.",
                fetchedAt: Date.now(),
            });
            assert("cache has 2 pages before prune", cache.getPageCount() === 2);
            const removed = cache.removePagesNotIn(new Set([testPage.url]));
            assert("removePagesNotIn returns 1", removed === 1);
            assert("cache has 1 page after prune", cache.getPageCount() === 1);
            assert("kept page still exists", cache.getPage(testPage.url) !== undefined);
            assert("stale page removed", cache.getPage("https://example.com/stale") === undefined);

            // Test: clear
            cache.clear();
            assert("cache empty after clear", cache.getPageCount() === 0);
            assert("cache not fresh after clear", !cache.isFresh());
        } finally {
            // Cleanup
            delete process.env["SBOX_DOCS_CACHE_DIR"];
            try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch { /* ignore */ }
        }

        return { passed, failed };
    }
}
