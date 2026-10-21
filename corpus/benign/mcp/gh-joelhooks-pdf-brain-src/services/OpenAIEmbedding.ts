/**
 * OpenAI Embedding Service
 */

import { Chunk, Context, Effect, Layer, Stream } from "effect";
import { OpenAIError, loadConfig } from "../types.js";
import { logDebug } from "../logger.js";

// ============================================================================
// Service Definition
// ============================================================================

export class OpenAIEmbedding extends Context.Tag("OpenAIEmbedding")<
  OpenAIEmbedding,
  {
    readonly embed: (text: string) => Effect.Effect<number[], OpenAIError>;
    readonly embedBatch: (
      texts: string[],
      concurrency?: number,
    ) => Effect.Effect<number[][], OpenAIError>;
    readonly checkHealth: () => Effect.Effect<void, OpenAIError>;
  }
>() {}

// ============================================================================
// Implementation
// ============================================================================

const OPENAI_BATCH_LIMIT = 2048;
const MAX_RETRY_ATTEMPTS = 5;
const INITIAL_RETRY_DELAY_MS = 250;
const MAX_RETRY_DELAY_MS = 8000;
const DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1";

interface OpenAIEmbeddingsResponse {
  data: Array<{ embedding: number[]; index: number }>;
  error?: {
    message?: string;
  };
}

let detectedEmbeddingDimension: number | null = null;

/**
 * Get the detected embedding dimension (for use by database schema)
 */
export function getOpenAIEmbeddingDimension(): number | null {
  return detectedEmbeddingDimension;
}

function validateEmbedding(
  embedding: number[],
): Effect.Effect<number[], OpenAIError> {
  if (embedding.length === 0) {
    return Effect.fail(
      new OpenAIError({
        reason: "Invalid embedding: dimension 0 (empty vector)",
      }),
    );
  }

  if (detectedEmbeddingDimension === null) {
    detectedEmbeddingDimension = embedding.length;
    logDebug(
      `OpenAI embedding dimension detected: ${detectedEmbeddingDimension}`,
    );
  } else if (embedding.length !== detectedEmbeddingDimension) {
    return Effect.fail(
      new OpenAIError({
        reason: `Invalid embedding: dimension ${embedding.length} (expected ${detectedEmbeddingDimension})`,
      }),
    );
  }

  if (embedding.some((v) => !Number.isFinite(v))) {
    return Effect.fail(
      new OpenAIError({
        reason:
          "Invalid embedding: contains non-finite values (NaN or Infinity)",
      }),
    );
  }

  return Effect.succeed(embedding);
}

