import { diagnosticEvent, diagnosticHash } from './diagnostic-events.js';
import type { DiagnosticSink } from './diagnostic-events.js';
import { mapAsync, filterAsync } from './async.js';
import { copy } from './storage/rows.js';
import { randomUUID } from 'node:crypto';
import { setTimeout as delay } from 'node:timers/promises';
import { BassfishError, activeStates, increment, prepareMutation, requireThat } from './domain.js';
import type {
  Actor,
  AgentHost,
  Clock,
  ContentStore,
  ControlState,
  ControlStore,
  DurableTask,
  WorkTask,
  TurnRequest,
  Instance,
  Mutation,
  MutationResult,
  ContentTurnRequest,
  FileTurnRequest,
  FileTarget,
  NotificationIntent,
  NotificationReason,
  MutationContext,
  ResourceType,
  StorageResult,
  Thread,
  ThreadMutation,
  Ticket,
  TicketMutation,
  WriteOperation,
} from './domain.js';
import { KeyedMutex } from './runtime.js';
import { adminSchemas } from './admin-api.js';
import type { AdminToolName } from './admin-api.js';
import { nameSchema } from './contracts.js';
import { outline } from './markdown.js';
import { fileSetsOverlap, resolveFileTargets } from './files.js';
import {
  normalizeDependencies,
  prepareTicket,
  ticketStatuses,
  validateTicketGraph,
} from './ticket.js';
import { exportProject as writeProjectExport } from './export.js';
import { RE2 } from 're2-wasm';
import { selectGeneratedAgentName } from './agent-names.js';
import { mcpSchemas } from './mcp-api.js';
import type { McpToolName } from './mcp-api.js';
import { presentClaim, presentTurnStatus } from './mcp-presenters.js';
import {
  finishRequest,
  materializeRequestOffer,
  pendingFor,
  promoteFileRequests,
  promoteRequests,
} from './service/turn-state.js';
import {
  compare,
  decodeCursor,
  describeTicket,
  describeTickets,
  encodeCursor,
  sortThreads,
} from './service/resources.js';
import {
  isWorkNotification,
  notificationPriority,
  presentNotification,
  WakeSignals,
} from './service/notifications.js';
import { dispatchAdmin } from './service/admin-dispatch.js';
import { dispatchMcp } from './service/mcp-dispatch.js';
import { Inbox } from './service/inbox.js';
import { AgentUpdates } from './service/updates.js';
import { ResourceReads } from './service/reads.js';
export interface Limits {
  offerMs: number;
  turnTimeoutMs: number;
  reconnectMs: number;
  instanceMs: number;
  queueMs: number;
  retentionMs: number;
  waitMs: number;
}
export const defaultLimits: Limits = {
  offerMs: 30000,
  turnTimeoutMs: 60000,
  reconnectMs: 30000,
  instanceMs: 20000,
  queueMs: 3600000,
  retentionMs: 3600000,
  waitMs: 20000,
};
const deliveryLeaseMs = 30000;

const uid = () => randomUUID();
const iso = (ms: number) => new Date(ms).toISOString();
const followKey = (projectId: string, threadId: string, identityId: string) =>
  `${projectId}:${threadId}:${identityId}`;
const hostSessionKey = (projectId: string, host: AgentHost, sessionId: string) =>
  `${projectId}:${host}:${sessionId}`;
