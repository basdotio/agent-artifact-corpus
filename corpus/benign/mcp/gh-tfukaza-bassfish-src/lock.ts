import { mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { createRequire } from 'node:module';
import { BassfishError } from './domain.js';

interface SqliteHandle {
  exec(sql: string): void;
  close(): void;
}
interface SqliteDriver {
  open(path: string): SqliteHandle;
}

let driver: SqliteDriver | null | undefined;

// Bun ships bun:sqlite on every version and node:sqlite only since 1.4; Node ships the
// reverse. Requiring the module this runtime owns keeps the lock synchronous, which the
// synchronous diagnostic flush depends on.
function openWith(load: NodeRequire, specifier: string): SqliteDriver | undefined {
  try {
    if (specifier === 'bun:sqlite') {
      // Unlike node:sqlite, bun:sqlite does not create a missing file unless asked.
      const { Database } = load(specifier) as {
        Database: new (path: string, options: { create: boolean }) => SqliteHandle;
      };
      return { open: path => new Database(path, { create: true }) };
    }
    const { DatabaseSync } = withoutSqliteExperimentalWarning(
      () =>
        load(specifier) as {
          DatabaseSync: new (path: string) => SqliteHandle;
        },
    );
    return { open: path => new DatabaseSync(path) };
  } catch {
    return undefined;
  }
}

/** node:sqlite warns on first require; the daemon and CLI must keep stderr clean. */
function withoutSqliteExperimentalWarning<T>(load: () => T): T {
  const original = process.emitWarning;
  process.emitWarning = function filtered(...args: Parameters<typeof process.emitWarning>) {
    const warning = args[0];
    const type =
      warning instanceof Error
        ? warning.name
        : typeof args[1] === 'string'
          ? args[1]
          : typeof args[1] === 'object' && args[1]
            ? args[1].type
            : undefined;
    const message = warning instanceof Error ? warning.message : String(warning);
    if (type === 'ExperimentalWarning' && message.startsWith('SQLite is an experimental feature'))
      return;
    return Reflect.apply(original, process, args);
  } as typeof process.emitWarning;
  try {
    return load();
  } finally {
    process.emitWarning = original;
  }
}

function loadDriver(): SqliteDriver | null {
  const load = createRequire(import.meta.url);
  const order = (process.versions as { bun?: string }).bun
    ? ['bun:sqlite', 'node:sqlite']
    : ['node:sqlite', 'bun:sqlite'];
  for (const specifier of order) {
    const driver = openWith(load, specifier);
    if (driver) return driver;
  }
  return null;
}
function sqliteDriver(): SqliteDriver | undefined {
  driver ??= loadDriver();
  return driver ?? undefined;
}

/** node:sqlite reports `errcode`; bun:sqlite reports `errno` plus a SQLITE_* name. */
export function sqliteResultCode(error: unknown): number | undefined {
  const details = error as { errcode?: number; errno?: number; code?: string };
  const numeric = details.errcode ?? details.errno;
  if (typeof numeric === 'number') return numeric & 0xff;
  switch (details.code) {
    case 'SQLITE_BUSY':
      return 5;
    case 'SQLITE_LOCKED':
      return 6;
    case 'SQLITE_NOTADB':
      return 26;
    default:
      return undefined;
  }
}

function acquire(sqlite: SqliteDriver, path: string, waitMs: number): () => void {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const db = sqlite.open(path);
  try {
    db.exec(`PRAGMA busy_timeout=${Math.trunc(waitMs)}; BEGIN EXCLUSIVE;`);
  } catch (error) {
    db.close();
    const code = sqliteResultCode(error);
    if (code === undefined || ![5, 6].includes(code)) throw error;
    throw new BassfishError('ALREADY_RUNNING', 'Another process holds the service ownership lock.');
  }
  return () => {
    db.exec('ROLLBACK');
    db.close();
  };
}

/** SQLite's rollback-journal EXCLUSIVE transaction holds a kernel file lock until close/process death. */
export function exclusiveLock(path: string, waitMs = 0): () => void {
  const sqlite = sqliteDriver();
  if (!sqlite)
    throw new BassfishError(
      'STORAGE_UNAVAILABLE',
      'This runtime provides neither node:sqlite nor bun:sqlite, so process ownership cannot be enforced.',
    );
  return acquire(sqlite, path, waitMs);
}

/** Logging is never authoritative: drop the advisory lock rather than retry flushes forever. */
export function bestEffortLock(path: string, waitMs = 0): (() => void) | undefined {
  const sqlite = sqliteDriver();
  return sqlite ? acquire(sqlite, path, waitMs) : undefined;
}
