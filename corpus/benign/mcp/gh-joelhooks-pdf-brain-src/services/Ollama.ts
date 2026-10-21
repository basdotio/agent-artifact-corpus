/**
 * Ollama Embedding Service
 */

import {
  Effect,
  Context,
  Layer,
  Schedule,
  Duration,
  Chunk,
  Stream,
} from "effect";
import { OllamaError, loadConfig } from "../types.js";
import { spawn } from "child_process";
import { getLogLevel, logDebug, logInfo } from "../logger.js";

// ============================================================================
// Service Definition
// ============================================================================

export class Ollama extends Context.Tag("Ollama")<
  Ollama,
  {
    readonly embed: (text: string) => Effect.Effect<number[], OllamaError>;
    readonly embedBatch: (
      texts: string[],
      concurrency?: number,
    ) => Effect.Effect<number[][], OllamaError>;
    readonly checkHealth: () => Effect.Effect<void, OllamaError>;
  }
>() {}

// ============================================================================
// Implementation
// ============================================================================

interface OllamaEmbeddingResponse {
  embedding: number[];
}

interface OllamaTagsResponse {
  models: Array<{ name: string }>;
}

/**
 * Detected embedding dimension (set on first embedding call)
 * Different models have different dimensions:
 * - mxbai-embed-large: 1024
 * - nomic-embed-text: 768
 * - all-minilm: 384
 */
let detectedEmbeddingDimension: number | null = null;

/**
 * Get the detected embedding dimension (for use by database schema)
 */
export function getEmbeddingDimension(): number | null {
  return detectedEmbeddingDimension;
}

/**
 * Validates embedding dimensions and values before database insert
 *
 * On first call, records the dimension for consistency checking.
 * Subsequent calls verify dimension matches the first.
 *
 * @param embedding - The embedding vector to validate
 * @returns Effect that fails with OllamaError if invalid
 */
function validateEmbedding(
  embedding: number[],
): Effect.Effect<number[], OllamaError> {
  if (embedding.length === 0) {
    return Effect.fail(
      new OllamaError({
        reason: "Invalid embedding: dimension 0 (empty vector)",
      }),
    );
  }

  // First embedding sets the expected dimension
  if (detectedEmbeddingDimension === null) {
    detectedEmbeddingDimension = embedding.length;
    logDebug(`Ollama embedding dimension detected: ${detectedEmbeddingDimension}`);
  } else if (embedding.length !== detectedEmbeddingDimension) {
    // Subsequent embeddings must match
    return Effect.fail(
      new OllamaError({
        reason: `Invalid embedding: dimension ${embedding.length} (expected ${detectedEmbeddingDimension})`,
      }),
    );
  }

  if (embedding.some((v) => !Number.isFinite(v))) {
    return Effect.fail(
      new OllamaError({
        reason:
          "Invalid embedding: contains non-finite values (NaN or Infinity)",
      }),
    );
  }

  return Effect.succeed(embedding);
}

/**
 * Auto-install a model using `ollama pull`
 * @param model - Model name to install
 * @param host - Ollama host URL
 */
function autoInstallModel(
  model: string,
  host: string,
): Effect.Effect<void, OllamaError> {
  logInfo(`Ollama: installing model ${model}...`);

  return Effect.tryPromise({
    try: () =>
      new Promise<void>((resolve, reject) => {
        const proc = spawn("ollama", ["pull", model], {
          // Never pollute stdout (agent protocol). Forward to stderr if enabled.
          stdio: ["ignore", "pipe", "pipe"],
        });

        // Forward streaming output to stderr only when debugging.
        const debug = getLogLevel() === "debug";
        if (debug) {
          proc.stdout?.on("data", (chunk) => {
            try {
              process.stderr.write(`[ollama:pull] ${chunk.toString()}`);
            } catch {}
          });
          proc.stderr?.on("data", (chunk) => {
            try {
              process.stderr.write(`[ollama:pull] ${chunk.toString()}`);
            } catch {}
          });
        }

        proc.on("close", (code) => {
          if (code === 0) {
            logInfo("Ollama: model installed successfully");
            resolve();
          } else {
            reject(
              new Error(
                `ollama pull exited with code ${code}. Ensure Ollama is running and the model name is valid.`,
              ),
            );
          }
        });

        proc.on("error", (err) => {
          reject(
            new Error(
              `Failed to spawn ollama pull: ${err.message}. Ensure Ollama CLI is installed.`,
            ),
          );
        });
      }),
    catch: (e) =>
      new OllamaError({
        reason: `Auto-install failed: ${
          e instanceof Error ? e.message : String(e)
        }`,
      }),
  });
}

