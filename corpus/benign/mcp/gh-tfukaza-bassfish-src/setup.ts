import { join } from 'node:path';
import { ensureDaemon } from './daemon.js';
import { requireSupportedPlatform, tursoVersion } from './storage/platform.js';
export async function setupTurso(
  dataDir: string,
): Promise<{ engine: string; version: string; state: string; path: string }> {
  requireSupportedPlatform();
  await ensureDaemon(dataDir);
  return {
    engine: 'turso',
    version: tursoVersion,
    state: 'ready',
    path: join(dataDir, 'bassfish.db'),
  };
}
