import { clientDiagnosticSink } from '../diagnostic-log.js';
import { setTimeout as delay } from 'node:timers/promises';
import { RpcClient } from '../ipc.js';
import { socketPath } from '../config.js';
import { BassfishError } from '../domain.js';
import type { ObservationRead } from '../observer.js';
import type { ObservationSnapshot } from '../observation-types.js';
import type { ObservationFilter } from '../storage/observation-content.js';

export interface SonarState {
  phase: 'waiting' | 'connecting' | 'live' | 'reconnecting' | 'error';
  snapshot?: ObservationSnapshot;
  message?: string;
  gap: boolean;
}
export class SonarClient {
  state: SonarState = { phase: 'connecting', gap: false };
  private connection?: RpcClient;
  private readonly stopSignal = new AbortController();
  private readonly listeners = new Set<() => void>();
  private generation = 0;
  private refreshId = 0;
  private filter: ObservationFilter = { threadState: 'active' };
  constructor(
    private readonly dataDir: string,
    private readonly workspace: string,
  ) {}
  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };
  getState = (): SonarState => this.state;
  private publish(next: SonarState) {
    this.state = next;
    for (const notify of this.listeners) notify();
  }
  async read<T>(request: ObservationRead): Promise<T> {
    const connection = this.connection;
    if (!connection) throw new BassfishError('CONNECTION_CLOSED', 'Waiting for the daemon.');
    const result = await connection.call<T>('readObservation', request, this.stopSignal.signal);
    if (connection !== this.connection)
      throw new BassfishError('CANCELLED', 'The observation connection changed.');
    return result;
  }
  async refresh(filter?: ObservationFilter): Promise<void> {
    if (filter) this.filter = filter;
    const id = ++this.refreshId;
    const generation = this.generation;
    const snapshot = await this.read<ObservationSnapshot>({
      kind: 'snapshot',
      filter: this.filter,
    });
    if (id !== this.refreshId || generation !== this.generation) return;
    const changedEpoch = this.state.snapshot && this.state.snapshot.epoch !== snapshot.epoch;
    this.publish({ phase: 'live', snapshot, gap: this.state.gap || Boolean(changedEpoch) });
  }
  async once(): Promise<ObservationSnapshot | null> {
    try {
      this.connection = await RpcClient.connect(
        socketPath(this.dataDir),
        clientDiagnosticSink(this.dataDir),
      );
      await this.connection.call('openObserver', { workspace: this.workspace, protocolVersion: 2 });
      return await this.read<ObservationSnapshot>({ kind: 'snapshot', filter: this.filter });
    } catch (error) {
      if (['ENOENT', 'ECONNREFUSED'].includes((error as NodeJS.ErrnoException).code ?? ''))
        return null;
      throw error;
    } finally {
      this.close();
    }
  }
  async run(): Promise<void> {
    let backoff = 250;
    while (!this.stopSignal.signal.aborted) {
      try {
        this.connection = await RpcClient.connect(
          socketPath(this.dataDir),
          clientDiagnosticSink(this.dataDir),
        );
        this.generation++;
        await this.connection.call(
          'openObserver',
          { workspace: this.workspace, protocolVersion: 2 },
          this.stopSignal.signal,
        );
        await this.refresh();
        backoff = 250;
        while (!this.stopSignal.signal.aborted) {
          const cursor = this.state.snapshot?.cursor ?? '0';
          const update = await this.connection.call<{ cursor: string; gap: boolean }>(
            'waitObservation',
            { cursor, timeoutMs: 20_000 },
            this.stopSignal.signal,
          );
          if (update.gap) this.publish({ ...this.state, gap: true });
          if (update.cursor !== cursor)
            await delay(100, undefined, { signal: this.stopSignal.signal });
          await this.refresh();
        }
      } catch (error) {
        if (this.stopSignal.signal.aborted) break;
        const code = (error as { code?: string }).code;
        if (
          ['UNKNOWN_METHOD', 'INVALID_ARGUMENT', 'NOT_A_REPOSITORY', 'OBSERVER_READ_ONLY'].includes(
            code ?? '',
          )
        ) {
          this.publish({
            ...this.state,
            phase: 'error',
            message:
              code === 'UNKNOWN_METHOD'
                ? 'This daemon does not support Sonar. Upgrade and restart the daemon.'
                : (error as Error).message,
          });
          break;
        }
        this.publish({
          ...this.state,
          phase: this.state.snapshot ? 'reconnecting' : 'waiting',
          message: 'Waiting for daemon · bassfish daemon start',
        });
      } finally {
        this.connection?.socket.destroy();
        this.connection = undefined;
        this.generation++;
      }
      try {
        await delay(backoff, undefined, { signal: this.stopSignal.signal });
      } catch {
        break;
      }
      backoff = Math.min(backoff * 2, 5000);
    }
  }
  close(): void {
    this.stopSignal.abort();
    this.connection?.socket.destroy();
    this.connection = undefined;
  }
}
