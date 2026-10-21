/** Seedable, dependency-free PRNG so identical seeds yield identical text. */

/** xmur3 string hash -> 32-bit seed. */
function xmur3(str: string): () => number {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return h >>> 0;
  };
}

/** mulberry32: fast 32-bit generator in [0, 1). */
function mulberry32(a: number): () => number {
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export class Rng {
  private next: () => number;

  /** Omit `seed` for a random stream; pass a string/number for reproducible output. */
  constructor(seed?: string | number) {
    const s = seed === undefined ? `${Date.now()}:${Math.random()}` : String(seed);
    this.next = mulberry32(xmur3(s)());
  }

  /** float in [0, 1). */
  float(): number {
    return this.next();
  }

  /** integer in [min, max]. */
  int(min: number, max: number): number {
    return min + Math.floor(this.next() * (max - min + 1));
  }

  /** Uniformly pick one element. */
  pick<T>(items: readonly T[]): T {
    return items[this.int(0, items.length - 1)]!;
  }

  /** True with probability `p`. */
  chance(p: number): boolean {
    return this.next() < p;
  }
}
