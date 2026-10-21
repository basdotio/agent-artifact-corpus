/**
 * @file config
 * @description Gateway configuration resolution: built-in defaults → config
 *   file → environment variables, each layer overriding the last.
 *
 * Responsibilities:
 * - Provide neutral per-provider defaults (base URL, model) with nothing personal baked in
 * - Parse fallback order/priority, strategy, timeout, result count and other settings
 *   from the config file and environment variables
 * - Validate each layer's input leniently: invalid values warn and fall back, never throwing
 * - Treat a blank value at any layer as "unset", so template placeholders never mask a lower layer
 * - Own the search-argument bounds (COUNT_MIN/COUNT_MAX/QUERY_MAX) shared by the tool layer and
 *   the CLI, and the rule that turns a requested count into the effective one
 *
 * Design notes:
 * - The default order is alphabetical — not a "recommended order"; custom priority is always
 *   explicit user configuration
 * - A provider's environment variable names are derived from its name (`<NAME>_API_KEY` etc.),
 *   so adding a provider requires no changes to the parsing branches in this file
 * - This module is pure: it never reads the disk (config file content is passed in by the
 *   caller), which keeps it easy to test
 */

// Configuration resolution layer. Precedence: built-in defaults < config file
// < environment variables. MCP clients can usually only pass environment
// variables, so env sits at the top layer.

import type { ConfigFileShape } from './config-file.js';
import { stripControlChars } from './errors.js';
import { clampInt, lenientInt, maybeObject } from './normalize.js';
import { SERVER_NAME } from './server-info.js';
import {
  COUNT_MAX, COUNT_MIN, SEARCH_STRATEGIES, type SearchStrategy,
} from './types.js';

/**
 * All supported providers, in alphabetical order. This order doubles as the
 * default priority order — deliberately neutral, with no vendor preference
 * baked in.
 */
export const KNOWN_PROVIDERS = ['kimi', 'mimo', 'stepfun', 'zhipu'] as const;
export type ProviderName = (typeof KNOWN_PROVIDERS)[number];

export const DEFAULT_ORDER: ProviderName[] = [...KNOWN_PROVIDERS];
export const DEFAULT_TIMEOUT_MS = 30_000;
export const DEFAULT_COUNT = 8;
export const DEFAULT_MAX_PROVIDERS = KNOWN_PROVIDERS.length;
export const DEFAULT_STRATEGY: SearchStrategy = 'fallback';

/**
 * Upper bound for any timeout budget, in ms. Beyond roughly 24.8 days a
 * `setTimeout` delay no longer fits a 32-bit signed integer and silently
 * becomes 1ms, which would turn a typo'd timeout into "every request times
 * out instantly". Ten minutes is far above any sane search budget, so this
 * only ever rejects a mistaken value.
 */
const TIMEOUT_MAX_MS = 600_000;

/**
 * Search-argument bounds shared by every entry surface (MCP tool layer and
 * CLI), so a `count` means the same range wherever it is supplied and the tool
 * schema cannot drift from the CLI's own help text.
 *
 * Defined next to the other cross-surface vocabulary in types.ts, which the
 * dependency-free argument parser can also reach; re-exported here so every
 * consumer of this layer keeps one import site.
 */
export { COUNT_MAX, COUNT_MIN, QUERY_MAX } from './types.js';

/**
 * The result count of one call: an omitted count takes the configured default,
 * anything else is clamped into the shared range above.
 *
 * Three surfaces resolve a count this way (MCP tool layer, one-shot `search`,
 * `test` probe and the REPL's /count), and each of them clamps to the same two
 * constants, so the rule lives here instead of being restated per surface.
 *
 * `requested` is unknown because the MCP tool layer receives raw client JSON:
 * a non-number falls back to the configured default, exactly as a blank or
 * unparseable value does at the config layer.
 */
export function effectiveCount(requested: unknown, fallback: number): number {
  return requested === undefined ? fallback : clampInt(requested, fallback, COUNT_MIN, COUNT_MAX);
}

const MAX_PROVIDERS_MIN = 1;