function normalizeBaseUrl(baseUrl: string | undefined): string {
  const value = (baseUrl ?? DEFAULT_OPENAI_BASE_URL).trim();
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function parseRetryAfterMs(header: string | null): number | null {
  if (!header) return null;
  const seconds = Number.parseInt(header, 10);
  if (Number.isFinite(seconds) && seconds >= 0) return seconds * 1000;
  return null;
}

function chunkTexts(texts: string[]): string[][] {
  const chunks: string[][] = [];
  for (let i = 0; i < texts.length; i += OPENAI_BATCH_LIMIT) {
    chunks.push(texts.slice(i, i + OPENAI_BATCH_LIMIT));
  }
  return chunks;
}

export const OpenAIEmbeddingLive = Layer.effect(
  OpenAIEmbedding,
  Effect.gen(function* () {
    const config = loadConfig();
    const apiKey = config.openaiApiKey;

    if (!apiKey) {
      return yield* Effect.fail(
        new OpenAIError({
          reason:
            "OpenAI API key not set. Use embedding.openai.apiKey or OPENAI_API_KEY.",
        }),
      );
    }

    const baseUrl = normalizeBaseUrl(config.embedding.openai.baseUrl);
    const model = config.embedding.openai.model ?? config.embedding.model;

    const requestEmbeddings = (
      texts: string[],
    ): Effect.Effect<number[][], OpenAIError> =>
      Effect.tryPromise({
        try: async () => {
          if (texts.length === 0) return [];
          if (texts.length > OPENAI_BATCH_LIMIT) {
            throw new Error(
              `OpenAI batch size exceeded: ${texts.length} (max ${OPENAI_BATCH_LIMIT})`,
            );
          }

          let delayMs = INITIAL_RETRY_DELAY_MS;
          let attempt = 0;

          while (attempt <= MAX_RETRY_ATTEMPTS) {
            const response = await fetch(`${baseUrl}/embeddings`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${apiKey}`,
              },
              body: JSON.stringify({
                model,
                input: texts,
              }),
            });

            if (response.status === 429 && attempt < MAX_RETRY_ATTEMPTS) {
              const retryAfterMs = parseRetryAfterMs(
                response.headers.get("retry-after"),
              );
              const waitMs = retryAfterMs ?? delayMs;
              await new Promise((resolve) => setTimeout(resolve, waitMs));
              delayMs = Math.min(delayMs * 2, MAX_RETRY_DELAY_MS);
              attempt += 1;
              continue;
            }

            if (!response.ok) {
              const responseText = await response.text();
              let reason = responseText || response.statusText;
              try {
                const parsed = JSON.parse(responseText) as OpenAIEmbeddingsResponse;
                reason = parsed.error?.message ?? reason;
              } catch {
                // Keep plain text as fallback when response is not JSON.
              }
              throw new Error(`OpenAI embeddings failed (${response.status}): ${reason}`);
            }

            const payload =
              (await response.json()) as OpenAIEmbeddingsResponse;

            if (!Array.isArray(payload.data)) {
              throw new Error("Invalid OpenAI embeddings response");
            }

            if (payload.data.length !== texts.length) {
              throw new Error(
                `OpenAI embeddings response size mismatch: expected ${texts.length}, received ${payload.data.length}`,
              );
            }

            const ordered = Array<number[]>(texts.length);
            for (const item of payload.data) {
              if (!Number.isInteger(item.index)) {
                throw new Error("Invalid OpenAI embeddings response index");
              }
              if (item.index < 0 || item.index >= texts.length) {
                throw new Error(
                  `OpenAI embeddings response index out of range: ${item.index}`,
                );
              }
              if (!Array.isArray(item.embedding)) {
                throw new Error("Invalid OpenAI embeddings response embedding");
              }
              if (ordered[item.index] !== undefined) {
                throw new Error(
                  `Duplicate OpenAI embeddings response index: ${item.index}`,
                );
              }
              ordered[item.index] = item.embedding;
            }

            if (ordered.some((embedding) => embedding === undefined)) {
              throw new Error("OpenAI embeddings response missing indices");
            }

            return ordered;
          }

          throw new Error("OpenAI rate limit retries exhausted");
        },
        catch: (e) =>
          new OpenAIError({
            reason: `Embedding failed: ${
              e instanceof Error ? e.message : String(e)
            }`,
          }),
      });

    const embedSingle = (text: string): Effect.Effect<number[], OpenAIError> =>
      Effect.gen(function* () {
        const embeddings = yield* requestEmbeddings([text]);
        const embedding = embeddings[0];
        if (!embedding) {
          return yield* Effect.fail(
            new OpenAIError({
              reason: "Embedding failed: empty embeddings response",
            }),
          );
        }
        return yield* validateEmbedding(embedding);
      });

    const embedManyChunk = (
      texts: string[],
    ): Effect.Effect<number[][], OpenAIError> =>
      Effect.gen(function* () {
        const embeddings = yield* requestEmbeddings(texts);
        const validated = yield* Effect.forEach(embeddings, validateEmbedding);
        return validated;
      });

    return {
      embed: embedSingle,

      embedBatch: (texts: string[], concurrency = 1) =>
        Effect.gen(function* () {
          if (texts.length === 0) return [];
          const chunks = chunkTexts(texts);
          const safeConcurrency = Math.max(1, Math.floor(concurrency));
          return yield* Stream.fromIterable(chunks).pipe(
            Stream.mapEffect(embedManyChunk, { concurrency: safeConcurrency }),
            Stream.runCollect,
            Effect.map(Chunk.toArray),
            Effect.map((groups) => groups.flat()),
          );
        }),

      checkHealth: () =>
        Effect.gen(function* () {
          yield* embedSingle("health check");
        }),
    };
  }),
);
