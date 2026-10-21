/**
 * Unified Embedding Provider - Routes to Ollama, Gateway, or OpenAI based on config
 */
import { Effect, Context, Layer } from "effect";
import { loadConfig, OllamaError, GatewayError, OpenAIError } from "../types.js";
import { Ollama, OllamaLive } from "./Ollama.js";
import { Gateway, GatewayLive } from "./Gateway.js";

// ============================================================================
// Service Definition
// ============================================================================

// Union error type
export type EmbeddingError = OllamaError | GatewayError | OpenAIError;

export class EmbeddingProvider extends Context.Tag("EmbeddingProvider")<
  EmbeddingProvider,
  {
    readonly embed: (text: string) => Effect.Effect<number[], EmbeddingError>;
    readonly embedBatch: (
      texts: string[],
      concurrency?: number,
    ) => Effect.Effect<number[][], EmbeddingError>;
    readonly checkHealth: () => Effect.Effect<void, EmbeddingError>;
    readonly provider: "ollama" | "gateway" | "openai";
  }
>() {}

/**
 * Agent workflows tend to call `search` repeatedly with the same query within a
 * single session (especially via MCP). Cache query embeddings in-process to
 * avoid repeated embed calls.
 *
 * Notes:
 * - This only wraps `embed()` (single text) and intentionally does NOT cache
 *   `embedBatch()` (chunk embeddings would explode memory).
 * - Cache is per-process (MCP session), not persisted.
 */
const DEFAULT_QUERY_EMBED_CACHE_SIZE = 256;

const readQueryEmbedCacheSize = (): number => {
  const raw = process.env.PDF_BRAIN_QUERY_EMBED_CACHE_SIZE;
  if (raw === undefined) return DEFAULT_QUERY_EMBED_CACHE_SIZE;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 0) return DEFAULT_QUERY_EMBED_CACHE_SIZE;
  return Math.floor(n);
};

const makeLruCache = <V>(maxSize: number) => {
  const map = new Map<string, V>();
  return {
    get(key: string): V | undefined {
      const value = map.get(key);
      if (value === undefined) return undefined;
      // Refresh recency.
      map.delete(key);
      map.set(key, value);
      return value;
    },
    set(key: string, value: V): void {
      if (maxSize <= 0) return;
      if (map.has(key)) map.delete(key);
      map.set(key, value);
      if (map.size <= maxSize) return;
      const oldest = map.keys().next().value as string | undefined;
      if (oldest) map.delete(oldest);
    },
  };
};

interface OpenAIEmbeddingsResponse {
  data: Array<{ embedding: number[]; index: number }>;
  error?: {
    message?: string;
  };
}

const DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1";
const DEFAULT_OPENAI_MODEL = "text-embedding-3-small";

const normalizeOpenAIBaseUrl = (baseUrl: string | undefined): string => {
  const value = (baseUrl ?? DEFAULT_OPENAI_BASE_URL).trim();
  return value.endsWith("/") ? value.slice(0, -1) : value;
};

const makeOpenAIProvider = (
  config: ReturnType<typeof loadConfig>,
): Effect.Effect<
  {
    readonly model: string;
    readonly embed: (text: string) => Effect.Effect<number[], OpenAIError>;
    readonly embedBatch: (
      texts: string[],
      concurrency?: number,
    ) => Effect.Effect<number[][], OpenAIError>;
    readonly checkHealth: () => Effect.Effect<void, OpenAIError>;
  },
  OpenAIError
