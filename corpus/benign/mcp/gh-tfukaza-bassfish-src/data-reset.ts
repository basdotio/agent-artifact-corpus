import { access, rename } from 'node:fs/promises';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';
import { exclusiveLock } from './lock.js';
import { loadRuntimeConfig, saveRuntimeConfig } from './config.js';

/** Archive everything, preserving only validated runtime settings in the fresh directory. */
export async function archiveData(dataDir: string): Promise<string> {
  const releases: Array<() => void> = [];
  try {
    // This sibling lock survives renaming the directory and serializes new startup/reset.
    releases.push(exclusiveLock(`${dataDir}.lifecycle.lock`, 10_000));
    await access(dataDir);
    releases.push(exclusiveLock(join(dataDir, 'run', 'startup.lock')));
    releases.push(exclusiveLock(join(dataDir, 'run', 'daemon-owner.lock')));
    // Refuse a still-running legacy SQL worker even when its daemon has stopped.
    releases.push(exclusiveLock(join(dataDir, 'run', 'sql-owner.lock')));
    const config = await loadRuntimeConfig(dataDir);
    const backup = `${dataDir}.backup-${new Date().toISOString().replaceAll(':', '-')}-${randomUUID().slice(0, 8)}`;
    await rename(dataDir, backup);
    // The archive remains intact even if creating the new config fails.
    await saveRuntimeConfig(dataDir, config);
    return backup;
  } finally {
    for (const release of releases.reverse()) release();
  }
}
