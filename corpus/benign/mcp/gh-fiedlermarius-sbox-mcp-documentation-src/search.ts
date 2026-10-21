import MiniSearch from "minisearch";
import type { CachedPage } from "./cache.js";

export interface SearchResult {
    title: string;
    url: string;
    category: string;
    snippet: string;
    score: number;
}

export interface CategoryInfo {
    name: string;
    pageCount: number;
    pages: Array<{ title: string; url: string }>;
}

export class DocSearch {
    static runSelfTest: () => { passed: string[]; failed: string[] };
    private index: MiniSearch;
    private pages: Map<string, CachedPage> = new Map();

    constructor() {
        this.index = new MiniSearch({
            fields: ["title", "category", "markdown"],
            storeFields: ["title", "url", "category"],
            searchOptions: {
                boost: { title: 3, category: 2, markdown: 1 },
                fuzzy: 0.2,
                prefix: true,
            },
        });
    }

    buildIndex(pages: CachedPage[]): void {
        this.pages.clear();
        this.index.removeAll();

        const docs = pages.map((p, i) => ({
            id: i,
            title: p.title,
            url: p.url,
            category: p.category,
            markdown: p.markdown,
        }));

        this.index.addAll(docs);
        for (const p of pages) {
            this.pages.set(p.url, p);
        }
    }

    search(
        query: string,
        limit: number = 10,
        category?: string
    ): SearchResult[] {
        let results = this.index.search(query);

        if (category) {
            results = results.filter(
                (r) =>
                    (r as unknown as { category: string }).category?.toLowerCase() ===
                    category.toLowerCase()
            );
        }

        return results.slice(0, limit).map((r) => {
            const page = this.pages.get(
                (r as unknown as { url: string }).url
            );
            return {
                title: (r as unknown as { title: string }).title || "",
                url: (r as unknown as { url: string }).url || "",
                category: (r as unknown as { category: string }).category || "",
                snippet: page ? extractSnippet(page.markdown, query) : "",
                score: r.score,
            };
        });
    }

    getCategories(): CategoryInfo[] {
        const categories = new Map<string, CategoryInfo>();
        for (const page of this.pages.values()) {
            let cat = categories.get(page.category);
            if (!cat) {
                cat = { name: page.category, pageCount: 0, pages: [] };
                categories.set(page.category, cat);
            }
            cat.pageCount++;
            cat.pages.push({ title: page.title, url: page.url });
        }
        return Array.from(categories.values()).sort((a, b) =>
            a.name.localeCompare(b.name)
        );
    }

    getPage(url: string): CachedPage | undefined {
        return this.pages.get(url);
    }

    get pageCount(): number {
        return this.pages.size;
    }
}

// --- Self-Test ---
DocSearch.runSelfTest = function (): { passed: string[]; failed: string[] } {
    const passed: string[] = [];
    const failed: string[] = [];

    function assert(name: string, condition: boolean) {
        (condition ? passed : failed).push(name);
    }

    const search = new DocSearch();

    // Test: empty index
    assert("empty index has 0 pages", search.pageCount === 0);
    assert("search on empty returns []", search.search("anything").length === 0);
    assert("getCategories on empty returns []", search.getCategories().length === 0);

    // Test: buildIndex + search
    const testPages: CachedPage[] = [
        {
            url: "https://docs.facepunch.com/s/sbox-dev/doc/controller-input-test",
            title: "Controller Input",
            category: "Systems",
            markdown: "You can control vibration intensity on gamepads using Input.TriggerHaptics.",
            fetchedAt: Date.now(),
        },
        {
            url: "https://docs.facepunch.com/s/sbox-dev/doc/getting-started-test",
            title: "Getting Started",
            category: "About",
            markdown: "Welcome to s&box! This guide will help you get started with game development.",
            fetchedAt: Date.now(),
        },
        {
            url: "https://docs.facepunch.com/s/sbox-dev/doc/networking-test",
            title: "Networking Basics",
            category: "Systems",
            markdown: "Networking in s&box uses a component-based sync system with [Sync] attributes.",
            fetchedAt: Date.now(),
        },
    ];

    search.buildIndex(testPages);
    assert("buildIndex sets pageCount to 3", search.pageCount === 3);

    // Test: search finds correct page
    const vibrationResults = search.search("vibration intensity");
    assert("vibration search returns results", vibrationResults.length > 0);
    assert("vibration top hit is Controller Input", vibrationResults[0]?.title === "Controller Input");

    // Test: search with category filter
    const systemsResults = search.search("s&box", 10, "Systems");
    assert("category filter excludes About pages", systemsResults.every(r => r.category === "Systems"));

    // Test: getPage
    const page = search.getPage(testPages[0]!.url);
    assert("getPage returns stored page", page !== undefined);
    assert("getPage title matches", page?.title === "Controller Input");

    // Test: getCategories
    const cats = search.getCategories();
    assert("getCategories returns 2 categories", cats.length === 2);
    const systemsCat = cats.find(c => c.name === "Systems");
    assert("Systems category has 2 pages", systemsCat?.pageCount === 2);

    // Test: search result has snippet
    assert("search result has snippet", (vibrationResults[0]?.snippet?.length ?? 0) > 0);

    // Test: search result has score
    assert("search result has positive score", (vibrationResults[0]?.score ?? 0) > 0);

    // Test: limit works
    const limited = search.search("s&box", 1);
    assert("limit=1 returns at most 1", limited.length <= 1);

    // Test: unknown query returns empty
    const noResults = search.search("xyzzyplugh");
    assert("nonsense query returns empty", noResults.length === 0);

    return { passed, failed };
};

function extractSnippet(
    markdown: string,
    query: string,
    maxLength: number = 200
): string {
    const lower = markdown.toLowerCase();
    const queryLower = query.toLowerCase();
    const words = queryLower.split(/\s+/);

    // Find the best position — where the most query words cluster together
    let bestPos = 0;
    let bestScore = -1;
    for (let i = 0; i < lower.length - 50; i += 20) {
        const window = lower.slice(i, i + maxLength);
        let score = 0;
        for (const w of words) {
            if (window.includes(w)) score++;
        }
        if (score > bestScore) {
            bestScore = score;
            bestPos = i;
        }
    }

    // If no match found, return the start of the document
    if (bestScore <= 0) bestPos = 0;

    // Expand to word boundaries
    const start = Math.max(
        0,
        markdown.lastIndexOf(" ", Math.max(0, bestPos - 10)) + 1
    );
    let end = Math.min(markdown.length, start + maxLength);
    const spaceEnd = markdown.indexOf(" ", end);
    if (spaceEnd !== -1 && spaceEnd - end < 20) end = spaceEnd;

    let snippet = markdown.slice(start, end).trim();
    // Clean up markdown artifacts
    snippet = snippet.replace(/#{1,6}\s*/g, "").replace(/\n{2,}/g, "\n");
    if (start > 0) snippet = "…" + snippet;
    if (end < markdown.length) snippet = snippet + "…";
    return snippet;
}
