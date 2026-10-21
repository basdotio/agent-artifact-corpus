import { startRuntimeDiagnostics } from './runtime-diagnostics.js';
import type { RuntimeDiagnostics } from './runtime-diagnostics.js';
import { DiagnosticOperation, withDiagnostics } from './diagnostic-events.js';
import { clientDiagnosticSink } from './diagnostic-log.js';
import { packageVersion } from './config.js';
import { closeSync } from 'node:fs';
import {
  daemonDiagnostics,
  daemonError,
  openDaemonLog,
  recordDaemonLifecycle,
  rotateDaemonLog,
} from './daemon-diagnostics.js';
import { startMaintenance } from './maintenance.js';
import { requireSupportedPlatform, tursoVersion } from './storage/platform.js';
import { mkdir, chmod, lstat, unlink } from 'node:fs/promises';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';
import type { Socket } from 'node:net';
import { z } from 'zod';
import { BassfishError, requireThat } from './domain.js';
import { Bassfish } from './service.js';
import { TursoControl } from './storage/coordination.js';
import { TursoContent } from './storage/content.js';
import { requireFreshStorage, type TursoStore } from './storage/turso.js';
import { SystemClock } from './runtime.js';
import { resolveRepository } from './repository.js';
import { nameSchema } from './contracts.js';
import { exclusiveLock } from './lock.js';
import { listenRpc, RpcClient } from './ipc.js';
import { loadRuntimeConfig, runtimeConfigSchema, socketPath, packageRoot } from './config.js';
import type { RuntimeConfig } from './config.js';
import { entryArgs } from './supervisor.js';
import { selectNativeCandidate } from './agents/claude-native.js';
import {
  ProjectObserver,
  observerOpenSchema,
  observationReadSchema,
  observationWaitSchema,
} from './observer.js';
const wakeHostSchema = z.enum(['claude', 'opencode']);
const wakeNativeSchema = z
  .object({
    host: wakeHostSchema,
    clientId: z.string().uuid(),
    processAncestors: z.array(z.number().int().positive()).min(1).max(64),
  })
  .strict();
const nativeSchema = z.union([wakeNativeSchema, z.object({ host: z.literal('codex') }).strict()]);
const hostSessionIdSchema = z.string().min(1).max(200);
const openSchema = z
  .object({
    workspace: z.string().min(1),
    name: nameSchema.optional(),
    native: nativeSchema.optional(),
    hostSessionId: hostSessionIdSchema.optional(),
  })
  .strict();
const callSchema = z
  .object({
    name: z.string(),
    args: z.unknown().default({}),
    taskCapable: z.boolean().default(false),
    hostSessionId: hostSessionIdSchema.optional(),
  })
  .strict();
const taskSchema = z
  .object({ taskId: z.string().min(1).max(200), hostSessionId: hostSessionIdSchema.optional() })
  .strict();
const waitTaskSchema = z
  .object({
    taskId: z.string().min(1).max(200),
    updatedAfter: z.number().int().nonnegative(),
    timeoutMs: z.number().int().min(0).max(20000),
    hostSessionId: hostSessionIdSchema.optional(),
  })
  .strict();
const waitWorkSchema = z
  .object({
    timeoutMs: z.number().int().min(0).max(20000),
    hostSessionId: hostSessionIdSchema.optional(),
  })
  .strict();
const bindHostSessionSchema = z.object({ sessionId: hostSessionIdSchema }).strict();
const releaseSchema = z.object({ turnId: z.string().min(1), force: z.literal(true) }).strict();
const nativeDeliverySchema = z
  .object({
    workspace: z.string().min(1),
    host: wakeHostSchema,
    clientId: z.string().uuid(),
    processAncestors: z.array(z.number().int().positive()).min(1).max(64),
    sessionId: hostSessionIdSchema.optional(),
    timeoutMs: z.number().int().min(0).max(20000),
  })
  .strict();
const closeNativeHostSessionSchema = nativeDeliverySchema
  .omit({ timeoutMs: true })
  .extend({ sessionId: hostSessionIdSchema })
  .strict();
