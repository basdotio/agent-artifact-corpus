/**
 * @file runtime
 * @description Runtime assembly: wiring config resolution, config file reading,
 *   and adapter construction in one place.
 *
 * Responsibilities:
 * - Locate and read the config file (missing/corrupt only warns, never blocks startup)
 * - Produce the final config, all known adapters, and the "enabled + has a key" fallback chain
 * - Serve as the single assembly point shared by the MCP entry and the CLI,
 *   avoiding duplicated wiring
 */

// Runtime assembly layer. Dependency direction: runtime → {config, config-file, providers}.
// Config file reading is injected as a function, so tests can cover every branch
// without touching the disk.

import {
  defaultWarn, loadConfig, type GatewayConfig, type ProviderConfig,
} from './config.js';
import {
  readConfigFile, resolveConfigPath, type ConfigFileShape, type FileExistsFn, type ReadFileFn,
} from './config-file.js';
import buildProviders from './providers/index.js';
import type { SearchProvider } from './types.js';

export interface GatewayRuntime {
  /** Effective config (defaults, config file and environment variables merged). */
  config: GatewayConfig;
  /** All built adapters, in configuration order. */
  providers: SearchProvider[];
  /** Adapters that can actually search: enabled and configured with an API key. */
  chain: SearchProvider[];
}

export interface RuntimeOptions {
  env?: NodeJS.ProcessEnv;
  warn?: (m: string) => void;
  cwd?: string;
  /** Override config file content reading (for tests). */
  readFile?: ReadFileFn;
  /** Override file-existence checks (for tests). */
  fileExists?: FileExistsFn;
  /** Provide the config file path directly, skipping path resolution. */
  configPath?: string;
}

/**
 * Whether a provider can search: enabled in config AND has a key (both are
 * required). The single place that decides this — the adapters do not answer it
 * themselves, so the chain a caller gets cannot disagree with the status the
 * tool layer reports. Implemented as a lenient table lookup; unknown names count
 * as unusable, with no type assertions involved.
 */
function isUsable(config: GatewayConfig, name: string): boolean {
  const entry = (config.providers as Record<string, ProviderConfig | undefined>)[name];
  return entry !== undefined && entry.enabled && entry.apiKey.trim() !== '';
}

/**
 * Assemble the runtime. Any config problem (corrupt file, unknown provider,
 * invalid value) only produces a warning; the function itself never throws —
 * the gateway must keep serving even with a flawed configuration.
 */
export function createRuntime(options: RuntimeOptions = {}): GatewayRuntime {
  const env = options.env ?? process.env;
  const warn = options.warn ?? defaultWarn;

  const path = options.configPath
    ?? resolveConfigPath(env, options.cwd ?? process.cwd(), options.fileExists);
  const file: ConfigFileShape | undefined = path
    ? readConfigFile(path, warn, options.readFile)
    : undefined;

  const config = loadConfig({
    env, warn, file, configFile: path,
  });
  const providers = buildProviders(config);
  const chain = providers.filter((p) => isUsable(config, p.name));

  return { config, providers, chain };
}
