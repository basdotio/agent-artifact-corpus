import { fileSetsOverlap } from '../files.js';
import { reservedStates } from '../domain.js';
import { randomUUID } from 'node:crypto';
import { requireThat } from '../domain.js';
import type { ControlRows as LegacyState } from '../domain.js';
import type { ActivityDraft } from '../observation-types.js';
import type { SqlValue, TursoStore, TursoTransaction } from './turso.js';

export type RowTypes = {
  [
    K in Exclude<
      keyof LegacyState,
      'observationEvents' | 'wallClockHighWaterMs' | 'fileQueueSequence'
    >
  ]: LegacyState[K] extends Record<string, infer V> ? V : never;
};
export type TableName = keyof RowTypes;
const tables: Record<TableName, string> = {
  notificationBatches: 'notificationBatches',
  projects: 'projects',
  identities: 'identities',
  instances: 'instances',
  resources: 'resources',
  requests: 'turnRequests',
  tasks: 'tasks',
  workTasks: 'workTasks',
  follows: 'threadFollows',
  notifications: 'notifications',
  hostSessionBindings: 'hostSessionBindings',
};
const booleanColumns = new Set(['active', 'present']);
const rawObjects = new WeakMap<object, object>();

/** Detach transaction records before they cross a transaction or transport boundary. */
export function copy<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

interface Entry {
  raw: Record<string, unknown>;
  value: Record<string, unknown>;
  before?: Record<string, unknown>;
  dirty: boolean;
  removed: boolean;
}

export class CoordinationState {
  observationEvents: ActivityDraft[] = [];
  wallClockHighWaterMs = 0;
  fileQueueSequence = '0';
  private originalWatermark = 0;
  private originalFileSequence = '0';
  private readonly rows = new Map<TableName, Map<string, Entry>>();

  constructor(
    readonly transaction: TursoTransaction,
    private readonly columns: Record<TableName, string[]>,
  ) {}

  async initialize(): Promise<void> {
    for (const row of await this.transaction.all<{ key: string; value: string }>(
      'SELECT key,value FROM controlMeta',
    )) {
      if (row.key === 'wallClockHighWaterMs') this.wallClockHighWaterMs = Number(row.value);
      if (row.key === 'fileQueueSequence') this.fileQueueSequence = row.value;
    }
    this.originalWatermark = this.wallClockHighWaterMs;
    this.originalFileSequence = this.fileQueueSequence;
  }

  private cache(table: TableName): Map<string, Entry> {
    let cache = this.rows.get(table);
    if (!cache) this.rows.set(table, (cache = new Map()));
    return cache;
  }

  private tracked(value: Record<string, unknown>, changed: () => void): Record<string, unknown> {
    const proxies = new WeakMap<object, object>();
    const wrap = (object: object): object => {
      if (proxies.has(object)) return proxies.get(object)!;
      const proxy = new Proxy(object, {
        get: (target, key, receiver) => {
          const item: unknown = Reflect.get(target, key, receiver);
          return item !== null && typeof item === 'object' ? wrap(item) : item;
        },
        set: (target, key, item) => {
          if (Reflect.get(target, key) !== item) {
            requireThat(
              this.transaction.writable,
              'READ_ONLY',
              'Cannot modify a read transaction.',
            );
            changed();
            Reflect.set(
              target,
              key,
              item && typeof item === 'object' ? (rawObjects.get(item) ?? item) : item,
            );
          }
          return true;
        },
        deleteProperty: (target, key) => {
          if (Reflect.has(target, key)) {
            requireThat(
              this.transaction.writable,
              'READ_ONLY',
              'Cannot modify a read transaction.',
            );
            changed();
            Reflect.deleteProperty(target, key);
          }
          return true;
        },
      });
      proxies.set(object, proxy);
      rawObjects.set(proxy, object);
      return proxy;
    };
    return wrap(value) as Record<string, unknown>;
  }

  private remember(
    table: TableName,
    key: string,
    raw: Record<string, unknown>,
    fresh = false,
  ): Entry {
    const entry: Entry = {
      raw,
      value: raw,
      before: fresh ? undefined : copy(raw),
      dirty: fresh,
      removed: false,
    };
    entry.value = this.tracked(raw, () => {
      entry.dirty = true;
    });
    this.cache(table).set(key, entry);
    return entry;
  }

  private decode(row: Record<string, unknown>): Record<string, unknown> {
    const result: Record<string, unknown> = {};
    for (const [column, value] of Object.entries(row)) {
      if (column === '_key' || value === null) continue;
      const key = column.endsWith('Json') ? column.slice(0, -4) : column;
      result[key] = column.endsWith('Json')
        ? JSON.parse(String(value))
        : booleanColumns.has(column)
          ? Boolean(value)
          : value;
    }
    return result;
  }