/**
 * Probe the embedding model to detect its dimension
 * Call this BEFORE creating database schema
 */
export function probeEmbeddingDimension(
  host: string,
  model: string,
): Effect.Effect<number, OllamaError> {
  return Effect.gen(function* () {
    const response = yield* Effect.tryPromise({
      try: () =>
        fetch(`${host}/api/embeddings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model,
            prompt: "dimension probe",
          }),
        }),
      catch: (e) => new OllamaError({ reason: `Connection failed: ${e}` }),
    });

    if (!response.ok) {
      const error = yield* Effect.tryPromise({
        try: () => response.text(),
        catch: () =>
          new OllamaError({ reason: "Failed to read error response" }),
      });
      return yield* Effect.fail(new OllamaError({ reason: error }));
    }

    const data = yield* Effect.tryPromise({
      try: () => response.json() as Promise<OllamaEmbeddingResponse>,
      catch: () => new OllamaError({ reason: "Invalid JSON response" }),
    });

    const dimension = data.embedding?.length ?? 0;
    if (dimension === 0) {
      return yield* Effect.fail(
        new OllamaError({ reason: "Probe returned empty embedding" }),
      );
    }

    // Cache the detected dimension
    detectedEmbeddingDimension = dimension;
    logDebug(`Ollama embedding dimension probed: ${dimension}`);
    return dimension;
  });
}

export const OllamaLive = Layer.effect(
  Ollama,
  Effect.gen(function* () {
    const config = loadConfig();

    const embedSingle = (text: string): Effect.Effect<number[], OllamaError> =>
      Effect.gen(function* () {
        const response = yield* Effect.tryPromise({
          try: () =>
            fetch(`${config.ollama.host}/api/embeddings`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                model: config.embedding.model,
                prompt: text,
              }),
            }),
          catch: (e) => new OllamaError({ reason: `Connection failed: ${e}` }),
        });

        if (!response.ok) {
          const error = yield* Effect.tryPromise({
            try: () => response.text(),
            catch: () =>
              new OllamaError({ reason: "Failed to read error response" }),
          });
          return yield* Effect.fail(new OllamaError({ reason: error }));
        }

        const data = yield* Effect.tryPromise({
          try: () => response.json() as Promise<OllamaEmbeddingResponse>,
          catch: () => new OllamaError({ reason: "Invalid JSON response" }),
        });

        // Validate embedding before returning to prevent database corruption
        return yield* validateEmbedding(data.embedding);
      }).pipe(
        // Retry with exponential backoff on transient failures
        Effect.retry(
          Schedule.exponential(Duration.millis(100)).pipe(
            Schedule.compose(Schedule.recurs(3)),
          ),
        ),
      );

    return {
      embed: embedSingle,

      embedBatch: (texts: string[], concurrency = 5) =>
        Stream.fromIterable(texts).pipe(
          Stream.mapEffect(embedSingle, { concurrency }),
          Stream.runCollect,
          Effect.map(Chunk.toArray),
        ),

      checkHealth: () =>
        Effect.gen(function* () {
          const response = yield* Effect.tryPromise({
            try: () => fetch(`${config.ollama.host}/api/tags`),
            catch: () =>
              new OllamaError({
                reason: `Cannot connect to Ollama at ${config.ollama.host}`,
              }),
          });

          if (!response.ok) {
            return yield* Effect.fail(
              new OllamaError({ reason: "Ollama not responding" }),
            );
          }

          const data = yield* Effect.tryPromise({
            try: () => response.json() as Promise<OllamaTagsResponse>,
            catch: () =>
              new OllamaError({ reason: "Invalid response from Ollama" }),
          });

          const modelName = config.embedding.model;
          const hasModel = data.models.some(
            (m) => m.name === modelName || m.name.startsWith(`${modelName}:`),
          );

          if (!hasModel) {
            if (config.ollama.autoInstall) {
              // Auto-install the model
              yield* autoInstallModel(modelName, config.ollama.host);
            } else {
              return yield* Effect.fail(
                new OllamaError({
                  reason: `Model ${modelName} not found. Run: ollama pull ${modelName}`,
                }),
              );
            }
          }
        }),
    };
  }),
);
