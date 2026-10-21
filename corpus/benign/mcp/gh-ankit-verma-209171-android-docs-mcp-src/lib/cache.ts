/**
 * In-memory LRU cache with configurable TTL.
 * Keys are URLs, values are parsed markdown strings.
 */

const DEFAULT_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const MAX_ENTRIES = 500;

interface CacheEntry {
  value: string;
  timestamp: number;
}

class LRUCache {
  private cache = new Map<string, CacheEntry>();
  private ttlMs: number;
  private maxEntries: number;

  constructor(ttlMs?: number, maxEntries?: number) {
    this.ttlMs = ttlMs ?? (Number(process.env.CACHE_TTL_MS) || DEFAULT_TTL_MS);
    this.maxEntries = maxEntries ?? MAX_ENTRIES;
  }

  get(key: string): string | null {
    const entry = this.cache.get(key);
    if (!entry) return null;

    // Evict if expired
    if (Date.now() - entry.timestamp > this.ttlMs) {
      this.cache.delete(key);
      return null;
    }

    // Move to end (most recently used) by re-inserting
    this.cache.delete(key);
    this.cache.set(key, entry);
    return entry.value;
  }

  set(key: string, value: string): void {
    // Delete first to reset position if key already exists
    this.cache.delete(key);

    // Evict oldest entry if at capacity
    if (this.cache.size >= this.maxEntries) {
      const oldestKey = this.cache.keys().next().value;
      if (oldestKey !== undefined) {
        this.cache.delete(oldestKey);
      }
    }

    this.cache.set(key, { value, timestamp: Date.now() });
  }

  has(key: string): boolean {
    return this.get(key) !== null;
  }

  clear(): void {
    this.cache.clear();
  }

  get size(): number {
    return this.cache.size;
  }
}

// Singleton instance shared across all tools
export const cache = new LRUCache();