/** Neutral per-provider defaults (no keys, no personalized parameters). */
interface ProviderDefaults {
  baseUrl: string;
  model?: string;
  /** Whether to use the OpenAI-compatible protocol (requires a /v1 root path). */
  openAiCompatible?: boolean;
}

const PROVIDER_DEFAULTS: Record<ProviderName, ProviderDefaults> = {
  kimi: { baseUrl: 'https://api.moonshot.cn', model: 'kimi-k3', openAiCompatible: true },
  mimo: { baseUrl: 'https://token-plan-cn.xiaomimimo.com', model: 'mimo-v2.5', openAiCompatible: true },
  stepfun: { baseUrl: 'https://api.stepfun.com' },
  zhipu: { baseUrl: 'https://open.bigmodel.cn' },
};

export interface ProviderConfig {
  apiKey: string;
  baseUrl: string;
  model?: string;
  /** Config-level switch: when false, the provider takes part in no search. */
  enabled: boolean;
  /** Priority: higher comes first; when all are 0 (the default), alphabetical by name. */
  priority: number;
  /**
   * Per-provider timeout budget (ms). Only present when it differs from the
   * global budget: a configured 0 means "no per-provider budget" and an
   * out-of-range value is dropped, so both end up as `undefined` here rather
   * than as a value that would be misread as a 0 ms or absurd budget.
   */
  timeoutMs?: number;
  /** Provider-specific optional parameters (validated and consumed by each adapter). */
  options?: Record<string, unknown>;
}

export interface GatewayConfig {
  /** Effective provider order (order/priority configuration applied). */
  order: ProviderName[];
  /** Default search strategy. */
  strategy: SearchStrategy;
  /** Wall-clock budget for a single attempt (ms). */
  timeoutMs: number;
  /** Result count the MCP tool uses when a call omits count. */
  count: number;
  /** Maximum number of providers used per call (fallback chain length cap). */
  maxProviders: number;
  /** Whether aggregated results are deduplicated by URL. */
  dedupe: boolean;
  providers: Record<ProviderName, ProviderConfig>;
  /** Path of the loaded config file (for diagnostics; empty when no file is used). */
  configFile?: string;
}

// Scanning from the end instead of anchoring a regex at `$`: a greedy `/+`
// before `$` backtracks across every split point of a long trailing-slash run
// that fails to match (super-linear in the input), and the loop is O(n) plain.
function trimSlash(s: string): string {
  let end = s.length;
  while (end > 0 && s[end - 1] === '/') end -= 1;
  return s.slice(0, end);
}

/**
 * Kimi/MiMo use the OpenAI-compatible protocol, rooted at /v1. Both the
 * bare-host and the /v1-suffixed forms are accepted, so either convention works.
 */
function ensureV1(baseUrl: string): string {
  const b = trimSlash(baseUrl);
  return b.endsWith('/v1') ? b : `${b}/v1`;
}

/**
 * Per-slot environment variable suffixes this layer reads, e.g. KIMI_API_KEY.
 *
 * This tuple is the single source of both halves of the environment contract:
 * providerEnvKey() only accepts a name from it (so a typo is a compile error),
 * and gatewayEnvKeys() enumerates every slot variable for the .env loader. Adding
 * a slot setting therefore cannot drift out of the .env whitelist.
 */
export const PROVIDER_ENV_SUFFIXES = [
  'API_KEY',
  'BASE_URL',
  'ENABLED',
  'MODEL',
  'PRIORITY',
  'TIMEOUT_MS',
] as const;
export type ProviderEnvSuffix = (typeof PROVIDER_ENV_SUFFIXES)[number];

/**
 * Gateway-wide environment variable names read outside the per-slot scheme,
 * including the legacy ZHIPU_SEARCH_ENGINE knob.
 *
 * Kept next to the code that consumes them so a new WEBSEARCH_* setting has one
 * obvious home; config.test.ts asserts every name here actually changes the
 * resolved config, so a name added to this list but never read is caught.
 */
