import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { readFileSync } from 'node:fs';
import { chmod, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { BassfishError } from './domain.js';
import { z } from 'zod';

export const runtimeConfigSchema = z
  .object({
    offerMs: z.number().int().min(5_000).max(300_000).default(30_000),
    turnTimeoutMs: z.number().int().min(5_000).max(300_000).default(60_000),
    reconnectMs: z.number().int().min(0).max(300_000).default(30_000),
    instanceMs: z.number().int().min(5_000).max(300_000).default(20_000),
    queueMs: z.number().int().min(60_000).max(86_400_000).default(3_600_000),
    retentionMs: z.number().int().min(60_000).max(86_400_000).default(3_600_000),
    waitMs: z.number().int().min(100).max(60_000).default(20_000),
    idleMs: z.number().int().min(60_000).max(86_400_000).default(900_000),
  })
  .strict();
export type RuntimeConfig = z.infer<typeof runtimeConfigSchema>;
export const defaultRuntimeConfig: RuntimeConfig = runtimeConfigSchema.parse({});

export function parseTurnTimeout(value: string): number {
  const match = /^(\d+)(ms|s|m)$/.exec(value);
  if (!match)
    throw new BassfishError(
      'INVALID_ARGUMENT',
      'Turn timeout must be an integer duration such as 30000ms, 60s, or 1m.',
    );
  const multipliers = { ms: 1, s: 1_000, m: 60_000 } as const;
  const milliseconds = Number(match[1]) * multipliers[match[2] as keyof typeof multipliers];
  const parsed = runtimeConfigSchema.shape.turnTimeoutMs.safeParse(milliseconds);
  if (!parsed.success)
    throw new BassfishError('INVALID_ARGUMENT', 'Turn timeout must be between 5s and 5m.');
  return parsed.data;
}

export async function loadRuntimeConfig(dataDir: string): Promise<RuntimeConfig> {
  try {
    return runtimeConfigSchema.parse(
      JSON.parse(await readFile(join(dataDir, 'config.json'), 'utf8')),
    );
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') return defaultRuntimeConfig;
    if (error instanceof z.ZodError || error instanceof SyntaxError)
      throw new BassfishError(
        'INVALID_CONFIG',
        'Bassfish config.json is invalid or contains unknown keys.',
      );
    throw error;
  }
}
export async function saveRuntimeConfig(dataDir: string, config: RuntimeConfig): Promise<void> {
  const valid = runtimeConfigSchema.parse(config);
  await mkdir(dataDir, { recursive: true, mode: 0o700 });
  const temporary = join(dataDir, `.config-${process.pid}.tmp`);
  await writeFile(temporary, JSON.stringify(valid, null, 2) + '\n', { mode: 0o600 });
  await rename(temporary, join(dataDir, 'config.json'));
  await chmod(join(dataDir, 'config.json'), 0o600);
}

export function dataDirectory(): string {
  if (process.env.BASSFISH_DATA_DIR) return resolve(process.env.BASSFISH_DATA_DIR);
  if (process.platform === 'darwin')
    return join(homedir(), 'Library', 'Application Support', 'bassfish');
  return join(process.env.XDG_DATA_HOME ?? join(homedir(), '.local', 'share'), 'bassfish');
}
export const packageRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const packageVersion = String(
  (JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8')) as { version: unknown })
    .version,
);
export function socketPath(dataDir: string): string {
  const path = join(dataDir, 'run', 'daemon.sock');
  if (Buffer.byteLength(path) > 96)
    throw new BassfishError(
      'SOCKET_PATH_TOO_LONG',
      'Choose a shorter BASSFISH_DATA_DIR (Unix socket path limit).',
    );
  return path;
}
