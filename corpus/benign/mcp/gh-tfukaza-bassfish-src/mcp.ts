import { CodexQueue } from './agents/codex-queue.js';
import { McpServer } from '@modelcontextprotocol/server';
import type {
  JSONRPCMessage,
  StandardSchemaWithJSON,
  Transport,
  TransportSendOptions,
} from '@modelcontextprotocol/server';
import { SUBSCRIPTION_ID_META_KEY } from '@modelcontextprotocol/server';
import { serveStdio, StdioServerTransport } from '@modelcontextprotocol/server/stdio';
import { BassfishError } from './domain.js';
import { realpath } from 'node:fs/promises';
import { isAbsolute } from 'node:path';
import { mcpDescriptions, mcpOutputSchemas, mcpSchemas } from './mcp-api.js';
import type { McpToolName } from './mcp-api.js';
import { presentMentionTask, presentNotifications, presentTask } from './mcp-presenters.js';
import { connectDaemon, ensureDaemon } from './daemon.js';
import type { RpcClient } from './ipc.js';
import {
  cancelTaskParams,
  getTaskParams,
  hasTasksCapability,
  taskAck,
  taskResult,
  tasksExtensionId,
  toolResult,
  updateTaskParams,
  wireTask,
  wireTaskNotification,
} from './tasks.js';
import { packageVersion } from './config.js';
import { formatDeliveryContext, type DeliveryBatch } from './notification-delivery.js';
import { z } from 'zod';
import {
  processAncestry,
  readOrCreateClaudeClientId,
  readOrCreateOpenCodeClientId,
} from './agents/claude-native.js';

const hostSessionRouteKey = '__bassfishHostSessionId';
const mcpInstructions =
  'Before acting, call getUpdates and inspect the latest relevant discussions and tickets. Check ticket dependencies and current owners to avoid duplicate work. Acquire an advisory file turn before editing, reread files after acquiring it, and release it when done. Use existing threads—especially Introductions—instead of creating duplicates. Process injected Bassfish notifications before drawing conclusions, and leave a handoff when work changes ownership.';
const hostSessionIdSchema = z.string().min(1).max(200);
function routedToolSchema(schema: z.ZodType): StandardSchemaWithJSON {
  const standard = schema['~standard'];
  return {
    '~standard': {
      ...standard,
      validate: value => {
        const raw =
          value && typeof value === 'object' && !Array.isArray(value)
            ? (value as Record<string, unknown>)
            : undefined;
        const route = raw?.[hostSessionRouteKey];
        const clean = raw ? { ...raw } : value;
        if (raw) delete (clean as Record<string, unknown>)[hostSessionRouteKey];
        const restoreRoute = (result: Awaited<ReturnType<typeof standard.validate>>) => {
          if (result.issues || route === undefined) return result;
          return {
            value: {
              ...(result.value as Record<string, unknown>),
              [hostSessionRouteKey]: route,
            },
          };
        };
        const result = standard.validate(clean);
        return result instanceof Promise ? result.then(restoreRoute) : restoreRoute(result);
      },
    },
  } as StandardSchemaWithJSON;
}
function routedHostSessionId(args: unknown): string | undefined {
  const value = (args as Record<string, unknown> | undefined)?.[hostSessionRouteKey];
  if (value === undefined) return undefined;
  const parsed = hostSessionIdSchema.safeParse(value);
  if (!parsed.success)
    throw new BassfishError('INVALID_ARGUMENT', 'The host session route is invalid.');
  return parsed.data;
}

