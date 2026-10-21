/**
 * Embedding Queue Service - Gated batch processing with backpressure
 *
 * Solves PGlite daemon crashes under heavy embedding load by:
 * 1. Processing embeddings in small batches (default: 50)
 * 2. Checkpointing after each batch to flush WAL
 * 3. Yielding to event loop between batches (backpressure)
 *
 * WASM Memory Constraints:
 * - PGlite runs in WASM with ~2GB memory limit
 * - Each 1024-dim embedding = 4KB
 * - WAL accumulates until CHECKPOINT
 * - HNSW index updates consume memory during inserts
 *
 * Without gating: 5000 embeddings = 20MB vectors + unbounded WAL = OOM
 * With gating: 50 embeddings/batch + checkpoint = bounded memory
 */

import { Chunk, Duration, Effect, Stream } from "effect";

/**
 * Configuration for embedding batch processing
 */
export interface EmbeddingQueueConfig {
  /**
   * Maximum embeddings per batch before checkpoint
   * Lower = more checkpoints, less memory pressure
   * Higher = fewer checkpoints, more throughput
   * Default: 50 (good balance for 1024-dim vectors)
   */
  batchSize: number;

  /**
   * Concurrency for Ollama embedding calls within a batch
   * Limited by Ollama's capacity and network
   * Default: 5
   */
  concurrency: number;

  /**
   * Delay between batches (milliseconds)
   * Allows event loop to breathe and GC to run
   * Default: 10ms
   */
  batchDelayMs: number;

  /**
   * Whether to run CHECKPOINT after each batch
   * Essential for preventing WAL accumulation
   * Default: true
   */
  checkpointAfterBatch: boolean;

  /**
   * Whether to use adaptive batch sizing based on memory pressure
   * Set to false for predictable behavior in tests
   * Default: true
   */
  adaptiveBatchSize: boolean;
}

/**
 * Default configuration - tuned for stability over speed
 *
 * CONSERVATIVE SETTINGS to prevent PGlite WASM crashes:
 * - batchSize: 20 (was 50) - smaller batches = less memory pressure
 * - concurrency: 3 (was 5) - fewer parallel Ollama calls
 * - batchDelayMs: 50 (was 10) - more time for GC between batches
 */
export const DEFAULT_QUEUE_CONFIG: EmbeddingQueueConfig = {
  batchSize: 20,
  concurrency: 3,
  batchDelayMs: 50,
  checkpointAfterBatch: true,
  adaptiveBatchSize: true,
};

/**
 * Progress callback for batch processing
 */
export interface BatchProgress {
  /** Current batch number (1-indexed) */
  batch: number;
  /** Total number of batches */
  totalBatches: number;
  /** Items processed so far */
  processed: number;
  /** Total items to process */
  total: number;
  /** Percentage complete (0-100) */
  percent: number;
}

/**
 * Process items in gated batches with backpressure
 *
 * This is the core primitive for preventing WASM OOM. It:
 * 1. Splits input into batches
 * 2. Processes each batch with bounded concurrency
 * 3. Runs afterBatch hook (for checkpoint)
 * 4. Yields between batches (backpressure)
 *
 * @param items - Items to process
 * @param process - Function to process each item
 * @param config - Queue configuration
 * @param afterBatch - Optional hook after each batch (e.g., checkpoint)
 * @param onProgress - Optional progress callback
 * @returns All processed results
 */
export function processInBatches<T, R, E>(
  items: readonly T[],
  process: (item: T) => Effect.Effect<R, E>,
  config: EmbeddingQueueConfig = DEFAULT_QUEUE_CONFIG,
  afterBatch?: () => Effect.Effect<void, E>,
  onProgress?: (progress: BatchProgress) => void
): Effect.Effect<R[], E> {
  return Effect.gen(function* () {
    const results: R[] = [];
    const totalBatches = Math.ceil(items.length / config.batchSize);

    for (let batchIdx = 0; batchIdx < totalBatches; batchIdx++) {
      const start = batchIdx * config.batchSize;
      const end = Math.min(start + config.batchSize, items.length);
      const batch = items.slice(start, end);

      // Process batch with bounded concurrency
      const batchResults = yield* Stream.fromIterable(batch).pipe(
        Stream.mapEffect(process, { concurrency: config.concurrency }),
        Stream.runCollect,
        Effect.map(Chunk.toArray)
      );

      results.push(...batchResults);

      // Report progress
      if (onProgress) {
        onProgress({
          batch: batchIdx + 1,
          totalBatches,
          processed: results.length,
          total: items.length,
          percent: Math.round((results.length / items.length) * 100),
        });
      }

      // Run after-batch hook (checkpoint)
      if (afterBatch && config.checkpointAfterBatch) {
        yield* afterBatch();
      }

      // Backpressure: yield to event loop between batches
      if (config.batchDelayMs > 0 && batchIdx < totalBatches - 1) {
        yield* Effect.sleep(Duration.millis(config.batchDelayMs));
      }
    }

    return results;
  });
}

/**
 * Adaptive batch sizing based on memory pressure
 *
 * Monitors process memory and reduces batch size if pressure is high.
 * This is a defense-in-depth measure for edge cases.
 *
 * Memory thresholds (of heap limit):
 * - < 50%: full batch size
 * - 50-70%: 75% batch size
 * - 70-85%: 50% batch size
 * - > 85%: 25% batch size (emergency mode)
 */
export function getAdaptiveBatchSize(baseBatchSize: number): number {
  // Only works in Node.js/Bun with v8 heap stats
  if (typeof process !== "undefined" && process.memoryUsage) {
    const mem = process.memoryUsage();
    const heapUsedRatio = mem.heapUsed / mem.heapTotal;

    if (heapUsedRatio > 0.85) {
      // Emergency: 25% batch size
      return Math.max(10, Math.floor(baseBatchSize * 0.25));
    } else if (heapUsedRatio > 0.7) {
      // High pressure: 50% batch size
      return Math.max(10, Math.floor(baseBatchSize * 0.5));
    } else if (heapUsedRatio > 0.5) {
      // Medium pressure: 75% batch size
      return Math.max(10, Math.floor(baseBatchSize * 0.75));
    }
  }

  return baseBatchSize;
}

/**
 * Create a gated embedding processor
 *
 * This is the high-level API for embedding with backpressure.
 * It wraps processInBatches with embedding-specific defaults.
 *
 * @param embedFn - Function to generate a single embedding
 * @param checkpointFn - Function to run CHECKPOINT
 * @param config - Optional configuration overrides
 */
export function createEmbeddingProcessor<E>(
  embedFn: (text: string) => Effect.Effect<number[], E>,
  checkpointFn: () => Effect.Effect<void, E>,
  config: Partial<EmbeddingQueueConfig> = {}
) {
  const fullConfig = { ...DEFAULT_QUEUE_CONFIG, ...config };

  return {
    /**
     * Process texts into embeddings with gated batching
     */
    embedBatch: (
      texts: readonly string[],
      onProgress?: (progress: BatchProgress) => void
    ): Effect.Effect<number[][], E> => {
      // Use adaptive batch size based on memory pressure (if enabled)
      const adaptiveConfig = {
        ...fullConfig,
        batchSize: fullConfig.adaptiveBatchSize
          ? getAdaptiveBatchSize(fullConfig.batchSize)
          : fullConfig.batchSize,
      };

      return processInBatches(
        texts,
        embedFn,
        adaptiveConfig,
        checkpointFn,
        onProgress
      );
    },

    /**
     * Get current configuration (for debugging)
     */
    getConfig: () => fullConfig,
  };
}