  async get<K extends TableName>(table: K, key: string): Promise<RowTypes[K] | undefined> {
    const cached = this.cache(table).get(key);
    if (cached) return cached.removed ? undefined : (cached.value as RowTypes[K]);
    const row = await this.transaction.get<Record<string, unknown>>(
      `SELECT * FROM ${tables[table]} WHERE _key=?`,
      key,
    );
    return row ? (this.remember(table, key, this.decode(row)).value as RowTypes[K]) : undefined;
  }

  async all<K extends TableName>(
    table: K,
    where: Partial<RowTypes[K]> = {},
  ): Promise<RowTypes[K][]> {
    const filters = Object.entries(where);
    for (const [column] of filters)
      requireThat(
        this.columns[table].includes(column),
        'INVALID_ARGUMENT',
        'Unknown storage filter.',
      );
    const sql = `SELECT * FROM ${tables[table]}${filters.length ? ' WHERE ' + filters.map(([key]) => `${key}=?`).join(' AND ') : ''}`;
    const rows = await this.transaction.all<Record<string, unknown>>(
      sql,
      ...filters.map(([, value]) =>
        typeof value === 'boolean' ? Number(value) : (value as SqlValue),
      ),
    );
    const cache = this.cache(table);
    for (const row of rows) {
      const key = String(row._key);
      if (!cache.has(key)) this.remember(table, key, this.decode(row));
    }
    return [...cache.values()]
      .filter(entry => !entry.removed && filters.every(([key, value]) => entry.raw[key] === value))
      .map(entry => entry.value as RowTypes[K]);
  }

  async set<K extends TableName>(table: K, key: string, value: RowTypes[K]): Promise<void> {
    requireThat(this.transaction.writable, 'READ_ONLY', 'Cannot modify a read transaction.');
    await this.get(table, key);
    const before = this.cache(table).get(key)?.before;
    const entry = this.remember(
      table,
      key,
      (rawObjects.get(value as object) ?? value) as Record<string, unknown>,
      true,
    );
    entry.before = before;
  }

  async remove<K extends TableName>(table: K, key: string): Promise<void> {
    requireThat(this.transaction.writable, 'READ_ONLY', 'Cannot modify a read transaction.');
    await this.get(table, key);
    const entry = this.cache(table).get(key);
    if (entry) {
      entry.removed = true;
      entry.dirty = true;
    }
  }

  private event(table: TableName, entry: Entry): void {
    const value = entry.raw,
      before = entry.before;
    if (entry.removed) return;
    if (table === 'requests' && before?.state !== value.state) {
      const record = (phase: string) =>
        this.observationEvents.push({
          id: randomUUID(),
          projectId: String(value.projectId),
          at: Number(value.updatedAt),
          kind: `${value.resourceType === 'files' ? 'files' : 'turn'}.${phase.toLowerCase()}`,
          identityId: String(value.identityId),
          resourceType: value.resourceType as ActivityDraft['resourceType'],
          resourceId: String(value.resourceId ?? value.id),
          details: {
            requestId: value.id,
            ...(value.paths ? { paths: copy(value.paths) } : {}),
            ...(value.terminalReason ? { reason: value.terminalReason } : {}),
          },
        });
      if (!before && value.state !== 'QUEUED') record('QUEUED');
      record(String(value.state));
    }
    if (table === 'projects' && !before)
      this.observationEvents.push({
        id: randomUUID(),
        projectId: String(value.id),
        at: Date.now(),
        kind: 'project.registered',
        resourceType: 'project',
        resourceId: String(value.id),
        details: {},
      });
  }

  private async agentEvents(): Promise<void> {
    const affected = new Set<string>();
    for (const entry of this.cache('instances').values())
      if (entry.dirty) affected.add(String(entry.raw.identityId));
    for (const entry of this.cache('identities').values())
      if (entry.dirty) affected.add(String(entry.raw.id));
    for (const identityId of affected) {
      const identity = await this.get('identities', identityId);
      if (!identity) continue;
      const persisted = await this.transaction.all<{ id: string; active: number }>(
        'SELECT id,active FROM instances WHERE identityId=?',
        identityId,
      );
      const before = persisted.some(instance => Boolean(instance.active));
      const current = new Map(persisted.map(instance => [instance.id, Boolean(instance.active)]));
      for (const [id, entry] of this.cache('instances'))
        if (entry.raw.identityId === identityId)
          current.set(id, !entry.removed && Boolean(entry.raw.active));
      const after = [...current.values()].some(Boolean);
      const identityEntry = this.cache('identities').get(identityId);
      const renamed = identityEntry?.before && identityEntry.before.name !== identity.name;
      if (!renamed && before === after) continue;
      const latest = (await this.all('instances', { identityId })).sort(
        (a, b) => b.lastSeen - a.lastSeen,
      )[0];
      this.observationEvents.push({
        id: randomUUID(),
        projectId: identity.projectId,
        at: Date.now(),
        kind: renamed ? 'agent.renamed' : after ? 'agent.connected' : 'agent.disconnected',
        actor: identity.name,
        identityId,
        resourceType: 'agent',
        resourceId: identityId,
        details: { workspace: latest?.workspace ?? '', host: latest?.host ?? null },
      });
    }
  }

