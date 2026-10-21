/**
 * @file dotenv
 * @description Minimal .env loader with zero runtime dependencies.
 *
 * Responsibilities:
 * - Read KEY=VALUE pairs from the .env file in a given directory (cwd by default)
 * - Strip matching surrounding quotes from values; skip comment lines and malformed lines
 * - Only export the names the gateway actually reads, so a .env cannot reach the
 *   variables the Node runtime itself acts on
 * - Refuse a file large enough to be an attack rather than configuration
 * - Never overwrite existing process.env entries; silently skip when the file is missing
 */

// Minimal .env loader (no runtime dependencies). Existing process.env entries win.
// The list of names it may export is owned by config.ts (gatewayEnvKeys), which
// is also the module that decides what "a gateway setting" means.

import { readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { defaultWarn, gatewayEnvKeys, PROVIDER_ENV_SUFFIXES } from './config.js';
import { stripBom } from './normalize.js';

/**
 * Largest `.env` this loader will read, checked before the read.
 *
 * The same threat model that motivates the name whitelist below applies to the
 * file's size: the working directory is not necessarily trusted, so any
 * repository can ship a `.env` — and an oversized one would be read whole into
 * memory and then split into lines before the whitelist ever got a say. A real
 * `.env` is a few dozen lines; this bound is two orders of magnitude above that
 * and only ever rejects a file that is not configuration.
 *
 * Size is measured first so the read never happens; the check is on the file as
 * it exists when it is measured, which is what makes the bound worth having
 * rather than a guarantee.
 */
const MAX_DOTENV_BYTES = 64 * 1024;

/**
 * The exact set of names this gateway reads, owned by config.ts.
 *
 * A .env file is data from the working directory, and the working directory is
 * not necessarily trusted: any repository can ship one. Writing every name it
 * contains into process.env would let such a file set NODE_OPTIONS or
 * LD_PRELOAD, which the runtime acts on before this program's first request —
 * turning "start the MCP server in this folder" into running someone else's
 * code. Only configuration the gateway resolves may cross that boundary, so the
 * whitelist is not restated here: adding a setting in config.ts is enough, and a
 * name listed twice could only drift.
 */
const GATEWAY_KEYS = gatewayEnvKeys();

/**
 * Names that look like a gateway setting without being one. Only these earn a
 * warning when they are skipped: a user who wrote SOMEVENDOR_API_KEY needs to
 * know it was ignored, one who put an unrelated name in their .env does not.
 *
 * Built from config.ts's own vocabulary instead of restating it. The suffix
 * alternation is PROVIDER_ENV_SUFFIXES, so adding a per-slot setting keeps this
 * recognizer honest automatically; a literal copy here would quietly stop
 * matching the new suffix and the typo it exists to report would go silent.
 * SEARCH_ENGINE is spelled out because it is a legacy per-provider knob
 * (ZHIPU_SEARCH_ENGINE) rather than one of the uniform slot suffixes.
 */
const GATEWAY_LIKE = new RegExp(`(?:^WEBSEARCH_|_(?:${PROVIDER_ENV_SUFFIXES.join('|')}|SEARCH_ENGINE)$)`);

/**
 * Load KEY=VALUE pairs from the .env file in the given directory (cwd by
 * default). A missing file is normal. Values get no extra trimming, only
 * matching surrounding quotes are removed; existing environment variables
 * are never overwritten, so explicit MCP client configuration keeps
 * precedence. Uses Object.hasOwn instead of `in` for the existence check, so
 * prototype-chain property names (e.g. "toString") are not mistaken for
 * existing entries.
 *
 * Names the gateway does not read are skipped: see GATEWAY_KEYS for why an
 * arbitrary .env must not become process.env. A skipped name that looks like a
 * gateway setting is reported through `warn`, so a typo is visible instead of
 * silently doing nothing. A file over MAX_DOTENV_BYTES is ignored with a
 * warning for the same reason: dropping it silently would look like a gateway
 * that had no keys configured.
 */
export default function loadDotEnv(
  dir: string = process.cwd(),
  into: NodeJS.ProcessEnv = process.env,
  warn: (message: string) => void = defaultWarn,
): void {
  const path = join(dir, '.env');
  let size: number;
  try {
    size = statSync(path).size;
  } catch {
    return; // a missing or unreadable .env is the normal case, not a problem
  }
  // Skipping an oversized .env silently would leave the gateway running on no
  // keys at all with no explanation, so it is reported like any other problem
  // this loader can have with the file.
  if (size > MAX_DOTENV_BYTES) {
    warn(`.env is too large (${size} bytes exceeds the ${MAX_DOTENV_BYTES} byte limit); ignoring it`);
    return;
  }
  let raw: string;
  try {
    raw = readFileSync(path, 'utf8');
  } catch {
    return;
  }
  raw = stripBom(raw);
  for (const line of raw.split(/\r?\n/)) {
    const t = line.trim();
    if (t === '' || t.startsWith('#')) continue;
    const eq = t.indexOf('=');
    if (eq <= 0) continue;
    const key = t.slice(0, eq).trim();
    let value = t.slice(eq + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (!GATEWAY_KEYS.has(key)) {
      if (GATEWAY_LIKE.test(key)) warn(`ignoring unknown setting "${key}" in .env`);
      continue;
    }
    // Writing into the caller-supplied record is this function's contract:
    // `into` is the export target (normally process.env), not an owned object.
    // eslint-disable-next-line no-param-reassign -- documented output parameter
    if (!Object.hasOwn(into, key)) into[key] = value;
  }
}
