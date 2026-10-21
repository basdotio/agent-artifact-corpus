/**
 * HTTP fetch wrapper for developer.android.com.
 * Handles User-Agent, retries on 5xx/network errors, and cache integration.
 */

import { cache } from "./cache.js";

const USER_AGENT = "AndroidDocsMCP/1.0 (https://github.com/ankit-verma-209171/android-docs-mcp)";
const RETRY_DELAY_MS = 2000;
const MAX_RETRIES = 1;
const REQUEST_TIMEOUT_MS = 15000;

export class FetchError extends Error {
    constructor(
        message: string,
        public statusCode?: number,
    ) {
        super(message);
        this.name = "FetchError";
    }
}

/**
 * Fetch a page from developer.android.com.
 * Returns cached HTML if available, otherwise fetches and caches.
 *
 * @param url - Full URL to fetch
 * @param skipCache - If true, bypass cache and always fetch fresh
 * @returns Raw HTML string
 */
export async function fetchPage(url: string, skipCache = false): Promise<string> {
    // Check cache first
    if (!skipCache) {
        const cached = cache.get(url);
        if (cached !== null) {
            return cached;
        }
    }

    const html = await fetchWithRetry(url);

    // Cache the result
    cache.set(url, html);

    return html;
}

async function fetchWithRetry(url: string, attempt = 0): Promise<string> {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

        const response = await fetch(url, {
            headers: {
                "User-Agent": USER_AGENT,
                Accept: "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            },
            signal: controller.signal,
            redirect: "follow",
        });

        clearTimeout(timeoutId);

        if (response.status >= 500 && attempt < MAX_RETRIES) {
            await delay(RETRY_DELAY_MS);
            return fetchWithRetry(url, attempt + 1);
        }

        if (!response.ok) {
            throw new FetchError(
                `Failed to fetch ${url}: HTTP ${response.status} ${response.statusText}`,
                response.status,
            );
        }

        return await response.text();
    } catch (error) {
        // Retry on network errors (not HTTP errors)
        if (
            attempt < MAX_RETRIES &&
            error instanceof Error &&
            !(error instanceof FetchError)
        ) {
            await delay(RETRY_DELAY_MS);
            return fetchWithRetry(url, attempt + 1);
        }
        if (error instanceof FetchError) throw error;
        throw new FetchError(`Network error fetching ${url}: ${error}`);
    }
}

function delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
}
