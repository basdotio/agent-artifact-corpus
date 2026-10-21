import type {
  ActivityEvent,
  ActivityPage,
  ActivityQuery,
  ActivityDraft,
} from '../observation-types.js';
import { KeyedMutex } from '../runtime.js';
import type { TursoStore } from './turso.js';

const activityRetentionMs = 7 * 86_400_000;
const activityLimit = 100_000;

/** UUID outbox writes do not contend on the observer's ordered publication cursor. */
export class TursoActivity {
  private readonly publisher = new KeyedMutex();
  private readonly observers = new Set<() => void>();
  private lastPrune = 0;
  constructor(private readonly store: TursoStore) {}

  subscribe(listener: () => void): () => void {
    this.observers.add(listener);
    return () => {
      this.observers.delete(listener);
    };
  }

  async publish(): Promise<void> {
    if (this.store.current()) return;
    await this.publisher.run('publish', async () => {
      const changed = await this.store.write(async tx => {
        const pending = await tx.all<{ id: string; eventJson: string }>(
          'SELECT id,eventJson FROM activityOutbox ORDER BY batchId,position',
        );
        for (const row of pending) {
          const event = JSON.parse(row.eventJson) as ActivityDraft;
          await tx.run(
            'INSERT OR IGNORE INTO activityProjects(projectId,since) VALUES(?,?)',
            event.projectId,
            event.at,
          );
          await tx.run(
            'INSERT OR IGNORE INTO activityEvents(id,projectId,at,kind,actor,resourceId,eventJson) VALUES(?,?,?,?,?,?,?)',
            event.id,
            event.projectId,
            event.at,
            event.kind,
            event.actor ?? null,
            event.resourceId,
            row.eventJson,
          );
          await tx.run('DELETE FROM activityOutbox WHERE id=?', row.id);
        }
        if (pending.length) {
          const latest = await tx.get<{ seq: number }>(
            'SELECT MAX(seq) AS seq FROM activityEvents',
          );
          await tx.run(
            "UPDATE controlMeta SET value=? WHERE key='activityHead'",
            String(latest!.seq),
          );
        }
        if (pending.length || Date.now() - this.lastPrune > 60_000) {
          for (const { projectId } of await tx.all<{ projectId: string }>(
            'SELECT projectId FROM activityProjects',
          )) {
            const boundary = await tx.get<{ seq: number }>(
              'SELECT seq FROM activityEvents WHERE projectId=? ORDER BY seq DESC LIMIT 1 OFFSET ?',
              projectId,
              activityLimit - 1,
            );
            const doomed = await tx.get<{ seq: number | null }>(
              'SELECT MAX(seq) AS seq FROM activityEvents WHERE projectId=? AND (at<? OR seq<?)',
              projectId,
              Date.now() - activityRetentionMs,
              boundary?.seq ?? 0,
            );
            if (doomed?.seq) {
              await tx.run(
                'DELETE FROM activityEvents WHERE projectId=? AND (at<? OR seq<?)',
                projectId,
                Date.now() - activityRetentionMs,
                boundary?.seq ?? 0,
              );
              await tx.run(
                'UPDATE activityProjects SET prunedThrough=MAX(prunedThrough,?) WHERE projectId=?',
                doomed.seq,
                projectId,
              );
            }
          }
          this.lastPrune = Date.now();
        }
        return pending.length > 0;
      });
      if (changed)
        for (const wake of this.observers) {
          try {
            wake();
          } catch {
            /* committed */
          }
        }
    });
  }

  async head(): Promise<string> {
    await this.publish();
    return this.store.read(async tx =>
      String(
        (await tx.get<{ value: string }>("SELECT value FROM controlMeta WHERE key='activityHead'"))
          ?.value ?? '0',
      ),
    );
  }

