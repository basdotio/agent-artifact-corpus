import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { DatabasePromise, type NativeDatabase } from '@tursodatabase/database-common';
import { BassfishError } from '../domain.js';
import { requireSupportedPlatform } from './platform.js';

const bindingIdentity = '0.7.2-bassfish.1';
export interface RegistryStats {
  prepareCount: number;
  retainedReferences: number;
  liveReferences: number;
  pruneCount: number;
}
interface PatchedNativeDatabase extends NativeDatabase {
  bassfishStatementRegistryStats(): RegistryStats;
}
interface Binding {
  Database: new (path: string) => PatchedNativeDatabase;
  bassfishBindingIdentity(): string;
}
let binding: Binding | undefined;

// Both source execution and compiled execution use the packaged, verified artifact.
export function loadBinding(directory = new URL('../../dist/native/', import.meta.url)): Binding {
  requireSupportedPlatform();
  const platform = `${process.platform}-${process.arch}${process.platform === 'linux' ? '-gnu' : ''}`;
  try {
    const manifest = JSON.parse(readFileSync(new URL('manifest.json', directory), 'utf8'));
    const metadata = manifest.artifacts[platform];
    const binary = `turso.${platform}.node`;
    if (
      manifest.identity !== bindingIdentity ||
      metadata?.identity !== bindingIdentity ||
      metadata?.binary !== binary ||
      metadata?.revision !== '046e9cbf67d22491e8ecc941ec2891b02a9f3cad'
    )
      throw new Error('Incompatible native build metadata');
    const path = new URL(binary, directory);
    const sha256 = createHash('sha256').update(readFileSync(path)).digest('hex');
    if (sha256 !== metadata.sha256) throw new Error('Native binary hash mismatch');
    const loaded = createRequire(import.meta.url)(fileURLToPath(path)) as Binding;
    if (loaded.bassfishBindingIdentity() !== bindingIdentity)
      throw new Error('Incompatible native binding identity');
    return loaded;
  } catch (error) {
    // Keep the cause: a runtime that cannot load the addon looks identical to a missing one.
    throw new BassfishError(
      'STORAGE_UNAVAILABLE',
      `Bassfish patched Turso artifact for ${platform} is missing or incompatible. Rebuild or reinstall the CLI.`,
      { cause: error instanceof Error ? error.message : String(error) },
    );
  }
}

export function nativeIdentity(): string {
  binding ??= loadBinding();
  return binding.bassfishBindingIdentity();
}

class Database extends DatabasePromise {
  constructor(private readonly native: PatchedNativeDatabase) {
    super(native);
  }
  registryStats(): RegistryStats {
    return this.native.bassfishStatementRegistryStats();
  }
}

export async function connect(path: string): Promise<Database> {
  binding ??= loadBinding();
  const db = new Database(new binding.Database(path));
  try {
    await db.connect();
    return db;
  } catch (error) {
    await db.close().catch(() => {});
    throw error;
  }
}