const hostDeliverySchema = z
  .object({
    sessionId: hostSessionIdSchema,
    phase: z.enum(['prompt', 'active', 'idle', 'paused']),
    queueEnabled: z.boolean().optional(),
  })
  .strict();
type NativeConnection = z.infer<typeof nativeSchema>;
interface AdapterSession {
  id: string;
  commonDir: string;
  workspace: string;
  name?: string;
  native?: NativeConnection;
  defaultHostSessionId?: string;
  defaultHandle?: string;
  handles: Map<string, string>;
}
function parse<T>(schema: z.ZodType<T>, value: unknown): T {
  const result = schema.safeParse(value);
  requireThat(result.success, 'INVALID_ARGUMENT', 'Invalid backend request.');
  return result.data;
}
export type DaemonOverrides = Partial<Pick<RuntimeConfig, 'turnTimeoutMs'>>;
export async function runDaemon(
  dataDir: string,
  overrides: DaemonOverrides = {},
): Promise<TursoStore> {
  requireSupportedPlatform();
  process.umask(0o077);
  const path = socketPath(dataDir);
  await mkdir(join(dataDir, 'run'), { recursive: true, mode: 0o700 });
  await chmod(dataDir, 0o700);
  await chmod(join(dataDir, 'run'), 0o700);
  const unlock = exclusiveLock(join(dataDir, 'run', 'daemon-owner.lock'));
  let control: TursoControl | undefined;
  let content: TursoContent | undefined;
  let rpc: Awaited<ReturnType<typeof listenRpc>> | undefined;
  let runtimeDiagnostics: RuntimeDiagnostics | undefined;
  let stopMaintenance: (() => void) | undefined;
  let epoch: string | undefined;
  const fatal = async (error: unknown): Promise<never> => {
    recordDaemonLifecycle(dataDir, 'failed', { epoch, ...daemonError(error) });
    // A fail-closed store can still have valid leased transactions. Drain them
    // before maintenance's fatal path exits the process.
    await stop('failed').catch(() => {});
    recordDaemonLifecycle(dataDir, 'failed', { epoch, ...daemonError(error) });
    process.exit(1);
  };
  recordDaemonLifecycle(dataDir, 'starting', {
    bassfishVersion: packageVersion,
    nodeVersion: process.versions.node,
    tursoVersion,
    platform: `${process.platform}-${process.arch}`,
  });
  let closing: Promise<void> | undefined;
  const stop = (reason = 'requested'): Promise<void> =>
    (closing ??= (async () => {
      stopMaintenance?.();
      const failures: unknown[] = [];
      for (const cleanup of [
        () => rpc?.close(),
        () => control?.activity.publish(),
        () => control?.close(),
        () => runtimeDiagnostics?.close(),
      ]) {
        try {
          await cleanup();
        } catch (error) {
          failures.push(error);
        }
      }
      if (reason !== 'startup_failed' && reason !== 'failed' && !failures.length)
        recordDaemonLifecycle(dataDir, 'stopped', { epoch, reason });
      unlock();
      if (failures.length) throw failures[0];
    })());
  try {
    const config = runtimeConfigSchema.parse({
      ...(await loadRuntimeConfig(dataDir)),
      ...overrides,
    });
    try {
      const stale = await lstat(path);
      requireThat(
        stale.isSocket(),
        'UNSAFE_SOCKET_PATH',
        'The daemon socket path contains a non-socket file.',
      );
      await unlink(path);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error;
    }
    await requireFreshStorage(dataDir);
    control = await TursoControl.open(join(dataDir, 'bassfish.db'));
    content = new TursoContent(control.store);
    const service = new Bassfish(
      control,
      content,
      new SystemClock(),
      {
        offerMs: config.offerMs,
        turnTimeoutMs: config.turnTimeoutMs,
        reconnectMs: config.reconnectMs,
        instanceMs: config.instanceMs,
        queueMs: config.queueMs,
        retentionMs: config.retentionMs,
        waitMs: config.waitMs,
      },
      dataDir,
    );
    runtimeDiagnostics = startRuntimeDiagnostics(dataDir, {
      bassfishVersion: packageVersion,
      nodeVersion: process.versions.node,
      tursoVersion,
      platform: `${process.platform}-${process.arch}`,
      epoch: service.epoch,
      config,
    });
    service.diagnostics = runtimeDiagnostics?.emit;
    await withDiagnostics(
      runtimeDiagnostics?.emit,
      { method: 'initialize', epoch: service.epoch },
      () => service.initialize(),
    );
    const sessions = new Map<Socket, AdapterSession>();
    const observers = new Map<Socket, string>();
    const observerSockets = new WeakSet<Socket>();
    const observer = new ProjectObserver(control, content, service.epoch);
    const nativeSessions = new Map<Socket, AdapterSession>();
    const idleHostSessions = new Set<string>();
    const nativeWaiters = new Set<() => void>();
    const signalNativeChange = () => {
      for (const wake of nativeWaiters) wake();
      nativeWaiters.clear();
    };
    control.subscribe(signalNativeChange);
    const waitNativeChange = (timeout: number, signal?: AbortSignal) =>
      new Promise<void>((resolve, reject) => {
        let timer: NodeJS.Timeout | undefined;
        const cleanup = () => {
          if (timer) clearTimeout(timer);
          nativeWaiters.delete(done);
          signal?.removeEventListener('abort', abort);
        };
        const done = () => {
          cleanup();
          resolve();
        };
        const abort = () => {
          cleanup();
          reject(new BassfishError('CANCELLED', 'Native wake observation was cancelled.'));
        };
        nativeWaiters.add(done);
        timer = setTimeout(done, Math.max(0, timeout));
        timer.unref();
        if (signal?.aborted) abort();
        else signal?.addEventListener('abort', abort, { once: true });
      });
    const closeHandle = async (session: AdapterSession, sessionId: string, clean = true) => {
      const handle = session.handles.get(sessionId);
      if (!handle) return;
      await service.disconnect(handle, clean, closing ? 'daemon_shutdown' : undefined);
      session.handles.delete(sessionId);
      idleHostSessions.delete(`${session.id}:${sessionId}`);
      if (session.defaultHostSessionId === sessionId) session.defaultHostSessionId = undefined;
    };
    const closeAdapter = async (session: AdapterSession, clean = true) => {
      for (const handle of new Set([
        ...(session.defaultHandle ? [session.defaultHandle] : []),
        ...session.handles.values(),
      ]))
        await service.disconnect(handle, clean, closing ? 'daemon_shutdown' : undefined);
      session.defaultHandle = undefined;
      session.defaultHostSessionId = undefined;
      session.handles.clear();
      for (const key of [...idleHostSessions])
        if (key.startsWith(`${session.id}:`)) idleHostSessions.delete(key);
    };
    const ensureHostHandle = async (session: AdapterSession, sessionId: string) => {
      requireThat(
        session.native,
        'HOST_SESSION_UNAVAILABLE',
        'This adapter was not started by a Bassfish host plugin.',
      );
      const existing = session.handles.get(sessionId);
      if (existing) {
        try {
          await service.heartbeat(existing);
          return existing;
        } catch (error) {
          if (!(error instanceof BassfishError) || error.code !== 'SESSION_EXPIRED') throw error;
          session.handles.delete(sessionId);
        }
      }
      const opened = await service.open(
        session.commonDir,
        undefined,
        session.native,
        session.workspace,
        sessionId,
        false,
      );
      session.handles.set(sessionId, opened.agentHandle);
      return opened.agentHandle;
    };
    const resolveHandle = async (session: AdapterSession, hostSessionId?: string) => {
      if (hostSessionId) return await ensureHostHandle(session, hostSessionId);
      if (session.defaultHostSessionId)
        return await ensureHostHandle(session, session.defaultHostSessionId);
      requireThat(
        session.defaultHandle,
        'HOST_SESSION_REQUIRED',
        'The host plugin must bind its current session before using Bassfish.',
      );
      return session.defaultHandle;
    };
    const bindHostSession = async (session: AdapterSession, sessionId: string) => {
      requireThat(
        session.native && session.native.host !== 'opencode',
        'HOST_SESSION_UNAVAILABLE',
        'Only Claude Code and Codex bind a default host session.',
      );
      if (session.defaultHostSessionId && session.defaultHostSessionId !== sessionId)
        await closeHandle(session, session.defaultHostSessionId);
      const handle = await ensureHostHandle(session, sessionId);
      session.defaultHostSessionId = sessionId;
      return { agentHandle: handle, session: await service.info(handle) };
    };
    let lastActivity = Date.now();
    const opening = new Set<Socket>();
    rpc = await listenRpc(
      path,
      async (method, params, signal, socket) => {
        lastActivity = Date.now();
        requireThat(!closing, 'DAEMON_STOPPING', 'The daemon is stopping.');
        requireThat(
          !observerSockets.has(socket) ||
            ['readObservation', 'waitObservation', 'closeObserver'].includes(method),
          'OBSERVER_READ_ONLY',
          'Observer connections are read-only.',
        );
        switch (method) {
          case 'openObserver': {
            requireThat(
              !sessions.has(socket) && !opening.has(socket),
              'SESSION_EXISTS',
              'This connection is already in use.',
            );
            const args = parse(observerOpenSchema, params);
            observerSockets.add(socket);
            opening.add(socket);
            try {
              const commonDir = await resolveRepository(args.workspace);
              requireThat(
                !signal.aborted && !socket.destroyed,
                'CANCELLED',
                'Observation opening cancelled.',
              );
              observers.set(socket, commonDir);
              return { protocolVersion: 2, epoch: service.epoch };
            } finally {
              opening.delete(socket);
            }
          }
          case 'readObservation': {
            const commonDir = observers.get(socket);
            requireThat(commonDir, 'OBSERVER_REQUIRED', 'Open an observer connection first.');
            return observer.read(commonDir, parse(observationReadSchema, params));
          }
          case 'waitObservation': {
            const commonDir = observers.get(socket);
            requireThat(commonDir, 'OBSERVER_REQUIRED', 'Open an observer connection first.');
            const args = parse(observationWaitSchema, params);
            return observer.wait(commonDir, args.cursor, args.timeoutMs, signal);
          }
          case 'closeObserver':
            observers.delete(socket);
            return { closed: true };
          case 'getHealth':
            return {
              apiVersion: 15,
              pid: process.pid,
              epoch: service.epoch,
              dataDir,
              state: 'ready',
              diagnostics: {
                ...daemonDiagnostics(dataDir),
                runtime: runtimeDiagnostics?.summary(),
              },
              storage: {
                engine: 'turso',
                version: tursoVersion,
                ...control!.store.diagnostics(),
                path: join(dataDir, 'bassfish.db'),
              },
              config,
              control: await service.inspect(),
            };
          case 'probeHealth':
            return {
              apiVersion: 15,
              pid: process.pid,
              epoch: service.epoch,
              state: 'ready',
              diagnostics: {
                ...daemonDiagnostics(dataDir),
                runtime: runtimeDiagnostics?.summary(),
              },
              storage: {
                engine: 'turso',
                version: tursoVersion,
                ...control!.store.diagnostics(),
                path: join(dataDir, 'bassfish.db'),
              },
            };
          case 'stopDaemon':
            setTimeout(() => {
              void stop().catch(fatal);
            }, 25);
            return { stopping: true };
          case 'inspectDaemon':
            return await service.inspect();
          case 'forceRelease':
            await service.forceRelease(parse(releaseSchema, params).turnId);
            return { released: true };
          case 'openSession': {
            requireThat(
              !sessions.has(socket) && !opening.has(socket),
              'SESSION_EXISTS',
              'One instance is allowed per adapter connection.',
            );
            const args = parse(openSchema, params);
            opening.add(socket);
            try {
              const commonDir = await resolveRepository(args.workspace);
              requireThat(!signal.aborted, 'CANCELLED', 'Session opening cancelled.');
              const session: AdapterSession = {
                id: randomUUID(),
                commonDir,
                workspace: args.workspace,
                name: args.name,
                native: args.native,
                handles: new Map(),
              };
              let result: {
                agentHandle?: string;
                session: unknown;
              } = { session: null };
              if (args.native && args.hostSessionId) {
                const handle = await ensureHostHandle(session, args.hostSessionId);
                session.defaultHostSessionId = args.hostSessionId;
                result = { agentHandle: handle, session: await service.info(handle) };
              } else if (!args.native) {
                const opened = await service.open(commonDir, args.name, undefined, args.workspace);
                session.defaultHandle = opened.agentHandle;
                result = opened;
              }
              if (socket.destroyed || signal.aborted) {
                await closeAdapter(session, false);
                throw new BassfishError('CANCELLED', 'Adapter disconnected while opening.');
              }
              sessions.set(socket, session);
              if (args.native && 'clientId' in args.native) {
                nativeSessions.set(socket, session);
                signalNativeChange();
              }
              return { ...result, epoch: service.epoch };
            } finally {
              opening.delete(socket);
            }
          }
          case 'closeSession': {
            const session = sessions.get(socket);
            if (session) await closeAdapter(session);
            sessions.delete(socket);
            if (nativeSessions.delete(socket)) signalNativeChange();
            return { closed: true };
          }
          case 'heartbeatSession': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter instance first.');
            for (const handle of new Set([
              ...(session.defaultHandle ? [session.defaultHandle] : []),
              ...session.handles.values(),
            ]))
              await service.heartbeat(handle);
            return { alive: true };
          }
          case 'bindHostSession': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const result = await bindHostSession(
              session,
              parse(bindHostSessionSchema, params).sessionId,
            );
            signalNativeChange();
            return result;
          }
          case 'takeHostDelivery': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            requireThat(
              session.native && session.native.host !== 'opencode',
              'HOST_SESSION_UNAVAILABLE',
              'Host delivery hooks are available only to Claude Code and Codex.',
            );
            const args = parse(hostDeliverySchema, params);
            if (session.defaultHostSessionId && session.defaultHostSessionId !== args.sessionId)
              await bindHostSession(session, args.sessionId);
            const handle = await ensureHostHandle(session, args.sessionId);
            session.defaultHostSessionId = args.sessionId;
            const key = `${session.id}:${args.sessionId}`;
            if (args.phase === 'idle') idleHostSessions.add(key);
            else idleHostSessions.delete(key);
            if (args.phase === 'prompt' || args.phase === 'active')
              await service.inbox.presented(handle, args.sessionId);
            const batch =
              session.native.host === 'codex' &&
              (args.phase === 'paused' || (args.phase === 'idle' && args.queueEnabled))
                ? { kind: 'none', count: 0, moreAvailable: false, notifications: [] }
                : await service.inbox.capture(
                    handle,
                    session.native.host === 'codex' || args.phase === 'active'
                      ? 'actionable'
                      : 'all',
                  );
            signalNativeChange();
            return batch;
          }
          case 'waitCodexWork':
          case 'reserveCodexDelivery':
          case 'codexDeliveryTransition': {
            const session = sessions.get(socket);
            requireThat(
              session?.native?.host === 'codex',
              'HOST_SESSION_UNAVAILABLE',
              'Codex native adapter required.',
            );
            const args = parse(
              z
                .object({
                  sessionId: hostSessionIdSchema,
                  timeoutMs: z.number().int().min(0).max(20000).optional(),
                  batchToken: z.string().uuid().optional(),
                  status: z.enum(['submitting', 'accepted', 'uncertain', 'released']).optional(),
                  issue: z.string().max(200).optional(),
                })
                .strict(),
              params,
            );
            requireThat(
              session.defaultHostSessionId === args.sessionId,
              'HOST_SESSION_REQUIRED',
              'Codex binding changed.',
            );
            const handle = await resolveHandle(session, args.sessionId);
            const key = `${session.id}:${args.sessionId}`;
            if (method === 'codexDeliveryTransition') {
              requireThat(
                args.batchToken && args.status,
                'INVALID_ARGUMENT',
                'Delivery token and status required.',
              );
              await service.inbox.transition(handle, args.batchToken, args.status, args.issue);
              return { updated: true };
            }
            if (method === 'reserveCodexDelivery')
              return idleHostSessions.has(key)
                ? service.inbox.capture(handle, 'actionable', args.sessionId)
                : { kind: 'none', count: 0, moreAvailable: false, notifications: [] };
            if (!idleHostSessions.has(key)) {
              await waitNativeChange(Math.min(args.timeoutMs ?? 20000, 1000), signal);
              return { ready: false };
            }
            return service.waitInbox(handle, args.timeoutMs ?? 20000, signal);
          }
          case 'callTool': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(callSchema, params);
            const handle = await resolveHandle(session, args.hostSessionId);
            return service.call(handle, args.name, args.args, signal, {
              taskCapable: args.taskCapable,
            });
          }
          case 'callMcpTool': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(callSchema, params);
            const handle = await resolveHandle(session, args.hostSessionId);
            return service.callMcp(handle, args.name, args.args, signal, {
              taskCapable: args.taskCapable,
            });
          }
          case 'getTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(taskSchema, params);
            return service.getTask(await resolveHandle(session, args.hostSessionId), args.taskId);
          }
          case 'peekTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(taskSchema, params);
            return service.getTask(
              await resolveHandle(session, args.hostSessionId),
              args.taskId,
              false,
            );
          }
          case 'cancelTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(taskSchema, params);
            return await service.cancelTask(
              await resolveHandle(session, args.hostSessionId),
              args.taskId,
            );
          }
          case 'waitTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(waitTaskSchema, params);
            return service.waitTask(
              await resolveHandle(session, args.hostSessionId),
              args.taskId,
              args.updatedAfter,
              args.timeoutMs,
              signal,
            );
          }
          case 'waitWork': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(waitWorkSchema, params);
            return service.waitForWork(
              await resolveHandle(session, args.hostSessionId),
              args.timeoutMs,
              signal,
            );
          }
          case 'createWorkTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(waitWorkSchema.omit({ timeoutMs: true }), params);
            return await service.createWorkTask(await resolveHandle(session, args.hostSessionId));
          }
          case 'getWorkTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(taskSchema, params);
            return service.getWorkTask(
              await resolveHandle(session, args.hostSessionId),
              args.taskId,
            );
          }
          case 'cancelWorkTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(taskSchema, params);
            return await service.cancelWorkTask(
              await resolveHandle(session, args.hostSessionId),
              args.taskId,
            );
          }
          case 'waitWorkTask': {
            const session = sessions.get(socket);
            requireThat(session, 'SESSION_REQUIRED', 'Open an adapter connection first.');
            const args = parse(waitTaskSchema, params);
            return service.waitWorkTask(
              await resolveHandle(session, args.hostSessionId),
              args.taskId,
              args.updatedAfter,
              args.timeoutMs,
              signal,
            );
          }
          case 'waitNativeDelivery': {
            const args = parse(nativeDeliverySchema, params);
            const commonDir = await resolveRepository(args.workspace);
            const until = performance.now() + args.timeoutMs;
            while (true) {
              const candidates = [...nativeSessions.values()].flatMap(value => {
                const native = value.native;
                return native &&
                  'clientId' in native &&
                  value.commonDir === commonDir &&
                  native.host === args.host &&
                  native.clientId === args.clientId
                  ? [
                      {
                        handle: value.id,
                        processAncestors: native.processAncestors,
                      },
                    ]
                  : [];
              });
              const match = selectNativeCandidate(candidates, args.processAncestors);
              const remaining = Math.max(0, until - performance.now());
              if (match) {
                const session = [...nativeSessions.values()].find(
                  candidate => candidate.id === match.handle,
                );
                const sessionId = args.sessionId ?? session?.defaultHostSessionId;
                try {
                  if (
                    session &&
                    sessionId &&
                    (args.host === 'opencode' || idleHostSessions.has(`${session.id}:${sessionId}`))
                  ) {
                    const batch = await service.inbox.capture(
                      await ensureHostHandle(session, sessionId),
                    );
                    if (
                      (
                        batch as {
                          count: number;
                        }
                      ).count > 0
                    ) {
                      idleHostSessions.delete(`${session.id}:${sessionId}`);
                      return batch;
                    }
                  }
                } catch (error) {
                  if (!(error instanceof BassfishError) || error.code !== 'SESSION_EXPIRED')
                    throw error;
                }
              }
              if (remaining <= 0)
                return { kind: 'none', count: 0, moreAvailable: false, notifications: [] };
              await waitNativeChange(Math.min(remaining, 250), signal);
            }
          }
          case 'closeNativeHostSession': {
            const args = parse(closeNativeHostSessionSchema, params);
            const commonDir = await resolveRepository(args.workspace);
            const candidates = [...nativeSessions.values()].flatMap(value => {
              const native = value.native;
              return native &&
                'clientId' in native &&
                value.commonDir === commonDir &&
                native.host === args.host &&
                native.clientId === args.clientId
                ? [{ handle: value.id, processAncestors: native.processAncestors }]
                : [];
            });
            const match = selectNativeCandidate(candidates, args.processAncestors);
            const session = match
              ? [...nativeSessions.values()].find(candidate => candidate.id === match.handle)
              : undefined;
            if (session) await closeHandle(session, args.sessionId);
            signalNativeChange();
            return { closed: Boolean(session) };
          }
          default:
            throw new BassfishError('UNKNOWN_METHOD', 'Unknown backend method.');
        }
      },
      async socket => {
        observers.delete(socket);
        const session = sessions.get(socket);
        if (session) await closeAdapter(session, false);
        sessions.delete(socket);
        if (nativeSessions.delete(socket)) signalNativeChange();
      },
      runtimeDiagnostics?.emit,
    );
    await chmod(path, 0o600);
    epoch = service.epoch;
    recordDaemonLifecycle(dataDir, 'ready', { epoch });
    stopMaintenance = startMaintenance(
      () =>
        withDiagnostics(runtimeDiagnostics?.emit, { method: 'maintenance', epoch }, async () => {
          const operation = new DiagnosticOperation('maintenance');
          try {
            operation.phase('log_rotation');
            rotateDaemonLog(dataDir);
            operation.phase('session_sweep');
            await service.sweep();
            operation.phase('idle_check');
            if (
              !closing &&
              sessions.size === 0 &&
              observers.size === 0 &&
              !(await service.hasPendingWork()) &&
              Date.now() - lastActivity >= config.idleMs
            )
              void stop('idle').catch(fatal);
            operation.finish();
          } catch (error) {
            operation.finish(error);
            throw error;
          }
        }),
      fatal,
      recovered =>
        recordDaemonLifecycle(
          dataDir,
          recovered ? 'maintenance_recovered' : 'maintenance_deferred',
          { epoch, code: 'STORAGE_BUSY' },
        ),
    );
    process.once('SIGINT', () => {
      void stop('SIGINT').catch(fatal);
    });
    process.once('SIGTERM', () => {
      void stop('SIGTERM').catch(fatal);
    });
    return control.store;
  } catch (error) {
    recordDaemonLifecycle(dataDir, 'failed', { epoch, ...daemonError(error) });
    await stop('startup_failed').catch(() => {});
    throw error;
  }
}
export async function connectDaemon(dataDir: string): Promise<RpcClient> {
  return RpcClient.connect(socketPath(dataDir), clientDiagnosticSink(dataDir));
}
async function probe(dataDir: string, signal?: AbortSignal): Promise<boolean> {
  signal?.throwIfAborted();
  let client: RpcClient | undefined;
  const abort = () => client?.socket.destroy();
  signal?.addEventListener('abort', abort, { once: true });
  try {
    client = await connectDaemon(dataDir);
    signal?.throwIfAborted();
    const result = await client.call<{
      apiVersion: number;
    }>('probeHealth', {}, undefined, 2000);
    requireThat(
      result.apiVersion === 15,
      'API_VERSION',
      'Incompatible daemon API. Update the CLI and host plugin together, then restart the daemon.',
    );
    return true;
  } catch (error) {
    signal?.throwIfAborted();
    if (['ENOENT', 'ECONNREFUSED'].includes((error as NodeJS.ErrnoException).code ?? ''))
      return false;
    throw error;
  } finally {
    signal?.removeEventListener('abort', abort);
    client?.socket.destroy();
  }
}
export async function ensureDaemon(
  dataDir: string,
  overrides: DaemonOverrides = {},
  signal?: AbortSignal,
): Promise<void> {
  if (await probe(dataDir, signal)) {
    requireThat(
      overrides.turnTimeoutMs === undefined,
      'DAEMON_RUNNING',
      'The daemon is already running. Stop it before starting with a different turn timeout.',
    );
    return;
  }
  await requireFreshStorage(dataDir);
  await mkdir(join(dataDir, 'run'), { recursive: true, mode: 0o700 });
  const deadline = performance.now() + 30000;
  let unlock: (() => void) | undefined;
  while (!unlock) {
    signal?.throwIfAborted();
    try {
      unlock = exclusiveLock(`${dataDir}.lifecycle.lock`);
    } catch (error) {
      if ((error as { code?: string }).code !== 'ALREADY_RUNNING') throw error;
      if (await probe(dataDir, signal)) {
        requireThat(
          overrides.turnTimeoutMs === undefined,
          'DAEMON_RUNNING',
          'Another daemon started first. Stop it before changing the turn timeout.',
        );
        return;
      }
      if (performance.now() >= deadline) throw error;
      await delay(100 + Math.random() * 100, undefined, { signal });
    }
  }
  try {
    await requireFreshStorage(dataDir);
    if (await probe(dataDir, signal)) {
      requireThat(
        overrides.turnTimeoutMs === undefined,
        'DAEMON_RUNNING',
        'Another daemon started first. Stop it before starting with a different turn timeout.',
      );
      return;
    }
    const daemonArgs =
      overrides.turnTimeoutMs === undefined
        ? []
        : ['--turn-timeout', `${overrides.turnTimeoutMs}ms`];
    // A stopping daemon removes its socket before draining requests and
    // disconnects. Do not spawn its replacement until ownership is released.
    for (;;) {
      signal?.throwIfAborted();
      try {
        exclusiveLock(join(dataDir, 'run', 'daemon-owner.lock'))();
        break;
      } catch (error) {
        if ((error as { code?: string }).code !== 'ALREADY_RUNNING') throw error;
        if (performance.now() >= deadline)
          throw new BassfishError(
            'DAEMON_START_FAILED',
            'The previous daemon did not release its ownership lock within 30 seconds. Inspect daemon status diagnostics.',
          );
        await delay(100, undefined, { signal });
      }
    }
    signal?.throwIfAborted();
    const logFd = openDaemonLog(dataDir);
    let child;
    try {
      child = spawn(process.execPath, entryArgs('daemon', 'run', ...daemonArgs), {
        cwd: packageRoot,
        detached: true,
        stdio: ['ignore', 'ignore', logFd],
        env: { ...process.env, BASSFISH_DATA_DIR: dataDir },
      });
    } finally {
      closeSync(logFd);
    }
    let failed = false;
    child.once('error', () => {
      failed = true;
    });
    child.once('exit', () => {
      failed = true;
    });
    child.unref();
    while (!(await probe(dataDir, signal))) {
      if (failed) {
        const { lastLifecycle, logPath } = daemonDiagnostics(dataDir);
        if (
          lastLifecycle &&
          lastLifecycle.pid === child.pid &&
          lastLifecycle.event === 'failed' &&
          typeof lastLifecycle.code === 'string'
        )
          throw new BassfishError(
            lastLifecycle.code,
            `${String(lastLifecycle.error ?? 'Daemon startup failed.')} Diagnostics: ${logPath}`,
          );
      }
      if (failed || performance.now() > deadline)
        throw new BassfishError(
          'DAEMON_START_FAILED',
          'Daemon startup failed. Run bassfish daemon status --json to locate persisted diagnostics.',
        );
      await delay(100, undefined, { signal });
    }
  } finally {
    unlock();
  }
}
