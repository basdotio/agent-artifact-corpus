import { randomUUID } from 'node:crypto';
import { AsyncLocalStorage } from 'node:async_hooks';
import { mkdir, chmod, access } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import type {
  DatabasePromise as Database,
  Transaction,
  StatementPromise,
} from '@tursodatabase/database-common';
import { connect, nativeIdentity, type RegistryStats } from './native.js';
import { requireSupportedPlatform } from './platform.js';
import { BassfishError, requireThat } from '../domain.js';
import { DiagnosticOperation } from '../diagnostic-events.js';

export type SqlValue = string | number | bigint | Uint8Array | null;

/** All statements in a unit of work use this handle, never its pooled connection. */
export class TursoTransaction {
  private readonly committed: Array<() => void> = [];
  private readonly publicationBatch = randomUUID();
  private publicationPosition = 0;
  outboxOrder(): [string, number] {
    return [this.publicationBatch, this.publicationPosition++];
  }
  constructor(
    private readonly transaction: Transaction,
    readonly writable: boolean,
    private readonly operation?: DiagnosticOperation,
  ) {}
  private statementCount = 0;
  private maxStatementMs = 0;
  metrics(): { statementCount: number; maxStatementMs: number } {
    return { statementCount: this.statementCount, maxStatementMs: this.maxStatementMs };
  }
  private async statement<T>(kind: string, work: () => Promise<T>): Promise<T> {
    const started = performance.now();
    this.operation?.phase('statement', {
      statementOrdinal: ++this.statementCount,
      statementKind: kind,
    });
    try {
      return await work();
    } finally {
      const durationMs = performance.now() - started;
      this.maxStatementMs = Math.max(this.maxStatementMs, durationMs);
      if (durationMs > 1000)
        this.operation?.event('storage.statement_slow', {
          statementOrdinal: this.statementCount,
          statementKind: kind,
          durationMs,
        });
      this.operation?.phase('callback');
    }
  }

  private async prepared<T>(sql: string, work: (stmt: StatementPromise) => Promise<T>): Promise<T> {
    const stmt = await this.transaction.prepare(sql);
    let failed = false;
    try {
      return await work(stmt);
    } catch (error) {
      failed = true;
      throw error;
    } finally {
      try {
        await stmt.close();
      } catch (error) {
        // Cleanup must not hide the original execution error, including rollback conflicts.
        if (!failed) throw error;
      }
    }
  }

  async all<T extends object>(sql: string, ...args: SqlValue[]): Promise<T[]> {
    return this.statement('all', () =>
      this.prepared(sql, stmt => stmt.all(...args) as Promise<T[]>),
    );
  }

  async get<T extends object>(sql: string, ...args: SqlValue[]): Promise<T | undefined> {
    return this.statement('get', () =>
      this.prepared(sql, stmt => stmt.get(...args) as Promise<T | undefined>),
    );
  }

  async run(sql: string, ...args: SqlValue[]): Promise<number> {
    requireThat(this.writable, 'READ_ONLY', 'A read transaction cannot modify storage.');
    return this.statement('run', () =>
      this.prepared(sql, async stmt => (await stmt.run(...args)).changes),
    );
  }

  afterCommit(callback: () => void): void {
    this.committed.push(callback);
  }

  publish(): void {
    for (const callback of this.committed) {
      try {
        callback();
      } catch {
        // A failed wakeup cannot turn a committed write into a failed operation.
      }
    }
  }
}