  async flush(): Promise<void> {
    if (!this.transaction.writable) return;
    await this.agentEvents();
    const changedFiles = [...this.cache('requests').values()].some(
      entry => entry.dirty && entry.raw.resourceType === 'files',
    );
    if (changedFiles) {
      await this.transaction.run(
        "UPDATE coordinationGuards SET revision=revision+1 WHERE id='files'",
      );
      const held = (await this.all('requests')).filter(
        r => r.resourceType === 'files' && reservedStates.includes(r.state),
      );
      for (let i = 0; i < held.length; i++)
        for (let j = i + 1; j < held.length; j++) {
          const left = held[i]!,
            right = held[j]!;
          requireThat(
            left.resourceType === 'files' &&
              right.resourceType === 'files' &&
              !fileSetsOverlap(left.paths, right.paths),
            'FILE_LOCK_CONFLICT',
            'Overlapping file sets cannot have simultaneous ownership.',
          );
        }
    }
    // Delete children first; create parents before children. Terminal turns release unique reservations first.
    for (const table of Object.keys(tables).reverse() as TableName[])
      for (const [key, entry] of this.cache(table))
        if (entry.dirty && entry.removed) {
          await this.transaction.run(`DELETE FROM ${tables[table]} WHERE _key=?`, key);
          entry.dirty = false;
        }
    for (const table of Object.keys(tables) as TableName[]) {
      const entries = [...this.cache(table)].filter(([, entry]) => entry.dirty && !entry.removed);
      if (table === 'requests')
        entries.sort(
          ([, a], [, b]) =>
            Number(['READY', 'OFFERED', 'CLAIMED'].includes(String(a.raw.state))) -
            Number(['READY', 'OFFERED', 'CLAIMED'].includes(String(b.raw.state))),
        );
      for (const [key, entry] of entries) {
        if (
          table === 'requests' &&
          entry.raw.state === 'CLAIMED' &&
          entry.raw.claimedAt === undefined
        )
          entry.raw.claimedAt = entry.raw.updatedAt;
        const columns = this.columns[table];
        const values = columns.map(column => {
          if (column === '_key') return key;
          const value = entry.raw[column.endsWith('Json') ? column.slice(0, -4) : column];
          return value === undefined || value === null
            ? null
            : column.endsWith('Json')
              ? JSON.stringify(value)
              : typeof value === 'boolean'
                ? Number(value)
                : (value as SqlValue);
        });
        await this.transaction.run(
          `INSERT INTO ${tables[table]}(${columns.join(',')}) VALUES(${columns.map(() => '?').join(',')}) ON CONFLICT(_key) DO UPDATE SET ${columns
            .filter(c => c !== '_key')
            .map(c => `${c}=excluded.${c}`)
            .join(',')}`,
          ...values,
        );
        this.event(table, entry);
        entry.before = copy(entry.raw);
        entry.dirty = false;
      }
    }
    if (this.originalWatermark !== this.wallClockHighWaterMs) {
      await this.transaction.run(
        "UPDATE controlMeta SET value=? WHERE key='wallClockHighWaterMs'",
        String(this.wallClockHighWaterMs),
      );
      this.originalWatermark = this.wallClockHighWaterMs;
    }
    if (this.originalFileSequence !== this.fileQueueSequence) {
      await this.transaction.run(
        "UPDATE controlMeta SET value=? WHERE key='fileQueueSequence'",
        this.fileQueueSequence,
      );
      this.originalFileSequence = this.fileQueueSequence;
    }
    for (const event of this.observationEvents.splice(0)) {
      if (event.identityId && !event.actor)
        event.actor = (await this.get('identities', event.identityId))?.name;
      await this.transaction.run(
        'INSERT INTO activityOutbox(id,batchId,position,projectId,at,eventJson) VALUES(?,?,?,?,?,?)',
        event.id,
        ...this.transaction.outboxOrder(),
        event.projectId,
        event.at,
        JSON.stringify(event),
      );
    }
  }
}

export async function coordinationColumns(store: TursoStore): Promise<Record<TableName, string[]>> {
  const result = {} as Record<TableName, string[]>;
  await store.read(async tx => {
    for (const [key, table] of Object.entries(tables))
      result[key as TableName] = (
        await tx.all<{ name: string }>(`PRAGMA table_info(${table})`)
      ).map(column => column.name);
  });
  return result;
}
