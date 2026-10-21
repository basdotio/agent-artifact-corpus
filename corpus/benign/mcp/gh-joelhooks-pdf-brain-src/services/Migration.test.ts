/**
 * Migration Service Unit Tests
 * TDD: Cleanup utilities for corrupted filesystem artifacts
 */

import { afterEach, beforeEach, describe, expect, test } from "bun:test";
import { Effect } from "effect";
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Migration, MigrationLive } from "./Migration.js";

// ============================================================================
// Test Helpers
// ============================================================================

let tempDir: string;

beforeEach(() => {
  tempDir = mkdtempSync(join(tmpdir(), "migration-test-"));
});

afterEach(() => {
  rmSync(tempDir, { recursive: true, force: true });
});

/**
 * Run a migration operation
 */
function runMigration<A, E>(
  effect: (
    migration: Effect.Effect.Success<typeof Migration>
  ) => Effect.Effect<A, E, never>
) {
  return Effect.runPromise(
    Effect.gen(function* () {
      const migration = yield* Migration;
      return yield* effect(migration);
    }).pipe(Effect.provide(MigrationLive))
  );
}

/**
 * Setup a mock database directory structure
 */
function setupMockDb(dbPath: string, includeCorrupted = false) {
  const pgDataDir = dbPath.replace(".db", "");
  mkdirSync(pgDataDir, { recursive: true });

  // Create valid PostgreSQL directories
  mkdirSync(join(pgDataDir, "base"), { recursive: true });
  mkdirSync(join(pgDataDir, "global"), { recursive: true });
  mkdirSync(join(pgDataDir, "pg_multixact"), { recursive: true });
  mkdirSync(join(pgDataDir, "pg_wal"), { recursive: true });

  // Add PG_VERSION file
  writeFileSync(join(pgDataDir, "PG_VERSION"), "17");

  if (includeCorrupted) {
    // Create corrupted artifacts
    mkdirSync(join(pgDataDir, "base 2"), { recursive: true });
    mkdirSync(join(pgDataDir, "pg_multixact 2"), { recursive: true });
  }
}

// ============================================================================
// detectCorruptedArtifacts Tests
// ============================================================================

describe("detectCorruptedArtifacts", () => {
  test("returns empty array when no database directory exists", async () => {
    const dbPath = join(tempDir, "nonexistent.db");
    const result = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(result).toEqual([]);
  });

  test("returns empty array when database directory is clean", async () => {
    const dbPath = join(tempDir, "clean.db");
    setupMockDb(dbPath, false);

    const result = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(result).toEqual([]);
  });

  test("detects 'base 2' corrupted artifact", async () => {
    const dbPath = join(tempDir, "corrupted.db");
    setupMockDb(dbPath, true);

    const result = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(result).toContain("base 2");
  });

  test("detects 'pg_multixact 2' corrupted artifact", async () => {
    const dbPath = join(tempDir, "corrupted.db");
    setupMockDb(dbPath, true);

    const result = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(result).toContain("pg_multixact 2");
  });

  test("detects multiple corrupted artifacts", async () => {
    const dbPath = join(tempDir, "multi-corrupt.db");
    setupMockDb(dbPath, true);

    const result = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(result).toHaveLength(2);
    expect(result).toContain("base 2");
    expect(result).toContain("pg_multixact 2");
  });

  test("ignores valid directories", async () => {
    const dbPath = join(tempDir, "valid.db");
    setupMockDb(dbPath, false);

    const result = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(result).not.toContain("base");
    expect(result).not.toContain("global");
    expect(result).not.toContain("pg_multixact");
  });

  test("detects space-number pattern variations", async () => {
    const dbPath = join(tempDir, "variations.db");
    const pgDataDir = dbPath.replace(".db", "");
    mkdirSync(pgDataDir, { recursive: true });

    // Create various corrupted patterns
    mkdirSync(join(pgDataDir, "base 2"), { recursive: true });
    mkdirSync(join(pgDataDir, "base 3"), { recursive: true });
    mkdirSync(join(pgDataDir, "pg_wal 2"), { recursive: true });

    const result = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(result).toHaveLength(3);
    expect(result).toContain("base 2");
    expect(result).toContain("base 3");
    expect(result).toContain("pg_wal 2");
  });
});

// ============================================================================
// cleanupCorruptedArtifacts Tests
// ============================================================================

