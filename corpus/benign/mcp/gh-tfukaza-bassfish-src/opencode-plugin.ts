import { clientDiagnosticSink } from './diagnostic-log.js';
import { setTimeout as delay } from 'node:timers/promises';
import type { Plugin as OpenCodeV1Plugin } from '@opencode-ai/plugin';
import type {
  Context as OpenCodeV2Context,
  Plugin as OpenCodeV2Plugin,
} from '@opencode/plugin/promise/plugin';
import { dataDirectory, socketPath } from './config.js';
import { mcpSchemas } from './mcp-api.js';
import { RpcClient } from './ipc.js';
import { processAncestry, readOrCreateOpenCodeClientId } from './agents/claude-native.js';
import { formatDeliveryContext, type DeliveryBatch } from './notification-delivery.js';
export type OpenCodeDeliveryBatch = DeliveryBatch;
interface OpenCodeClient {
  session: {
    get(options: unknown): Promise<unknown>;
    status(options: unknown): Promise<unknown>;
    prompt(options: unknown): Promise<unknown>;
  };
  app: {
    log(options: unknown): Promise<unknown>;
  };
}
export interface OpenCodePluginInput {
  client: OpenCodeClient;
  directory: string;
}
export type OpenCodePluginOptions = Record<string, never>;
interface WakeClient {
  call<T = unknown>(method: string, params?: unknown, signal?: AbortSignal): Promise<T>;
  close(): void;
}
export interface OpenCodePluginDependencies {
  connect?: (dataDir: string) => Promise<WakeClient>;
  clientId?: (dataDir: string) => Promise<string>;
  ancestry?: () => Promise<number[]>;
  delay?: (milliseconds: number, signal: AbortSignal) => Promise<void>;
}
const reservedEnvironment = {
  BASSFISH_OPENCODE_NATIVE: '1',
};
const hostSessionRouteKey = '__bassfishHostSessionId';
// Derived, never restated. A hand-written copy drifted from the MCP tool set at 0.6.0 and
// stopped matching getUpdates and readResource, which silently dropped per-call session routing
// from the very first call every agent is told to make.
export const bassfishToolNames: ReadonlySet<string> = new Set(Object.keys(mcpSchemas));
function record(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : undefined;
}
function responseData(value: unknown): unknown {
  const wrapper = record(value);
  if (!wrapper) return value;
  if (wrapper.error) throw new Error('OpenCode rejected a Bassfish plugin request.');
  return 'data' in wrapper ? wrapper.data : value;
}
function commandIsBassfish(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.every(item => typeof item === 'string') &&
    value.some(item => item === 'bassfish' || item.endsWith('/bassfish')) &&
    value.includes('mcp')
  );
}
function configuredDataDirectory(environment: Record<string, unknown>): string {
  const configured = environment.BASSFISH_DATA_DIR;
  return typeof configured === 'string' && configured !== '{env:BASSFISH_DATA_DIR}'
    ? configured
    : dataDirectory();
}
function isBassfishTool(value: unknown): value is string {
  if (typeof value !== 'string') return false;
  for (const name of bassfishToolNames)
    if (
      value === name ||
      value === `bassfish_${name}` ||
      value === `mcp__bassfish__${name}` ||
      value.endsWith(`__bassfish__${name}`)
    )
      return true;
  return false;
}
/** Adds native delivery metadata without replacing user-owned Bassfish MCP settings. */
export function configureOpenCodeMcp(
  config: Record<string, unknown>,
  directory: string,
  _rawOptions: unknown = {},
): string {
  const mcp = config.mcp === undefined ? {} : record(config.mcp);
  if (!mcp) throw new Error('OpenCode config.mcp must be an object for the Bassfish plugin.');
  const current = mcp.bassfish === undefined ? undefined : record(mcp.bassfish);
  if (mcp.bassfish !== undefined && !current)
    throw new Error('OpenCode mcp.bassfish must be a local MCP object.');
  if (current && (current.type !== 'local' || !commandIsBassfish(current.command))) {
    throw new Error(
      'The Bassfish OpenCode plugin cannot augment a non-local or non-Bassfish mcp.bassfish entry.',
    );
  }
  const environment = current?.environment === undefined ? {} : record(current.environment);
  if (!environment) throw new Error('OpenCode mcp.bassfish.environment must be an object.');
  const configuredEnvironment: Record<string, unknown> = {
    ...environment,
    ...reservedEnvironment,
  };
  delete configuredEnvironment.BASSFISH_WAKE_MODE;
  delete configuredEnvironment.BASSFISH_MAX_AUTO_WAKES_PER_HOUR;
  mcp.bassfish = {
    ...(current ?? {}),
    type: 'local',
    enabled: true,
    command: current?.command ?? ['bassfish', 'mcp', '--workspace', directory],
    environment: configuredEnvironment,
  };
  config.mcp = mcp;
  return configuredDataDirectory(configuredEnvironment);
}
interface OpenCodeV2McpEditor {
  get(name: string): unknown;
  set(name: string, config: unknown): void;
}
/** Current OpenCode V2 uses a transformed mcp.servers map and `disabled`. */
export function configureOpenCodeV2Mcp(editor: OpenCodeV2McpEditor, directory: string): string {
  const raw = editor.get('bassfish');
  const current = raw === undefined ? undefined : record(raw);
  if (raw !== undefined && !current)
    throw new Error('OpenCode V2 mcp.servers.bassfish must be a local MCP object.');
  if (current && (current.type !== 'local' || !commandIsBassfish(current.command)))
    throw new Error(
      'The Bassfish OpenCode plugin cannot augment a non-local or non-Bassfish V2 MCP entry.',
    );
  const environment = current?.environment === undefined ? {} : record(current.environment);
  if (!environment)
    throw new Error('OpenCode V2 mcp.servers.bassfish.environment must be an object.');
  const configuredEnvironment: Record<string, unknown> = {
    ...environment,
    ...reservedEnvironment,
  };
  delete configuredEnvironment.BASSFISH_WAKE_MODE;
  delete configuredEnvironment.BASSFISH_MAX_AUTO_WAKES_PER_HOUR;
  editor.set('bassfish', {
    ...(current ?? {}),
    type: 'local',
    disabled: false,
    command: current?.command ?? ['bassfish', 'mcp', '--workspace', directory],
    environment: configuredEnvironment,
  });
  return configuredDataDirectory(configuredEnvironment);
}
export function formatOpenCodeDeliveryPrompt(batch: OpenCodeDeliveryBatch): string {
  return formatDeliveryContext(batch);
}
export function createBassfishPlugin(dependencies: OpenCodePluginDependencies = {}) {
  const connect =
    dependencies.connect ??
    (async dir => RpcClient.connect(socketPath(dir), clientDiagnosticSink(dir)));
  const getClientId = dependencies.clientId ?? readOrCreateOpenCodeClientId;
  const getAncestry = dependencies.ancestry ?? processAncestry;
  const wait =
    dependencies.delay ??
    (async (milliseconds, signal) => {
      await delay(milliseconds, undefined, { signal });
    });
  return async function BassfishPlugin(input: OpenCodePluginInput, rawOptions: unknown = {}) {
    const abort = new AbortController();
    const parents = new Map<string, string | undefined>();
    const sessions = new Map<
      string,
      {
        idle: boolean;
        actionable: OpenCodeDeliveryBatch[];
        activity: OpenCodeDeliveryBatch[];
        injecting: boolean;
        controller: AbortController;
        client?: WakeClient;
      }
    >();
    let runtimeDataDir: string | undefined;
    let nativeIdentity:
      | Promise<{
          clientId: string;
          processAncestors: number[];
        }>
      | undefined;
    const log = async (level: 'info' | 'warn' | 'error', message: string, error?: unknown) => {
      await input.client.app
        .log({
          body: {
            service: 'bassfish',
            level,
            message,
            ...(error === undefined
              ? {}
              : { extra: { error: error instanceof Error ? error.message : String(error) } }),
          },
        })
        .catch(() => {});
    };
    const session = async (sessionID: string): Promise<Record<string, unknown> | undefined> => {
      const result = record(
        responseData(
          await input.client.session.get({
            path: { id: sessionID },
            query: { directory: input.directory },
          }),
        ),
      );
      if (result)
        parents.set(sessionID, typeof result.parentID === 'string' ? result.parentID : undefined);
      return result;
    };
    const rootSession = async (sessionID: string): Promise<string> => {
      let current = sessionID;
      const seen = new Set<string>();
      while (!seen.has(current)) {
        seen.add(current);
        if (!parents.has(current)) await session(current);
        const parent = parents.get(current);
        if (!parent) return current;
        current = parent;
      }
      return sessionID;
    };
    const statusIsIdle = async (sessionID: string): Promise<boolean> => {
      const statuses = record(
        responseData(await input.client.session.status({ query: { directory: input.directory } })),
      );
      return record(statuses?.[sessionID])?.type === 'idle';
    };
    const schedule = (sessionID: string) => {
      const state = sessions.get(sessionID);
      if (!state || state.injecting) return;
      const queue =
        state.actionable.length > 0
          ? 'actionable'
          : state.idle && state.activity.length > 0
            ? 'activity'
            : undefined;
      if (!queue) return;
      state.injecting = true;
      let attempted: OpenCodeDeliveryBatch | undefined;
      queueMicrotask(() => {
        void (async () => {
          if (state.idle) {
            const idle = await statusIsIdle(sessionID);
            if (!idle) {
              state.idle = false;
              if (queue === 'activity') return;
            }
          }
          attempted = state[queue].shift()!;
          const resume = state.idle;
          if (resume) state.idle = false;
          responseData(
            await input.client.session.prompt({
              path: { id: sessionID },
              query: { directory: input.directory },
              body: {
                ...(!resume ? { noReply: true } : {}),
                parts: [
                  { type: 'text', text: formatOpenCodeDeliveryPrompt(attempted), synthetic: true },
                ],
              },
            }),
          );
        })()
          .catch(error => {
            if (attempted) state[queue].unshift(attempted);
            void log('error', 'Bassfish notification injection failed.', error);
          })
          .finally(() => {
            state.injecting = false;
            schedule(sessionID);
          });
      });
    };
    const runPump = async (sessionID: string, dataDir: string) => {
      const state = sessions.get(sessionID);
      if (!state) return;
      const { clientId, processAncestors } = await (nativeIdentity ??= Promise.all([
        await getClientId(dataDir),
        getAncestry(),
      ]).then(([id, ancestors]) => ({ clientId: id, processAncestors: ancestors })));
      let backoff = 250;
      while (!abort.signal.aborted && !state.controller.signal.aborted) {
        try {
          state.client = await connect(dataDir);
          backoff = 250;
          while (!abort.signal.aborted && !state.controller.signal.aborted) {
            const batch: OpenCodeDeliveryBatch = await state.client.call<OpenCodeDeliveryBatch>(
              'waitNativeDelivery',
              {
                workspace: input.directory,
                host: 'opencode',
                clientId,
                processAncestors,
                sessionId: sessionID,
                timeoutMs: 20000,
              },
              state.controller.signal,
            );
            if (batch.count > 0 && batch.batchToken) {
              const queue = batch.kind === 'actionable' ? 'actionable' : 'activity';
              state[queue].push(batch);
              schedule(sessionID);
            }
          }
        } catch (error) {
          state.client?.close();
          state.client = undefined;
          if (abort.signal.aborted || state.controller.signal.aborted) return;
          await log('error', 'Bassfish native delivery connection stopped; reconnecting.', error);
          try {
            await wait(backoff, state.controller.signal);
          } catch {
            return;
          }
          backoff = Math.min(backoff * 2, 5000);
        }
      }
    };
    const ensureSession = (sessionID: string) => {
      let state = sessions.get(sessionID);
      if (!state) {
        state = {
          idle: false,
          actionable: [],
          activity: [],
          injecting: false,
          controller: new AbortController(),
        };
        sessions.set(sessionID, state);
        if (runtimeDataDir) void runPump(sessionID, runtimeDataDir);
      }
      return state;
    };
    const closeSession = async (sessionID: string) => {
      const state = sessions.get(sessionID);
      if (!state) return;
      state.controller.abort();
      state.client?.close();
      sessions.delete(sessionID);
      if (!runtimeDataDir) return;
      try {
        const { clientId, processAncestors } = await nativeIdentity!;
        const client = await connect(runtimeDataDir);
        try {
          await client.call('closeNativeHostSession', {
            workspace: input.directory,
            host: 'opencode',
            clientId,
            processAncestors,
            sessionId: sessionID,
          });
        } finally {
          client.close();
        }
      } catch (error) {
        if (!abort.signal.aborted)
          await log('error', 'Bassfish OpenCode session cleanup failed.', error);
      }
    };
    return {
      config: async (config: Record<string, unknown>) => {
        runtimeDataDir = configureOpenCodeMcp(config, input.directory, rawOptions);
        nativeIdentity = Promise.all([await getClientId(runtimeDataDir), getAncestry()]).then(
          ([clientId, processAncestors]) => ({ clientId, processAncestors }),
        );
        for (const sessionID of sessions.keys()) void runPump(sessionID, runtimeDataDir);
      },
      'chat.message': async (
        hookInput: Record<string, unknown>,
        hookOutput: Record<string, unknown>,
      ) => {
        const sessionID = hookInput.sessionID;
        const parts = Array.isArray(hookOutput.parts) ? hookOutput.parts : [];
        if (typeof sessionID === 'string' && parts.some(part => record(part)?.synthetic !== true)) {
          const root = await rootSession(sessionID);
          ensureSession(root).idle = false;
        }
      },
      'tool.execute.before': async (
        hookInput: Record<string, unknown>,
        hookOutput: Record<string, unknown>,
      ) => {
        if (!isBassfishTool(hookInput.tool)) return;
        const sessionID = hookInput.sessionID;
        if (typeof sessionID !== 'string')
          throw new Error('OpenCode did not provide a session ID for a Bassfish tool call.');
        const root = await rootSession(sessionID);
        ensureSession(root);
        const args = record(hookOutput.args) ?? {};
        args[hostSessionRouteKey] = root;
        hookOutput.args = args;
      },
      event: async ({ event }: { event: unknown }) => {
        const value = record(event);
        const properties = record(value?.properties);
        const info = record(properties?.info);
        const sessionID =
          typeof properties?.sessionID === 'string'
            ? properties.sessionID
            : typeof info?.id === 'string'
              ? info.id
              : undefined;
        if (sessionID && (value?.type === 'session.created' || value?.type === 'session.updated'))
          parents.set(sessionID, typeof info?.parentID === 'string' ? info.parentID : undefined);
        if (!sessionID) return;
        if (value?.type === 'session.deleted') {
          if (!parents.get(sessionID)) await closeSession(sessionID);
          parents.delete(sessionID);
          return;
        }
        const state = sessions.get(sessionID);
        if (!state) return;
        if (value?.type === 'session.idle') state.idle = true;
        else if (value?.type === 'session.status')
          state.idle = record(properties?.status)?.type === 'idle';
        else return;
        schedule(sessionID);
      },
      dispose: async () => {
        abort.abort();
        for (const state of sessions.values()) {
          state.controller.abort();
          state.client?.close();
        }
        sessions.clear();
      },
    };
  };
}
export const BassfishPlugin = createBassfishPlugin();
/**
 * OpenCode V2 adapter. It translates V2 domains into the stable V1 hooks so
 * identity routing and delivery semantics have one implementation.
 */