export const GATEWAY_ENV_KEYS = [
  'WEBSEARCH_CONFIG',
  'WEBSEARCH_COUNT',
  'WEBSEARCH_DEDUPE',
  'WEBSEARCH_MAX_PROVIDERS',
  'WEBSEARCH_ORDER',
  'WEBSEARCH_STRATEGY',
  'WEBSEARCH_TIMEOUT_MS',
  'ZHIPU_SEARCH_ENGINE',
] as const;

/** Derive a provider's environment variable name, e.g. kimi + "API_KEY" -> KIMI_API_KEY. */
export function providerEnvKey(name: ProviderName, suffix: ProviderEnvSuffix): string {
  return `${name.toUpperCase()}_${suffix}`;
}

/**
 * Every environment variable name this gateway reads.
 *
 * The .env loader exports a .env file into process.env, and the working
 * directory is not necessarily trusted, so it must only ever let these names
 * across. It consumes this set rather than keeping its own copy: a setting added
 * to loadConfig without being added here would otherwise be silently dropped
 * from every .env file.
 */
export function gatewayEnvKeys(): ReadonlySet<string> {
  const keys = new Set<string>(GATEWAY_ENV_KEYS);
  for (const name of KNOWN_PROVIDERS) {
    for (const suffix of PROVIDER_ENV_SUFFIXES) keys.add(providerEnvKey(name, suffix));
  }
  return keys;
}

/**
 * Lenient string getter: returns the trimmed value, or undefined for a
 * non-string, an empty string, or a whitespace-only string.
 *
 * Blank counts as "unset" on purpose. Template files ship empty placeholders
 * (`KIMI_API_KEY=`), and the env layer sits above the config file, so treating
 * a blank env value as a real override would silently mask a key configured in
 * the file — the failure mode the `model` field already avoids.
 */
function asString(v: unknown): string | undefined {
  if (typeof v !== 'string') return undefined;
  const trimmed = v.trim();
  return trimmed === '' ? undefined : trimmed;
}

/** Lenient boolean getter: accepts booleans and on/off/yes/no/true/false/1/0 strings. */
function asBool(v: unknown): boolean | undefined {
  if (typeof v === 'boolean') return v;
  if (typeof v === 'string') {
    const s = v.trim().toLowerCase();
    if (s === '1' || s === 'true' || s === 'yes' || s === 'on') return true;
    if (s === '0' || s === 'false' || s === 'no' || s === 'off') return false;
  }
  return undefined;
}

/** Lenient non-negative integer getter (0 is valid, used for priority). */
function asNonNegativeInt(v: unknown): number | undefined {
  const n = lenientInt(v);
  if (!Number.isInteger(n) || n < 0) return undefined;
  return n;
}

/** Lenient getter for obj.key as a trimmed, non-blank string; undefined when missing or blank. */
function strField(obj: Record<string, unknown> | undefined, key: string): string | undefined {
  return obj ? asString(obj[key]) : undefined;
}

/** Lenient getter for obj.key as a boolean. */
function boolField(obj: Record<string, unknown> | undefined, key: string): boolean | undefined {
  return obj ? asBool(obj[key]) : undefined;
}

/** Lenient getter for obj.key as a non-negative integer. */
function intField(obj: Record<string, unknown> | undefined, key: string): number | undefined {
  return obj ? asNonNegativeInt(obj[key]) : undefined;
}

/**
 * Read obj.key as a positive integer; undefined when missing or invalid (for optional overrides).
 *
 * Only a number or a non-blank numeric string counts: lenientInt decides what "a number here"
 * means, so this and every other numeric setting in the file agree on blank and on booleans.
 */
function optionalPositiveInt(
  obj: Record<string, unknown> | undefined,
  key: string,
  warn: (m: string) => void,
  source: string,
): number | undefined {
  const raw = obj?.[key];
  if (raw === undefined || raw === null || raw === '') return undefined;
  const n = lenientInt(raw);
  if (Number.isInteger(n) && n > 0) return n;
  warn(`${source}="${String(raw)}" is not a positive integer, ignoring it`);
  return undefined;
}

