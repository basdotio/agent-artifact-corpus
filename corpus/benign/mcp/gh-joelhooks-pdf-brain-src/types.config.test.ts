import { afterEach, describe, expect, test } from "bun:test";
import { existsSync, mkdtempSync, rmSync, writeFileSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";
import { loadConfig } from "./types.js";

const ORIGINAL_PDF_BRAIN_CONFIG = process.env.PDF_BRAIN_CONFIG;

const LEGACY_CONFIG_SHAPE = {
  embedding: {
    provider: "ollama",
    model: "mxbai-embed-large",
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
};

function makeTempDir(): string {
  return mkdtempSync(join(tmpdir(), "pdf-brain-config-"));
}

afterEach(() => {
  if (ORIGINAL_PDF_BRAIN_CONFIG === undefined) {
    delete process.env.PDF_BRAIN_CONFIG;
  } else {
    process.env.PDF_BRAIN_CONFIG = ORIGINAL_PDF_BRAIN_CONFIG;
  }
});

describe("loadConfig path and database defaults", () => {
  test("uses PDF_BRAIN_CONFIG path and creates defaults including database backend", () => {
    const tempDir = makeTempDir();

    try {
      const configPath = join(tempDir, "custom-config.json");
      process.env.PDF_BRAIN_CONFIG = configPath;

      const config = loadConfig();

      expect(existsSync(configPath)).toBe(true);
      expect(config.database.backend).toBe("libsql");
      expect(config.database.qdrant.url).toBe("http://localhost:6333");
      expect(config.database.qdrant.collection).toBe("pdf-brain");
      expect(config.server.host).toBe("127.0.0.1");
      expect(config.server.port).toBe(3838);
      expect(config.server.auth.enabled).toBe(false);
      expect(config.server.auth.token).toBeUndefined();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test("applies default database settings when loading legacy config without database section", () => {
    const tempDir = makeTempDir();

    try {
      const configPath = join(tempDir, "legacy-config.json");
      process.env.PDF_BRAIN_CONFIG = configPath;
      writeFileSync(configPath, JSON.stringify(LEGACY_CONFIG_SHAPE), "utf-8");

      const config = loadConfig();
      expect(config.database.backend).toBe("libsql");
      expect(config.database.qdrant.url).toBe("http://localhost:6333");
      expect(config.database.qdrant.collection).toBe("pdf-brain");
      expect(config.server.host).toBe("127.0.0.1");
      expect(config.server.port).toBe(3838);
      expect(config.server.auth.enabled).toBe(false);
      expect(config.server.auth.token).toBeUndefined();
    } finally {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });
});
