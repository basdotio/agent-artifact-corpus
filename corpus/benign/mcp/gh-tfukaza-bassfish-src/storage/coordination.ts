import { TursoStore } from './turso.js';
import { CoordinationState, coordinationColumns, copy } from './rows.js';
import type { TableName } from './rows.js';
import type { TursoTransaction } from './turso.js';
import { coordinationSchema, contentSchema, schemaVersion } from './schema.js';
import { TursoActivity } from './turso-activity.js';
import { BassfishError } from '../domain.js';

export class TursoControl {
  private readonly scopes = new WeakMap<TursoTransaction, Promise<CoordinationState>>();
  readonly activity: TursoActivity;
  private constructor(
    readonly store: TursoStore,
    private readonly columns: Record<TableName, string[]>,
  ) {
    this.activity = new TursoActivity(store);
  }

  static async open(path: string): Promise<TursoControl> {
    const store = await TursoStore.open(path);
    try {
      const version = await store.read(tx =>
        tx.get<{ user_version: number }>('PRAGMA user_version'),
      );
      if (version?.user_version && ![1, schemaVersion].includes(version.user_version))
        throw new BassfishError(
          'SCHEMA_MISMATCH',
          'This Turso schema requires a compatible Bassfish version.',
        );
      await store.close();
      // TursoStore.open executes initialization in one write transaction.
      const initialized = await TursoStore.open(path, coordinationSchema + contentSchema);
      try {
        return new TursoControl(initialized, await coordinationColumns(initialized));
      } catch (error) {
        await initialized.close();
        throw error;
      }
    } catch (error) {
      await store.close();
      throw error;
    }
  }

  private async state(tx: TursoTransaction): Promise<CoordinationState> {
    let state = this.scopes.get(tx);
    if (!state) {
      const created = new CoordinationState(tx, this.columns);
      state = created.initialize().then(() => created);
      this.scopes.set(tx, state);
    }
    return state;
  }

  async view<T>(callback: (state: CoordinationState) => T | Promise<T>): Promise<T> {
    return this.store.read(async tx => callback(await this.state(tx)));
  }

  async update<T>(callback: (state: CoordinationState) => T | Promise<T>): Promise<T> {
    const nested = Boolean(this.store.current());
    const result = await this.store.write(async tx => {
      const state = await this.state(tx);
      const result = await callback(state);
      await state.flush();
      return result;
    });
    if (!nested) await this.publishActivity();
    return result;
  }

  async transaction<T>(callback: () => Promise<T>): Promise<T> {
    const result = await this.store.write(async tx => {
      const result = await callback();
      await (await this.state(tx)).flush();
      return result === undefined ? result : copy(result);
    });
    await this.publishActivity();
    return result;
  }

  private async publishActivity(): Promise<void> {
    // Content is already committed. Retain the durable outbox if publication fails;
    // the next observer poll or daemon startup will retry without replaying mutations.
    try {
      await this.activity.publish();
    } catch (error) {
      process.stderr.write(
        `Bassfish activity publication deferred: ${error instanceof Error ? error.message : String(error)}\n`,
      );
    }
  }

  readTransaction<T>(callback: () => Promise<T>): Promise<T> {
    return this.store.read(() => callback());
  }

  inTransaction(): boolean {
    return Boolean(this.store.current());
  }

  afterCommit(callback: () => void): void {
    const tx = this.store.current();
    if (tx) tx.afterCommit(callback);
    else callback();
  }

  subscribe(listener: () => void): () => void {
    return this.activity.subscribe(listener);
  }
  close(): Promise<void> {
    return this.store.close();
  }
}