/** Read the providers.<name> sub-object from the config file; undefined on type mismatch. */
function providerEntry(
  file: ConfigFileShape | undefined,
  name: ProviderName,
): Record<string, unknown> | undefined {
  const providers = maybeObject(file?.providers);
  return providers ? maybeObject(providers[name]) : undefined;
}

/** Read the top-level providers object from the config file, filtering out non-object values. */
function providerEntries(file: ConfigFileShape | undefined): Record<string, unknown> {
  const entries: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(maybeObject(file?.providers) ?? {})) {
    const entry = maybeObject(value);
    if (entry) entries[key] = entry;
  }
  return entries;
}

/**
 * Parse a provider name list: accepts either an "a,b" string (env-friendly)
 * or an array (config-file-friendly). Unknown names warn and are ignored;
 * duplicates are removed while preserving first-occurrence order.
 */
export function parseProviderList(
  raw: unknown,
  warn: (m: string) => void,
  source: string,
): ProviderName[] {
  const parts: unknown[] = Array.isArray(raw) ? raw : [];
  if (typeof raw === 'string') parts.push(...raw.split(','));
  const seen = new Set<ProviderName>();
  for (const part of parts) {
    const name = (typeof part === 'string' ? part : '').trim().toLowerCase();
    if (name === '') continue;
    if ((KNOWN_PROVIDERS as readonly string[]).includes(name)) seen.add(name as ProviderName);
    else warn(`${source}: unknown provider "${name}" ignored`);
  }
  return [...seen];
}

/** Parse a strategy name; undefined when missing, warn-and-return-undefined when invalid. */
export function parseStrategy(
  raw: unknown,
  warn: (m: string) => void,
  source: string,
): SearchStrategy | undefined {
  if (raw === undefined || raw === null || raw === '') return undefined;
  const s = typeof raw === 'string' ? raw.trim().toLowerCase() : '';
  if ((SEARCH_STRATEGIES as readonly string[]).includes(s)) return s as SearchStrategy;
  warn(`${source}: unknown strategy "${String(raw)}", expected ${SEARCH_STRATEGIES.join('|')}`);
  return undefined;
}

/**
 * Parse a positive integer; return the fallback when missing, unparseable or
 * out of range (with a warning).
 *
 * Only a number or a non-blank numeric string counts (see lenientInt), so a
 * stray boolean in a config file warns and falls back instead of silently
 * becoming a 1 ms budget that makes every search time out instantly.
 */
function positiveInt(
  raw: unknown,
  fallback: number,
  source: string,
  warn: (m: string) => void,
  max = Number.POSITIVE_INFINITY,
): number {
  if (raw === undefined || raw === null || raw === '') return fallback;
  const n = lenientInt(raw);
  if (!Number.isInteger(n) || n <= 0) {
    warn(`${source}="${String(raw)}" is not a positive integer, using ${fallback}`);
    return fallback;
  }
  if (n > max) {
    warn(`${source}="${String(raw)}" exceeds the maximum of ${max}, using ${fallback}`);
    return fallback;
  }
  return n;
}

/**
 * Validate a per-provider timeout budget.
 *
 * - 0 is an explicit "no per-provider budget" (the orchestrator then uses the
 *   global one), so it is normalized to `undefined`: reporting `timeout_ms: 0`
 *   in a status payload would read as "a zero millisecond budget", which is
 *   exactly what it does not mean.
 * - A value beyond TIMEOUT_MAX_MS is dropped for the same reason.
 *
 * `source` names where the value actually came from, so a warning points the
 * user at the variable or file field they really set.
 */
function perProviderTimeout(
  value: number | undefined,
  source: string,
  warn: (m: string) => void,
): number | undefined {
  if (value === undefined || value === 0) return undefined;
  if (value <= TIMEOUT_MAX_MS) return value;
  warn(`${source}=${value} exceeds the maximum of ${TIMEOUT_MAX_MS}, using the global timeout`);
  return undefined;
}

/**
 * Whether a base URL is safe to send an Authorization header to. Non-https
 * endpoints leak the key in cleartext.
 */