describe("cleanupCorruptedArtifacts", () => {
  test("returns empty array when no corrupted artifacts exist", async () => {
    const dbPath = join(tempDir, "clean.db");
    setupMockDb(dbPath, false);

    const result = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(result).toEqual([]);
  });

  test("removes 'base 2' corrupted artifact", async () => {
    const dbPath = join(tempDir, "corrupted.db");
    setupMockDb(dbPath, true);

    const result = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(result).toContain("base 2");

    // Verify artifact was actually removed
    const pgDataDir = dbPath.replace(".db", "");
    const { existsSync } = await import("fs");
    expect(existsSync(join(pgDataDir, "base 2"))).toBe(false);
  });

  test("removes 'pg_multixact 2' corrupted artifact", async () => {
    const dbPath = join(tempDir, "corrupted.db");
    setupMockDb(dbPath, true);

    const result = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(result).toContain("pg_multixact 2");

    // Verify artifact was actually removed
    const pgDataDir = dbPath.replace(".db", "");
    const { existsSync } = await import("fs");
    expect(existsSync(join(pgDataDir, "pg_multixact 2"))).toBe(false);
  });

  test("removes all corrupted artifacts", async () => {
    const dbPath = join(tempDir, "multi-corrupt.db");
    setupMockDb(dbPath, true);

    const result = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(result).toHaveLength(2);

    // Verify all artifacts were removed
    const pgDataDir = dbPath.replace(".db", "");
    const { existsSync } = await import("fs");
    expect(existsSync(join(pgDataDir, "base 2"))).toBe(false);
    expect(existsSync(join(pgDataDir, "pg_multixact 2"))).toBe(false);
  });

  test("preserves valid directories", async () => {
    const dbPath = join(tempDir, "mixed.db");
    setupMockDb(dbPath, true);

    await runMigration((m) => m.cleanupCorruptedArtifacts(dbPath));

    // Verify valid directories still exist
    const pgDataDir = dbPath.replace(".db", "");
    const { existsSync } = await import("fs");
    expect(existsSync(join(pgDataDir, "base"))).toBe(true);
    expect(existsSync(join(pgDataDir, "global"))).toBe(true);
    expect(existsSync(join(pgDataDir, "pg_multixact"))).toBe(true);
    expect(existsSync(join(pgDataDir, "pg_wal"))).toBe(true);
  });

  test("handles nested files in corrupted directories", async () => {
    const dbPath = join(tempDir, "nested.db");
    const pgDataDir = dbPath.replace(".db", "");
    mkdirSync(pgDataDir, { recursive: true });

    // Create corrupted directory with nested files
    const corruptedDir = join(pgDataDir, "base 2");
    mkdirSync(join(corruptedDir, "subdir"), { recursive: true });
    writeFileSync(join(corruptedDir, "file.txt"), "data");
    writeFileSync(join(corruptedDir, "subdir", "nested.txt"), "more data");

    const result = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(result).toContain("base 2");

    // Verify entire tree was removed
    const { existsSync } = await import("fs");
    expect(existsSync(corruptedDir)).toBe(false);
  });

  test("deep flag is accepted (future extension point)", async () => {
    const dbPath = join(tempDir, "deep.db");
    setupMockDb(dbPath, true);

    // Currently deep=true behaves same as false, but accepted for API compatibility
    const result = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath, true)
    );
    expect(result).toHaveLength(2);
  });
});

// ============================================================================
// Integration Tests
// ============================================================================

describe("cleanup integration", () => {
  test("detect then cleanup workflow", async () => {
    const dbPath = join(tempDir, "workflow.db");
    setupMockDb(dbPath, true);

    // Detect
    const detected = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(detected).toHaveLength(2);

    // Cleanup
    const removed = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(removed).toEqual(detected);

    // Verify clean
    const afterCleanup = await runMigration((m) =>
      m.detectCorruptedArtifacts(dbPath)
    );
    expect(afterCleanup).toEqual([]);
  });

  test("cleanup is idempotent", async () => {
    const dbPath = join(tempDir, "idempotent.db");
    setupMockDb(dbPath, true);

    // First cleanup
    const first = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(first).toHaveLength(2);

    // Second cleanup (should find nothing)
    const second = await runMigration((m) =>
      m.cleanupCorruptedArtifacts(dbPath)
    );
    expect(second).toEqual([]);
  });
});