/** Native 0.7.2 uses GenericFailure for many unrelated errors. Match only known conflicts. */
export function isTransactionConflict(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  return /^(?:step failed: )?(?:Write-write conflict|Transaction conflict|database is locked|database is busy)(?:$| \()/i.test(
    error.message,
  );
}

export async function requireFreshStorage(dataDir: string): Promise<void> {
  for (const name of ['control.sqlite', 'dolt', 'projects', 'dolt-config']) {
    try {
      await access(join(dataDir, name));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') continue;
      throw error;
    }
    throw new BassfishError(
      'RESET_REQUIRED',
      'Legacy Bassfish data found. Stop the old daemon and run bassfish data reset --yes to archive it before initializing Turso.',
    );
  }
}

interface ConnectionSlot {
  db: Database;
  generation: number;
  prepares: number;
  totalPrepares: number;
  state: 'available' | 'leased' | 'retiring' | 'quarantined' | 'closed';
}

/** Internal injection points let acceptance tests exercise each protection independently. */
export interface TursoStoreOptions {
  prepareLimit?: number;
  connect?: (path: string) => Promise<Database>;
  bindingIdentity?: string;
}
const connectionPragmas =
  "PRAGMA journal_mode='mvcc'; PRAGMA foreign_keys=ON; PRAGMA synchronous=FULL;";

/** One daemon owns the file; independent units of work lease independent connections. */
export class TursoStore {
  private readonly context = new AsyncLocalStorage<TursoTransaction>();
  private readonly available: ConnectionSlot[];
  private readonly waiters: Array<{
    resolve: (slot: ConnectionSlot) => void;
    reject: (error: Error) => void;
  }> = [];
  private readonly drained = new Set<() => void>();
  // Includes replacements as soon as they open, until close succeeds.
  private readonly openConnections = new Set<Database>();
  private active = 0;
  private closing = false;
  private closePromise?: Promise<void>;
  private replacements: Promise<void> = Promise.resolve();
  private replacementsPending = 0;
  private replacementSuccesses = 0;
  private replacementFailures = 0;
  private lastReplacement?: {
    slot: number;
    generation: number;
    durationMs: number;
    success: boolean;
  };

  private constructor(
    private readonly path: string,
    private readonly slots: ConnectionSlot[],
    private readonly connector: (path: string) => Promise<Database>,
    private readonly prepareLimit: number,
    private readonly identity: string,
  ) {
    this.available = [...slots];
    for (const slot of slots) this.openConnections.add(slot.db);
  }

  static async open(
    path: string,
    schema = '',
    connectionCount = 8,
    options: TursoStoreOptions = {},
  ): Promise<TursoStore> {
    requireThat(
      Number.isInteger(connectionCount) && connectionCount > 0,
      'INVALID_ARGUMENT',
      'Invalid connection count.',
    );
    const prepareLimit = options.prepareLimit ?? 4096;
    requireThat(
      (Number.isSafeInteger(prepareLimit) && prepareLimit > 0) || prepareLimit === Infinity,
      'INVALID_ARGUMENT',
      'Invalid prepare limit.',
    );
    requireSupportedPlatform();
    const connector = options.connect ?? connect;
    const identity = options.bindingIdentity ?? nativeIdentity();
    await mkdir(dirname(path), { recursive: true, mode: 0o700 });
    const connections: Database[] = [];
    try {
      for (let index = 0; index < connectionCount; index++) {
        const db = await connector(path);
        connections.push(db);
        await db.exec(connectionPragmas);
        if (index === 0 && schema) {
          await db.transactionAsync(async transaction => {
            await transaction.exec(schema);
          })();
        }
      }
      await chmod(path, 0o600);
      return new TursoStore(
        path,
        connections.map(db => ({
          db,
          generation: 0,
          prepares: 0,
          totalPrepares: 0,
          state: 'available',
        })),
        connector,
        prepareLimit,
        identity,
      );
    } catch (error) {
      await Promise.allSettled(connections.map(db => db.close()));
      throw error;
    }
  }

  diagnostics() {
    return {
      bindingIdentity: this.identity,
      prepareLimit: Number.isFinite(this.prepareLimit) ? this.prepareLimit : null,
      closing: this.closing,
      active: this.active,
      queued: this.waiters.length,
      openConnections: this.openConnections.size,
      replacementsPending: this.replacementsPending,
      replacementSuccesses: this.replacementSuccesses,
      replacementFailures: this.replacementFailures,
      lastReplacement: this.lastReplacement,
      connections: this.slots.map((slot, index) => {
        let registry: RegistryStats | undefined;
        if (this.openConnections.has(slot.db)) {
          try {
            registry = (
              slot.db as Database & { registryStats?: () => RegistryStats }
            ).registryStats?.();
          } catch {
            /* closing */
          }
        }
        return {
          slot: index,
          generation: slot.generation,
          prepares: slot.prepares,
          totalPrepares: slot.totalPrepares,
          state: slot.state,
          registry,
        };
      }),
    };
  }

  current(): TursoTransaction | undefined {
    return this.context.getStore();
  }

  read<T>(callback: (transaction: TursoTransaction) => Promise<T>): Promise<T> {
    return this.execute(false, callback);
  }

  write<T>(callback: (transaction: TursoTransaction) => Promise<T>): Promise<T> {
    return this.execute(true, callback);
  }

  private async acquire(): Promise<ConnectionSlot> {
    requireThat(!this.closing, 'STORAGE_UNAVAILABLE', 'Storage is closing.');
    const slot = this.available.shift();
    if (slot) {
      slot.state = 'leased';
      this.active++;
      return slot;
    }
    return new Promise((resolve, reject) => this.waiters.push({ resolve, reject }));
  }

  private makeAvailable(slot: ConnectionSlot): void {
    if (this.closing) return;
    const waiter = this.waiters.shift();
    if (waiter) {
      slot.state = 'leased';
      this.active++;
      waiter.resolve(slot);
    } else {
      slot.state = 'available';
      this.available.push(slot);
    }
  }

  private release(slot: ConnectionSlot): void {
    this.active--;
    if (!this.closing && slot.prepares >= this.prepareLimit) {
      slot.state = 'retiring';
      this.replacementsPending++;
      // Serialized opening/configuration/closing permits at most one extra connection.
      // No await here: a completed transaction's outcome and publication stand alone.
      this.replacements = this.replacements.then(() => this.replace(slot));
    } else {
      this.makeAvailable(slot);
    }
    if (!this.active) {
      for (const resolve of this.drained) resolve();
      this.drained.clear();
    }
  }

  private async replace(slot: ConnectionSlot): Promise<void> {
    const started = performance.now();
    const operation = new DiagnosticOperation('storage.replacement', {
      slot: this.slots.indexOf(slot),
      generation: slot.generation,
    });
    try {
      if (this.closing) {
        operation.finish();
        return;
      }
      operation.phase('open');
      const replacement = await this.connector(this.path);
      this.openConnections.add(replacement);
      operation.phase('configure');
      await replacement.exec(connectionPragmas);
      operation.phase('close_retired');
      await slot.db.close();
      this.openConnections.delete(slot.db);
      slot.db = replacement;
      slot.generation++;
      slot.prepares = 0;
      this.replacementSuccesses++;
      this.lastReplacement = {
        slot: this.slots.indexOf(slot),
        generation: slot.generation,
        durationMs: performance.now() - started,
        success: true,
      };
      operation.event('storage.replacement_succeeded', this.lastReplacement);
      this.makeAvailable(slot);
      operation.finish();
    } catch (error) {
      slot.state = 'quarantined';
      this.replacementFailures++;
      this.lastReplacement = {
        slot: this.slots.indexOf(slot),
        generation: slot.generation,
        durationMs: performance.now() - started,
        success: false,
      };
      operation.event('storage.replacement_failed', this.lastReplacement);
      operation.finish(error);
      // This closes acquisition immediately, but drains already leased transactions.
      // Never await close here: shutdown itself awaits this replacement chain.
      void this.close().catch(() => {});
    } finally {
      this.replacementsPending--;
    }
  }

  private async execute<T>(
    writable: boolean,
    callback: (transaction: TursoTransaction) => Promise<T>,
  ): Promise<T> {
    const parent = this.context.getStore();
    if (parent) {
      requireThat(
        !writable || parent.writable,
        'READ_ONLY',
        'Cannot promote a read transaction to a write transaction.',
      );
      return callback(parent);
    }
    const operation = new DiagnosticOperation('storage', { writable });
    let poolWaitMs = 0,
      conflicts = 0,
      backoffMs = 0,
      attempts = 0;
    let statementCount = 0,
      maxStatementMs = 0;
    try {
      for (let attempt = 0; ; attempt++) {
        attempts++;
        operation.phase('pool_wait', {
          attempt: attempts,
          poolActive: this.active,
          poolSize: this.slots.length,
          poolQueued: this.waiters.length + (this.available.length === 0 ? 1 : 0),
        });
        const waitStarted = performance.now();
        const slot = await this.acquire();
        const db = slot.db;
        poolWaitMs += performance.now() - waitStarted;
        operation.phase('transaction_begin', {
          poolWaitMs,
          bindingIdentity: this.identity,
          connectionSlot: this.slots.indexOf(slot),
          connectionGeneration: slot.generation,
          connectionPrepares: slot.prepares,
        });
        let scope: TursoTransaction | undefined;
        let callbackError: unknown;
        let commitError: unknown;
        try {
          const result = await db
            .transactionAsync(async transaction => {
              // 0.7.2 can automatically abort a conflicting transaction. Its wrapper then
              // masks the conflict with "cannot rollback". Preserve COMMIT's original error.
              const exec = transaction.exec.bind(transaction);
              transaction.exec = async (sql, options) => {
                const phase = sql.trim().toUpperCase();
                if (phase === 'COMMIT' || phase === 'ROLLBACK')
                  operation.phase(phase.toLowerCase());
                try {
                  return await exec(sql, options);
                } catch (error) {
                  if (sql.trim().toUpperCase() === 'COMMIT') commitError = error;
                  throw error;
                }
              };
              const prepare = transaction.prepare.bind(transaction);
              transaction.prepare = async sql => {
                const stmt = await prepare(sql);
                slot.prepares++;
                slot.totalPrepares++;
                return stmt;
              };
              scope = new TursoTransaction(transaction, writable, operation);
              operation.phase('callback');
              try {
                return await this.context.run(scope, () => callback(scope!));
              } catch (error) {
                callbackError = error;
                throw error;
              }
            })
            .concurrent();
          operation.phase('publication');
          scope!.publish();
          operation.finish(undefined, {
            poolWaitMs,
            attempts,
            conflicts,
            backoffMs,
            statementCount: statementCount + scope!.metrics().statementCount,
            maxStatementMs: Math.max(maxStatementMs, scope!.metrics().maxStatementMs),
          });
          return result;
        } catch (error) {
          // The driver returns the original callback error only after successful rollback.
          // A rollback error can mask it; that case must never be retried.
          const original = callbackError ?? commitError ?? error;
          const alreadyAborted =
            error instanceof Error &&
            error.message ===
              'step failed: Transaction error: cannot rollback - no transaction is active';
          const rolledBack = !db.inTransaction && (original === error || alreadyAborted);
          operation.event('storage.attempt_failed', {
            writable,
            attempt: attempts,
            conflict: isTransactionConflict(original),
            rollbackConfirmed: rolledBack && (!commitError || isTransactionConflict(commitError)),
            commitUnresolved: Boolean(commitError) && !isTransactionConflict(commitError),
            commitFailed: Boolean(commitError),
            rollbackUnresolved: db.inTransaction,
          });
          if (db.inTransaction) {
            // Never lease a connection whose rollback outcome is unresolved.
            void this.close().catch(() => {});
            throw new BassfishError(
              'OUTCOME_UNKNOWN',
              'Storage could not confirm rollback. Reconnect and inspect the resource before retrying.',
            );
          }
          if (!rolledBack || !isTransactionConflict(original)) {
            if (commitError)
              throw new BassfishError(
                'OUTCOME_UNKNOWN',
                'Storage could not confirm commit. Reconnect and inspect the resource before retrying.',
              );
            throw original;
          }
          conflicts++;
          if (attempt === 4)
            throw new BassfishError(
              'STORAGE_BUSY',
              'Storage remained busy after five transaction attempts. Try again.',
            );
        } finally {
          if (scope) {
            statementCount += scope.metrics().statementCount;
            maxStatementMs = Math.max(maxStatementMs, scope.metrics().maxStatementMs);
          }
          this.release(slot);
        }
        const backoff = 5 * 2 ** attempt + Math.floor(Math.random() * 5);
        backoffMs += backoff;
        operation.phase('retry_backoff', { conflicts, backoffMs });
        await delay(backoff);
      }
    } catch (error) {
      operation.finish(error, {
        poolWaitMs,
        attempts,
        conflicts,
        backoffMs,
        statementCount,
        maxStatementMs,
      });
      throw error;
    }
  }

  close(): Promise<void> {
    if (this.closePromise) return this.closePromise;
    this.closing = true;
    this.available.length = 0;
    for (const waiter of this.waiters.splice(0))
      waiter.reject(new BassfishError('STORAGE_UNAVAILABLE', 'Storage is closing.'));
    this.closePromise = (async () => {
      if (this.active) await new Promise<void>(resolve => this.drained.add(resolve));
      await this.replacements;
      const results = await Promise.allSettled(
        [...this.openConnections].map(async db => {
          await db.close();
          this.openConnections.delete(db);
        }),
      );
      for (const slot of this.slots) if (!this.openConnections.has(slot.db)) slot.state = 'closed';
      const failures = results.filter(
        (result): result is PromiseRejectedResult => result.status === 'rejected',
      );
      if (failures.length)
        throw new AggregateError(
          failures.map(result => result.reason),
          'Storage connection cleanup failed.',
        );
    })();
    return this.closePromise;
  }
}