> =>
  Effect.gen(function* () {
    const apiKey = config.openaiApiKey;
    if (!apiKey) {
      return yield* Effect.fail(
        new OpenAIError({
          reason:
            "OpenAI API key not set. Use embedding.openai.apiKey or OPENAI_API_KEY.",
        }),
      );
    }

    const baseUrl = normalizeOpenAIBaseUrl(config.embedding.openai.baseUrl);
    const model = config.embedding.openai.model ?? DEFAULT_OPENAI_MODEL;

    const requestEmbeddings = (
      texts: string[],
    ): Effect.Effect<number[][], OpenAIError> =>
      Effect.tryPromise({
        try: async () => {
          if (texts.length === 0) return [];

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

          if (!response.ok) {
            const responseText = await response.text();
            let reason = responseText || response.statusText;
            try {
              const parsed = JSON.parse(responseText) as OpenAIEmbeddingsResponse;
              reason = parsed.error?.message ?? reason;
            } catch {
              // Keep plain text when response body is not JSON.
            }
            throw new Error(
              `OpenAI embeddings failed (${response.status}): ${reason}`,
            );
          }

          const payload = (await response.json()) as OpenAIEmbeddingsResponse;
          if (!Array.isArray(payload.data)) {
            throw new Error("Invalid OpenAI embeddings response");
          }

          if (payload.data.length !== texts.length) {
            throw new Error(
              `OpenAI embeddings response size mismatch: expected ${texts.length}, received ${payload.data.length}`,
            );
          }

          const ordered: Array<number[] | undefined> = Array(texts.length).fill(
            undefined,
          );
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

          return ordered as number[][];
        },
        catch: (e) =>
          new OpenAIError({
            reason: `Embedding failed: ${
              e instanceof Error ? e.message : String(e)
            }`,
          }),
      });

    return {
      model,
      embed: (text: string) =>
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
          return embedding;
        }),
      embedBatch: (texts: string[]) => requestEmbeddings(texts),
      checkHealth: () => Effect.asVoid(requestEmbeddings(["test"])),
    };
  });

// ============================================================================
// Implementation
// ============================================================================

/**
 * Live implementation that routes based on config.embedding.provider
 */
export const EmbeddingProviderLive = Layer.effect(
  EmbeddingProvider,
  Effect.gen(function* () {
    const config = loadConfig();
    const provider = config.embedding.provider;
    const defaultModel = config.embedding.model;
    const queryCacheSize = readQueryEmbedCacheSize();
    const queryEmbedCache = makeLruCache<number[]>(queryCacheSize);

    const wrapQueryCache = <E>(
      embed: (text: string) => Effect.Effect<number[], E>,
      label: string,
      model: string = defaultModel,
    ) => {
      if (queryCacheSize <= 0) return embed;
      return (text: string) =>
        Effect.gen(function* () {
          const key = `${label}:${model}:${text}`;
          const cached = queryEmbedCache.get(key);
          if (cached) return cached;
          const embedding = yield* embed(text);
          queryEmbedCache.set(key, embedding);
          return embedding;
        });
    };

    if (provider === "gateway") {
      // Use Gateway
      const gateway = yield* Gateway;
      return {
        embed: wrapQueryCache(gateway.embed, "gateway", defaultModel),
        embedBatch: gateway.embedBatch,
        checkHealth: gateway.checkHealth,
        provider: "gateway" as const,
      };
    } else if (provider === "openai") {
      const openai = yield* makeOpenAIProvider(config);
      return {
        embed: wrapQueryCache(openai.embed, "openai", openai.model),
        embedBatch: openai.embedBatch,
        checkHealth: openai.checkHealth,
        provider: "openai" as const,
      };
    } else {
      // Default to Ollama
      const ollama = yield* Ollama;
      return {
        embed: wrapQueryCache(ollama.embed, "ollama", defaultModel),
        embedBatch: ollama.embedBatch,
        checkHealth: ollama.checkHealth,
        provider: "ollama" as const,
      };
    }
  }),
);

/**
 * Full layer with dependencies - use this in app composition.
 * Only constructs the provider layer that's actually configured.
 */
export const EmbeddingProviderFullLive = Layer.unwrapEffect(
  Effect.gen(function* () {
    const config = loadConfig();
    const gatewayStub = Layer.succeed(Gateway, {
      embed: () =>
        Effect.fail(new GatewayError({ reason: "Gateway not configured" })),
      embedBatch: () =>
        Effect.fail(new GatewayError({ reason: "Gateway not configured" })),
      checkHealth: () =>
        Effect.fail(new GatewayError({ reason: "Gateway not configured" })),
    });

    const deps =
      config.embedding.provider === "gateway"
        ? Layer.merge(OllamaLive, GatewayLive)
        : Layer.merge(OllamaLive, gatewayStub);

    return Layer.provide(EmbeddingProviderLive, deps);
  }),
);
