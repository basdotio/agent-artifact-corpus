/**
 * @license
 * Copyright 2025 Google Inc.
 * SPDX-License-Identifier: Apache-2.0
 */

export class Mutex {
  static Guard = class Guard {
    #mutex: Mutex;
    constructor(mutex: Mutex) {
      this.#mutex = mutex;
    }
    dispose(): void {
      return this.#mutex.release();
    }
  };

  #locked = false;
  #acquirers: Array<() => void> = [];

  // This is FIFO.
  async acquire(
    options: {timeoutMs?: number; signal?: AbortSignal} = {},
  ): Promise<InstanceType<typeof Mutex.Guard>> {
    if (options.signal?.aborted) {
      throw options.signal.reason instanceof Error
        ? options.signal.reason
        : new Error('Tool call was cancelled');
    }
    if (!this.#locked) {
      this.#locked = true;
      return new Mutex.Guard(this);
    }

    const {resolve, reject, promise} = Promise.withResolvers<void>();
    let timeoutId: ReturnType<typeof setTimeout> | undefined;

    const cleanup = () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      options.signal?.removeEventListener('abort', abort);
    };

    const abort = () => {
      this.#acquirers = this.#acquirers.filter(item => item !== acquire);
      cleanup();
      reject(
        options.signal?.reason instanceof Error
          ? options.signal.reason
          : new Error('Tool call was cancelled'),
      );
    };

    const acquire = () => {
      cleanup();
      resolve();
    };

    this.#acquirers.push(acquire);

    if (options.timeoutMs !== undefined) {
      timeoutId = setTimeout(() => {
        this.#acquirers = this.#acquirers.filter(item => item !== acquire);
        cleanup();
        reject(new Error('Timed out waiting for another tool call to finish'));
      }, options.timeoutMs);
    }
    options.signal?.addEventListener('abort', abort, {once: true});

    await promise;
    return new Mutex.Guard(this);
  }

  release(): void {
    const resolve = this.#acquirers.shift();
    if (!resolve) {
      this.#locked = false;
      return;
    }
    resolve();
  }
}
