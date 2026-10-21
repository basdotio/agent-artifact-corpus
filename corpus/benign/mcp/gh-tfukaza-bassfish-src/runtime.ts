import { performance } from 'node:perf_hooks';
import type { Clock } from './domain.js';

export class SystemClock implements Clock {
  private readonly origin = Date.now() - performance.now();
  private offset = Date.now() - performance.now();
  now(): number {
    return this.origin + performance.now();
  }
  wallNow(): number {
    return Date.now();
  }
  discontinuity(): boolean {
    const offset = Date.now() - performance.now();
    const changed = Math.abs(offset - this.offset) > 2_000;
    this.offset = offset;
    return changed;
  }
}

export class KeyedMutex {
  private readonly tails = new Map<string, Promise<void>>();
  async run<T>(key: string, fn: () => Promise<T>): Promise<T> {
    const previous = this.tails.get(key) ?? Promise.resolve();
    let release!: () => void;
    const next = new Promise<void>(resolve => {
      release = resolve;
    });
    this.tails.set(key, next);
    await previous;
    try {
      return await fn();
    } finally {
      release();
      if (this.tails.get(key) === next) this.tails.delete(key);
    }
  }
}
