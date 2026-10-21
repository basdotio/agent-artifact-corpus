import { ApiCache, type ApiType } from "./api-cache.js";

const SCHEMA_PAGE_URL = "https://sbox.game/api/schema";
const REQUEST_TIMEOUT_MS = 30000; // schema JSON can be large

// CDN release URL scraped from the schema page on 2026-04-09 — used as last-resort fallback.
// Override via SBOX_API_SCHEMA_URL env var for a more current version.
const KNOWN_SCHEMA_URL = "https://cdn.sbox.game/releases/2026-04-09-18-37-34.zip.json";

export interface ApiCrawlStats {
    typeCount: number;
    fromCache: boolean;
    schemaUrl: string;
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

/** Scrape the schema page HTML to extract the CDN download URL. */
async function discoverSchemaUrl(): Promise<string | null> {
    try {
        const res = await fetchWithTimeout(SCHEMA_PAGE_URL, 15000);
        if (!res.ok) return null;
        const html = await res.text();
        // URL pattern: https://cdn.sbox.game/releases/YYYY-MM-DD-HH-MM-SS.zip.json
        const match = html.match(/https:\/\/cdn\.sbox\.game\/releases\/[^"'\s<>]+\.json/);
        return match?.[0] ?? null;
    } catch {
        return null;
    }
}

/** Verify a candidate URL still responds with 200. */
async function verifyUrl(url: string): Promise<boolean> {
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        const res = await fetch(url, { method: "HEAD", signal: controller.signal });
        clearTimeout(timeout);
        return res.ok;
    } catch {
        return false;
    }
}

/** Resolve which schema URL to use, in priority order. */
async function resolveSchemaUrl(cachedUrl: string): Promise<string | null> {
    // 1. Explicit env override
    const envUrl = process.env["SBOX_API_SCHEMA_URL"];
    if (envUrl) return envUrl;

    // 2. Scrape the live page (works if page becomes server-side rendered again)
    const scraped = await discoverSchemaUrl();
    if (scraped) return scraped;

    // 3. Re-use the cached URL (CDN keeps old releases indefinitely)
    if (cachedUrl && await verifyUrl(cachedUrl)) return cachedUrl;

    // 4. Built-in fallback URL
    if (await verifyUrl(KNOWN_SCHEMA_URL)) return KNOWN_SCHEMA_URL;

    return null;
}

/** Download and parse the JSON schema from the CDN URL. */
async function downloadSchema(url: string): Promise<{ Types: ApiType[] } | null> {
    try {
        const res = await fetchWithTimeout(url, REQUEST_TIMEOUT_MS);
        if (!res.ok) return null;
        const json = (await res.json()) as { Types?: ApiType[] };
        if (!Array.isArray(json?.Types)) return null;
        return json as { Types: ApiType[] };
    } catch {
        return null;
    }
}

/** Filter to types worth indexing: public, non-compiler-generated. */
function filterTypes(types: ApiType[]): ApiType[] {
    return types.filter((t) => {
        if (!t.IsPublic) return false;
        // Skip compiler-generated and internal types
        if (!t.Name || t.Name.startsWith("<") || t.Name.startsWith("__")) return false;
        if (!t.FullName) return false;
        return true;
    });
}

export class ApiCrawler {
    private cache: ApiCache;

    constructor(cache: ApiCache) {
        this.cache = cache;
    }

    async crawlAll(onProgress?: (msg: string) => void): Promise<ApiCrawlStats> {
        // Return from cache if still fresh
        if (this.cache.isFresh()) {
            const types = this.cache.loadTypes() ?? [];
            return { typeCount: types.length, fromCache: true, schemaUrl: this.cache.getSchemaUrl() };
        }

        onProgress?.("Resolving schema URL...");
        const schemaUrl = await resolveSchemaUrl(this.cache.getSchemaUrl());
        if (!schemaUrl) {
            process.stderr.write(
                "\n[sbox-docs-mcp] ERROR: Could not find a valid API schema URL.\n" +
                "[sbox-docs-mcp] Set SBOX_API_SCHEMA_URL env var to the URL from https://sbox.game/api/schema\n"
            );
            const stale = this.cache.loadTypes();
            return { typeCount: stale?.length ?? 0, fromCache: true, schemaUrl: "" };
        }

        onProgress?.(`Downloading schema from ${schemaUrl}...`);
        const schema = await downloadSchema(schemaUrl);
        if (!schema) {
            process.stderr.write(`\n[sbox-docs-mcp] ERROR: Could not download or parse API schema from ${schemaUrl}\n`);
            const stale = this.cache.loadTypes();
            return {
                typeCount: stale?.length ?? 0,
                fromCache: true,
                schemaUrl,
            };
        }

        const filtered = filterTypes(schema.Types);
        process.stderr.write(
            `\n[sbox-docs-mcp] API schema: ${schema.Types.length} total types, ${filtered.length} public after filtering\n`
        );

        this.cache.save(schemaUrl, filtered);
        return { typeCount: filtered.length, fromCache: false, schemaUrl };
    }

    // --- Self-Test (pure functions only, no network) ---
    static runSelfTest(): { passed: string[]; failed: string[] } {
        const passed: string[] = [];
        const failed: string[] = [];

        function assert(name: string, condition: boolean) {
            (condition ? passed : failed).push(name);
        }

        // Test: filterTypes
        const types: ApiType[] = [
            { FullName: "Sandbox.Component", Name: "Component", IsPublic: true, IsClass: true },
            { FullName: "Sandbox.Internal.Stuff", Name: "<>Compiler", IsPublic: true, IsClass: true },
            { FullName: "Sandbox.Private", Name: "Private", IsPublic: false, IsClass: true },
            { FullName: "", Name: "NoName", IsPublic: true, IsClass: true },
        ];

        const filtered = filterTypes(types);

        assert("filterTypes keeps public types", filtered.some((t) => t.Name === "Component"));
        assert("filterTypes removes compiler-generated (<>)", !filtered.some((t) => t.Name === "<>Compiler"));
        assert("filterTypes removes non-public", !filtered.some((t) => t.Name === "Private"));
        assert("filterTypes removes empty FullName", !filtered.some((t) => t.Name === "NoName"));
        assert("filterTypes result has 1 type", filtered.length === 1);

        return { passed, failed };
    }
}