const threadMutationKinds = [
  'appendMessage',
  'renameThread',
  'setThreadDescription',
  'archiveThread',
  'activateThread',
  'deleteThread',
  'retractMessage',
  'reinstateMessage',
];
const ticketMutationKinds = [
  'updateTicket',
  'replaceTicketBody',
  'appendTicketBody',
  'patchTicketBody',
];
/** Application service: all coordination is persisted by ControlStore; all content uses ContentStore. */
export class Bassfish {
  readonly inbox = new Inbox(this);
  readonly updates = new AgentUpdates(this);
  readonly reads = new ResourceReads(this);
  readonly epoch = uid();
  diagnostics?: DiagnosticSink;
  readonly limits: Limits;
  private readonly writers = new KeyedMutex();
  private readonly committingTurns = new Set<string>();
  private readonly taskAcquisitions = new KeyedMutex();
  private readonly wakeSignals = new WakeSignals();
  constructor(
    readonly control: ControlStore,
    readonly content: ContentStore,
    readonly clock: Clock,
    limits: Partial<Limits> = {},
    private readonly dataDir?: string,
    private readonly selectAgentName: (
      usedNames: Iterable<string>,
    ) => string | undefined = selectGeneratedAgentName,
  ) {
    this.limits = { ...defaultLimits, ...limits };
  }
  async initialize(): Promise<void> {
    const now = this.clock.now();
    await this.control.update(async state => {
      for (const instance of await state.all('instances')) {
        if (instance.active) {
          const details = {
            epoch: this.epoch,
            instanceId: instance.id,
            projectId: instance.projectId,
            reason: 'daemon_restart',
          };
          this.control.afterCommit(() =>
            diagnosticEvent('session.disconnected', details, this.diagnostics),
          );
        }
        instance.active = false;
      }
      for (const batch of await state.all('notificationBatches')) {
        if (batch.status === 'submitting' || batch.status === 'reserved') {
          batch.status = 'uncertain';
          batch.issue =
            'Delivery interrupted by daemon restart; inspect this batch at the next checkpoint.';
        }
      }
      for (const request of await state.all('requests')) {
        if (request.resourceType === 'files') {
          if (activeStates.includes(request.state))
            await this.finish(request, 'EXPIRED', state, 'daemon_restart');
        } else {
          if (request.state === 'QUEUED' || request.state === 'READY')
            request.reconnectUntil = Math.min(request.queueUntil, now + this.limits.reconnectMs);
          if (request.state === 'READY') request.state = 'QUEUED';
          if (request.state === 'OFFERED' || request.state === 'CLAIMED')
            await this.finish(request, 'EXPIRED', state, 'daemon_restart');
        }
      }
    });
  }
  async open(
    commonDir: string,
    preferredName?: string,
    native?: {
      host: AgentHost;
    },
    workspace = commonDir,
    hostSessionId?: string,
    _initializeContent = true,
  ): Promise<{
    agentHandle: string;
    session: unknown;
  }> {
    if (preferredName) nameSchema.parse(preferredName);
    const project = await this.control.update(async state => {
      let project = (await state.all('projects')).find(p => p.commonDir === commonDir);
      if (!project) {
        project = { id: `p_${uid().replaceAll('-', '')}`, commonDir };
        await state.set('projects', project.id, project);
      }
      return project;
    });
    await this.content.ensureProject(project.id);
    await this.sweep();
    const handle = uid();
    await this.control.update(async state => {
      const key =
        native && hostSessionId
          ? hostSessionKey(project.id, native.host, hostSessionId)
          : undefined;
      let binding = key ? await state.get('hostSessionBindings', key) : undefined;
      let identity = binding ? await state.get('identities', binding.identityId) : undefined;
      requireThat(
        !binding || identity,
        'SESSION_BINDING_INVALID',
        'The host session binding is invalid.',
      );
      if (!identity) {
        const name =
          preferredName ??
          this.selectAgentName(
            (await state.all('identities'))
              .filter(candidate => candidate.projectId === project.id)
              .map(candidate => candidate.name),
          );
        requireThat(
          name,
          'NAME_POOL_EXHAUSTED',
          'All generated agent names are registered in this repository; provide an explicit name.',
        );
        identity = (await state.all('identities')).find(
          candidate =>
            candidate.projectId === project.id &&
            candidate.name.toLowerCase() === name.toLowerCase(),
        );
        if (identity) {
          const reserved = (await state.all('hostSessionBindings')).some(
            candidate =>
              candidate.projectId === project.id && candidate.identityId === identity!.id,
          );
          requireThat(
            !reserved,
            'NAME_BOUND_TO_SESSION',
            'This name belongs to another host session.',
          );
        } else {
          identity = { id: uid(), projectId: project.id, name };
          await state.set('identities', identity.id, identity);
        }
      }
      if (!binding)
        requireThat(
          !(await state.all('instances')).some(i => i.identityId === identity.id && i.active),
          'NAME_IN_USE',
          'This identity has a live adapter instance.',
        );
      if (key && native && hostSessionId && !binding) {
        const now = this.clock.now();
        binding = {
          projectId: project.id,
          identityId: identity.id,
          host: native.host,
          sessionId: hostSessionId,
          wakeKey: uid(),
          createdAt: now,
          updatedAt: now,
        };
        await state.set('hostSessionBindings', key, binding);
      } else if (
        binding &&
        !(await state.all('instances')).some(i => i.identityId === identity.id && i.active)
      ) {
        binding.wakeKey = uid();
        binding.updatedAt = this.clock.now();
      }
      const instance: Instance = {
        id: uid(),
        projectId: project.id,
        identityId: identity.id,
        handle,
        epoch: this.epoch,
        active: true,
        lastSeen: this.clock.now(),
        workspace,
        ...(native
          ? {
              host: native.host,
              ...(hostSessionId ? { hostSessionId } : {}),
            }
          : {}),
      };
      await state.set('instances', instance.id, instance);
      this.control.afterCommit(() =>
        diagnosticEvent(
          'session.connected',
          {
            epoch: this.epoch,
            instanceId: instance.id,
            projectId: instance.projectId,
            identityId: instance.identityId,
            host: instance.host,
            hostSessionHash: instance.hostSessionId
              ? diagnosticHash(instance.hostSessionId)
              : undefined,
          },
          this.diagnostics,
        ),
      );
      await this.rebind(state, instance);
      await this.promote(state);
    });
    return { agentHandle: handle, session: await this.info(handle) };
  }
  async actor(state: ControlState, handle: string): Promise<Actor> {
    const instance = (await state.all('instances')).find(
      i => i.handle === handle && i.active && i.epoch === this.epoch,
    );
    requireThat(
      instance,
      'SESSION_EXPIRED',
      'Open a new Bassfish instance; this handle is no longer current.',
    );
    const identity = (await state.get('identities', instance.identityId))!;
    return {
      projectId: instance.projectId,
      instanceId: instance.id,
      identityId: identity.id,
      name: identity.name,
    };
  }
  async ready(state: ControlState, projectId: string): Promise<void> {
    requireThat(await state.get('projects', projectId), 'NOT_FOUND', 'Project not found.');
  }
  private async creationAllowed(state: ControlState, projectId: string): Promise<void> {
    await this.ready(state, projectId);
  }
  private async finish(
    request: TurnRequest,
    state: 'EXPIRED' | 'CANCELLED' | 'RELEASED' | 'FAILED' | 'COMMITTED',
    control?: ControlState,
    reason?: string,
  ): Promise<void> {
    request.terminalReason =
      reason ??
      {
        EXPIRED: 'deadline_elapsed',
        CANCELLED: 'cancelled',
        RELEASED: 'released_by_owner',
        FAILED: 'operation_failed',
        COMMITTED: 'committed',
      }[state];
    await finishRequest(request, state, this.clock.now(), this.limits.retentionMs, control);
    if (state === 'EXPIRED') {
      const details = {
        epoch: this.epoch,
        instanceId: request.instanceId,
        projectId: request.projectId,
        requestId: request.id,
        tokenHash: request.turnId ? diagnosticHash(request.turnId) : undefined,
        resourceType: request.resourceType,
        reason: request.terminalReason,
      };
      this.control.afterCommit(() =>
        diagnosticEvent('reservation.expired', details, this.diagnostics),
      );
    }
  }
  private async disconnectIn(
    state: ControlState,
    instance: Instance,
    clean: boolean,
    reason = clean ? 'explicit_close' : 'socket_lost',
  ): Promise<void> {
    const wasActive = instance.active;
    const lostReservations = (await state.all('requests')).filter(
      r => r.instanceId === instance.id && activeStates.includes(r.state),
    ).length;
    const details = {
      epoch: this.epoch,
      instanceId: instance.id,
      projectId: instance.projectId,
      identityId: instance.identityId,
      host: instance.host,
      hostSessionHash: instance.hostSessionId ? diagnosticHash(instance.hostSessionId) : undefined,
      reason,
      heartbeatAgeMs: this.clock.now() - instance.lastSeen,
      instanceTimeoutMs: this.limits.instanceMs,
      affectedReservationCount: lostReservations,
    };
    if (wasActive)
      this.control.afterCommit(() =>
        diagnosticEvent('session.disconnected', details, this.diagnostics),
      );
    instance.active = false;
    for (const request of (await state.all('requests')).filter(r => r.instanceId === instance.id)) {
      if (request.resourceType === 'files') {
        if (activeStates.includes(request.state))
          await this.finish(
            request,
            clean ? 'CANCELLED' : 'EXPIRED',
            state,
            clean ? 'session_closed' : 'session_lost',
          );
        continue;
      }
      if (request.turnId && this.committingTurns.has(request.turnId)) continue;
      if (request.state === 'QUEUED') {
        if (clean) await this.finish(request, 'CANCELLED', state);
        else
          request.reconnectUntil = Math.min(
            request.queueUntil,
            this.clock.now() + this.limits.reconnectMs,
          );
      }
      if (request.state === 'READY') {
        if (clean) await this.finish(request, 'CANCELLED', state);
        else {
          request.state = 'QUEUED';
          request.updatedAt = this.clock.now();
          request.reconnectUntil = Math.min(
            request.queueUntil,
            this.clock.now() + this.limits.reconnectMs,
          );
        }
      }
      if (request.state === 'CLAIMED' || request.state === 'OFFERED')
        await this.finish(request, clean ? 'RELEASED' : 'EXPIRED', state);
    }
  }
  async disconnect(handle: string, clean = true, reason?: string): Promise<void> {
    await this.control.update(async state => {
      const instance = (await state.all('instances')).find(
        i => i.handle === handle && i.epoch === this.epoch,
      );
      if (instance) await this.disconnectIn(state, instance, clean, reason);
      await this.promote(state);
    });
    this.updates.close(handle);
    this.reads.close(handle);
  }
  async heartbeat(handle: string): Promise<void> {
    await this.sweep();
    await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      const instance = (await state.get('instances', actor.instanceId))!;
      const now = this.clock.now();
      const details = {
        instanceId: instance.id,
        projectId: instance.projectId,
        previousHeartbeatAgeMs: now - instance.lastSeen,
        acceptedAt: Date.now(),
      };
      instance.lastSeen = now;
      this.control.afterCommit(() =>
        diagnosticEvent('session.heartbeat', details, this.diagnostics),
      );
    });
  }
  async sweep(): Promise<void> {
    if (this.control.inTransaction()) return;
    const now = this.clock.now();
    const wall = this.clock.wallNow();
    const clockChanged = this.clock.discontinuity();
    await this.control.update(async state => {
      const discontinuity =
        clockChanged ||
        (state.wallClockHighWaterMs > 0 && wall + 2000 < state.wallClockHighWaterMs);
      state.wallClockHighWaterMs = Math.max(state.wallClockHighWaterMs, wall);
      for (const instance of await state.all('instances'))
        if (instance.active && now - instance.lastSeen >= this.limits.instanceMs)
          await this.disconnectIn(state, instance, false, 'heartbeat_expired');
      for (const request of await state.all('requests')) {
        if (request.turnId && this.committingTurns.has(request.turnId)) continue;
        const contentPaused = false;
        if (
          !contentPaused &&
          (request.state === 'QUEUED' || request.state === 'READY') &&
          (now >= request.queueUntil ||
            (request.reconnectUntil !== undefined && now >= request.reconnectUntil))
        )
          await this.finish(request, 'EXPIRED', state);
        if (!contentPaused && request.state === 'READY' && discontinuity)
          await this.finish(request, 'EXPIRED', state);
        if (
          !contentPaused &&
          request.state === 'OFFERED' &&
          (discontinuity || now >= request.claimBy!)
        )
          await this.finish(request, 'EXPIRED', state);
        if (
          !contentPaused &&
          request.resourceType !== 'files' &&
          request.state === 'CLAIMED' &&
          (discontinuity || now >= request.expiresAt!)
        )
          await this.finish(request, 'EXPIRED', state);
        if (request.finishedAt !== undefined && now - request.finishedAt >= this.limits.retentionMs)
          await state.remove('requests', request.id);
      }
      for (const task of await state.all('tasks'))
        if (now >= task.discardAt) await state.remove('tasks', task.id);
      for (const task of await state.all('workTasks'))
        if (now >= task.discardAt) await state.remove('workTasks', task.id);
      for (const batch of await state.all('notificationBatches'))
        if (batch.finishedAt !== undefined && now - batch.finishedAt >= this.limits.retentionMs)
          await state.remove('notificationBatches', batch.id);
      await this.promote(state);
    });
  }
  private async promote(state: ControlState): Promise<void> {
    await promoteRequests(state, this.clock.now(), this.limits.offerMs, uid);
    if (state.wallClockHighWaterMs > 0 && this.clock.wallNow() + 2000 < state.wallClockHighWaterMs)
      for (const request of await state.all('requests'))
        if (request.state === 'READY' || request.state === 'OFFERED')
          await this.finish(request, 'EXPIRED', state, 'clock_discontinuity');
  }
  private async promoteFiles(state: ControlState): Promise<void> {
    await promoteFileRequests(state, this.clock.now(), this.limits.offerMs, uid);
  }
  async requestFileTurn(
    handle: string,
    targets: FileTarget[],
    deliveryMode: 'ticket' | 'task' = 'ticket',
  ): Promise<Record<string, unknown>> {
    await this.sweep();
    const workspace = await this.control.view(
      async state =>
        (await state.get('instances', (await this.actor(state, handle)).instanceId))!.workspace,
    );
    const paths = await resolveFileTargets(workspace, targets);
    await this.sweep();
    const id = await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      requireThat(
        !(await pendingFor(state, actor.instanceId)).some(
          request => request.resourceType === 'files',
        ),
        'TURN_REQUEST_EXISTS',
        'This session already has a pending or held file set. Release it before acquiring another.',
      );
      state.fileQueueSequence = increment(state.fileQueueSequence);
      const now = this.clock.now();
      const request: FileTurnRequest = {
        id: uid(),
        projectId: actor.projectId,
        identityId: actor.identityId,
        instanceId: actor.instanceId,
        resourceType: 'files',
        paths,
        sequence: state.fileQueueSequence,
        state: 'QUEUED',
        createdAt: now,
        updatedAt: now,
        queueUntil: now + this.limits.queueMs,
        deliveryMode,
      };
      await state.set('requests', request.id, request);
      if (deliveryMode === 'task')
        await state.set('tasks', request.id, {
          id: request.id,
          projectId: actor.projectId,
          identityId: actor.identityId,
          requestId: request.id,
          status: 'working',
          statusMessage: 'Waiting for the file set.',
          createdAt: now,
          updatedAt: now,
          discardAt: request.queueUntil,
        });
      await this.promoteFiles(state);
      if (deliveryMode === 'task' && request.state === 'READY') {
        await this.materializeOffer(state, request);
        await state.remove('tasks', request.id);
        request.deliveryMode = 'ticket';
      }
      return request.id;
    });
    return await this.status(handle, id);
  }
  private fileClaim(request: FileTurnRequest): Record<string, unknown> {
    return {
      state: 'claimed',
      requestId: request.id,
      target: { type: 'files', paths: request.paths },
      turn: { id: request.turnId },
      lifetime: 'session',
    };
  }
  private async claimedFiles(
    state: ControlState,
    handle: string,
    turnToken: string,
  ): Promise<FileTurnRequest> {
    const actor = await this.actor(state, handle);
    const request = (await state.all('requests')).find(value => value.turnId === turnToken);
    requireThat(
      request &&
        request.projectId === actor.projectId &&
        request.instanceId === actor.instanceId &&
        request.identityId === actor.identityId,
      'NOT_TURN_OWNER',
      'The file turn is not bound to this session.',
    );
    requireThat(
      request.resourceType === 'files',
      'RESOURCE_TYPE_MISMATCH',
      'A file turn is required.',
    );
    requireThat(
      request.state === 'CLAIMED',
      'STALE_TURN',
      'This file turn is no longer held. Acquire a new set and reread its files before editing.',
    );
    return request;
  }
  private async claimFiles(handle: string, offerId: string): Promise<Record<string, unknown>> {
    return await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      const request = (await state.all('requests')).find(value => value.offerId === offerId);
      requireThat(
        request &&
          request.resourceType === 'files' &&
          request.instanceId === actor.instanceId &&
          request.projectId === actor.projectId,
        'NOT_TURN_OWNER',
        'The file offer is not bound to this session.',
      );
      requireThat(
        request.state !== 'EXPIRED' && this.clock.now() < request.claimBy!,
        'OFFER_EXPIRED',
        'The offer claim window has elapsed.',
      );
      requireThat(
        request.state === 'OFFERED',
        'OFFER_UNAVAILABLE',
        'The file offer is no longer available.',
      );
      request.state = 'CLAIMED';
      request.turnId = uid();
      request.updatedAt = this.clock.now();
      return this.fileClaim(request);
    });
  }
  async releaseFiles(
    handle: string,
    turnToken: string,
  ): Promise<{
    released: true;
  }> {
    await this.sweep();
    return await this.control.update(async state => {
      await this.finish(await this.claimedFiles(state, handle, turnToken), 'RELEASED', state);
      await this.promoteFiles(state);
      return { released: true };
    });
  }
  private async materializeOffer(state: ControlState, request: TurnRequest): Promise<void> {
    await materializeRequestOffer(state, request, this.clock.now(), this.limits.offerMs, uid);
  }
  private async rebind(state: ControlState, instance: Instance): Promise<void> {
    const request = (await state.all('requests'))
      .filter(
        candidate =>
          candidate.resourceType !== 'files' &&
          candidate.identityId === instance.identityId &&
          (candidate.state === 'QUEUED' || candidate.state === 'READY') &&
          candidate.reconnectUntil !== undefined &&
          candidate.reconnectUntil > this.clock.now(),
      )
      .sort((left, right) => {
        const created = left.createdAt - right.createdAt;
        if (created) return created;
        const leftSequence = BigInt(left.sequence);
        const rightSequence = BigInt(right.sequence);
        return leftSequence < rightSequence ? -1 : leftSequence > rightSequence ? 1 : 0;
      })[0];
    if (request) {
      request.instanceId = instance.id;
      delete request.reconnectUntil;
    }
  }
  async info(handle: string): Promise<unknown> {
    await this.sweep();
    return await this.control.view(async state => {
      const actor = await this.actor(state, handle);
      return {
        projectId: actor.projectId,
        identityId: actor.identityId,
        adapterInstanceId: actor.instanceId,
        name: actor.name,
        pendingRequests: await mapAsync(
          await pendingFor(state, actor.instanceId),
          async r => await this.statusIn(state, r),
        ),
        unreadNotificationCount: (await state.all('notifications')).filter(
          n => n.projectId === actor.projectId && n.identityId === actor.identityId,
        ).length,
      };
    });
  }
  private async followIn(state: ControlState, actor: Actor, threadId: string): Promise<void> {
    if (!(await state.get('follows', followKey(actor.projectId, threadId, actor.identityId))))
      await state.set('follows', followKey(actor.projectId, threadId, actor.identityId), {
        projectId: actor.projectId,
        threadId,
        identityId: actor.identityId,
        createdAt: this.clock.now(),
      });
  }
  async followThread(handle: string, threadId: string): Promise<unknown> {
    const actor = await this.control.view(async state => await this.actor(state, handle));
    requireThat(
      (await this.content.listThreads(actor.projectId)).some(thread => thread.id === threadId),
      'NOT_FOUND',
      'Thread not found in this project.',
    );
    return await this.control.update(async state => {
      const current = await this.actor(state, handle);
      await this.followIn(state, current, threadId);
      return { threadId, following: true };
    });
  }
  async unfollowThread(handle: string, threadId: string): Promise<unknown> {
    const actor = await this.control.view(async state => await this.actor(state, handle));
    requireThat(
      (await this.content.listThreads(actor.projectId)).some(thread => thread.id === threadId),
      'NOT_FOUND',
      'Thread not found in this project.',
    );
    return await this.control.update(async state => {
      const current = await this.actor(state, handle);
      await state.remove('follows', followKey(current.projectId, threadId, current.identityId));
      return { threadId, following: false };
    });
  }
  async listAgents(handle: string, onlineOnly: boolean, includeSelf: boolean): Promise<unknown> {
    return await this.control.view(async state => {
      const actor = await this.actor(state, handle);
      const agents = (
        await mapAsync(
          (await state.all('identities')).filter(
            identity =>
              identity.projectId === actor.projectId &&
              (includeSelf || identity.id !== actor.identityId),
          ),
          async identity => {
            const instances = (await state.all('instances'))
              .filter(instance => instance.identityId === identity.id)
              .sort((a, b) => b.lastSeen - a.lastSeen);
            const active = instances.find(instance => instance.active);
            const latest = active ?? instances[0];
            return {
              identityId: identity.id,
              name: identity.name,
              online: Boolean(active),
              lastSeenAt: latest ? iso(latest.lastSeen) : null,
              host: active?.host ?? null,
              self: identity.id === actor.identityId,
            };
          },
        )
      ).filter(agent => !onlineOnly || agent.online);
      return { agents };
    });
  }
  private async presentNotifications(items: import('./domain.js').Notification[]) {
    return items.map(item =>
      presentNotification(
        item,
        item.content ??
          (item.resourceType === 'thread'
            ? {
                kind: 'thread_message',
                threadTitle: 'Unavailable thread',
                body: '',
                retracted: true,
              }
            : {
                kind: 'ticket_summary',
                title: 'Unavailable ticket',
                state: 'unknown',
                owner: 'unknown',
              }),
      ),
    );
  }
  async listNotifications(handle: string, limit: number, cursor?: string): Promise<unknown> {
    let after: [number, number, string] | undefined;
    if (cursor) {
      let parsed: unknown;
      try {
        parsed = JSON.parse(Buffer.from(cursor, 'base64url').toString('utf8'));
      } catch {
        throw new BassfishError('INVALID_CURSOR', 'The notification cursor is invalid.');
      }
      requireThat(
        Array.isArray(parsed) &&
          parsed.length === 3 &&
          parsed.every((item, index) =>
            index < 2 ? Number.isInteger(item) : typeof item === 'string',
          ),
        'INVALID_CURSOR',
        'The notification cursor is invalid.',
      );
      after = parsed as [number, number, string];
    }
    const page = await this.control.view(async state => {
      const actor = await this.actor(state, handle);
      let notifications = (await state.all('notifications'))
        .filter(item => item.projectId === actor.projectId && item.identityId === actor.identityId)
        .sort(
          (a, b) =>
            notificationPriority(a) - notificationPriority(b) ||
            a.createdAt - b.createdAt ||
            compare(a.id, b.id),
        );
      if (after)
        notifications = notifications.filter(item => {
          const priority = notificationPriority(item);
          return (
            priority > after![0] ||
            (priority === after![0] &&
              (item.createdAt > after![1] || (item.createdAt === after![1] && item.id > after![2])))
          );
        });
      const page = notifications.slice(0, limit);
      const last = page.at(-1);
      return {
        notifications: page,
        nextCursor:
          notifications.length > limit && last
            ? Buffer.from(
                JSON.stringify([notificationPriority(last), last.createdAt, last.id]),
              ).toString('base64url')
            : null,
      };
    });
    return { ...page, notifications: await this.presentNotifications(page.notifications) };
  }
  private async workNotifications(
    handle: string,
  ): Promise<{ notifications: Record<string, unknown>[]; moreAvailable: boolean }> {
    return (await this.inbox.capture(handle, 'actionable')) as unknown as {
      notifications: Record<string, unknown>[];
      moreAvailable: boolean;
    };
  }
  async waitForWork(handle: string, timeout: number, signal?: AbortSignal): Promise<unknown> {
    const until = performance.now() + Math.min(timeout, 20000);
    while (true) {
      const actor = await this.control.view(async state => await this.actor(state, handle));
      const remaining = Math.max(0, until - performance.now());
      // Register before inspecting the inbox so a commit cannot land between
      // the empty check and waiter registration.
      const waiting = this.wakeSignals.wait(actor.identityId, remaining, signal);
      const batch = await this.workNotifications(handle);
      if (batch.notifications.length > 0 || remaining <= 0) {
        waiting.cancel();
        return batch;
      }
      await waiting.promise;
      if (performance.now() >= until) return { notifications: [], moreAvailable: false };
    }
  }
  private async ownWorkTask(
    state: ControlState,
    handle: string,
    taskId: string,
  ): Promise<WorkTask> {
    const actor = await this.actor(state, handle);
    const task = await state.get('workTasks', taskId);
    requireThat(
      task && task.projectId === actor.projectId && task.identityId === actor.identityId,
      'TASK_NOT_FOUND',
      'Work task not found for this identity.',
    );
    return task;
  }
  private workTaskView(task: WorkTask): Record<string, unknown> {
    return {
      taskId: task.id,
      status: task.status,
      ...(task.statusMessage ? { statusMessage: task.statusMessage } : {}),
      createdAt: iso(task.createdAt),
      lastUpdatedAt: iso(task.updatedAt),
      ttlMs: task.status === 'working' ? null : this.limits.retentionMs,
      pollIntervalMs: 1000,
      ...(task.status === 'completed' && task.result ? { result: task.result } : {}),
      ...(task.status === 'failed' && task.error ? { error: task.error } : {}),
    };
  }
  async createWorkTask(handle: string): Promise<Record<string, unknown>> {
    await this.sweep();
    return await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      const active = (await state.all('workTasks')).find(
        task =>
          task.projectId === actor.projectId &&
          task.identityId === actor.identityId &&
          task.status === 'working',
      );
      if (active) return this.workTaskView(active);
      const at = this.clock.now();
      const task: WorkTask = {
        id: `work_${uid()}`,
        projectId: actor.projectId,
        identityId: actor.identityId,
        status: 'working',
        statusMessage: 'Waiting for Bassfish work.',
        createdAt: at,
        updatedAt: at,
        discardAt: Number.MAX_SAFE_INTEGER,
      };
      await state.set('workTasks', task.id, task);
      return this.workTaskView(task);
    });
  }
  async getWorkTask(handle: string, taskId: string): Promise<Record<string, unknown>> {
    await this.sweep();
    const status = await this.control.view(async state =>
      this.workTaskView(await this.ownWorkTask(state, handle, taskId)),
    );
    if (status.status !== 'working') return status;
    const batch = await this.workNotifications(handle);
    if (batch.notifications.length === 0) return status;
    return await this.control.update(async state => {
      const task = await this.ownWorkTask(state, handle, taskId);
      if (task.status === 'working') {
        task.status = 'completed';
        task.statusMessage = `Received ${batch.notifications.length} Bassfish work notification${batch.notifications.length === 1 ? '' : 's'}.`;
        task.updatedAt = Math.max(this.clock.now(), task.updatedAt + 1);
        task.discardAt = task.updatedAt + this.limits.retentionMs;
        task.result = batch;
      }
      return this.workTaskView(task);
    });
  }
  async cancelWorkTask(handle: string, taskId: string): Promise<Record<string, unknown>> {
    await this.sweep();
    return await this.control.update(async state => {
      const task = await this.ownWorkTask(state, handle, taskId);
      if (task.status === 'working') {
        task.status = 'cancelled';
        task.statusMessage = 'Work listening was cancelled.';
        task.updatedAt = Math.max(this.clock.now(), task.updatedAt + 1);
        task.discardAt = task.updatedAt + this.limits.retentionMs;
      }
      return this.workTaskView(task);
    });
  }
  async waitWorkTask(
    handle: string,
    taskId: string,
    updatedAfter: number,
    timeout: number,
    signal?: AbortSignal,
  ): Promise<Record<string, unknown>> {
    const until = performance.now() + Math.min(timeout, this.limits.waitMs);
    while (true) {
      const task = await this.getWorkTask(handle, taskId);
      if (
        Date.parse(String(task.lastUpdatedAt)) > updatedAfter ||
        task.status !== 'working' ||
        performance.now() >= until
      )
        return task;
      const actor = await this.control.view(async state => await this.actor(state, handle));
      const waiting = this.wakeSignals.wait(
        actor.identityId,
        Math.max(0, until - performance.now()),
        signal,
      );
      try {
        await waiting.promise;
      } catch {
        throw new BassfishError('CANCELLED', 'Task observation was cancelled.');
      }
    }
  }
  async ackNotifications(handle: string, notificationIds: string[]): Promise<unknown> {
    return await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      let acknowledged = 0;
      for (const id of new Set(notificationIds)) {
        const item = await state.get('notifications', id);
        requireThat(
          item && item.projectId === actor.projectId && item.identityId === actor.identityId,
          'NOTIFICATION_NOT_FOUND',
          'Unread notification not found for this identity.',
        );
        await state.remove('notifications', id);
        acknowledged++;
      }
      return {
        acknowledged,
        unreadNotificationCount: (await state.all('notifications')).filter(
          item => item.projectId === actor.projectId && item.identityId === actor.identityId,
        ).length,
      };
    });
  }
  private signalWake(identityIds: Iterable<string>): void {
    this.control.afterCommit(() => this.wakeSignals.signal(identityIds));
  }
  async waitInbox(
    handle: string,
    timeout: number,
    signal?: AbortSignal,
  ): Promise<{ ready: boolean }> {
    const until = performance.now() + Math.min(timeout, 20000);
    while (true) {
      const actor = await this.control.view(state => this.actor(state, handle));
      const remaining = Math.max(0, until - performance.now());
      const waiting = this.wakeSignals.wait(actor.identityId, remaining, signal);
      if (await this.inbox.hasActionable(handle)) {
        waiting.cancel();
        return { ready: true };
      }
      if (!remaining) {
        waiting.cancel();
        return { ready: false };
      }
      await waiting.promise;
    }
  }
  private async takeDelivery(
    handle: string,
    scope: 'actionable' | 'all',
  ): Promise<{
    kind: 'actionable' | 'activity' | 'none';
    count: number;
    notificationIds: string[];
    threadIds: string[];
    ticketIds: string[];
    reasons: NotificationReason[];
    senders: string[];
    notifications: Record<string, unknown>[];
  }> {
    const empty = {
      kind: 'none' as const,
      count: 0,
      notificationIds: [],
      threadIds: [],
      ticketIds: [],
      reasons: [],
      senders: [],
      notifications: [],
    };
    const selected = await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      const binding = (await state.all('hostSessionBindings')).find(
        candidate =>
          candidate.projectId === actor.projectId && candidate.identityId === actor.identityId,
      );
      if (!binding) return [];
      const now = this.clock.now();
      const available = (await state.all('notifications')).filter(
        item =>
          item.identityId === actor.identityId &&
          (item.lastDeliveredWakeKey !== binding.wakeKey ||
            item.lastDeliveredAt === undefined ||
            now - item.lastDeliveredAt >= deliveryLeaseMs),
      );
      const actionable = available.filter(isWorkNotification);
      const chosen = (actionable.length ? actionable : scope === 'all' ? available : []).sort(
        (a, b) =>
          notificationPriority(a) - notificationPriority(b) ||
          a.createdAt - b.createdAt ||
          compare(a.id, b.id),
      );
      for (const item of chosen) {
        item.lastDeliveredWakeKey = binding.wakeKey;
        item.lastDeliveredAt = now;
      }
      return chosen;
    });
    if (!selected.length) return empty;
    return {
      kind: selected.some(isWorkNotification) ? 'actionable' : 'activity',
      count: selected.length,
      notificationIds: selected.map(item => item.id),
      threadIds: [...new Set(selected.flatMap(item => (item.threadId ? [item.threadId] : [])))],
      ticketIds: [...new Set(selected.flatMap(item => (item.ticketId ? [item.ticketId] : [])))],
      reasons: [...new Set(selected.flatMap(item => item.reasons))],
      senders: [...new Set(selected.map(item => item.senderName))],
      notifications: await this.presentNotifications(selected),
    };
  }
  async waitForDeliveryHandle(
    handle: string,
    timeout: number,
    scope: 'actionable' | 'all' = 'all',
    signal?: AbortSignal,
  ): Promise<unknown> {
    const until = performance.now() + Math.min(timeout, 20000);
    while (true) {
      const actor = await this.control.view(async state => await this.actor(state, handle));
      const remaining = Math.max(0, until - performance.now());
      const waiting = this.wakeSignals.wait(actor.identityId, remaining, signal);
      const batch = await this.takeDelivery(handle, scope);
      if (batch.count > 0 || remaining <= 0) {
        waiting.cancel();
        return batch;
      }
      await waiting.promise;
      if (performance.now() >= until)
        return {
          kind: 'none',
          count: 0,
          notificationIds: [],
          threadIds: [],
          ticketIds: [],
          reasons: [],
          senders: [],
          notifications: [],
        };
    }
  }
  async requestName(handle: string, name: string): Promise<unknown> {
    nameSchema.parse(name);
    await this.sweep();
    await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      const attachedInstances = (await state.all('instances')).filter(
        instance => instance.identityId === actor.identityId && instance.active,
      );
      requireThat(
        !(await state.all('requests')).some(
          request =>
            request.identityId === actor.identityId && activeStates.includes(request.state),
        ),
        'TURN_REQUEST_EXISTS',
        'Finish operations in every attachment of this identity before changing its name.',
      );
      const target = (await state.all('identities')).find(
        i => i.projectId === actor.projectId && i.name.toLowerCase() === name.toLowerCase(),
      );
      if (target && target.id !== actor.identityId) {
        const targetBinding = (await state.all('hostSessionBindings')).find(
          binding => binding.projectId === actor.projectId && binding.identityId === target.id,
        );
        requireThat(
          !targetBinding,
          'NAME_BOUND_TO_SESSION',
          'This name belongs to another host session.',
        );
        requireThat(
          !(await state.all('instances')).some(i => i.identityId === target.id && i.active),
          'NAME_IN_USE',
          'This identity has a live adapter instance.',
        );
        for (const instance of attachedInstances) instance.identityId = target.id;
        const binding = (await state.all('hostSessionBindings')).find(
          candidate =>
            candidate.projectId === actor.projectId && candidate.identityId === actor.identityId,
        );
        if (binding) {
          binding.identityId = target.id;
          binding.updatedAt = this.clock.now();
        }
      } else (await state.get('identities', actor.identityId))!.name = name;
      await this.promote(state);
    });
    return await this.info(handle);
  }
  private async statusIn(
    state: ControlState,
    request: TurnRequest,
  ): Promise<Record<string, unknown>> {
    const position = (await state.all('requests')).filter(
      other =>
        other.state === 'QUEUED' &&
        BigInt(other.sequence) <= BigInt(request.sequence) &&
        (request.resourceType === 'files'
          ? other.resourceType === 'files' && fileSetsOverlap(other.paths, request.paths)
          : other.resourceType !== 'files' && other.resourceId === request.resourceId),
    ).length;
    const target =
      request.resourceType === 'files'
        ? { type: 'files', paths: request.paths }
        : { type: request.resourceType, id: request.resourceId };
    return {
      state: request.state.toLowerCase(),
      requestId: request.id,
      target,
      ...(request.resourceType === 'files' ? { lifetime: 'session' } : {}),
      ...(request.state === 'QUEUED' ? { position } : {}),
      ...(request.state === 'OFFERED'
        ? { offerId: request.offerId, claimBy: iso(request.claimBy!) }
        : {}),
      ...(request.resourceType !== 'files' && request.expiresAt !== undefined
        ? { expiresAt: iso(request.expiresAt) }
        : {}),
      ...(request.resourceType !== 'files' && request.result ? { result: request.result } : {}),
    };
  }
  private async ownRequest(
    state: ControlState,
    handle: string,
    ticketId: string,
  ): Promise<TurnRequest> {
    const actor = await this.actor(state, handle);
    const request = await state.get('requests', ticketId);
    requireThat(
      request && request.projectId === actor.projectId && request.identityId === actor.identityId,
      'NOT_TURN_OWNER',
      'This ticket does not belong to the calling identity.',
    );
    return request;
  }
  private async ownTask(state: ControlState, handle: string, taskId: string): Promise<DurableTask> {
    const actor = await this.actor(state, handle);
    const task = await state.get('tasks', taskId);
    requireThat(
      task && task.projectId === actor.projectId && task.identityId === actor.identityId,
      'TASK_NOT_FOUND',
      'Task not found for this identity.',
    );
    return task;
  }
  taskView(task: DurableTask, includeResult = true): Record<string, unknown> {
    return {
      taskId: task.id,
      status: task.status,
      ...(task.statusMessage ? { statusMessage: task.statusMessage } : {}),
      createdAt: iso(task.createdAt),
      lastUpdatedAt: iso(task.updatedAt),
      ttlMs: Math.max(0, task.discardAt - task.createdAt),
      pollIntervalMs: 1000,
      ...(includeResult && task.status === 'completed' && task.result
        ? { result: task.result }
        : {}),
      ...(task.status === 'failed' && task.error ? { error: task.error } : {}),
    };
  }
  async getTask(
    handle: string,
    taskId: string,
    materialize = true,
  ): Promise<Record<string, unknown>> {
    await this.sweep();
    if (!materialize)
      return await this.control.view(async state =>
        this.taskView(await this.ownTask(state, handle, taskId), false),
      );
    return this.taskAcquisitions.run(taskId, async () => {
      const pending = await this.control.update(async state => {
        const task = await this.ownTask(state, handle, taskId);
        const request = await state.get('requests', task.requestId);
        if (task.status === 'working' && request?.state === 'READY')
          await this.materializeOffer(state, request);
        if (task.status === 'working' && request?.state === 'CLAIMED') {
          task.status = 'completed';
          task.statusMessage = 'The turn is claimed.';
          task.updatedAt = this.clock.now();
          task.discardAt = task.updatedAt + this.limits.retentionMs;
          task.result = { requestId: request.id };
        }
        return {
          task: await copy(task),
          request: request ? copy(request) : undefined,
        };
      });
      if (pending.task.status === 'working' && pending.request?.state === 'OFFERED') {
        try {
          await this.claimTurn(handle, pending.request.offerId!, 20);
          await this.control.update(async state => {
            const task = await this.ownTask(state, handle, taskId);
            const request = await state.get('requests', task.requestId);
            requireThat(
              request?.state === 'CLAIMED',
              'OFFER_UNAVAILABLE',
              'The ready turn could not be claimed.',
            );
            task.status = 'completed';
            task.statusMessage = 'The turn is claimed.';
            task.updatedAt = this.clock.now();
            task.discardAt = task.updatedAt + this.limits.retentionMs;
            task.result = { requestId: request.id };
          });
        } catch (error) {
          await this.control.update(async state => {
            const task = await this.ownTask(state, handle, taskId);
            const request = await state.get('requests', task.requestId);
            if (task.status !== 'working') return;
            if (request && activeStates.includes(request.state))
              await this.finish(request, 'FAILED', state);
            else {
              task.status = 'failed';
              task.statusMessage = 'The turn could not be acquired.';
              task.updatedAt = this.clock.now();
              task.discardAt = task.updatedAt + this.limits.retentionMs;
              task.error = { code: -32603, message: 'The turn could not be acquired.' };
            }
            await this.promote(state);
          });
        }
      }
      const completed = await this.control.view(async state => {
        const task = await this.ownTask(state, handle, taskId);
        return {
          view: this.taskView(task, false),
          requestId: task.status === 'completed' ? task.requestId : undefined,
        };
      });
      if (!completed.requestId) return completed.view;
      return {
        ...completed.view,
        result: await this.claimedSnapshot(handle, completed.requestId, false),
      };
    });
  }
  async cancelTask(handle: string, taskId: string): Promise<Record<string, unknown>> {
    await this.sweep();
    return await this.control.update(async state => {
      const task = await this.ownTask(state, handle, taskId);
      const request = await state.get('requests', task.requestId);
      if (
        request &&
        task.status === 'working' &&
        ['QUEUED', 'READY', 'OFFERED'].includes(request.state)
      )
        await this.finish(request, 'CANCELLED', state);
      await this.promote(state);
      return this.taskView(task);
    });
  }
  async waitTask(
    handle: string,
    taskId: string,
    updatedAfter: number,
    timeout: number,
    signal?: AbortSignal,
  ): Promise<Record<string, unknown>> {
    const until = performance.now() + Math.min(timeout, this.limits.waitMs);
    while (true) {
      const task = await this.control.view(async state =>
        this.taskView(await this.ownTask(state, handle, taskId), false),
      );
      const updated = Date.parse(String(task.lastUpdatedAt));
      if (updated > updatedAfter || performance.now() >= until) return task;
      try {
        await delay(Math.min(100, Math.max(1, until - performance.now())), undefined, { signal });
      } catch {
        throw new BassfishError('CANCELLED', 'Task observation was cancelled.');
      }
    }
  }
  async status(handle: string, ticketId: string): Promise<Record<string, unknown>> {
    await this.sweep();
    return await this.control.update(async state => {
      const request = await this.ownRequest(state, handle, ticketId);
      await this.materializeOffer(state, request);
      return await this.statusIn(state, request);
    });
  }
  private async claimed(
    state: ControlState,
    handle: string,
    turnId: string,
    fence: string,
  ): Promise<ContentTurnRequest> {
    requireThat(turnId && fence, 'TURN_REQUIRED', 'Current turn credentials are required.');
    const actor = await this.actor(state, handle);
    const request = (await state.all('requests')).find(r => r.turnId === turnId);
    requireThat(
      request &&
        request.projectId === actor.projectId &&
        request.identityId === actor.identityId &&
        request.instanceId === actor.instanceId,
      'NOT_TURN_OWNER',
      'The turn is not bound to this adapter instance.',
    );
    requireThat(
      request.resourceType !== 'files',
      'RESOURCE_TYPE_MISMATCH',
      'File locks use native filesystem tools and releaseTurn.',
    );
    requireThat(
      request.fence === fence &&
        (await state.get('resources', request.resourceId))?.fence === fence,
      'STALE_TURN',
      'The fencing token is no longer current.',
    );
    requireThat(
      request.state !== 'EXPIRED' && this.clock.now() < request.expiresAt!,
      'TURN_EXPIRED',
      'The turn deadline has elapsed.',
    );
    requireThat(
      request.state !== 'COMMITTING',
      'COMMIT_IN_PROGRESS',
      'This turn has an accepted write in progress.',
    );
    requireThat(
      request.state === 'CLAIMED',
      'STALE_TURN',
      'The turn has already been released or consumed.',
    );
    await this.ready(state, actor.projectId);
    return request;
  }
  async requestResourceTurn(
    handle: string,
    resourceTypeOrId: ResourceType | string,
    maybeResourceId?: string,
    deliveryMode: 'ticket' | 'task' = 'ticket',
  ): Promise<Record<string, unknown>> {
    await this.sweep();
    const actor = await this.control.view(async s => await this.actor(s, handle));
    return this.writers.run('acquire:' + actor.instanceId, () =>
      this.control.transaction(async () => {
        await this.control.view(async s => await this.ready(s, actor.projectId));
        const resourceId = maybeResourceId ?? resourceTypeOrId;
        const requestedType =
          maybeResourceId === undefined ? undefined : (resourceTypeOrId as ResourceType);
        const actualType = await this.content.resourceType(actor.projectId, resourceId);
        requireThat(
          requestedType === undefined || actualType === requestedType,
          'NOT_FOUND',
          'Resource type does not match this identifier.',
        );
        const resourceType = actualType;
        const ticketId = await this.control.update(async state => {
          await this.actor(state, handle);
          await this.ready(state, actor.projectId);
          requireThat(
            !(await pendingFor(state, actor.instanceId)).some(
              request => request.resourceType !== 'files',
            ),
            'TURN_REQUEST_EXISTS',
            'This adapter already has a pending turn request.',
          );
          const resource = (await state.get('resources', resourceId)) ?? {
            id: resourceId,
            projectId: actor.projectId,
            type: resourceType,
            fence: '0',
            queueSequence: '0',
            present: true,
          };
          requireThat(
            resource.projectId === actor.projectId && resource.present,
            'NOT_FOUND',
            'Resource not found in this project.',
          );
          await state.set('resources', resourceId, resource);
          resource.queueSequence = increment(resource.queueSequence);
          const now = this.clock.now();
          const request: TurnRequest = {
            id: uid(),
            projectId: actor.projectId,
            resourceId,
            resourceType,
            identityId: actor.identityId,
            instanceId: actor.instanceId,
            sequence: resource.queueSequence,
            state: 'QUEUED',
            createdAt: now,
            updatedAt: now,
            queueUntil: now + this.limits.queueMs,
            deliveryMode,
          };
          await state.set('requests', request.id, request);
          if (deliveryMode === 'task')
            await state.set('tasks', request.id, {
              id: request.id,
              projectId: actor.projectId,
              identityId: actor.identityId,
              requestId: request.id,
              status: 'working',
              statusMessage: 'Waiting for the turn.',
              createdAt: now,
              updatedAt: now,
              discardAt: request.queueUntil,
            });
          await this.promote(state);
          if (deliveryMode === 'task' && request.state === 'READY') {
            await this.materializeOffer(state, request);
            await state.remove('tasks', request.id);
            request.deliveryMode = 'ticket';
          }
          return request.id;
        });
        return await this.status(handle, ticketId);
      }),
    );
  }
  async claimTurn(
    handle: string,
    offerId: string,
    limit: number,
    bodyCursor?: string,
  ): Promise<unknown> {
    await this.sweep();
    const file = await this.control.view(async state =>
      (await state.all('requests')).find(
        request => request.offerId === offerId && request.resourceType === 'files',
      ),
    );
    if (file) return await this.claimFiles(handle, offerId);
    return this.claimContentTurn(handle, offerId, limit, bodyCursor);
  }
  private async claimContentTurn(
    handle: string,
    offerId: string,
    limit: number,
    bodyCursor?: string,
  ): Promise<unknown> {
    await this.sweep();
    const actor = await this.control.view(async s => await this.actor(s, handle));
    return this.writers.run('claim:' + offerId, () =>
      this.control.transaction(async () => {
        const offer = async () =>
          await this.control.view(async state => {
            await this.actor(state, handle);
            await this.ready(state, actor.projectId);
            const request = (await state.all('requests')).find(r => r.offerId === offerId);
            requireThat(
              request &&
                request.instanceId === actor.instanceId &&
                request.projectId === actor.projectId,
              'NOT_TURN_OWNER',
              'The offer is not bound to this instance.',
            );
            requireThat(
              request.state !== 'EXPIRED' && this.clock.now() < request.claimBy!,
              'OFFER_EXPIRED',
              'The offer claim window has elapsed.',
            );
            requireThat(
              request.state === 'OFFERED',
              'OFFER_UNAVAILABLE',
              'This offer is no longer available.',
            );
            return request;
          });
        const request = await offer();
        requireThat(
          request.resourceType !== 'files',
          'RESOURCE_TYPE_MISMATCH',
          'A content turn is required.',
        );
        const snapshot =
          request.resourceType === 'thread'
            ? await this.content.snapshot(actor.projectId, request.resourceId, limit)
            : await this.content.ticketSnapshot(actor.projectId, request.resourceId, bodyCursor);
        await this.sweep();
        await offer();
        const turn = await this.control.update(async state => {
          const current = (await state.get('requests', request.id))!;
          requireThat(
            current.resourceType !== 'files',
            'RESOURCE_TYPE_MISMATCH',
            'A content turn is required.',
          );
          const resource = (await state.get('resources', current.resourceId))!;
          resource.fence = increment(resource.fence);
          current.state = 'CLAIMED';
          current.turnId = uid();
          current.fence = resource.fence;
          current.baseRevision =
            snapshot.resourceType === 'thread'
              ? snapshot.thread.revision
              : snapshot.ticket.revision;
          current.expiresAt = this.clock.now() + this.limits.turnTimeoutMs;
          if (snapshot.resourceType === 'thread')
            await this.followIn(state, actor, request.resourceId);
          return current;
        });
        await this.control.view(
          async s => await this.claimed(s, handle, turn.turnId!, turn.fence!),
        );
        const page =
          snapshot.resourceType === 'thread'
            ? {
                type: 'thread',
                thread: snapshot.thread,
                messages: snapshot.messages,
                truncated: snapshot.truncated,
              }
            : {
                type: 'ticket',
                ticket: describeTicket(
                  snapshot.ticket,
                  await this.content.listTickets(actor.projectId),
                ),
                ...snapshot.page,
              };
        return {
          requestId: turn.id,
          target: { type: snapshot.resourceType, id: request.resourceId },
          turn: { id: turn.turnId, fencingToken: turn.fence, expiresAt: iso(turn.expiresAt!) },
          snapshot: { revision: turn.baseRevision },
          page,
          nextCursor:
            snapshot.resourceType === 'thread' ? snapshot.nextBefore : snapshot.page.nextCursor,
          serverTime: iso(this.clock.now()),
        };
      }),
    );
  }
  async read(
    handle: string,
    turnId: string,
    fence: string,
    limit: number,
    before?: string,
  ): Promise<unknown> {
    await this.sweep();
    const request = await this.control.view(
      async s => await this.claimed(s, handle, turnId, fence),
    );
    requireThat(
      request.resourceType === 'thread',
      'RESOURCE_TYPE_MISMATCH',
      'This operation requires a thread turn.',
    );
    const snapshot = await this.content.snapshot(
      request.projectId,
      request.resourceId,
      limit,
      before,
      request.baseRevision,
    );
    await this.sweep();
    await this.control.view(async s => await this.claimed(s, handle, turnId, fence));
    return {
      target: { type: 'thread', id: request.resourceId },
      snapshot: { revision: request.baseRevision },
      page: { type: 'thread', messages: snapshot.messages },
      nextCursor: snapshot.nextBefore,
    };
  }
  async readTurn(handle: string, turnId: string, fence: string, cursor?: string): Promise<unknown> {
    const request = await this.control.view(
      async s => await this.claimed(s, handle, turnId, fence),
    );
    if (request.resourceType === 'thread') return this.read(handle, turnId, fence, 20, cursor);
    if (request.resourceType === 'ticket') {
      const snapshot = await this.content.ticketSnapshot(
        request.projectId,
        request.resourceId,
        cursor,
        request.baseRevision,
      );
      await this.sweep();
      await this.control.view(async state => await this.claimed(state, handle, turnId, fence));
      return {
        target: { type: 'ticket', id: snapshot.ticket.id },
        snapshot: { revision: request.baseRevision },
        page: {
          type: 'ticket',
          ticket: describeTicket(
            snapshot.ticket,
            await this.content.listTickets(request.projectId),
          ),
          ...snapshot.page,
        },
        nextCursor: snapshot.page.nextCursor,
      };
    }
    throw new BassfishError(
      'RESOURCE_TYPE_MISMATCH',
      'Project turns have operation-specific readers.',
    );
  }
  async ticketOutline(handle: string, turnId: string, fence: string): Promise<unknown> {
    await this.sweep();
    const request = await this.control.view(
      async s => await this.claimed(s, handle, turnId, fence),
    );
    requireThat(
      request.resourceType === 'ticket',
      'RESOURCE_TYPE_MISMATCH',
      'This turn does not belong to a Markdown resource.',
    );
    const snapshot = await this.content.ticketSnapshot(
      request.projectId,
      request.resourceId,
      undefined,
      request.baseRevision,
    );
    await this.sweep();
    await this.control.view(async s => await this.claimed(s, handle, turnId, fence));
    return {
      resourceType: request.resourceType,
      resourceId: request.resourceId,
      revision: request.baseRevision,
      snapshotRevision: request.baseRevision,
      headings: outline(snapshot.ticket.body),
    };
  }
  async findTicket(
    handle: string,
    turnId: string,
    fence: string,
    query: string,
    mode: 'literal' | 'regex',
    limit: number,
  ): Promise<unknown> {
    await this.sweep();
    const request = await this.control.view(
      async s => await this.claimed(s, handle, turnId, fence),
    );
    requireThat(
      request.resourceType === 'ticket',
      'RESOURCE_TYPE_MISMATCH',
      'This turn does not belong to a Markdown resource.',
    );
    const snapshot = await this.content.ticketSnapshot(
      request.projectId,
      request.resourceId,
      undefined,
      request.baseRevision,
    );
    const body = snapshot.ticket.body;
    const ranges: {
      start: number;
      end: number;
    }[] = [];
    if (mode === 'literal') {
      let at = 0;
      while (ranges.length < limit && (at = body.indexOf(query, at)) >= 0) {
        ranges.push({ start: at, end: at + query.length });
        at += Math.max(1, query.length);
      }
    } else {
      const regex = new RE2(query, 'gu');
      let match: RegExpExecArray | null;
      while (ranges.length < limit && (match = regex.exec(body) as RegExpExecArray | null)) {
        ranges.push({ start: match.index, end: match.index + match[0].length });
        if (!match[0]) regex.lastIndex++;
      }
    }
    await this.sweep();
    await this.control.view(async s => await this.claimed(s, handle, turnId, fence));
    return {
      resourceType: request.resourceType,
      resourceId: request.resourceId,
      revision: request.baseRevision,
      snapshotRevision: request.baseRevision,
      matches: ranges.map(range => ({
        startCharacter: range.start,
        endCharacter: range.end,
        line: body.slice(0, range.start).split('\n').length,
        snippet: body.slice(Math.max(0, range.start - 128), Math.min(body.length, range.end + 384)),
      })),
    };
  }
  async releaseTurn(handle: string, turnId: string, fence: string): Promise<unknown> {
    await this.sweep();
    return await this.control.update(async state => {
      const request = await this.claimed(state, handle, turnId, fence);
      await this.finish(request, 'RELEASED', state);
      await this.promote(state);
      return await this.statusIn(state, request);
    });
  }
  async cancelTurnRequest(handle: string, ticketId: string): Promise<unknown> {
    await this.sweep();
    return await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      const request = await this.ownRequest(state, handle, ticketId);
      requireThat(
        request.instanceId === actor.instanceId,
        'NOT_TURN_OWNER',
        'Rebind this queue request before cancelling it.',
      );
      requireThat(
        request.state !== 'CLAIMED' && request.state !== 'COMMITTING',
        'TURN_ALREADY_CLAIMED',
        'The turn has already been claimed.',
      );
      if (request.state === 'QUEUED' || request.state === 'READY' || request.state === 'OFFERED')
        await this.finish(request, 'CANCELLED', state);
      await this.promote(state);
      return await this.statusIn(state, request);
    });
  }
  async waitForTurn(
    handle: string,
    ticketId: string,
    timeout: number,
    signal?: AbortSignal,
  ): Promise<unknown> {
    requireThat(
      timeout <= this.limits.waitMs,
      'INVALID_ARGUMENT',
      'The wait exceeds the configured maximum.',
    );
    const until = performance.now() + timeout;
    while (true) {
      const status = await this.status(handle, ticketId);
      if (status.state !== 'queued' || performance.now() >= until) return status;
      try {
        await delay(Math.min(100, Math.max(1, until - performance.now())), undefined, { signal });
      } catch {
        try {
          await this.cancelTurnRequest(handle, ticketId);
        } catch {
          /* Claim may already have won. */
        }
        throw new BassfishError('CANCELLED', 'The wait was cancelled; inspect ticket state.');
      }
    }
  }
  async createThread(handle: string, title: string, description: string): Promise<unknown> {
    const actor = await this.control.view(async s => await this.actor(s, handle));
    return this.writers.run('create:' + uid(), () =>
      this.control.transaction(async () => {
        let context!: MutationContext;
        await this.control.view(async s => {
          await this.actor(s, handle);
          await this.creationAllowed(s, actor.projectId);
        });
        const thread: Thread = {
          id: uid(),
          title,
          description,
          state: 'active',
          revision: '1',
          headSequence: '0',
          creator: actor.identityId,
          createdAt: iso(this.clock.now()),
        };
        const operation: WriteOperation = {
          id: uid(),
          actor,
          resourceId: thread.id,
          resourceType: 'thread',
          at: thread.createdAt,
          thread,
          mutation: { kind: 'createThread' },
        };
        await this.control.update(async state => {
          await this.actor(state, handle);
          await this.creationAllowed(state, actor.projectId);
          await (context = {
            id: operation.id,
            projectId: actor.projectId,
            resourceId: thread.id,
            resourceType: 'thread',
            kind: 'createThread',
            actor,
            followIdentityId: actor.identityId,
          });
        });
        const result = await this.persist(operation, context);
        return { threadId: thread.id, title, state: thread.state, ...result };
      }),
    );
  }
  async listThreadMetadata(handle: string, args: Record<string, unknown>): Promise<unknown> {
    const actor = await this.control.view(async state => {
      const current = await this.actor(state, handle);
      await this.ready(state, current.projectId);
      return current;
    });
    const cursor = decodeCursor(args.cursor);
    let threads = sortThreads(await this.content.listThreads(actor.projectId)).filter(
      thread => thread.state === args.state,
    );
    if (args.creatorIdentityId) {
      threads = threads.filter(thread => thread.creator === args.creatorIdentityId);
    }
    if (args.titlePrefix) {
      threads = threads.filter(thread => thread.title.startsWith(args.titlePrefix as string));
    }
    if (args.following !== undefined) {
      threads = await filterAsync(
        threads,
        async thread =>
          Boolean(
            await this.control.view(
              async state =>
                await state.get('follows', followKey(actor.projectId, thread.id, actor.identityId)),
            ),
          ) === args.following,
      );
    }
    if (cursor) {
      threads = threads.filter(
        thread =>
          thread.createdAt > cursor[0] || (thread.createdAt === cursor[0] && thread.id > cursor[1]),
      );
    }
    const limit = args.limit as number;
    const page = threads.slice(0, limit);
    const last = page.at(-1);
    return {
      threads: await mapAsync(page, async thread => ({
        ...thread,
        following: Boolean(
          await this.control.view(
            async state =>
              await state.get('follows', followKey(actor.projectId, thread.id, actor.identityId)),
          ),
        ),
      })),
      nextCursor: threads.length > limit && last ? encodeCursor([last.createdAt, last.id]) : null,
    };
  }
  async getThreadMetadata(handle: string, threadId: string): Promise<unknown> {
    const actor = await this.control.view(async state => {
      const current = await this.actor(state, handle);
      await this.ready(state, current.projectId);
      return current;
    });
    const thread = (await this.content.listThreads(actor.projectId)).find(
      value => value.id === threadId,
    );
    requireThat(thread, 'NOT_FOUND', 'Thread not found in this project.');
    return {
      ...thread,
      following: await this.control.view(async state =>
        Boolean(
          await state.get('follows', followKey(actor.projectId, thread.id, actor.identityId)),
        ),
      ),
    };
  }
  async searchThreadMetadata(handle: string, args: Record<string, unknown>): Promise<unknown> {
    const actor = await this.control.view(async state => {
      const current = await this.actor(state, handle);
      await this.ready(state, current.projectId);
      return current;
    });
    const query = String(args.query).toLowerCase();
    const threads = sortThreads(await this.content.listThreads(actor.projectId))
      .filter(
        thread =>
          thread.state === args.state &&
          [thread.title, thread.description].some(value => value.toLowerCase().includes(query)),
      )
      .slice(0, args.limit as number);
    return { threads };
  }
  async ticketOwner(
    projectId: string,
    ownerName: string,
  ): Promise<{
    id: string;
    name: string;
  }> {
    return await this.control.view(async state => {
      const owner = (await state.all('identities')).find(
        identity =>
          identity.projectId === projectId &&
          identity.name.toLowerCase() === ownerName.toLowerCase(),
      );
      requireThat(owner, 'UNKNOWN_AGENT', `No agent named ${ownerName} exists in this repository.`);
      return { id: owner.id, name: owner.name };
    });
  }
  async createTicket(
    handle: string,
    input: {
      title: string;
      description: string;
      owner: string;
      state: Ticket['state'];
      body: string;
      dependsOn: string[];
    },
  ): Promise<unknown> {
    const actor = await this.control.view(async state => await this.actor(state, handle));
    return this.writers.run('graph:' + actor.projectId, () =>
      this.control.transaction(async () => {
        let context!: MutationContext;
        await this.control.view(async state => {
          await this.actor(state, handle);
          await this.creationAllowed(state, actor.projectId);
        });
        const owner = await this.ticketOwner(actor.projectId, input.owner);
        const tickets = await this.content.listTickets(actor.projectId);
        const at = iso(this.clock.now());
        const ticket: Ticket = {
          id: uid(),
          title: input.title,
          description: input.description,
          owner: owner.id,
          ownerName: owner.name,
          state: input.state,
          body: input.body,
          dependsOn: normalizeDependencies(input.dependsOn),
          revision: '1',
          creator: actor.identityId,
          creatorName: actor.name,
          lastEditor: actor.identityId,
          lastEditorName: actor.name,
          createdAt: at,
          updatedAt: at,
        };
        validateTicketGraph([...tickets, ticket]);
        const operation: WriteOperation = {
          id: uid(),
          actor,
          resourceId: ticket.id,
          resourceType: 'ticket',
          at,
          ticket,
          mutation: { kind: 'createTicket' },
        };
        const notificationIntents: NotificationIntent[] =
          owner.id === actor.identityId
            ? []
            : [
                {
                  identityId: owner.id,
                  resourceType: 'ticket',
                  resourceId: ticket.id,
                  reasons: ['ticket_assigned'],
                  content: {
                    kind: 'ticket_summary',
                    title: ticket.title,
                    state: ticket.state,
                    owner: ticket.ownerName,
                  },
                },
              ];
        await this.control.update(async state => {
          await this.actor(state, handle);
          await this.creationAllowed(state, actor.projectId);
          await (context = {
            id: operation.id,
            projectId: actor.projectId,
            resourceId: ticket.id,
            resourceType: 'ticket',
            kind: 'createTicket',
            actor,
            notificationIntents,
            notificationCreatedAt: this.clock.now(),
          });
        });
        const result = await this.persist(operation, context);
        return {
          ticketId: ticket.id,
          title: ticket.title,
          owner: ticket.ownerName,
          state: ticket.state,
          ...result,
        };
      }),
    );
  }
  async resourceHistory(
    handle: string,
    resourceId: string,
    offset: number,
    limit: number,
  ): Promise<unknown> {
    return this.control.readTransaction(async () => {
      const actor = await this.control.view(state => this.actor(state, handle));
      const type = await this.content.resourceType(actor.projectId, resourceId);
      const entries = await this.content.history(actor.projectId, type, resourceId);
      return {
        target: { type, id: resourceId },
        entries: entries.slice(offset, offset + limit),
        nextOffset: offset + limit < entries.length ? offset + limit : null,
      };
    });
  }
  async resourceAt(
    handle: string,
    resourceId: string,
    revision: string,
    limit: number,
    cursor?: string,
  ): Promise<unknown> {
    return this.control.readTransaction(async () => {
      const actor = await this.control.view(state => this.actor(state, handle));
      const type = await this.content.resourceType(actor.projectId, resourceId);
      if (type === 'thread') {
        const snapshot = await this.content.snapshot(
          actor.projectId,
          resourceId,
          limit,
          cursor,
          revision,
        );
        return {
          target: { type, id: resourceId },
          revision,
          page: {
            type,
            thread: snapshot.thread,
            messages: snapshot.messages,
            truncated: snapshot.truncated,
          },
          nextCursor: snapshot.nextBefore,
        };
      }
      const snapshot = await this.content.ticketSnapshot(
        actor.projectId,
        resourceId,
        cursor,
        revision,
      );
      const { body: _body, ...ticket } = snapshot.ticket;
      return {
        target: { type, id: resourceId },
        revision,
        page: { type, ticket, ...snapshot.page },
        nextCursor: snapshot.page.nextCursor,
      };
    });
  }
  async diffResource(handle: string, resourceId: string, revision: string): Promise<unknown> {
    return this.control.readTransaction(async () => {
      const actor = await this.control.view(state => this.actor(state, handle));
      const type = await this.content.resourceType(actor.projectId, resourceId);
      if (type === 'ticket') {
        const before = await this.content.ticketSnapshot(
          actor.projectId,
          resourceId,
          undefined,
          revision,
        );
        const after = await this.content.ticketSnapshot(actor.projectId, resourceId);
        const { body: beforeBody, ...beforeMetadata } = before.ticket;
        const { body: afterBody, ...afterMetadata } = after.ticket;
        return {
          target: { type, id: resourceId },
          fromRevision: revision,
          toRevision: after.ticket.revision,
          metadataChanged: JSON.stringify(beforeMetadata) !== JSON.stringify(afterMetadata),
          before: { ...beforeMetadata, body: beforeBody },
          after: { ...afterMetadata, body: afterBody },
        };
      }
      const before = await this.content.snapshot(
        actor.projectId,
        resourceId,
        1000000,
        undefined,
        revision,
      );
      const after = await this.content.snapshot(actor.projectId, resourceId, 1000000);
      const beforeIds = new Set(before.messages.filter(m => !m.retracted).map(m => m.id));
      const afterIds = new Set(after.messages.filter(m => !m.retracted).map(m => m.id));
      return {
        target: { type, id: resourceId },
        fromRevision: revision,
        toRevision: after.thread.revision,
        metadataChanged: JSON.stringify(before.thread) !== JSON.stringify(after.thread),
        messagesAdded: [...afterIds].filter(id => !beforeIds.has(id)),
        messagesRemoved: [...beforeIds].filter(id => !afterIds.has(id)),
      };
    });
  }
  async projectSnapshotInfo(handle: string): Promise<unknown> {
    const actor = await this.control.view(state => this.actor(state, handle));
    const snapshot = await this.content.projectSnapshot(actor.projectId);
    return {
      exportedAt: new Date().toISOString(),
      threads: snapshot.threads,
      tickets: describeTickets(snapshot.tickets),
      messageCount: snapshot.messages.length,
    };
  }
  async projectHistoryList(handle: string, limit: number, cursor?: string): Promise<unknown> {
    const actor = await this.control.view(state => this.actor(state, handle));
    const entries = await this.content.projectHistory(actor.projectId);
    const marker = decodeCursor(cursor);
    const start = marker ? entries.findIndex(entry => entry.operationId === marker[1]) + 1 : 0;
    requireThat(!marker || start > 0, 'INVALID_CURSOR', 'History cursor not found.');
    const page = entries.slice(start, start + limit),
      last = page.at(-1);
    return {
      entries: page,
      nextCursor:
        start + limit < entries.length && last
          ? encodeCursor([last.createdAt, last.operationId])
          : null,
    };
  }
  async exportProject(handle: string): Promise<unknown> {
    const actor = await this.control.view(state => this.actor(state, handle));
    requireThat(this.dataDir, 'EXPORT_UNAVAILABLE', 'Export storage is unavailable.');
    return writeProjectExport(
      this.dataDir,
      actor.projectId,
      await this.content.projectSnapshot(actor.projectId),
    );
  }
  async commitTurn(
    handle: string,
    turnId: string,
    fence: string,
    base: string,
    mutation: Mutation,
  ): Promise<MutationResult> {
    await this.sweep();
    const actor = await this.control.view(async s => await this.actor(s, handle));
    return this.writers
      .run(mutation.kind === 'updateTicket' ? 'graph:' + actor.projectId : 'turn:' + turnId, () =>
        this.control.transaction(async () => {
          let context!: MutationContext;
          await this.sweep();
          const request = await this.control.view(
            async s => await this.claimed(s, handle, turnId, fence),
          );
          const snapshot =
            request.resourceType === 'thread'
              ? await this.content.snapshot(actor.projectId, request.resourceId, 1)
              : await this.content.ticketSnapshot(actor.projectId, request.resourceId);
          const currentRevision =
            snapshot.resourceType === 'thread'
              ? snapshot.thread.revision
              : snapshot.ticket.revision;
          requireThat(
            base === request.baseRevision && base === currentRevision,
            'REVISION_CHANGED',
            'The mutation base must match the current claimed revision.',
          );
          if (mutation.kind === 'appendMessage') {
            const append = mutation;
            const normalized = await this.control.view(async state => {
              await this.actor(state, handle);
              const resolveAgent = async (name: string) => {
                const identity = (await state.all('identities')).find(
                  item =>
                    item.projectId === actor.projectId &&
                    item.name.toLowerCase() === name.toLowerCase(),
                );
                requireThat(
                  identity,
                  'UNKNOWN_AGENT',
                  `No agent named ${name} exists in this repository.`,
                );
                return identity;
              };
              const agents = [
                ...new Set(
                  await mapAsync(
                    append.mentions?.agents ?? [],
                    async (name: string) => (await resolveAgent(name)).name,
                  ),
                ),
              ];
              requireThat(
                !append.mentions?.global || (agents.length === 0 && !append.mentions.here),
                'INVALID_ARGUMENT',
                '@global cannot be combined with direct mentions or @here.',
              );
              return { agents };
            });
            mutation = {
              ...append,
              mentions: {
                agents: normalized.agents,
                here: append.mentions?.here ?? false,
                global: append.mentions?.global ?? false,
              },
            };
          }
          const at = iso(this.clock.now());
          let operation: WriteOperation;
          let notificationIntents: NotificationIntent[] = [];
          if (snapshot.resourceType === 'thread') {
            requireThat(
              threadMutationKinds.includes(mutation.kind),
              'RESOURCE_TYPE_MISMATCH',
              'This mutation does not apply to a thread.',
            );
            if (mutation.kind === 'retractMessage' || mutation.kind === 'reinstateMessage') {
              const visibilityMutation = mutation;
              const current = await this.content.snapshot(
                actor.projectId,
                request.resourceId,
                1000000,
              );
              const message = current.messages.find(
                value => value.id === visibilityMutation.messageId,
              );
              requireThat(message, 'NOT_FOUND', 'Message not found in this thread.');
              requireThat(
                mutation.kind === 'retractMessage' ? !message.retracted : message.retracted,
                'NO_CHANGE',
                `The message is already ${mutation.kind === 'retractMessage' ? 'retracted' : 'visible'}.`,
              );
            }
            const thread = prepareMutation(snapshot.thread, mutation as ThreadMutation);
            operation = {
              id: uid(),
              actor,
              resourceId: request.resourceId,
              resourceType: 'thread',
              at,
              thread,
              mutation: mutation as ThreadMutation,
            };
          } else {
            requireThat(
              ticketMutationKinds.includes(mutation.kind),
              'RESOURCE_TYPE_MISMATCH',
              'This mutation does not apply to a ticket.',
            );
            let ticketMutation = mutation as TicketMutation;
            let owner = { id: snapshot.ticket.owner, name: snapshot.ticket.ownerName };
            if (ticketMutation.kind === 'updateTicket' && ticketMutation.owner !== undefined) {
              owner = await this.ticketOwner(actor.projectId, ticketMutation.owner);
              ticketMutation = { ...ticketMutation, owner: owner.id };
            }
            const beforeTickets = await this.content.listTickets(actor.projectId);
            const ticket = prepareTicket(snapshot.ticket, ticketMutation, actor, at);
            ticket.ownerName = owner.name;
            const afterTickets = beforeTickets.map(value =>
              value.id === ticket.id ? ticket : value,
            );
            validateTicketGraph(afterTickets);
            const beforeStatuses = ticketStatuses(beforeTickets);
            const afterStatuses = ticketStatuses(afterTickets);
            if (ticket.owner !== snapshot.ticket.owner && ticket.owner !== actor.identityId)
              notificationIntents.push({
                identityId: ticket.owner,
                resourceType: 'ticket',
                resourceId: ticket.id,
                reasons: ['ticket_assigned'],
                content: {
                  kind: 'ticket_summary',
                  title: ticket.title,
                  state: ticket.state,
                  owner: ticket.ownerName,
                },
              });
            for (const candidate of afterTickets) {
              const before = beforeTickets.find(value => value.id === candidate.id)!;
              if (
                !beforeStatuses.get(before.id)!.ready &&
                afterStatuses.get(candidate.id)!.ready &&
                candidate.owner !== actor.identityId
              )
                notificationIntents.push({
                  identityId: candidate.owner,
                  resourceType: 'ticket',
                  resourceId: candidate.id,
                  reasons: ['ticket_ready'],
                  content: {
                    kind: 'ticket_summary',
                    title: candidate.title,
                    state: candidate.state,
                    owner: candidate.ownerName,
                  },
                });
            }
            mutation = ticketMutation;
            operation = {
              id: uid(),
              actor,
              resourceId: request.resourceId,
              resourceType: 'ticket',
              at,
              ticket,
              mutation: ticketMutation,
            };
          }
          const notificationContent =
            mutation.kind === 'appendMessage' && snapshot.resourceType === 'thread'
              ? {
                  kind: 'thread_message' as const,
                  threadTitle: snapshot.thread.title,
                  body: mutation.body,
                  retracted: false,
                }
              : undefined;
          await this.control.update(async state => {
            const current = await this.claimed(state, handle, turnId, fence);
            current.state = 'COMMITTING';
            this.committingTurns.add(turnId);
            let notificationRecipients: Record<string, NotificationReason[]> | undefined;
            if (mutation.kind === 'appendMessage') {
              const append = mutation;
              notificationRecipients = {};
              const add = (identityId: string, reason: NotificationReason) => {
                if (identityId === actor.identityId) return;
                const reasons = (notificationRecipients![identityId] ??= []);
                if (!reasons.includes(reason)) reasons.push(reason);
              };
              const online = new Set(
                (await state.all('instances'))
                  .filter(
                    instance =>
                      instance.projectId === actor.projectId &&
                      instance.active &&
                      this.clock.now() - instance.lastSeen < this.limits.instanceMs,
                  )
                  .map(instance => instance.identityId),
              );
              const followers = (await state.all('follows')).filter(
                item => item.projectId === actor.projectId && item.threadId === request.resourceId,
              );
              for (const follow of followers)
                if (online.has(follow.identityId)) add(follow.identityId, 'followed_message');
              for (const name of append.mentions?.agents ?? [])
                add(
                  (await state.all('identities')).find(
                    item =>
                      item.projectId === actor.projectId &&
                      item.name.toLowerCase() === name.toLowerCase(),
                  )!.id,
                  'direct_mention',
                );
              if (append.mentions?.here)
                for (const follow of followers)
                  if (online.has(follow.identityId)) add(follow.identityId, 'here');
              if (append.mentions?.global)
                for (const identity of await state.all('identities'))
                  if (identity.projectId === actor.projectId && online.has(identity.id))
                    add(identity.id, 'global');
              for (const identity of await state.all('identities'))
                if (identity.projectId === actor.projectId && online.has(identity.id))
                  if (identity.id !== actor.identityId && !notificationRecipients[identity.id])
                    add(identity.id, 'thread_activity');
            }
            await (context = {
              id: operation.id,
              projectId: actor.projectId,
              resourceId: request.resourceId,
              resourceType: request.resourceType,
              turnRequestId: request.id,
              kind: mutation.kind,
              actor,
              ...(mutation.kind === 'appendMessage'
                ? {
                    followIdentityId: actor.identityId,
                    notificationRecipients,
                    notificationContent,
                    notificationCreatedAt: this.clock.now(),
                  }
                : {}),
              ...(notificationIntents.length
                ? { notificationIntents, notificationCreatedAt: this.clock.now() }
                : {}),
            });
          });
          return this.persist(operation, context);
        }),
      )
      .finally(() => this.committingTurns.delete(turnId));
  }
  private async finalize(pending: MutationContext, result?: StorageResult): Promise<void> {
    const intents: NotificationIntent[] = [...(pending.notificationIntents ?? [])];
    if (result && pending.notificationRecipients && 'messageId' in result && result.messageId)
      for (const [identityId, reasons] of Object.entries(pending.notificationRecipients))
        intents.push({
          identityId,
          resourceType: 'thread',
          resourceId: pending.resourceId,
          reasons,
          content: pending.notificationContent,
        });
    const wakeRecipients = result ? intents.map(intent => intent.identityId) : [];
    await this.control.update(async state => {
      (state.observationEvents ??= []).push({
        id: `content:${pending.id}`,
        projectId: pending.projectId,
        kind: result
          ? `${pending.resourceType}.${pending.kind}`
          : `${pending.resourceType}.write_failed`,
        at: this.clock.now(),
        actor: pending.actor.name,
        identityId: pending.actor.identityId,
        resourceType: pending.resourceType,
        resourceId: pending.resourceId,
        details: {
          ...pending.observation,
          ...(result
            ? {
                operationId: result.operationId,
                ...('messageId' in result ? { messageId: result.messageId } : {}),
              }
            : {}),
        },
      });
      if (pending.turnRequestId) {
        const request = (await state.get('requests', pending.turnRequestId))!;
        requireThat(
          request.resourceType !== 'files',
          'RESOURCE_TYPE_MISMATCH',
          'A pending commit requires a content turn.',
        );
        await this.finish(request, result ? 'COMMITTED' : 'FAILED', state);
        if (result) request.result = result;
      }
      if (result && !(await state.get('resources', pending.resourceId)))
        await state.set('resources', pending.resourceId, {
          id: pending.resourceId,
          projectId: pending.projectId,
          type: pending.resourceType,
          fence: '0',
          queueSequence: '0',
          present: true,
        });
      if (result && pending.followIdentityId && pending.resourceType === 'thread')
        await this.followIn(
          state,
          { ...pending.actor, identityId: pending.followIdentityId },
          pending.resourceId,
        );
      if (result && intents.length) {
        const merged = new Map<string, NotificationIntent>();
        for (const intent of intents) {
          const key = `${intent.identityId}:${intent.resourceType}:${intent.resourceId}`;
          const existing = merged.get(key);
          if (existing) existing.reasons = [...new Set([...existing.reasons, ...intent.reasons])];
          else merged.set(key, copy(intent));
        }
        for (const intent of merged.values()) {
          const messageId =
            intent.resourceType === 'thread' && 'messageId' in result
              ? result.messageId
              : undefined;
          const activityOnly =
            intent.resourceType === 'thread' &&
            intent.reasons.length === 1 &&
            intent.reasons[0] === 'thread_activity';
          const existing = activityOnly
            ? (await state.all('notifications')).find(
                notification =>
                  notification.projectId === pending.projectId &&
                  notification.identityId === intent.identityId &&
                  notification.threadId === intent.resourceId &&
                  notification.reasons.length === 1 &&
                  notification.reasons[0] === 'thread_activity',
              )
            : undefined;
          const notification = {
            id: existing?.id ?? uid(),
            projectId: pending.projectId,
            identityId: intent.identityId,
            resourceType: intent.resourceType,
            resourceId: intent.resourceId,
            eventId: messageId ?? pending.id,
            ...(intent.resourceType === 'thread'
              ? {
                  threadId: intent.resourceId,
                  messageId,
                  sequence: 'sequence' in result ? result.sequence : undefined,
                }
              : { ticketId: intent.resourceId }),
            senderIdentityId: pending.actor.identityId,
            senderName: pending.actor.name,
            createdAt: pending.notificationCreatedAt ?? this.clock.now(),
            reasons: intent.reasons,
            content: intent.content,
          };
          await state.set('notifications', notification.id, notification);
        }
      }

      await this.promote(state);
    });
    this.signalWake(wakeRecipients);
  }
  private async persist(
    operation: WriteOperation,
    context: MutationContext,
  ): Promise<MutationResult> {
    context.observation =
      operation.resourceType === 'thread'
        ? { title: operation.thread.title, revision: operation.thread.revision }
        : {
            title: operation.ticket.title,
            revision: operation.ticket.revision,
            state: operation.ticket.state,
            owner: operation.ticket.ownerName,
            dependsOn: operation.ticket.dependsOn,
          };
    const result = (await this.content.write(operation)) as MutationResult;
    await this.finalize(context, result);
    return result;
  }
  async inspect(): Promise<unknown> {
    await this.sweep();
    return await this.control.view(async s => ({
      epoch: this.epoch,
      projects: await s.all('projects'),
      turns: await mapAsync(await s.all('requests'), async r => ({
        ...(await this.statusIn(s, r)),
        projectId: r.projectId,
        turnId: r.turnId,
        owner: (await s.get('identities', r.identityId))?.name,
        identityId: r.identityId,
        instanceId: r.instanceId,
      })),
    }));
  }
  async hasPendingWork(): Promise<boolean> {
    return await this.control.view(async s =>
      (await s.all('requests')).some(r => activeStates.includes(r.state)),
    );
  }
  async forceRelease(turnId: string): Promise<void> {
    await this.sweep();
    await this.control.update(async state => {
      const request = (await state.all('requests')).find(r => r.turnId === turnId);
      requireThat(
        request?.state === 'CLAIMED' && !this.committingTurns.has(turnId),
        'NOT_CLAIMED',
        'Only a claimed turn can be force-released; committing writes are protected.',
      );
      await this.finish(request, 'RELEASED', state, 'force_released');
      await this.promote(state);
    });
  }
  async mcpTurnCredential(
    handle: string,
    turnToken: string,
  ): Promise<{
    id: string;
    fencingToken: string;
    baseRevision: string;
    resourceType: 'thread' | 'ticket';
    resourceId: string;
  }> {
    await this.sweep();
    return await this.control.view(async state => {
      const request = (await state.all('requests')).find(value => value.turnId === turnToken);
      if (request?.resourceType === 'files') {
        await this.claimedFiles(state, handle, turnToken);
        throw new BassfishError(
          'RESOURCE_TYPE_MISMATCH',
          'File locks use native filesystem tools and releaseTurn.',
        );
      }
      const current = await this.claimed(state, handle, turnToken, request?.fence ?? '');
      return {
        id: turnToken,
        fencingToken: current.fence!,
        baseRevision: current.baseRevision!,
        resourceType: current.resourceType,
        resourceId: current.resourceId,
      };
    });
  }
  private async claimedSnapshot(
    handle: string,
    requestId: string,
    requireActive = true,
  ): Promise<unknown> {
    await this.sweep();
    const file = await this.control.view(
      async state => await this.ownRequest(state, handle, requestId),
    );
    if (file.resourceType === 'files') {
      if (!requireActive && file.state !== 'CLAIMED')
        return await this.control.view(async state => await this.statusIn(state, file));
      return await this.control.view(async state =>
        this.fileClaim(await this.claimedFiles(state, handle, file.turnId ?? '')),
      );
    }
    const request = await this.control.view(async state => {
      const current = await this.ownRequest(state, handle, requestId);
      requireThat(
        current.resourceType !== 'files',
        'RESOURCE_TYPE_MISMATCH',
        'A content turn is required.',
      );
      requireThat(
        current.turnId && current.fence && current.baseRevision && current.expiresAt,
        'TURN_REQUEST_UNAVAILABLE',
        'This request has not acquired a turn.',
      );
      if (requireActive) await this.claimed(state, handle, current.turnId, current.fence);
      return await copy(current);
    });
    const snapshot =
      request.resourceType === 'thread'
        ? await this.content.snapshot(
            request.projectId,
            request.resourceId,
            20,
            undefined,
            request.baseRevision,
          )
        : await this.content.ticketSnapshot(
            request.projectId,
            request.resourceId,
            undefined,
            request.baseRevision,
          );
    if (requireActive) {
      await this.sweep();
      await this.control.view(
        async state => await this.claimed(state, handle, request.turnId!, request.fence!),
      );
    }
    const page =
      snapshot.resourceType === 'thread'
        ? {
            type: 'thread',
            thread: snapshot.thread,
            messages: snapshot.messages,
            truncated: snapshot.truncated,
          }
        : {
            type: 'ticket',
            ticket: describeTicket(
              snapshot.ticket,
              await this.content.listTickets(request.projectId),
            ),
            ...snapshot.page,
          };
    return {
      requestId: request.id,
      target: { type: snapshot.resourceType, id: request.resourceId },
      turn: { id: request.turnId, fencingToken: request.fence, expiresAt: iso(request.expiresAt!) },
      snapshot: { revision: request.baseRevision },
      page,
      nextCursor:
        snapshot.resourceType === 'thread' ? snapshot.nextBefore : snapshot.page.nextCursor,
      serverTime: iso(this.clock.now()),
    };
  }
  private async ensureTurnTask(
    handle: string,
    requestId: string,
  ): Promise<Record<string, unknown>> {
    return await this.control.update(async state => {
      const actor = await this.actor(state, handle);
      const request = await this.ownRequest(state, handle, requestId);
      requireThat(
        request.instanceId === actor.instanceId,
        'NOT_TURN_OWNER',
        'Rebind this queue request before resuming it.',
      );
      requireThat(
        request.state === 'QUEUED' || request.state === 'READY',
        'TURN_REQUEST_UNAVAILABLE',
        'Only a queued request can become a Task.',
      );
      let task = (await state.all('tasks')).find(value => value.requestId === request.id);
      if (!task) {
        const now = this.clock.now();
        request.deliveryMode = 'task';
        task = {
          id: request.id,
          projectId: actor.projectId,
          identityId: actor.identityId,
          requestId: request.id,
          status: 'working',
          statusMessage:
            request.state === 'READY'
              ? 'Turn ready; poll the task to claim it.'
              : 'Waiting for the turn.',
          createdAt: now,
          updatedAt: now,
          discardAt: request.queueUntil,
        };
        await state.set('tasks', task.id, task);
      }
      return this.taskView(task, false);
    });
  }
  async acquireMcpTurn(
    handle: string,
    args: Record<string, unknown>,
    signal: AbortSignal | undefined,
    taskCapable: boolean,
  ): Promise<unknown> {
    let status: Record<string, unknown>;
    if (args.target) {
      const target = args.target as {
        type: 'thread' | 'ticket' | 'files';
        threadId?: string;
        ticketId?: string;
        paths?: FileTarget[];
      };
      status =
        target.type === 'files'
          ? await this.requestFileTurn(handle, target.paths!, taskCapable ? 'task' : 'ticket')
          : await this.requestResourceTurn(
              handle,
              target.type,
              target.type === 'thread' ? target.threadId! : target.ticketId!,
              taskCapable ? 'task' : 'ticket',
            );
    } else {
      const requestToken = args.requestToken as string;
      await this.sweep();
      status = await this.control.view(
        async state =>
          await this.statusIn(state, await this.ownRequest(state, handle, requestToken)),
      );
    }
    if (taskCapable && (status.state === 'queued' || status.state === 'ready')) {
      return { task: await this.ensureTurnTask(handle, status.requestId as string) };
    }
    if (status.state === 'queued' || status.state === 'ready') {
      status = (await this.waitForTurn(
        handle,
        status.requestId as string,
        args.timeoutMs as number,
        signal,
      )) as Record<string, unknown>;
    }
    if (status.state === 'offered')
      return presentClaim(await this.claimTurn(handle, status.offerId as string, 20));
    if (status.state === 'claimed')
      return presentClaim(await this.claimedSnapshot(handle, status.requestId as string));
    if (status.state === 'queued' || status.state === 'ready') return presentTurnStatus(status);
    throw new BassfishError(
      'TURN_REQUEST_UNAVAILABLE',
      `The turn request is ${String(status.state)}; start a new acquisition.`,
    );
  }
  async callMcp(
    handle: string,
    name: string,
    input: unknown,
    signal?: AbortSignal,
    options: {
      taskCapable?: boolean;
    } = {},
  ): Promise<unknown> {
    requireThat(Object.hasOwn(mcpSchemas, name), 'UNKNOWN_TOOL', 'Unknown Bassfish MCP operation.');
    const parsed = mcpSchemas[name as McpToolName].safeParse(input);
    requireThat(
      parsed.success,
      'INVALID_ARGUMENT',
      'Arguments do not match the MCP operation schema.',
    );
    await this.heartbeat(handle);
    return dispatchMcp(
      this,
      handle,
      name,
      parsed.data as Record<string, unknown>,
      signal,
      Boolean(options.taskCapable),
    );
  }
  async call(
    handle: string,
    name: string,
    input: unknown,
    signal?: AbortSignal,
    options: {
      taskCapable?: boolean;
    } = {},
  ): Promise<unknown> {
    requireThat(Object.hasOwn(adminSchemas, name), 'UNKNOWN_TOOL', 'Unknown Bassfish operation.');
    const parsed = adminSchemas[name as AdminToolName].safeParse(input);
    requireThat(parsed.success, 'INVALID_ARGUMENT', 'Arguments do not match the operation schema.');
    await this.heartbeat(handle);
    return dispatchAdmin(
      this,
      handle,
      name,
      parsed.data as Record<string, unknown>,
      signal,
      options,
    );
  }
}
