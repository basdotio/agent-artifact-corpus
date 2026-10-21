import { describe, expect, test } from "bun:test";
import { Effect } from "effect";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { Database } from "./Database.js";
import { DatabaseRegistry } from "./DatabaseRegistry.js";
import { LibraryConfig } from "../types.js";

function withTempEnv(
  env: Record<string, string>,
  run: () => Promise<void> | void
): Promise<void> | void {
  const previousValues = new Map<string, string | undefined>();
  for (const [key, value] of Object.entries(env)) {
    previousValues.set(key, process.env[key]);
    process.env[key] = value;
  }

  const cleanup = () => {
    for (const [key, previous] of previousValues.entries()) {
      if (previous === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = previous;
      }
    }
  };

  try {
    const result = run();
    if (result instanceof Promise) {
      return result.finally(cleanup);
    }
    cleanup();
    return result;
  } catch (error) {
    cleanup();
    throw error;
  }
}

describe("DatabaseRegistry", () => {
  test("returns a working libsql database layer when backend is libsql", async () => {
    const tempDir = mkdtempSync(join(tmpdir(), "pdf-brain-db-registry-"));
    const configPath = join(tempDir, "config.json");
    const libraryPath = join(tempDir, "library");

    try {
      mkdirSync(libraryPath, { recursive: true });
      writeFileSync(
        configPath,
        JSON.stringify({
          embedding: { provider: "ollama", model: "mxbai-embed-large" },
          enrichment: { provider: "ollama", model: "llama3.2" },
          judge: { provider: "ollama", model: "llama3.2" },
          ollama: { host: "http://localhost:11434", autoInstall: true },
          gateway: {},
          database: {
            backend: "libsql",
            qdrant: {
              url: "http://localhost:6333",
              collection: "pdf-brain",
            },
          },
        }),
        "utf-8"
      );

      await withTempEnv(
        {
          PDF_BRAIN_CONFIG: configPath,
          PDF_LIBRARY_PATH: libraryPath,
        },
        async () => {
          const program = Effect.gen(function* () {
            const db = yield* Database;
            return yield* db.getStats();
          });

          const stats = await Effect.runPromise(
            program.pipe(Effect.provide(DatabaseRegistry.make()))
          );

          expect(stats.documents).toBe(0);
          expect(stats.chunks).toBe(0);
          expect(stats.embeddings).toBe(0);
        }
      );
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("returns a qdrant database layer when backend is qdrant", async () => {
    const tempDir = mkdtempSync(join(tmpdir(), "pdf-brain-db-registry-"));
    const configPath = join(tempDir, "config.json");
    const libraryPath = join(tempDir, "library");

    try {
      mkdirSync(libraryPath, { recursive: true });
      writeFileSync(
        configPath,
        JSON.stringify({
          embedding: { provider: "ollama", model: "mxbai-embed-large" },
          enrichment: { provider: "ollama", model: "llama3.2" },
          judge: { provider: "ollama", model: "llama3.2" },
          ollama: { host: "http://localhost:11434", autoInstall: true },
          gateway: {},
          database: {
            backend: "qdrant",
            qdrant: {
              url: "http://localhost:6333",
              collection: "pdf-brain",
            },
          },
        }),
        "utf-8"
      );

      await withTempEnv(
        {
          PDF_BRAIN_CONFIG: configPath,
          PDF_LIBRARY_PATH: libraryPath,
        },
        async () => {
          const program = Effect.gen(function* () {
            const db = yield* Database;
            return {
              hasAddDocument: typeof db.addDocument === "function",
              hasVectorSearch: typeof db.vectorSearch === "function",
            };
          });

          const result = await Effect.runPromise(
            program.pipe(Effect.provide(DatabaseRegistry.make()))
          );

          expect(result.hasAddDocument).toBe(true);
          expect(result.hasVectorSearch).toBe(true);
        }
      );
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("applies Config schema defaults when provided config object omits database section", async () => {
    const tempDir = mkdtempSync(join(tmpdir(), "pdf-brain-db-registry-"));
    const dbPath = join(tempDir, "library.db");

    try {
      const legacyShapeConfig = {
        embedding: { provider: "ollama", model: "mxbai-embed-large" },
        enrichment: { provider: "ollama", model: "llama3.2" },
        judge: { provider: "ollama", model: "llama3.2" },
        ollama: { host: "http://localhost:11434", autoInstall: true },
        gateway: {},
      };

      const program = Effect.gen(function* () {
        const db = yield* Database;
        return yield* db.getStats();
      });

      const stats = await Effect.runPromise(
        program.pipe(
          Effect.provide(
            DatabaseRegistry.make({
              config: legacyShapeConfig as any,
              libraryConfig: new LibraryConfig({
                libraryPath: tempDir,
                dbPath,
                ollamaModel: "mxbai-embed-large",
                ollamaHost: "http://localhost:11434",
                chunkSize: 512,
                chunkOverlap: 50,
              }),
            })
          )
        )
      );

      expect(stats.documents).toBe(0);
      expect(stats.chunks).toBe(0);
      expect(stats.embeddings).toBe(0);
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});