function isHttpsUrl(url: string): boolean {
  try {
    return new URL(url).protocol === 'https:';
  } catch {
    return false;
  }
}

/**
 * Merge one setting across the two layers and describe where it came from, so
 * a warning quotes the source the user actually configured instead of always
 * blaming the environment variable.
 *
 * A blank environment value counts as "unset", matching the per-provider
 * getters and strategy/dedupe. Template files ship empty placeholders
 * (`WEBSEARCH_COUNT=`), and the env layer sits above the config file, so
 * honoring a blank here would drop the caller's file value straight back to
 * the built-in default.
 */
function layer(
  envValue: string | undefined,
  fileValue: unknown,
  envSource: string,
  fileSource: string,
): { raw: unknown; source: string } {
  return envValue !== undefined && envValue.trim() !== ''
    ? { raw: envValue, source: envSource }
    : { raw: fileValue, source: fileSource };
}

/**
 * Compute the effective order, highest precedence first:
 * 1. Explicit order (env WEBSEARCH_ORDER > config file order)
 * 2. priority from the config file / per-provider env (descending; ties broken alphabetically)
 * 3. Default alphabetical order (neutral, no vendor preference)
 */
function resolveOrder(
  env: NodeJS.ProcessEnv,
  file: ConfigFileShape | undefined,
  providers: Record<ProviderName, ProviderConfig>,
  warn: (m: string) => void,
): ProviderName[] {
  const envOrder = parseProviderList(env.WEBSEARCH_ORDER, warn, 'WEBSEARCH_ORDER');
  if (envOrder.length) return envOrder;
  const fileOrder = parseProviderList(file?.order, warn, 'config order');
  if (fileOrder.length) return fileOrder;
  if (KNOWN_PROVIDERS.some((name) => providers[name].priority > 0)) {
    return [...KNOWN_PROVIDERS].sort(
      (a, b) => providers[b].priority - providers[a].priority || a.localeCompare(b),
    );
  }
  return [...DEFAULT_ORDER];
}

export interface LoadConfigOptions {
  env?: NodeJS.ProcessEnv;
  warn?: (m: string) => void;
  /** Parsed config file content; read by runtime — this module never touches the disk. */
  file?: ConfigFileShape;
  /** Config file path, for diagnostic output only (never read). */
  configFile?: string;
}

/**
 * The one place a diagnostic is written when the caller supplied no `warn`
 * callback. Exported so every layer that can warn (config file reading, config
 * resolution, .env loading) formats the same line to the same stderr stream;
 * otherwise the same class of problem is reported under three different
 * prefixes, and the entry points have to know which default they landed on.
 *
 * The message is scrubbed of control characters because these diagnostics quote
 * the offending value verbatim — an unknown provider name, a rejected strategy,
 * a config path — and all three can be supplied by a `.env` or a config file
 * shipped in the working directory, which this codebase already treats as
 * untrusted. Left alone, one ESC would let that file repaint or forge lines on
 * the operator's terminal.
 */
export const defaultWarn = (m: string): void => {
  console.error(`[${SERVER_NAME}] ${stripControlChars(m)}`);
};

/**
 * Merge the three config layers into the final GatewayConfig. Invalid values
 * at any layer only warn and fall back, so this function never throws in any
 * environment.
 */
