/**
 * Runtime-config store for the tunnel runtime manager.
 *
 * Persists `runtime-config.json` under `<dshHome>/chatgpt-bridge/`, kept
 * deliberately separate from the Bridge ConfigSchema (runtime fields change
 * without restarting the Bridge). Writes are atomic (temp file + rename) and
 * the file is schema-versioned so future migrations can run without crashing.
 * This file never holds secrets: only file: references.
 */
import { mkdirSync, readFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { randomUUID } from 'node:crypto';

import type { RuntimeConfig } from './types.js';

export const CONFIG_SCHEMA_VERSION = 1 as const;

/** The error raised when a stored config carries an unsupported schemaVersion. */
export class UnknownSchemaVersionError extends Error {
  readonly version: unknown;
  constructor(version: unknown) {
    super(`runtime-config.json has unsupported schemaVersion: ${JSON.stringify(version)}`);
    this.name = 'UnknownSchemaVersionError';
    this.version = version;
  }
}

export function defaultRuntimeConfig(): RuntimeConfig {
  return {
    schemaVersion: CONFIG_SCHEMA_VERSION,
    tunnel: {
      proxy: { enabled: false },
      autoStart: false,
    },
    openai: {},
    bridge: {},
  };
}

/** Merge a partial config over the defaults (deep for the known sections). */
export function mergeRuntimeConfig(base: RuntimeConfig, patch: Partial<RuntimeConfig>): RuntimeConfig {
  const tunnelPatch: Partial<NonNullable<RuntimeConfig['tunnel']>> = patch.tunnel ?? {};
  const openaiPatch: Partial<NonNullable<RuntimeConfig['openai']>> = patch.openai ?? {};
  const bridgePatch: Partial<NonNullable<RuntimeConfig['bridge']>> = patch.bridge ?? {};

  const mergedTunnel: NonNullable<RuntimeConfig['tunnel']> = {
    ...base.tunnel,
    ...tunnelPatch,
    proxy: { ...(base.tunnel.proxy ?? { enabled: false }), ...(tunnelPatch.proxy ?? {}) },
  };
  if ('executable' in tunnelPatch && (tunnelPatch.executable === '' || tunnelPatch.executable === undefined)) {
    delete (mergedTunnel as { executable?: string }).executable;
  }

  const mergedOpenai: NonNullable<RuntimeConfig['openai']> = {
    ...base.openai,
    ...openaiPatch,
  };
  if ('controlPlaneBaseUrl' in openaiPatch && (openaiPatch.controlPlaneBaseUrl === '' || openaiPatch.controlPlaneBaseUrl === undefined)) {
    delete (mergedOpenai as { controlPlaneBaseUrl?: string }).controlPlaneBaseUrl;
  }

  return {
    schemaVersion: CONFIG_SCHEMA_VERSION,
    tunnel: mergedTunnel,
    openai: mergedOpenai,
    bridge: { ...base.bridge, ...bridgePatch },
  };
}

export class ConfigStore {
  private readonly file: string;
  private readonly dshHome: string;

  constructor(dshHome: string) {
    this.dshHome = dshHome;
    this.file = join(dshHome, 'chatgpt-bridge', 'runtime-config.json');
  }

  get filePath(): string {
    return this.file;
  }

  /** Read the stored config; missing or empty file yields defaults. */
  load(): RuntimeConfig {
    let raw: string;
    try {
      raw = readFileSync(this.file, 'utf8');
    } catch {
      return defaultRuntimeConfig();
    }
    if (raw.trim() === '') return defaultRuntimeConfig();
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      throw new Error('runtime-config.json is not valid JSON');
    }
    return this.validate(parsed);
  }

  /** Validate/normalize a parsed value into a RuntimeConfig (migration-ready). */
  validate(parsed: unknown): RuntimeConfig {
    if (typeof parsed !== 'object' || parsed === null) {
      throw new Error('runtime-config.json must be a JSON object');
    }
    const raw = parsed as Record<string, unknown>;
    const version = raw.schemaVersion;
    if (version !== CONFIG_SCHEMA_VERSION) {
      if (typeof version === 'number' && version < CONFIG_SCHEMA_VERSION) {
        // Future migration hook: migrate(version) would run here.
        return this.migrate(raw, version);
      }
      throw new UnknownSchemaVersionError(version);
    }
    return mergeRuntimeConfig(defaultRuntimeConfig(), parsed as Partial<RuntimeConfig>);
  }

  /** Migration seam. schemaVersion 1 is the only known version today. */
  private migrate(raw: Record<string, unknown>, version: number): RuntimeConfig {
    if (version !== 1) throw new UnknownSchemaVersionError(version);
    return mergeRuntimeConfig(defaultRuntimeConfig(), raw as Partial<RuntimeConfig>);
  }

  /** Atomic write: temp file in the same directory, then rename over the target. */
  save(config: RuntimeConfig): void {
    const dir = dirname(this.file);
    mkdirSync(dir, { recursive: true });
    const tmp = join(dir, `runtime-config.${process.pid}.${randomUUID()}.tmp`);
    try {
      writeFileSync(tmp, JSON.stringify(config, null, 2) + '\n', 'utf8');
      renameSync(tmp, this.file);
    } catch (error) {
      try {
        rmSync(tmp, { force: true });
      } catch {
        // best-effort cleanup
      }
      throw error;
    }
  }

  /** Read-modify-write with a single atomic save at the end. */
  update(mutate: (config: RuntimeConfig) => RuntimeConfig): RuntimeConfig {
    const next = mutate(this.load());
    this.save(next);
    return next;
  }
}
