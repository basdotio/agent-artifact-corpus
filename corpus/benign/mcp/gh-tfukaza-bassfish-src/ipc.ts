import { createConnection, createServer } from 'node:net';
import type { Server, Socket } from 'node:net';
import { randomUUID } from 'node:crypto';
import { BassfishError } from './domain.js';
import { z } from 'zod';
import {
  DiagnosticOperation,
  diagnosticCode,
  diagnosticHash,
  emitDiagnostic,
  withDiagnostics,
} from './diagnostic-events.js';
import type { DiagnosticSink } from './diagnostic-events.js';

const requestSchema = z
  .object({
    id: z.string().min(1).max(100),
    method: z.string().min(1).max(100),
    params: z.unknown().optional(),
  })
  .strict();
interface Reply {
  id: string;
  result?: unknown;
  error?: { code: string; message: string };
}
const maximumFrame = 2_000_000;
function frames(socket: Socket, receive: (frame: unknown) => void): void {
  let buffer = '';
  socket.setEncoding('utf8');
  socket.on('data', data => {
    buffer += data;
    if (Buffer.byteLength(buffer) > maximumFrame) {
      socket.destroy(new Error('IPC frame limit exceeded'));
      return;
    }
    let newline: number;
    while ((newline = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newline);
      buffer = buffer.slice(newline + 1);
      try {
        receive(JSON.parse(line));
      } catch {
        socket.destroy(new Error('Invalid IPC frame'));
        return;
      }
    }
  });
}
export type RpcHandler = (
  method: string,
  params: unknown,
  signal: AbortSignal,
  socket: Socket,
) => Promise<unknown>;
export async function listenRpc(
  path: string,
  handler: RpcHandler,
  disconnected: (socket: Socket) => void | Promise<void>,
  diagnostics?: DiagnosticSink,
): Promise<{ server: Server; close: () => Promise<void> }> {
  const sockets = new Set<Socket>();
  const jobs = new Set<Promise<unknown>>();
  const server = createServer(socket => {
    sockets.add(socket);
    const connectionId = randomUUID();
    const running = new Map<string, AbortController>();
    const connectionJobs = new Set<Promise<unknown>>();
    socket.on('error', () => {
      emitDiagnostic(diagnostics, 'connection.error', { connectionId });
    });
    socket.on('close', () => {
      for (const controller of running.values()) controller.abort();
      sockets.delete(socket);
      emitDiagnostic(diagnostics, 'connection.closed', {
        connectionId,
        pendingRequestCount: running.size,
      });
      // Disconnect releases durable session state. Finish cancelled requests
      // first, and keep this cleanup in the drain before storage can close.
      const cleanup = Promise.allSettled([...connectionJobs])
        .then(() => disconnected(socket))
        .catch(error => {
          emitDiagnostic(diagnostics, 'connection.disconnect_failed', {
            connectionId,
            code: diagnosticCode(error),
          });
        })
        .finally(() => jobs.delete(cleanup));
      jobs.add(cleanup);
    });
    frames(socket, frame => {
      const parsed = requestSchema.safeParse(frame);
      if (!parsed.success) {
        socket.destroy();
        return;
      }
      const request = parsed.data;
      if (request.method === '$cancel') {
        const p = request.params as { id?: string };
        if (typeof p?.id === 'string') running.get(p.id)?.abort();
        return;
      }
      if (running.has(request.id)) {
        socket.destroy();
        return;
      }
      const controller = new AbortController();
      running.set(request.id, controller);
      const fields = {
        connectionId,
        ipcRequestId: request.id,
        ...requestMetadata(request.method, request.params),
      };
      const job = withDiagnostics(diagnostics, fields, async () => {
        const operation = new DiagnosticOperation(
          'request',
          {},
          expectedRequestMs(request.method, request.params),
        );
        try {
          operation.phase('handler');
          const result = await handler(request.method, request.params, controller.signal, socket);
          operation.finish(undefined, {
            socketOpenAtCompletion: !socket.destroyed,
            cancelled: controller.signal.aborted,
          });
          return result;
        } catch (error) {
          operation.finish(error, {
            socketOpenAtCompletion: !socket.destroyed,
            cancelled: controller.signal.aborted,
          });
          throw error;
        }
      })
        .then(
          result => {
            if (!socket.destroyed)
              socket.write(JSON.stringify({ id: request.id, result } satisfies Reply) + '\n');
          },
          error => {
            const failure =
              error instanceof BassfishError
                ? error
                : new BassfishError(
                    'INTERNAL_ERROR',
                    'The backend operation failed; inspect daemon health.',
                  );
            if (!socket.destroyed)
              socket.write(
                JSON.stringify({
                  id: request.id,
                  error: { code: failure.code, message: failure.message },
                } satisfies Reply) + '\n',
              );
          },
        )
        .finally(() => {
          running.delete(request.id);
          connectionJobs.delete(job);
          jobs.delete(job);
        });
      jobs.add(job);
      connectionJobs.add(job);
    });
  });
  await new Promise<void>((resolve, reject) => {
    server.once('error', reject);
    server.listen(path, resolve);
  });
  return {
    server,
    close: async () => {
      const closed = [...sockets].map(
        socket => new Promise<void>(resolve => socket.once('close', () => resolve())),
      );
      for (const socket of sockets) socket.destroy();
      await new Promise<void>(resolve => server.close(() => resolve()));
      await Promise.all(closed);
      while (jobs.size) await Promise.allSettled([...jobs]);
    },
  };
}