async function within<T>(work: Promise<T>, timeoutMs: number): Promise<T> {
  let timer: NodeJS.Timeout | undefined;
  try {
    return await Promise.race([
      work,
      new Promise<never>((_resolve, reject) => {
        timer = setTimeout(
          () =>
            reject(
              new BassfishError(
                'BACKEND_UNAVAILABLE',
                'Bassfish notification delivery exceeded its hook deadline.',
              ),
            ),
          timeoutMs,
        );
        timer.unref();
      }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
}

export class TaskAwareStdioTransport implements Transport {
  onclose?: () => void;
  onerror?: (error: Error) => void;
  onmessage?: (message: JSONRPCMessage) => void;
  private readonly pending = new Map<string, Set<string>>();
  private readonly subscriptions = new Map<
    string,
    { taskIds: Set<string>; meta: Record<string, unknown> }
  >();
  private protocolVersion?: string;
  constructor(
    private readonly subscribe: (ids: string[]) => void,
    private readonly inner: Transport = new StdioServerTransport(),
  ) {}
  async start(): Promise<void> {
    this.inner.onclose = () => this.onclose?.();
    this.inner.onerror = error => this.onerror?.(error);
    this.inner.onmessage = message => {
      const raw = message as unknown as Record<string, unknown>;
      if (raw.method === 'notifications/cancelled') {
        const requestId = (raw.params as Record<string, unknown> | undefined)?.requestId;
        if (requestId !== undefined) {
          const key = String(requestId);
          this.pending.delete(key);
          this.subscriptions.delete(key);
          this.publishSubscriptions();
        }
      }
      if (raw.method === 'subscriptions/listen') {
        const clone = structuredClone(raw) as Record<string, unknown>;
        const params = clone.params as Record<string, unknown> | undefined;
        const notifications = params?.notifications as Record<string, unknown> | undefined;
        const ids = Array.isArray(notifications?.taskIds)
          ? (notifications.taskIds.filter(value => typeof value === 'string') as string[])
          : [];
        if (ids.length) {
          const meta = params?._meta as Record<string, unknown> | undefined;
          const envelope = meta?.['io.modelcontextprotocol/clientCapabilities']
            ? { clientCapabilities: meta['io.modelcontextprotocol/clientCapabilities'] }
            : undefined;
          if (this.protocolVersion !== '2026-07-28' || !hasTasksCapability(envelope, 'modern')) {
            void this.inner.send({
              jsonrpc: '2.0',
              id: raw.id as string,
              error: {
                code: -32021,
                message: 'Missing required client capability',
                data: { requiredCapabilities: { extensions: { [tasksExtensionId]: {} } } },
              },
            } as JSONRPCMessage);
            return;
          }
          this.pending.set(String(raw.id), new Set(ids));
          delete notifications!.taskIds;
          this.publishSubscriptions();
        }
        this.onmessage?.(clone as unknown as JSONRPCMessage);
        return;
      }
      this.onmessage?.(message);
    };
    await this.inner.start();
  }
  async close(): Promise<void> {
    this.pending.clear();
    this.subscriptions.clear();
    this.publishSubscriptions();
    await this.inner.close();
  }
  setProtocolVersion(version: string): void {
    this.protocolVersion = version;
    this.inner.setProtocolVersion?.(version);
  }
  setSupportedProtocolVersions(versions: string[]): void {
    this.inner.setSupportedProtocolVersions?.(versions);
  }
  async send(message: JSONRPCMessage, options?: TransportSendOptions): Promise<void> {
    const raw = structuredClone(message) as unknown as Record<string, unknown>;
    if (raw.method === 'notifications/subscriptions/acknowledged') {
      const params = raw.params as Record<string, unknown>;
      const meta = (params._meta ?? {}) as Record<string, unknown>;
      const subscriptionId = meta[SUBSCRIPTION_ID_META_KEY];
      const taskIds =
        subscriptionId === undefined ? undefined : this.pending.get(String(subscriptionId));
      if (taskIds?.size) {
        this.pending.delete(String(subscriptionId));
        this.subscriptions.set(String(subscriptionId), { taskIds, meta });
        this.publishSubscriptions();
      }
      const notifications = (params.notifications ??= {}) as Record<string, unknown>;
      if (taskIds?.size) notifications.taskIds = [...taskIds];
    }
    if (raw.method === 'notifications/tasks') {
      const params = raw.params as Record<string, unknown>;
      const taskId = String(params.taskId ?? '');
      for (const subscription of this.subscriptions.values())
        if (subscription.taskIds.has(taskId))
          await this.inner.send(
            {
              ...(raw as object),
              params: {
                ...params,
                _meta: { ...(params._meta as object | undefined), ...subscription.meta },
              },
            } as JSONRPCMessage,
            options,
          );
      return;
    }
    const result = raw.result as Record<string, unknown> | undefined;
    const structured = result?.structuredContent as Record<string, unknown> | undefined;
    if (structured?.__bassfishTask)
      raw.result = {
        ...wireTask(structured.__bassfishTask as Record<string, unknown>, 'task'),
        ...(result?._meta ? { _meta: result._meta } : {}),
      };
    await this.inner.send(raw as unknown as JSONRPCMessage, options);
  }
  private publishSubscriptions(): void {
    this.subscribe([
      ...new Set(
        [
          ...this.pending.values(),
          ...[...this.subscriptions.values()].map(value => value.taskIds),
        ].flatMap(value => [...value]),
      ),
    ]);
  }
}

/** Stdio adapter: MCP validation and transport around the shared Bassfish daemon. */
export async function runMcp(workspace: string, dataDir: string, name?: string): Promise<void> {
  let client: RpcClient | undefined;
  let connecting: Promise<RpcClient> | undefined;
  let heartbeat: NodeJS.Timeout | undefined;
  let stopped = false;
  let preferredName = name;
  let defaultHostSessionId: string | undefined;
  let reportedWakeStatus: string | undefined;
  let adapterWorkspace = workspace;
  const nativeClaude = process.env.BASSFISH_CLAUDE_NATIVE === '1';
  const nativeCodex = process.env.BASSFISH_CODEX_NATIVE === '1';
  const nativeOpenCode = process.env.BASSFISH_OPENCODE_NATIVE === '1';
  const deferredCodex = nativeCodex && !(name ?? process.env.BASSFISH_AGENT_NAME);
  if ([nativeClaude, nativeCodex, nativeOpenCode].filter(Boolean).length > 1)
    throw new BassfishError('INVALID_NATIVE_HOST', 'Only one native host may own an MCP adapter.');
  const nativeHost = nativeClaude
    ? ('claude' as const)
    : nativeCodex
      ? ('codex' as const)
      : nativeOpenCode
        ? ('opencode' as const)
        : undefined;
  async function connection(): Promise<RpcClient> {
    if (client && !client.socket.destroyed) return client;
    return (connecting ??= (async () => {
      const openedWorkspace = adapterWorkspace;
      await ensureDaemon(dataDir);
      const opened = await connectDaemon(dataDir);
      try {
        if (
          [
            process.env.BASSFISH_RUN_ID,
            process.env.BASSFISH_DELIVERY_TOKEN,
            process.env.BASSFISH_AGENT_HOST,
            process.env.BASSFISH_OPENCODE_DELIVERY_URL,
            process.env.BASSFISH_OPENCODE_DELIVERY_TOKEN,
          ].some(Boolean)
        ) {
          throw new BassfishError(
            'MANAGED_RUN_REMOVED',
            'The Bassfish-managed OpenCode runner was removed; install @bassfish/cli with `opencode plugin @bassfish/cli --global`.',
          );
        }
        let native: Record<string, unknown> | undefined;
        const configuredName = preferredName ?? process.env.BASSFISH_AGENT_NAME;
        if (nativeHost && !configuredName) {
          if (nativeHost === 'codex') native = { host: nativeHost };
          else {
            const clientId =
              nativeHost === 'claude'
                ? await readOrCreateClaudeClientId(process.env.BASSFISH_CLAUDE_PLUGIN_DATA ?? '')
                : await readOrCreateOpenCodeClientId(dataDir);
            native = {
              host: nativeHost,
              clientId,
              processAncestors: await processAncestry(),
            };
          }
        }
        const result = await opened.call<{ session: { name: string } | null }>('openSession', {
          workspace: openedWorkspace,
          name: configuredName,
          ...(native ? { native } : {}),
          ...(native && defaultHostSessionId ? { hostSessionId: defaultHostSessionId } : {}),
        });
        if (stopped) {
          await opened.call('closeSession');
          throw new BassfishError('CANCELLED', 'Adapter stopped during startup.');
        }
        if (result.session && !native) preferredName = result.session.name;
        client = opened;
        if (heartbeat) clearInterval(heartbeat);
        heartbeat = setInterval(() => {
          void opened.call('heartbeatSession').catch(() => {
            if (heartbeat) clearInterval(heartbeat);
            opened.socket.destroy();
          });
        }, 5000);
        heartbeat.unref();
        return opened;
      } catch (error) {
        opened.close();
        throw error;
      }
    })().finally(() => {
      connecting = undefined;
    }));
  }
  const codexQueue = nativeCodex
    ? new CodexQueue(
        {
          wait: async (sessionId, signal) =>
            (await connection()).call(
              'waitCodexWork',
              { sessionId, timeoutMs: 20000 },
              signal,
              25000,
            ),
          reserve: async sessionId =>
            (await connection()).call('reserveCodexDelivery', { sessionId }),
          transition: async (sessionId, batchToken, status, issue) =>
            (await connection()).call('codexDeliveryTransition', {
              sessionId,
              batchToken,
              status,
              ...(issue ? { issue } : {}),
            }),
        },
        () => adapterWorkspace,
      )
    : undefined;
  let parentTurnId: string | undefined;
  const taskRoutes = new Map<string, string | undefined>();
  let protocolServer: McpServer | undefined;
  const watchers = new Map<string, AbortController>();
  const watchTasks = (ids: string[]) => {
    const wanted = new Set(ids);
    for (const [taskId, watcher] of watchers)
      if (!wanted.has(taskId)) {
        watcher.abort();
        watchers.delete(taskId);
        taskRoutes.delete(taskId);
      }
    for (const taskId of ids)
      if (!watchers.has(taskId)) {
        const controller = new AbortController();
        watchers.set(taskId, controller);
        void (async () => {
          let after = 0;
          while (!controller.signal.aborted) {
            try {
              const rawTask = taskId.startsWith('work_')
                ? await (
                    await connection()
                  ).call<Record<string, unknown>>(
                    'waitWorkTask',
                    {
                      taskId,
                      updatedAfter: after,
                      timeoutMs: 20_000,
                      ...(taskRoutes.get(taskId) ? { hostSessionId: taskRoutes.get(taskId) } : {}),
                    },
                    controller.signal,
                  )
                : await (
                    await connection()
                  ).call<Record<string, unknown>>(
                    'waitTask',
                    {
                      taskId,
                      updatedAfter: after,
                      timeoutMs: 20_000,
                      ...(taskRoutes.get(taskId) ? { hostSessionId: taskRoutes.get(taskId) } : {}),
                    },
                    controller.signal,
                  );
              const task = taskId.startsWith('work_')
                ? presentMentionTask(rawTask)
                : presentTask(rawTask);
              const updated = Date.parse(String(task.lastUpdatedAt));
              if (updated > after) {
                after = updated;
                await protocolServer?.server.notification({
                  method: 'notifications/tasks',
                  params: wireTaskNotification(task),
                } as never);
              }
              if (['completed', 'failed', 'cancelled'].includes(String(task.status))) break;
            } catch (error) {
              if (
                !controller.signal.aborted &&
                error instanceof BassfishError &&
                error.code !== 'TASK_NOT_FOUND'
              )
                continue;
              break;
            }
          }
          watchers.delete(taskId);
        })();
      }
  };
  const taskTransport = new TaskAwareStdioTransport(watchTasks);
  // Codex starts plugin servers in the plugin cache. Its hooks supply the
  // session workspace after MCP initializes; an unbound native adapter has
  // no agent presence yet. Other adapters still register at startup.
  if (!deferredCodex) await connection();
  const transport = await serveStdio(
    ({ era }) => {
      const tasksEnabled = era === 'modern';
      const server = new McpServer(
        { name: 'bassfish', version: packageVersion },
        {
          instructions: mcpInstructions,
          capabilities: {
            tools: {},
            ...(tasksEnabled ? { extensions: { [tasksExtensionId]: {} } } : {}),
          } as never,
        },
      );
      protocolServer = server;
      if (tasksEnabled)
        server.server.setRequestHandler(
          'tasks/get',
          { params: getTaskParams, result: taskResult },
          async params => {
            if (params.taskId.startsWith('work_')) {
              const backend = await connection();
              const hostSessionId = taskRoutes.get(params.taskId);
              return wireTask(
                presentMentionTask(
                  await backend.call<Record<string, unknown>>('getWorkTask', {
                    taskId: params.taskId,
                    ...(hostSessionId ? { hostSessionId } : {}),
                  }),
                ),
                'complete',
              ) as never;
            }
            const backend = await connection();
            const hostSessionId = taskRoutes.get(params.taskId);
            return wireTask(
              presentTask(
                await backend.call<Record<string, unknown>>('getTask', {
                  taskId: params.taskId,
                  ...(hostSessionId ? { hostSessionId } : {}),
                }),
              ),
              'complete',
            ) as never;
          },
        );
      if (tasksEnabled)
        server.server.setRequestHandler(
          'tasks/cancel',
          { params: cancelTaskParams, result: taskAck },
          async params => {
            if (params.taskId.startsWith('work_')) {
              const backend = await connection();
              const hostSessionId = taskRoutes.get(params.taskId);
              await backend.call('cancelWorkTask', {
                taskId: params.taskId,
                ...(hostSessionId ? { hostSessionId } : {}),
              });
              return { resultType: 'complete' as const };
            }
            const backend = await connection();
            const hostSessionId = taskRoutes.get(params.taskId);
            await backend.call('cancelTask', {
              taskId: params.taskId,
              ...(hostSessionId ? { hostSessionId } : {}),
            });
            return { resultType: 'complete' as const };
          },
        );
      if (tasksEnabled)
        server.server.setRequestHandler(
          'tasks/update',
          { params: updateTaskParams, result: taskAck },
          async params => {
            if (params.taskId.startsWith('work_'))
              throw new BassfishError(
                'INVALID_TASK_STATE',
                'Bassfish mention tasks never request client input.',
              );
            const backend = await connection();
            const hostSessionId = taskRoutes.get(params.taskId);
            await backend.call('peekTask', {
              taskId: params.taskId,
              ...(hostSessionId ? { hostSessionId } : {}),
            });
            throw new BassfishError(
              'INVALID_TASK_STATE',
              'Bassfish turn tasks never request client input.',
            );
          },
        );
      for (const name of Object.keys(mcpSchemas) as McpToolName[]) {
        const inputSchema = routedToolSchema(mcpSchemas[name]);
        server.registerTool(
          name,
          {
            description: mcpDescriptions[name],
            inputSchema,
            outputSchema: mcpOutputSchemas[name],
            annotations: {
              readOnlyHint: [
                'bindHostSession',
                'getUpdates',
                'waitForWork',
                'findResources',
                'readResource',
              ].includes(name),
              destructiveHint: false,
              idempotentHint: [
                'bindHostSession',
                'getUpdates',
                'findResources',
                'readResource',
                'waitForWork',
              ].includes(name),
              openWorldHint: false,
            },
          },
          async (args, context) => {
            try {
              const hookDeadline = name === 'deliverHostNotifications' ? Date.now() + 3_000 : 0;
              const routedSessionId = routedHostSessionId(args);
              if (routedSessionId && nativeHost === 'opencode')
                defaultHostSessionId = routedSessionId;
              const publicArgs = { ...(args as Record<string, unknown>) };
              delete publicArgs[hostSessionRouteKey];
              if (routedSessionId && nativeHost !== 'opencode')
                throw new BassfishError(
                  'HOST_SESSION_UNAVAILABLE',
                  'Per-call host session routing is only available to the OpenCode plugin.',
                );
              const binding = name === 'bindHostSession' || name === 'deliverHostNotifications';
              if (deferredCodex && !binding && !defaultHostSessionId)
                throw new BassfishError(
                  'HOST_SESSION_REQUIRED',
                  'The host plugin must bind its current session before using Bassfish.',
                );
              if (nativeCodex && binding && publicArgs.workspace !== undefined) {
                const suppliedWorkspace = publicArgs.workspace as string;
                if (!isAbsolute(suppliedWorkspace))
                  throw new BassfishError(
                    'INVALID_ARGUMENT',
                    'The host session workspace must be an absolute path.',
                  );
                const hostWorkspace = await realpath(suppliedWorkspace);
                if (
                  (client || connecting || defaultHostSessionId) &&
                  hostWorkspace !== (await realpath(adapterWorkspace))
                )
                  throw new BassfishError(
                    'HOST_WORKSPACE_CHANGED',
                    'Start a new MCP adapter when changing the host session workspace.',
                  );
                adapterWorkspace = hostWorkspace;
              }
              const backend =
                hookDeadline > 0
                  ? await within(connection(), Math.max(1, hookDeadline - Date.now()))
                  : await connection();
              if (name === 'bindHostSession') {
                if (!nativeHost || nativeHost === 'opencode')
                  throw new BassfishError(
                    'HOST_SESSION_UNAVAILABLE',
                    'This adapter does not support default host session binding.',
                  );
                const sessionId = publicArgs.sessionId as string;
                const data = await backend.call('bindHostSession', { sessionId });
                defaultHostSessionId = sessionId;
                codexQueue?.bind(sessionId);
                return toolResult(data) as never;
              }
              if (name === 'deliverHostNotifications') {
                if (!nativeHost || nativeHost === 'opencode')
                  throw new BassfishError(
                    'HOST_SESSION_UNAVAILABLE',
                    'This adapter does not support notification delivery hooks.',
                  );
                const sessionId = publicArgs.sessionId as string;
                const phase = publicArgs.phase as 'prompt' | 'active' | 'idle' | 'paused';
                if (nativeCodex) {
                  if (phase === 'prompt') parentTurnId = publicArgs.turnId as string | undefined;
                  else if (parentTurnId && publicArgs.turnId && publicArgs.turnId !== parentTurnId)
                    return toolResult({}) as never;
                  if (phase === 'paused') codexQueue?.pause();
                }
                const batch = await backend.call<DeliveryBatch>(
                  'takeHostDelivery',
                  {
                    sessionId,
                    phase,
                    ...(nativeCodex ? { queueEnabled: codexQueue?.status === 'available' } : {}),
                  },
                  context.mcpReq.signal,
                  Math.max(1, hookDeadline - Date.now()),
                );
                defaultHostSessionId = sessionId;
                if (phase === 'prompt') codexQueue?.bind(sessionId);
                codexQueue?.observeHook(phase);
                if (
                  nativeCodex &&
                  (phase === 'paused' || (phase === 'idle' && codexQueue?.status === 'available'))
                )
                  return toolResult({}) as never;
                if (batch.count === 0) return toolResult({}) as never;
                const message = formatDeliveryContext(batch);
                if (phase === 'idle')
                  return toolResult({ decision: 'block', reason: message }) as never;
                const hookEventName =
                  phase === 'prompt'
                    ? 'UserPromptSubmit'
                    : nativeHost === 'claude'
                      ? 'PostToolBatch'
                      : 'PostToolUse';
                return toolResult({
                  hookSpecificOutput: { hookEventName, additionalContext: message },
                }) as never;
              }
              if (name === 'waitForWork') {
                if (!hasTasksCapability(context.mcpReq.envelope, era))
                  throw new BassfishError(
                    'TASKS_REQUIRED',
                    'waitForWork requires the MCP Tasks extension.',
                  );
                const pending = await backend.call<{
                  notifications: Record<string, unknown>[];
                  moreAvailable: boolean;
                }>(
                  'waitWork',
                  {
                    timeoutMs: 0,
                    ...(routedSessionId ? { hostSessionId: routedSessionId } : {}),
                  },
                  context.mcpReq.signal,
                );
                if (pending.notifications.length > 0)
                  return toolResult(presentNotifications(pending)) as never;
                const task = await backend.call<Record<string, unknown>>('createWorkTask', {
                  ...(routedSessionId ? { hostSessionId: routedSessionId } : {}),
                });
                const taskId = task.taskId;
                if (typeof taskId === 'string') taskRoutes.set(taskId, routedSessionId);
                return {
                  content: [],
                  structuredContent: { __bassfishTask: task },
                };
              }
              const taskCapable =
                name === 'acquireTurn' && hasTasksCapability(context.mcpReq.envelope, era);
              const data = await backend.call(
                'callMcpTool',
                {
                  name,
                  args: publicArgs,
                  taskCapable,
                  ...(routedSessionId ? { hostSessionId: routedSessionId } : {}),
                },
                context.mcpReq.signal,
                75_000,
              );
              if (name === 'setAgentName' && !nativeHost)
                preferredName = (data as { agentName: string }).agentName;
              if (data && typeof data === 'object' && 'task' in data) {
                const task = (data as { task: { taskId?: string } }).task;
                if (task.taskId) taskRoutes.set(task.taskId, routedSessionId);
                return {
                  content: [],
                  structuredContent: { __bassfishTask: task },
                };
              }
              if (name === 'getUpdates' && codexQueue) {
                const update = data as Record<string, unknown>;
                if (update.changed || reportedWakeStatus !== codexQueue.readiness) {
                  if (!update.changed)
                    Object.assign(update, {
                      changed: true,
                      mode: 'delta',
                      cursor: publicArgs.cursor,
                    });
                  update.nativeWake = codexQueue.readiness;
                  reportedWakeStatus = codexQueue.readiness;
                }
              }
              return toolResult(data) as never;
            } catch (error) {
              const failure =
                error instanceof BassfishError
                  ? error
                  : new BassfishError(
                      'BACKEND_UNAVAILABLE',
                      'Bassfish could not complete the request. No operation was retried.',
                    );
              if (
                name === 'deliverHostNotifications' &&
                [
                  'OUTCOME_UNKNOWN',
                  'CONNECTION_CLOSED',
                  'BACKEND_UNAVAILABLE',
                  'STORAGE_UNAVAILABLE',
                  'STORAGE_BUSY',
                  'API_VERSION',
                  'DAEMON_START_FAILED',
                  'CANCELLED',
                ].includes(failure.code)
              )
                return toolResult({ deferred: true }) as never;
              const output = { error: { code: failure.code, message: failure.message } };
              return {
                isError: true,
                content: [{ type: 'text' as const, text: `${failure.code}: ${failure.message}` }],
                structuredContent: output,
              };
            }
          },
        );
      }
      return server;
    },
    { transport: taskTransport },
  );
  const stop = async () => {
    if (stopped) return;
    stopped = true;
    if (heartbeat) clearInterval(heartbeat);
    codexQueue?.stop();
    for (const watcher of watchers.values()) watcher.abort();
    watchers.clear();
    try {
      if (client && !client.socket.destroyed) await client.call('closeSession');
    } finally {
      client?.close();
      await transport.close();
    }
  };
  const shutdown = () => {
    void stop().catch(() => {
      client?.socket.destroy();
    });
  };
  process.stdin.once('end', shutdown);
  process.once('SIGTERM', shutdown);
  process.once('SIGINT', shutdown);
  if (process.stdin.readableEnded) await stop();
}
