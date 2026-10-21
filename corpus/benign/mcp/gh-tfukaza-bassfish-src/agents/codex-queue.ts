import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { setTimeout as delay } from 'node:timers/promises';
import { isAbsolute } from 'node:path';
import type { DeliveryBatch } from '../notification-delivery.js';
import { formatDeliveryContext } from '../notification-delivery.js';

const execute = promisify(execFile);
export interface QueueBackend {
  wait(sessionId: string, signal: AbortSignal): Promise<{ ready: boolean }>;
  reserve(sessionId: string): Promise<DeliveryBatch>;
  transition(
    sessionId: string,
    token: string,
    status: 'submitting' | 'accepted' | 'uncertain' | 'released',
    issue?: string,
  ): Promise<unknown>;
}
export class CodexQueue {
  private controller?: AbortController;
  private sessionId?: string;
  private checked?: Promise<boolean>;
  private paused = false;
  private hostPhase?: 'prompt' | 'active' | 'idle' | 'paused';
  status = 'checking';
  get readiness(): string {
    if (this.status !== 'available') return this.status;
    if (!this.hostPhase) return 'hooks-unobserved';
    if (this.hostPhase === 'paused') return 'paused';
    return this.hostPhase === 'idle' ? 'available' : 'active';
  }
  observeHook(phase: 'prompt' | 'active' | 'idle' | 'paused'): void {
    this.hostPhase = phase;
  }
  constructor(
    private readonly backend: QueueBackend,
    private readonly workspace: () => string,
    private readonly run: typeof execute = execute,
    private readonly coalesceMs = 750,
  ) {}
  private executable(): string {
    return process.env.BASSFISH_CODEX_QUEUE_EXECUTABLE ?? 'codex';
  }
  private supported(): Promise<boolean> {
    return (this.checked ??= (async () => {
      const sqliteHome = process.env.BASSFISH_CODEX_QUEUE_SQLITE_HOME;
      if (sqliteHome && !isAbsolute(sqliteHome)) {
        this.status = 'unavailable';
        return false;
      }
      try {
        const result = await this.run(this.executable(), ['--version'], {
          timeout: 3000,
          maxBuffer: 8192,
        });
        const match = /codex-cli (\d+)\.(\d+)/.exec(String(result.stdout));
        const supported = Boolean(match && (Number(match[1]) > 0 || Number(match[2]) >= 154));
        this.status = supported ? 'available' : 'unsupported';
        return supported;
      } catch {
        this.status = 'unavailable';
        return false;
      }
    })());
  }
  bind(sessionId: string): void {
    this.paused = false;
    if (this.sessionId === sessionId && this.controller && !this.controller.signal.aborted) return;
    this.stop();
    this.sessionId = sessionId;
    const controller = new AbortController();
    this.controller = controller;
    void this.listen(sessionId, controller.signal);
  }
  pause(): void {
    this.paused = true;
  }
  stop(): void {
    this.controller?.abort();
    this.controller = undefined;
    this.sessionId = undefined;
    this.hostPhase = undefined;
  }
  private async listen(sessionId: string, signal: AbortSignal): Promise<void> {
    if (!(await this.supported()) || signal.aborted) return;
    while (!signal.aborted) {
      try {
        if (this.paused) {
          await delay(1000, undefined, { signal });
          continue;
        }
        if (!(await this.backend.wait(sessionId, signal)).ready) continue;
        await delay(this.coalesceMs, undefined, { signal });
        if (this.paused) continue;
        const batch = await this.backend.reserve(sessionId);
        if (!batch.batchToken || !batch.count) continue;
        if (signal.aborted || this.paused) {
          await this.backend.transition(sessionId, batch.batchToken, 'released');
          if (signal.aborted) break;
          continue;
        }
        await this.backend.transition(sessionId, batch.batchToken, 'submitting');
        const args = ['queue', '--thread', sessionId, '--message', formatDeliveryContext(batch)];
        if (process.env.BASSFISH_CODEX_QUEUE_PROFILE)
          args.push('--profile', process.env.BASSFISH_CODEX_QUEUE_PROFILE);
        if (process.env.BASSFISH_CODEX_QUEUE_SQLITE_HOME)
          args.push(
            '-c',
            `sqlite_home=${JSON.stringify(process.env.BASSFISH_CODEX_QUEUE_SQLITE_HOME)}`,
          );
        try {
          await this.run(this.executable(), args, {
            cwd: this.workspace(),
            env: process.env,
            timeout: 15000,
            maxBuffer: 8192,
            signal,
          });
          await this.backend.transition(sessionId, batch.batchToken, 'accepted');
        } catch (error) {
          const code = (error as NodeJS.ErrnoException).code;
          const known = code === 'ENOENT' || code === 'EACCES';
          await this.backend.transition(
            sessionId,
            batch.batchToken,
            known ? 'released' : 'uncertain',
            known
              ? 'Codex queue executable unavailable.'
              : 'Queue acceptance unknown; inspect this batch at the next checkpoint.',
          );
          if (known) {
            this.status = 'unavailable';
            break;
          }
        }
      } catch {
        if (!signal.aborted) await delay(1000, undefined, { signal }).catch(() => {});
      }
    }
  }
}