export class RpcClient {
  private readonly requests = new Map<
    string,
    { resolve: (value: unknown) => void; reject: (error: Error) => void }
  >();
  private readonly expired = new Map<string, { method: string; started: number }>();
  private readonly connectionId = randomUUID();
  private epoch?: string;
  private constructor(
    readonly socket: Socket,
    private readonly diagnostics?: DiagnosticSink,
  ) {
    frames(socket, raw => {
      const reply = raw as Reply;
      const request = this.requests.get(reply.id);
      if (!request) {
        const late = this.expired.get(reply.id);
        if (late) {
          this.expired.delete(reply.id);
          this.log('client.late_reply', {
            ipcRequestId: reply.id,
            method: late.method,
            replyOutcome: reply.error ? 'error' : 'success',
            durationMs: performance.now() - late.started,
            code:
              reply.error?.code && /^[A-Z_]{1,64}$/.test(reply.error.code)
                ? reply.error.code
                : undefined,
          });
        }
        return;
      }
      const result = reply.result as { epoch?: unknown } | undefined;
      if (typeof result?.epoch === 'string' && /^[a-f0-9-]{36}$/.test(result.epoch))
        this.epoch = result.epoch;
      this.requests.delete(reply.id);
      if (reply.error) request.reject(new BassfishError(reply.error.code, reply.error.message));
      else request.resolve(reply.result);
    });
    const failed = () => {
      if (this.requests.size)
        this.log('client.connection_lost', {
          ipcRequestIds: [...this.requests.keys()].slice(0, 20),
          pendingRequestCount: this.requests.size,
        });
      for (const r of this.requests.values())
        r.reject(
          new BassfishError(
            'OUTCOME_UNKNOWN',
            'The connection closed. No request was retried; inspect its outcome before writing again.',
          ),
        );
      this.requests.clear();
    };
    socket.on('error', failed);
    socket.on('close', failed);
  }
  static async connect(path: string, diagnostics?: DiagnosticSink): Promise<RpcClient> {
    const started = performance.now();
    emitDiagnostic(diagnostics, 'client.connect_attempt', {});
    const socket = createConnection(path);
    await new Promise<void>((resolve, reject) => {
      socket.once('connect', resolve);
      socket.once('error', reject);
    }).catch(error => {
      const code = (error as NodeJS.ErrnoException).code;
      emitDiagnostic(diagnostics, 'client.connect_failed', {
        durationMs: performance.now() - started,
        code: code && /^[A-Z_]{1,64}$/.test(code) ? code : 'CONNECTION_FAILED',
      });
      throw error;
    });
    const client = new RpcClient(socket, diagnostics);
    client.log('client.connected', { nodeVersion: process.versions.node });
    return client;
  }
  async call<T = unknown>(
    method: string,
    params: unknown = {},
    signal?: AbortSignal,
    timeoutMs = 35_000,
  ): Promise<T> {
    if (signal?.aborted)
      throw new BassfishError('CANCELLED', 'Request was cancelled before submission.');
    if (this.socket.destroyed)
      throw new BassfishError(
        'CONNECTION_CLOSED',
        'Reconnect explicitly before submitting a new operation.',
      );
    const id = randomUUID();
    const started = performance.now();
    const metadata = requestMetadata(method, params);
    const abort = () => {
      if (!this.socket.destroyed)
        this.socket.write(
          JSON.stringify({ id: randomUUID(), method: '$cancel', params: { id } }) + '\n',
        );
    };
    const timer = setTimeout(() => {
      this.log('client.deadline', {
        ipcRequestId: id,
        ...metadata,
        timeoutMs,
        durationMs: performance.now() - started,
      });
      if (this.expired.size >= 1024) this.expired.delete(this.expired.keys().next().value!);
      this.expired.set(id, { method: metadata.method, started });
      this.requests
        .get(id)
        ?.reject(
          new BassfishError(
            'OUTCOME_UNKNOWN',
            'The response deadline elapsed. No operation was retried; inspect current state.',
          ),
        );
      this.requests.delete(id);
    }, timeoutMs);
    signal?.addEventListener('abort', abort, { once: true });
    try {
      return await new Promise<T>((resolve, reject) => {
        this.requests.set(id, { resolve: value => resolve(value as T), reject });
        this.socket.write(JSON.stringify({ id, method, params }) + '\n');
      });
    } catch (error) {
      if (method === 'heartbeatSession')
        this.log('client.heartbeat_failed', {
          ipcRequestId: id,
          code: diagnosticCode(error),
          durationMs: performance.now() - started,
        });
      throw error;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener('abort', abort);
    }
  }
  private log(event: string, fields: Record<string, unknown>): void {
    emitDiagnostic(this.diagnostics, event, {
      ...fields,
      connectionId: this.connectionId,
      epoch: this.epoch,
    });
  }
  close(): void {
    this.socket.end();
  }
}

