import { afterEach, describe, expect, test } from "bun:test";
import { Effect } from "effect";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { OpenAIEmbedding, OpenAIEmbeddingLive } from "./OpenAIEmbedding.js";

const ORIGINAL_PDF_BRAIN_CONFIG = process.env.PDF_BRAIN_CONFIG;
const ORIGINAL_OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const ORIGINAL_FETCH = globalThis.fetch;

function makeTempDir(): string {
  return mkdtempSync(join(tmpdir(), "pdf-brain-openai-"));
}

function writeConfig(path: string, overrides?: Record<string, unknown>) {
  const config = {
    embedding: {
      provider: "openai",
      model: "text-embedding-3-small",
      openai: {
        baseUrl: "https://openai.test/v1",
      },
    },
    enrichment: {
      provider: "ollama",
      model: "llama3.2",
    },
    judge: {
      provider: "ollama",
      model: "llama3.2",
    },
    ollama: {
      host: "http://localhost:11434",
      autoInstall: true,
    },
    gateway: {},
    ...(overrides ?? {}),
  };

  writeFileSync(path, JSON.stringify(config), "utf-8");
}

afterEach(() => {
  if (ORIGINAL_PDF_BRAIN_CONFIG === undefined) {
    delete process.env.PDF_BRAIN_CONFIG;
  } else {
    process.env.PDF_BRAIN_CONFIG = ORIGINAL_PDF_BRAIN_CONFIG;
  }

  if (ORIGINAL_OPENAI_API_KEY === undefined) {
    delete process.env.OPENAI_API_KEY;
  } else {
    process.env.OPENAI_API_KEY = ORIGINAL_OPENAI_API_KEY;
  }

  globalThis.fetch = ORIGINAL_FETCH;
});