export function loadConfig(options: LoadConfigOptions = {}): GatewayConfig {
  const env = options.env ?? process.env;
  const warn = options.warn ?? defaultWarn;
  const { file } = options;

  // Warn about unknown provider names in the config file (usually typos).
  const entries = providerEntries(file);
  for (const key of Object.keys(entries)) {
    if (!(KNOWN_PROVIDERS as readonly string[]).includes(key)) {
      warn(`config providers: unknown provider "${key}" ignored`);
    }
  }

  const providers = {} as Record<ProviderName, ProviderConfig>;
  for (const name of KNOWN_PROVIDERS) {
    const defaults = PROVIDER_DEFAULTS[name];
    const entry = providerEntry(file, name);

    // A blank value at either layer means "not set", so a template file's empty
    // placeholder can never mask a real value from the layer below it.
    const rawBase = asString(env[providerEnvKey(name, 'BASE_URL')]) ?? strField(entry, 'baseUrl') ?? defaults.baseUrl;
    const baseUrl = defaults.openAiCompatible ? ensureV1(rawBase) : trimSlash(rawBase);
    const apiKey = asString(env[providerEnvKey(name, 'API_KEY')]) ?? strField(entry, 'apiKey') ?? '';
    if (apiKey && !isHttpsUrl(baseUrl)) {
      warn(`${name}: baseUrl is not an https URL, so a configured key would be sent in cleartext — use https, or keep http only for a proxy you trust`);
    }

    // ZHIPU_SEARCH_ENGINE is a legacy knob kept for backward compatibility;
    // the option normally comes from the config file.
    const providerOptions: Record<string, unknown> = { ...maybeObject(entry?.options) };
    if (name === 'zhipu') {
      const envEngine = (env.ZHIPU_SEARCH_ENGINE ?? '').trim();
      if (envEngine) providerOptions.searchEngine = envEngine;
    }

    const fileTimeoutSource = `config providers.${name}.timeoutMs`;
    const envTimeout = asNonNegativeInt(env[providerEnvKey(name, 'TIMEOUT_MS')]);
    const fileTimeout = optionalPositiveInt(entry, 'timeoutMs', warn, fileTimeoutSource);
    const timeoutSource = envTimeout !== undefined ? providerEnvKey(name, 'TIMEOUT_MS') : fileTimeoutSource;

    providers[name] = {
      apiKey,
      baseUrl,
      model: asString(env[providerEnvKey(name, 'MODEL')]) ?? strField(entry, 'model') ?? defaults.model,
      enabled: asBool(env[providerEnvKey(name, 'ENABLED')]) ?? boolField(entry, 'enabled') ?? true,
      priority: asNonNegativeInt(env[providerEnvKey(name, 'PRIORITY')]) ?? intField(entry, 'priority') ?? 0,
      timeoutMs: perProviderTimeout(envTimeout ?? fileTimeout, timeoutSource, warn),
      options: Object.keys(providerOptions).length ? providerOptions : undefined,
    };
  }

  // Read each layer separately so a warning names the variable or the file
  // field the value actually came from, not whichever one happens to win.
  const budget = layer(
    env.WEBSEARCH_TIMEOUT_MS,
    file?.timeoutMs,
    'WEBSEARCH_TIMEOUT_MS',
    'config timeoutMs',
  );
  const timeoutMs = positiveInt(
    budget.raw,
    DEFAULT_TIMEOUT_MS,
    budget.source,
    warn,
    TIMEOUT_MAX_MS,
  );
  const resultCount = layer(env.WEBSEARCH_COUNT, file?.count, 'WEBSEARCH_COUNT', 'config count');
  const count = Math.min(
    COUNT_MAX,
    positiveInt(resultCount.raw, DEFAULT_COUNT, resultCount.source, warn),
  );
  const fanOut = layer(
    env.WEBSEARCH_MAX_PROVIDERS,
    file?.maxProviders,
    'WEBSEARCH_MAX_PROVIDERS',
    'config maxProviders',
  );
  const maxProviders = Math.max(
    MAX_PROVIDERS_MIN,
    positiveInt(fanOut.raw, DEFAULT_MAX_PROVIDERS, fanOut.source, warn),
  );

  return {
    order: resolveOrder(env, file, providers, warn),
    strategy:
      parseStrategy(env.WEBSEARCH_STRATEGY, warn, 'WEBSEARCH_STRATEGY')
      ?? parseStrategy(file?.strategy, warn, 'config strategy')
      ?? DEFAULT_STRATEGY,
    timeoutMs,
    count,
    maxProviders,
    dedupe: asBool(env.WEBSEARCH_DEDUPE) ?? asBool(file?.dedupe) ?? true,
    providers,
    configFile: options.configFile,
  };
}