// Only validated, non-content metadata may cross into the diagnostic stream.
const waitMethods = new Set([
  'waitObservation',
  'waitNativeDelivery',
  'waitCodexWork',
  'getTurnOffer',
  'waitTask',
  'waitForWork',
  'waitWorkTask',
]);
function expectedRequestMs(method: string, params: unknown): number {
  const raw = params && typeof params === 'object' ? (params as Record<string, unknown>) : {};
  const args =
    raw.args && typeof raw.args === 'object' ? (raw.args as Record<string, unknown>) : raw;
  const timeout = args.timeoutMs;
  const deliberateWait =
    waitMethods.has(method) ||
    ((method === 'callMcpTool' || method === 'callTool') &&
      ['acquireTurn', 'waitForWork'].includes(String(raw.name)));
  return deliberateWait &&
    typeof timeout === 'number' &&
    Number.isInteger(timeout) &&
    timeout >= 0 &&
    timeout <= 60000
    ? timeout
    : 0;
}
function requestMetadata(
  method: string,
  params: unknown,
): {
  method: string;
  tool?: string;
  resourceId?: string;
  hostSessionHash?: string;
  tokenHash?: string;
} {
  const raw = params && typeof params === 'object' ? (params as Record<string, unknown>) : {};
  const fields: ReturnType<typeof requestMetadata> = {
    method: /^[a-zA-Z]{1,100}$/.test(method) ? method : 'unknown',
  };
  if (
    typeof raw.name === 'string' &&
    /^[a-zA-Z]{1,100}$/.test(raw.name) &&
    ['callTool', 'callMcpTool'].includes(method)
  )
    fields.tool = raw.name;
  if (typeof raw.hostSessionId === 'string')
    fields.hostSessionHash = diagnosticHash(raw.hostSessionId);
  const args =
    raw.args && typeof raw.args === 'object' ? (raw.args as Record<string, unknown>) : raw;
  if (typeof args.turnToken === 'string') fields.tokenHash = diagnosticHash(args.turnToken);
  const target =
    args.target && typeof args.target === 'object' ? (args.target as Record<string, unknown>) : {};
  for (const source of [args, target])
    for (const key of ['threadId', 'ticketId', 'resourceId'])
      if (typeof source[key] === 'string' && /^[a-f0-9-]{36}$/.test(source[key]))
        fields.resourceId = source[key] as string;
  return fields;
}