  private summary(event: ActivityEvent, pathOffset = 0): ActivityEvent {
    const paths = event.details.paths;
    if (!Array.isArray(paths)) return event;
    return {
      ...event,
      details: {
        ...event.details,
        paths: paths.slice(pathOffset, pathOffset + 8),
        pathCount: paths.length,
        nextPathOffset: pathOffset + 8 < paths.length ? pathOffset + 8 : null,
      },
    };
  }

  async event(projectId: string, id: string, pathOffset = 0): Promise<ActivityEvent | undefined> {
    await this.publish();
    return this.store.read(async tx => {
      const row = await tx.get<{ seq: number; eventJson: string }>(
        'SELECT seq,eventJson FROM activityEvents WHERE projectId=? AND id=? AND at>=?',
        projectId,
        id,
        Date.now() - activityRetentionMs,
      );
      return row
        ? this.summary({ ...JSON.parse(row.eventJson), cursor: String(row.seq) }, pathOffset)
        : undefined;
    });
  }

  async gap(projectId: string, cursor: string): Promise<boolean> {
    return this.store.read(
      async tx =>
        BigInt(cursor) <
        BigInt(
          (
            await tx.get<{ prunedThrough: number }>(
              'SELECT prunedThrough FROM activityProjects WHERE projectId=?',
              projectId,
            )
          )?.prunedThrough ?? 0,
        ),
    );
  }

  async page(query: ActivityQuery): Promise<ActivityPage> {
    await this.publish();
    return this.store.read(async tx => {
      const where = ['projectId=?', 'at>=?'];
      const args: (string | number)[] = [query.projectId, Date.now() - activityRetentionMs];
      for (const [value, clause] of [
        [query.before, 'seq<?'],
        [query.actor, 'actor=? COLLATE NOCASE'],
        [query.resourceId, 'resourceId=?'],
        [query.kind ? `${query.kind}%` : undefined, 'kind LIKE ?'],
      ]) {
        if (value) {
          where.push(clause!);
          args.push(value);
        }
      }
      const limit = Math.min(100, query.limit ?? 50);
      const rows = await tx.all<{ seq: number; eventJson: string }>(
        `SELECT seq,eventJson FROM activityEvents WHERE ${where.join(' AND ')} ORDER BY seq DESC LIMIT ?`,
        ...args,
        limit + 1,
      );
      const events: ActivityEvent[] = [];
      let bytes = 0;
      for (const row of rows.slice(0, limit)) {
        const event = this.summary({ ...JSON.parse(row.eventJson), cursor: String(row.seq) });
        const size = Buffer.byteLength(JSON.stringify(event));
        if (events.length && bytes + size > 200_000) break;
        events.push(event);
        bytes += size;
      }
      const bucketStart = Math.floor(Date.now() / 60_000) * 60_000 - 29 * 60_000;
      const buckets = Array<number>(30).fill(0);
      for (const row of await tx.all<{ bucket: number; count: number }>(
        'SELECT CAST((at-?)/60000 AS INTEGER) AS bucket,COUNT(*) AS count FROM activityEvents WHERE projectId=? AND at>=? AND at<? GROUP BY bucket',
        bucketStart,
        query.projectId,
        bucketStart,
        bucketStart + 30 * 60_000,
      ))
        if (row.bucket >= 0 && row.bucket < 30) buckets[row.bucket] = row.count;
      const project = await tx.get<{ since: number }>(
        'SELECT since FROM activityProjects WHERE projectId=?',
        query.projectId,
      );
      const oldest = await tx.get<{ at: number | null }>(
        'SELECT MIN(at) AS at FROM activityEvents WHERE projectId=? AND at>=?',
        query.projectId,
        Date.now() - activityRetentionMs,
      );
      return {
        events,
        nextBefore: rows.length > events.length && events.length ? events.at(-1)!.cursor : null,
        recordingSince: project?.since ?? Date.now(),
        retainedSince: oldest?.at ?? null,
        buckets,
        bucketStart,
      };
    });
  }
}
