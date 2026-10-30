"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.cachedFetch = cachedFetch;
const cache = new Map();
async function cachedFetch(url, options) {
    const cacheKey = `${url}:${JSON.stringify(options)}`;
    if (cache.has(cacheKey)) {
        return cache.get(cacheKey);
    }
    try {
        const resp = await fetch(url, options);
        if (!resp.ok) {
            throw new Error(`Network response was not ok: ${resp.status} ${resp.statusText}`);
        }
        if (resp.headers.get('Content-Type')?.includes('application/json')) {
            const data = (await resp.json());
            cache.set(cacheKey, data);
            return data;
        }
        const textData = (await resp.text());
        cache.set(cacheKey, textData);
        return textData;
    }
    catch (error) {
        throw new Error(`Fetch failed for ${url}: ${error.message}`);
    }
}
