import { AsyncLocalStorage } from 'node:async_hooks';
import { createHash, randomUUID } from 'node:crypto';
import { performance } from 'node:perf_hooks';

export type DiagnosticFields = Record<string, unknown>;
export type DiagnosticSink = (event: string, fields: DiagnosticFields) => void;
interface Context {
  sink: DiagnosticSink;
  fields: DiagnosticFields;
}
const context = new AsyncLocalStorage<Context>();

export function diagnosticHash(value: string): string {
  return createHash('sha256').update(value).digest('hex').slice(0, 24);
}
export function diagnosticCode(error: unknown): string {
  const code = (error as { code?: unknown } | null)?.code;
  if (typeof code === 'string' && /^[A-Z][A-Z_0-9]{0,63}$/.test(code)) return code;
  return code === 'GenericFailure' ? 'NATIVE_FAILURE' : 'INTERNAL_ERROR';
}
/** Diagnostic callbacks must never become an application failure. */
export function emitDiagnostic(
  sink: DiagnosticSink | undefined,
  event: string,
  fields: DiagnosticFields,
): void {
  try {
    sink?.(event, fields);
  } catch {
    /* best effort */
  }
}
export function withDiagnostics<T>(
  sink: DiagnosticSink | undefined,
  fields: DiagnosticFields,
  work: () => T,
): T {
  return sink ? context.run({ sink, fields }, work) : work();
}
export function diagnosticEvent(
  event: string,
  fields: DiagnosticFields,
  fallback?: DiagnosticSink,
): void {
  const current = context.getStore();
  emitDiagnostic(current?.sink ?? fallback, event, { ...current?.fields, ...fields });
}
/** Transient state is consumed by the worker, not written for each successful operation. */
export class DiagnosticOperation {
  private readonly started = performance.now();
  private readonly id = randomUUID();
  private phaseName = 'started';
  private phaseStarted = this.started;
  private readonly phases: Record<string, number> = {};
  private readonly current = context.getStore();
  constructor(
    private readonly kind: string,
    private readonly fields: DiagnosticFields = {},
    private readonly expectedMs = 0,
  ) {
    this.phase('started');
  }
  phase(phase: string, fields: DiagnosticFields = {}): void {
    if (!this.current) return;
    const now = performance.now();
    this.phases[this.phaseName] = (this.phases[this.phaseName] ?? 0) + now - this.phaseStarted;
    this.phaseName = phase;
    this.phaseStarted = now;
    emitDiagnostic(this.current.sink, 'operation.active', {
      ...this.current.fields,
      ...this.fields,
      ...fields,
      operationId: this.id,
      kind: this.kind,
      phase,
      startedMonoMs: this.started,
      phaseStartedMonoMs: now,
      expectedMs: this.expectedMs,
    });
  }
  event(event: string, fields: DiagnosticFields): void {
    if (this.current)
      emitDiagnostic(this.current.sink, event, {
        ...this.current.fields,
        ...this.fields,
        operationId: this.id,
        ...fields,
      });
  }
  finish(error?: unknown, fields: DiagnosticFields = {}): void {
    if (!this.current) return;
    const now = performance.now();
    this.phases[this.phaseName] = (this.phases[this.phaseName] ?? 0) + now - this.phaseStarted;
    const result = {
      ...this.current.fields,
      ...this.fields,
      ...fields,
      operationId: this.id,
      kind: this.kind,
      durationMs: now - this.started,
      phasesMs: this.phases,
      ...(error === undefined ? {} : { code: diagnosticCode(error) }),
    };
    emitDiagnostic(this.current.sink, 'operation.finished', result);
    if (error !== undefined || now - this.started > this.expectedMs + 1000)
      emitDiagnostic(
        this.current.sink,
        `${this.kind}.${error === undefined ? 'slow' : 'failed'}`,
        result,
      );
  }
}