export const BassfishV2Plugin: OpenCodeV2Plugin = {
  id: 'bassfish',
  async setup(context: OpenCodeV2Context) {
    const abort = new AbortController();
    const statuses: Record<
      string,
      {
        type: string;
      }
    > = {};
    let runtimeDataDir = dataDirectory();
    const mcpRegistration = await context.mcp.transform(editor => {
      runtimeDataDir = configureOpenCodeV2Mcp(editor, context.location.directory);
    });
    const hooks = await BassfishPlugin({
      directory: context.location.directory,
      client: {
        session: {
          get: async options => {
            const id = record(record(options)?.path)?.id;
            if (typeof id !== 'string') throw new Error('Missing OpenCode V2 session ID.');
            return await context.session.get({ sessionID: id });
          },
          status: async () => statuses,
          prompt: async options => {
            const input = record(options);
            const id = record(input?.path)?.id;
            const body = record(input?.body);
            const parts = Array.isArray(body?.parts) ? body.parts : [];
            const text = parts
              .map(part => record(part)?.text)
              .filter((value): value is string => typeof value === 'string')
              .join('\n');
            if (typeof id !== 'string' || !text)
              throw new Error('Invalid Bassfish delivery for OpenCode V2.');
            const active = body?.noReply === true;
            return await context.session.synthetic({
              sessionID: id,
              text,
              description: 'Bassfish collaboration notification',
              metadata: { bassfish: true },
              delivery: active ? 'steer' : 'queue',
              resume: !active,
            });
          },
        },
        app: { log: async () => ({}) },
      },
    });
    await hooks.config?.({
      mcp: {
        bassfish: {
          type: 'local',
          command: ['bassfish', 'mcp', '--workspace', context.location.directory],
          environment: {
            BASSFISH_DATA_DIR: runtimeDataDir,
            ...reservedEnvironment,
          },
        },
      },
    });
    const toolRegistration = await context.tool.hook('execute.before', async event => {
      const output: Record<string, unknown> = { args: record(event.input) ?? {} };
      await hooks['tool.execute.before']?.(
        { sessionID: event.sessionID, tool: event.tool },
        output,
      );
      event.input = output.args;
    });
    const events = context.event.subscribe({ signal: abort.signal });
    const eventLoop = (async () => {
      for await (const event of events) {
        const value = event as unknown as Record<string, unknown>;
        const data = record(value.data);
        const sessionID = data?.sessionID;
        if (typeof sessionID !== 'string') continue;
        const eventData = data!;
        if (value.type === 'session.created')
          await hooks.event?.({
            event: {
              type: 'session.created',
              properties: {
                info: {
                  id: sessionID,
                  ...(eventData.parentID ? { parentID: eventData.parentID } : {}),
                },
              },
            },
          });
        else if (value.type === 'session.deleted')
          await hooks.event?.({
            event: { type: 'session.deleted', properties: { sessionID } },
          });
        else if (value.type === 'session.idle') {
          statuses[sessionID] = { type: 'idle' };
          await hooks.event?.({ event: { type: 'session.idle', properties: { sessionID } } });
        } else if (value.type === 'session.status') {
          const status = record(eventData.status);
          statuses[sessionID] = { type: String(status?.type ?? 'busy') };
          await hooks.event?.({
            event: { type: 'session.status', properties: { sessionID, status } },
          });
        } else if (value.type === 'session.execution.started') {
          statuses[sessionID] = { type: 'busy' };
          await hooks['chat.message']?.(
            { sessionID },
            { parts: [{ type: 'text', text: 'OpenCode V2 session activity' }] },
          );
        }
      }
    })().catch(error => {
      if (!abort.signal.aborted) console.error('Bassfish OpenCode V2 event stream failed.', error);
    });
    return async () => {
      abort.abort();
      await eventLoop;
      await toolRegistration.dispose();
      await mcpRegistration.dispose();
      await hooks.dispose?.();
    };
  },
};
const plugin: {
  id: string;
  server: OpenCodeV1Plugin;
  setup: OpenCodeV2Plugin['setup'];
} = {
  id: 'bassfish',
  server: BassfishPlugin as OpenCodeV1Plugin,
  setup: BassfishV2Plugin.setup,
};
export default plugin;
