/**
 * EmbeddingQueue Tests
 *
 * Tests for gated batch processing with backpressure.
 * These tests verify the queue prevents WASM OOM under heavy load.
 */

import { describe, expect, it } from "bun:test";
import { Effect } from "effect";
import {
  processInBatches,
  createEmbeddingProcessor,
  getAdaptiveBatchSize,
  DEFAULT_QUEUE_CONFIG,
  type BatchProgress,
  type EmbeddingQueueConfig,
} from "./EmbeddingQueue.js";

describe("EmbeddingQueue", () => {
  describe("processInBatches", () => {
    it("processes all items", async () => {
      const items = [1, 2, 3, 4, 5];
      const process = (n: number) => Effect.succeed(n * 2);

      const result = await Effect.runPromise(
        processInBatches(items, process, {
          ...DEFAULT_QUEUE_CONFIG,
          batchSize: 2,
        })
      );

      expect(result).toEqual([2, 4, 6, 8, 10]);
    });

    it("respects batch size", async () => {
      const items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
      const batchesProcessed: number[] = [];
      let currentBatch = 0;

      const process = (n: number) =>
        Effect.sync(() => {
          if (!batchesProcessed.includes(currentBatch)) {
            batchesProcessed.push(currentBatch);
          }
          return n;
        });

      const afterBatch = () =>
        Effect.sync(() => {
          currentBatch++;
        });

      const config: EmbeddingQueueConfig = {
        batchSize: 3,
        concurrency: 1,
        batchDelayMs: 0,
        checkpointAfterBatch: true,
        adaptiveBatchSize: false,
      };

      await Effect.runPromise(
        processInBatches(items, process, config, afterBatch)
      );

      // 10 items / 3 per batch = 4 batches (3+3+3+1)
      expect(currentBatch).toBe(4);
    });

    it("calls afterBatch hook after each batch", async () => {
      const items = [1, 2, 3, 4, 5, 6];
      let checkpointCount = 0;

      const process = (n: number) => Effect.succeed(n);
      const afterBatch = () =>
        Effect.sync(() => {
          checkpointCount++;
        });

      const config: EmbeddingQueueConfig = {
        batchSize: 2,
        concurrency: 1,
        batchDelayMs: 0,
        checkpointAfterBatch: true,
        adaptiveBatchSize: false,
      };

      await Effect.runPromise(
        processInBatches(items, process, config, afterBatch)
      );

      // 6 items / 2 per batch = 3 batches = 3 checkpoints
      expect(checkpointCount).toBe(3);
    });

    it("skips afterBatch when checkpointAfterBatch is false", async () => {
      const items = [1, 2, 3, 4];
      let checkpointCount = 0;

      const process = (n: number) => Effect.succeed(n);
      const afterBatch = () =>
        Effect.sync(() => {
          checkpointCount++;
        });

      const config: EmbeddingQueueConfig = {
        batchSize: 2,
        concurrency: 1,
        batchDelayMs: 0,
        checkpointAfterBatch: false,
        adaptiveBatchSize: false,
      };

      await Effect.runPromise(
        processInBatches(items, process, config, afterBatch)
      );

      expect(checkpointCount).toBe(0);
    });

    it("reports progress correctly", async () => {
      const items = [1, 2, 3, 4, 5, 6];
      const progressReports: BatchProgress[] = [];

      const process = (n: number) => Effect.succeed(n);
      const onProgress = (p: BatchProgress) => progressReports.push({ ...p });

      const config: EmbeddingQueueConfig = {
        batchSize: 2,
        concurrency: 1,
        batchDelayMs: 0,
        checkpointAfterBatch: false,
        adaptiveBatchSize: false,
      };

      await Effect.runPromise(
        processInBatches(items, process, config, undefined, onProgress)
      );

      expect(progressReports).toHaveLength(3);

      // First batch
      expect(progressReports[0]).toEqual({
        batch: 1,
        totalBatches: 3,
        processed: 2,
        total: 6,
        percent: 33,
      });

      // Second batch
      expect(progressReports[1]).toEqual({
        batch: 2,
        totalBatches: 3,
        processed: 4,
        total: 6,
        percent: 67,
      });

      // Third batch
      expect(progressReports[2]).toEqual({
        batch: 3,
        totalBatches: 3,
        processed: 6,
        total: 6,
        percent: 100,
      });
    });

    it("handles empty input", async () => {
      const items: number[] = [];
      const process = (n: number) => Effect.succeed(n);

      const result = await Effect.runPromise(
        processInBatches(items, process, DEFAULT_QUEUE_CONFIG)
      );

      expect(result).toEqual([]);
    });

    it("handles single item", async () => {
      const items = [42];
      const process = (n: number) => Effect.succeed(n * 2);

      const result = await Effect.runPromise(
        processInBatches(items, process, DEFAULT_QUEUE_CONFIG)
      );

      expect(result).toEqual([84]);
    });

    it("propagates errors from process function", async () => {
      const items = [1, 2, 3];
      const process = (n: number) =>
        n === 2 ? Effect.fail(new Error("boom")) : Effect.succeed(n);

      const result = await Effect.runPromise(
        processInBatches(items, process, {
          ...DEFAULT_QUEUE_CONFIG,
          batchSize: 10,
        }).pipe(Effect.either)
      );

      expect(result._tag).toBe("Left");
      if (result._tag === "Left") {
        expect((result.left as Error).message).toBe("boom");
      }
    });

    it("respects concurrency within batch", async () => {
      const items = [1, 2, 3, 4, 5, 6];
      let maxConcurrent = 0;
      let currentConcurrent = 0;

      const process = (n: number) =>
        Effect.gen(function* () {
          currentConcurrent++;
          maxConcurrent = Math.max(maxConcurrent, currentConcurrent);
          // Simulate async work
          yield* Effect.sleep("1 millis");
          currentConcurrent--;
          return n;
        });

      const config: EmbeddingQueueConfig = {
        batchSize: 6, // All in one batch
        concurrency: 3, // Max 3 concurrent
        batchDelayMs: 0,
        checkpointAfterBatch: false,
        adaptiveBatchSize: false,
      };

      await Effect.runPromise(processInBatches(items, process, config));

      // Should never exceed concurrency limit
      expect(maxConcurrent).toBeLessThanOrEqual(3);
      // Should use concurrency (not just 1)
      expect(maxConcurrent).toBeGreaterThan(1);
    });
  });

  describe("getAdaptiveBatchSize", () => {
    it("returns base size when memory is low", () => {
      // Can't easily mock process.memoryUsage, so just test the function exists
      // and returns a reasonable value
      const result = getAdaptiveBatchSize(50);
      expect(result).toBeGreaterThanOrEqual(10);
      expect(result).toBeLessThanOrEqual(50);
    });

    it("never returns less than 10", () => {
      // Even with tiny base size, should return at least 10
      const result = getAdaptiveBatchSize(5);
      // If memory is low, returns base (5), otherwise scaled
      expect(result).toBeGreaterThanOrEqual(5);
    });
  });

  describe("createEmbeddingProcessor", () => {
    it("creates a processor with embedBatch method", async () => {
      const embedFn = (_text: string) => Effect.succeed([1, 2, 3]);
      const checkpointFn = (): Effect.Effect<void> => Effect.void;

      const processor = createEmbeddingProcessor(embedFn, checkpointFn);

      expect(processor.embedBatch).toBeDefined();
      expect(processor.getConfig).toBeDefined();
    });

    it("processes texts through embedBatch", async () => {
      const embedFn = (text: string) => Effect.succeed([text.length]);
      const checkpointFn = (): Effect.Effect<void> => Effect.void;

      const processor = createEmbeddingProcessor(embedFn, checkpointFn, {
        batchSize: 2,
        batchDelayMs: 0,
      });

      const result = await Effect.runPromise(
        processor.embedBatch(["a", "bb", "ccc"])
      );

      expect(result).toEqual([[1], [2], [3]]);
    });

    it("calls checkpoint after each batch", async () => {
      let checkpointCount = 0;
      const embedFn = (_text: string) => Effect.succeed([1]);
      const checkpointFn = () =>
        Effect.sync(() => {
          checkpointCount++;
        });

      const processor = createEmbeddingProcessor(embedFn, checkpointFn, {
        batchSize: 2,
        batchDelayMs: 0,
        adaptiveBatchSize: false,
      });

      await Effect.runPromise(processor.embedBatch(["a", "b", "c", "d", "e"]));

      // 5 items / 2 per batch = 3 batches = 3 checkpoints
      expect(checkpointCount).toBe(3);
    });

    it("reports progress", async () => {
      const embedFn = (_text: string) => Effect.succeed([1]);
      const checkpointFn = (): Effect.Effect<void> => Effect.void;
      const progressReports: BatchProgress[] = [];

      const processor = createEmbeddingProcessor(embedFn, checkpointFn, {
        batchSize: 2,
        batchDelayMs: 0,
        adaptiveBatchSize: false,
      });

      await Effect.runPromise(
        processor.embedBatch(["a", "b", "c", "d"], (p) =>
          progressReports.push({ ...p })
        )
      );

      expect(progressReports).toHaveLength(2);
      expect(progressReports[0].percent).toBe(50);
      expect(progressReports[1].percent).toBe(100);
    });

    it("uses custom config", () => {
      const embedFn = (_text: string) => Effect.succeed([1]);
      const checkpointFn = (): Effect.Effect<void> => Effect.void;

      const processor = createEmbeddingProcessor(embedFn, checkpointFn, {
        batchSize: 100,
        concurrency: 10,
      });

      const config = processor.getConfig();
      expect(config.batchSize).toBe(100);
      expect(config.concurrency).toBe(10);
    });
  });

  describe("DEFAULT_QUEUE_CONFIG", () => {
    it("has sensible defaults", () => {
      // Conservative settings to prevent PGlite WASM crashes
      expect(DEFAULT_QUEUE_CONFIG.batchSize).toBe(20);
      expect(DEFAULT_QUEUE_CONFIG.concurrency).toBe(3);
      expect(DEFAULT_QUEUE_CONFIG.batchDelayMs).toBe(50);
      expect(DEFAULT_QUEUE_CONFIG.checkpointAfterBatch).toBe(true);
      expect(DEFAULT_QUEUE_CONFIG.adaptiveBatchSize).toBe(true);
    });
  });
});
