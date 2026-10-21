/**
 * @file config-file
 * @description Locating and reading the JSON config file (I/O and syntax only; no
 *   semantic validation).
 *
 * Responsibilities:
 * - Locate the config file: explicit WEBSEARCH_CONFIG wins, otherwise the conventional
 *   file under cwd
 * - Read and parse JSON; any failure (missing, unreadable, invalid JSON, non-object) only
 *   warns and returns undefined
 * - Refuse a file too large to be configuration, through that same warn-and-continue path
 * - Define the config file's field shape (loose types; semantic validation is the config
 *   module's job)
 */

// Config file I/O layer. Deliberately dumb: it only turns on-disk JSON into
// an object; field semantics and value validity are config.ts's job, so the
// two layers can be tested independently.

import { existsSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { redactSecrets } from './errors.js';
import { stripBom } from './normalize.js';

/** Conventional file name looked up under cwd when no explicit path is set. */
export const CONFIG_FILENAME = 'cn-websearch.config.json';

/**
 * Largest config file read from disk, measured before the read.
 *
 * The path can be a conventional file under an untrusted cwd, and a read is
 * synchronous: a repository that ships an enormous `cn-websearch.config.json`
 * would have the whole thing buffered and parsed on the main thread before
 * anything could warn about it. Nothing this gateway reads from one file
 * approaches a megabyte, so the bound only ever rejects a file that is not
 * configuration. The size is measured on the file as it exists when it is
 * checked, which is what makes it worth having rather than a guarantee.
 */
const MAX_CONFIG_FILE_BYTES = 1024 * 1024;

/**
 * Raw shape of the config file. Every field is unknown: the entry point is
 * loose and each field is validated individually, so one typo doesn't get
 * the whole config rejected.
 */
export interface ConfigFileShape {
  strategy?: unknown;
  order?: unknown;
  count?: unknown;
  timeoutMs?: unknown;
  maxProviders?: unknown;
  dedupe?: unknown;
  providers?: unknown;
}

/** Injection point for reading a text file (defaults to a synchronous, size-bounded UTF-8 read). */
export type ReadFileFn = (path: string) => string;

/**
 * Default reader: measure, then read. Refusing here rather than inside
 * readConfigFile keeps the size bound part of *how a file is read* — a caller
 * that supplies its own ReadFileFn has taken over that step — and lets the
 * refusal travel the existing "unreadable" path, which already warns and
 * returns undefined instead of blocking startup.
 */
const readConfigText: ReadFileFn = (path) => {
  const { size } = statSync(path);
  if (size > MAX_CONFIG_FILE_BYTES) {
    throw new Error(`config file is ${size} bytes, over the ${MAX_CONFIG_FILE_BYTES} byte limit`);
  }
  return readFileSync(path, 'utf8');
};

/** Injection point for file-existence checks (defaults to fs.existsSync). */
export type FileExistsFn = (path: string) => boolean;

/**
 * Locate the config file path:
 * - When WEBSEARCH_CONFIG is set, it wins (returned even if the file doesn't exist; the
 *   read layer warns)
 * - Otherwise `cn-websearch.config.json` under cwd, returned only when the file actually
 *   exists
 * - Neither → undefined (pure environment-variable mode)
 */
export function resolveConfigPath(
  env: NodeJS.ProcessEnv = process.env,
  cwd: string = process.cwd(),
  fileExists: FileExistsFn = existsSync,
): string | undefined {
  const explicit = (env.WEBSEARCH_CONFIG ?? '').trim();
  if (explicit) return explicit;
  const conventional = join(cwd, CONFIG_FILENAME);
  return fileExists(conventional) ? conventional : undefined;
}

/**
 * Read and parse the config file. Nothing throws: missing, unreadable,
 * invalid JSON, or a non-object top level all warn and return undefined,
 * letting the gateway keep running on defaults / environment variables.
 */
export function readConfigFile(
  path: string,
  warn: (m: string) => void,
  readFile: ReadFileFn = readConfigText,
): ConfigFileShape | undefined {
  let raw: string;
  try {
    raw = readFile(path);
  } catch (err) {
    // Same reasoning as the JSON branch below: this file may hold API keys, so
    // nothing from the read failure goes to stderr unscrubbed.
    const detail = err instanceof Error ? err.message : String(err);
    warn(`config file not readable (${path}): ${redactSecrets(detail)}`);
    return undefined;
  }
  raw = stripBom(raw);
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    // Some V8 versions echo a snippet of the source in JSON syntax errors; the
    // file may contain API keys, so redact before the warning goes to stderr.
    const detail = err instanceof Error ? err.message : String(err);
    warn(`config file is not valid JSON (${path}): ${redactSecrets(detail)}`);
    return undefined;
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    warn(`config file must contain a JSON object (${path})`);
    return undefined;
  }
  return parsed;
}