describe("OpenAIEmbedding", () => {
  test("embed uses OpenAI API and returns embedding", async () => {
    const tempDir = makeTempDir();
    const configPath = join(tempDir, "config.json");
    process.env.PDF_BRAIN_CONFIG = configPath;
    process.env.OPENAI_API_KEY = "test-openai-key";
    writeConfig(configPath);

    let requestUrl = "";
    let requestAuth = "";
    globalThis.fetch = async (input, init) => {
      requestUrl = String(input);
      requestAuth = String(init?.headers ? (init.headers as any).Authorization ?? (init.headers as any).authorization ?? "" : "");

      return new Response(
        JSON.stringify({
          data: [{ index: 0, embedding: [0.1, 0.2, 0.3] }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    };

    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const service = yield* OpenAIEmbedding;
        return yield* service.embed("hello");
      }).pipe(Effect.provide(OpenAIEmbeddingLive)),
    );

    expect(result).toEqual([0.1, 0.2, 0.3]);
    expect(requestUrl).toBe("https://openai.test/v1/embeddings");
    expect(requestAuth).toContain("Bearer test-openai-key");

    rmSync(tempDir, { recursive: true, force: true });
  });

  test("embedBatch sends requests in chunks of 2048 inputs", async () => {
    const tempDir = makeTempDir();
    const configPath = join(tempDir, "config.json");
    process.env.PDF_BRAIN_CONFIG = configPath;
    process.env.OPENAI_API_KEY = "test-openai-key";
    writeConfig(configPath);

    let callCount = 0;
    const batchSizes: number[] = [];

    globalThis.fetch = async (_input, init) => {
      callCount++;
      const body = JSON.parse(String(init?.body));
      const inputs = body.input as string[];
      batchSizes.push(inputs.length);

      return new Response(
        JSON.stringify({
          data: inputs.map((_text, index) => ({
            index,
            embedding: [index + 1, index + 2, index + 3],
          })),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    };

    const texts = Array.from({ length: 2050 }, (_, i) => `text-${i}`);
    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const service = yield* OpenAIEmbedding;
        return yield* service.embedBatch(texts);
      }).pipe(Effect.provide(OpenAIEmbeddingLive)),
    );

    expect(callCount).toBe(2);
    expect(batchSizes).toEqual([2048, 2]);
    expect(result).toHaveLength(2050);

    rmSync(tempDir, { recursive: true, force: true });
  });

  test("uses config apiKey and openai.model override when env is unset", async () => {
    const tempDir = makeTempDir();
    const configPath = join(tempDir, "config.json");
    process.env.PDF_BRAIN_CONFIG = configPath;
    delete process.env.OPENAI_API_KEY;
    writeConfig(configPath, {
      embedding: {
        provider: "openai",
        model: "fallback-model",
        openai: {
          apiKey: "config-openai-key",
          model: "text-embedding-3-large",
          baseUrl: "https://openai.test/v1",
        },
      },
    });

    let requestAuth = "";
    let requestModel = "";
    globalThis.fetch = async (_input, init) => {
      requestAuth = String(
        init?.headers
          ? (init.headers as any).Authorization ??
              (init.headers as any).authorization ??
              ""
          : "",
      );
      const body = JSON.parse(String(init?.body));
      requestModel = String(body.model);

      return new Response(
        JSON.stringify({
          data: [{ index: 0, embedding: [1, 2, 3] }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    };

    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const service = yield* OpenAIEmbedding;
        return yield* service.embed("hello");
      }).pipe(Effect.provide(OpenAIEmbeddingLive)),
    );

    expect(result).toEqual([1, 2, 3]);
    expect(requestAuth).toContain("Bearer config-openai-key");
    expect(requestModel).toBe("text-embedding-3-large");

    rmSync(tempDir, { recursive: true, force: true });
  });

  test("fails when OpenAI response omits embeddings for some inputs", async () => {
    const tempDir = makeTempDir();
    const configPath = join(tempDir, "config.json");
    process.env.PDF_BRAIN_CONFIG = configPath;
    process.env.OPENAI_API_KEY = "test-openai-key";
    writeConfig(configPath);

    globalThis.fetch = async () =>
      new Response(
        JSON.stringify({
          data: [{ index: 0, embedding: [0.1, 0.2, 0.3] }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );

    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const service = yield* OpenAIEmbedding;
        return yield* service.embedBatch(["first", "second"]);
      }).pipe(Effect.provide(OpenAIEmbeddingLive), Effect.either),
    );

    expect(result._tag).toBe("Left");

    rmSync(tempDir, { recursive: true, force: true });
  });

  test("retries on 429 and eventually succeeds", async () => {
    const tempDir = makeTempDir();
    const configPath = join(tempDir, "config.json");
    process.env.PDF_BRAIN_CONFIG = configPath;
    process.env.OPENAI_API_KEY = "test-openai-key";
    writeConfig(configPath);

    let callCount = 0;
    globalThis.fetch = async () => {
      callCount++;
      if (callCount === 1) {
        return new Response(
          JSON.stringify({ error: { message: "rate limited" } }),
          { status: 429, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(
        JSON.stringify({
          data: [{ index: 0, embedding: [0.5, 0.6, 0.7] }],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    };

    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const service = yield* OpenAIEmbedding;
        return yield* service.embed("retry me");
      }).pipe(Effect.provide(OpenAIEmbeddingLive)),
    );

    expect(callCount).toBe(2);
    expect(result).toEqual([0.5, 0.6, 0.7]);

    rmSync(tempDir, { recursive: true, force: true });
  });

  test("fails when no OpenAI API key is configured", async () => {
    const tempDir = makeTempDir();
    const configPath = join(tempDir, "config.json");
    process.env.PDF_BRAIN_CONFIG = configPath;
    delete process.env.OPENAI_API_KEY;
    writeConfig(configPath);

    const result = await Effect.runPromise(
      Effect.gen(function* () {
        const service = yield* OpenAIEmbedding;
        return yield* service.checkHealth();
      }).pipe(Effect.provide(OpenAIEmbeddingLive), Effect.either),
    );

    expect(result._tag).toBe("Left");

    rmSync(tempDir, { recursive: true, force: true });
  });
});
