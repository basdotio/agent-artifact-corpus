import type { ActivityDraft } from './observation-types.js';

export class BassfishError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'BassfishError';
  }
}

export function requireThat(condition: unknown, code: string, message: string): asserts condition {
  if (!condition) throw new BassfishError(code, message);
}

export interface Actor {
  projectId: string;
  identityId: string;
  instanceId: string;
  name: string;
}
interface Project {
  id: string;
  commonDir: string;
}
interface Identity {
  id: string;
  projectId: string;
  name: string;
}
export interface Instance {
  id: string;
  projectId: string;
  identityId: string;
  handle: string;
  epoch: string;
  active: boolean;
  lastSeen: number;
  workspace: string;
  host?: AgentHost;
  hostSessionId?: string;
}
export type AgentHost = 'claude' | 'codex' | 'opencode';
export type ContentResourceType = 'thread' | 'ticket';
export type ResourceType = ContentResourceType;
interface Resource {
  id: string;
  projectId: string;
  type: ResourceType;
  fence: string;
  queueSequence: string;
  present: boolean;
}
export type TurnState =
  | 'QUEUED'
  | 'READY'
  | 'OFFERED'
  | 'CLAIMED'
  | 'COMMITTING'
  | 'COMMITTED'
  | 'RELEASED'
  | 'EXPIRED'
  | 'CANCELLED'
  | 'FAILED';
interface TurnRequestBase {
  id: string;
  projectId: string;
  identityId: string;
  instanceId: string;
  sequence: string;
  state: TurnState;
  createdAt: number;
  queueUntil: number;
  reconnectUntil?: number;
  offerId?: string;
  claimBy?: number;
  turnId?: string;
  finishedAt?: number;
  deliveryMode: 'ticket' | 'task';
  updatedAt: number;
  claimedAt?: number;
  terminalReason?: string;
}
export interface ContentTurnRequest extends TurnRequestBase {
  resourceType: ResourceType;
  resourceId: string;
  fence?: string;
  baseRevision?: string;
  expiresAt?: number;
  result?: StorageResult;
}
export interface FileTarget {
  path: string;
  kind: 'file' | 'directory';
}
export interface FileTurnRequest extends TurnRequestBase {
  resourceType: 'files';
  paths: FileTarget[];
}
export type TurnRequest = ContentTurnRequest | FileTurnRequest;
type TaskStatus = 'working' | 'completed' | 'failed' | 'cancelled';
export interface DurableTask {
  id: string;
  projectId: string;
  identityId: string;
  requestId: string;
  status: TaskStatus;
  statusMessage?: string;
  createdAt: number;
  updatedAt: number;
  discardAt: number;
  result?: Record<string, unknown>;
  error?: { code: number; message: string; data?: Record<string, unknown> };
}
export interface WorkTask {
  id: string;
  projectId: string;
  identityId: string;
  status: TaskStatus;
  statusMessage?: string;
  createdAt: number;
  updatedAt: number;
  discardAt: number;
  result?: Record<string, unknown>;
  error?: { code: number; message: string; data?: Record<string, unknown> };
}
export interface MutationContext {
  id: string;
  projectId: string;
  resourceId: string;
  resourceType: ResourceType;
  turnRequestId?: string;
  kind: string;
  actor: Actor;
  followIdentityId?: string;
  notificationRecipients?: Record<string, NotificationReason[]>;
  notificationIntents?: NotificationIntent[];
  notificationContent?: NotificationContent;
  notificationCreatedAt?: number;
  observation?: Record<string, unknown>;
}
export type NotificationReason =
  | 'direct_mention'
  | 'here'
  | 'global'
  | 'followed_message'
  | 'thread_activity'
  | 'ticket_assigned'
  | 'ticket_ready';
export interface NotificationIntent {
  identityId: string;
  resourceType: 'thread' | 'ticket';
  resourceId: string;
  reasons: NotificationReason[];
  content?: NotificationContent;
}
export type NotificationContent =
  | {
      kind: 'thread_message';
      threadTitle: string;
      body: string;
      retracted: boolean;
    }
  | {
      kind: 'ticket_summary';
      title: string;
      state: string;
      owner: string;
    };
interface ThreadFollow {
  projectId: string;
  threadId: string;
  identityId: string;
  createdAt: number;
}
export interface Notification {
  id: string;
  projectId: string;
  identityId: string;
  resourceType: 'thread' | 'ticket';
  resourceId: string;
  eventId: string;
  threadId?: string;
  ticketId?: string;
  messageId?: string;
  sequence?: string;
  senderIdentityId: string;
  senderName: string;
  createdAt: number;
  reasons: NotificationReason[];
  content?: NotificationContent;
  lastDeliveredWakeKey?: string;
  lastDeliveredAt?: number;
}
interface HostSessionBinding {
  projectId: string;
  identityId: string;
  host: AgentHost;
  sessionId: string;
  wakeKey: string;
  createdAt: number;
  updatedAt: number;
}
export interface NotificationBatchRecord {
  id: string;
  projectId: string;
  identityId: string;
  sessionId?: string;
  status:
    'reserved' | 'submitting' | 'accepted' | 'uncertain' | 'presented' | 'handled' | 'released';
  entries: Notification[];
  acknowledged: number[];
  payload: import('./notification-delivery.js').DeliveryBatch;
  createdAt: number;
  finishedAt?: number;
  issue?: string;
}
export interface ControlRows {
  notificationBatches: Record<string, NotificationBatchRecord>;
  /** Transaction-local activity outbox; never loaded as retained history. */
  observationEvents?: ActivityDraft[];
  projects: Record<string, Project>;
  identities: Record<string, Identity>;
  instances: Record<string, Instance>;
  resources: Record<string, Resource>;
  requests: Record<string, TurnRequest>;
  tasks: Record<string, DurableTask>;
  workTasks: Record<string, WorkTask>;
  follows: Record<string, ThreadFollow>;
  notifications: Record<string, Notification>;
  hostSessionBindings: Record<string, HostSessionBinding>;
  wallClockHighWaterMs: number;
  fileQueueSequence: string;
}
export type ControlState = import('./storage/rows.js').CoordinationState;
export interface ControlStore {
  activity: { head(): Promise<string>; gap(projectId: string, cursor: string): Promise<boolean> };
  view<T>(fn: (state: ControlState) => T | Promise<T>): Promise<T>;
  update<T>(fn: (state: ControlState) => T | Promise<T>): Promise<T>;
  readTransaction<T>(fn: () => Promise<T>): Promise<T>;
  inTransaction(): boolean;
  transaction<T>(fn: () => Promise<T>): Promise<T>;
  afterCommit(fn: () => void): void;
  close(): Promise<void>;
}
export interface Clock {
  now(): number;
  wallNow(): number;
  discontinuity(): boolean;
}
type ThreadState = 'active' | 'archived' | 'deleted';
export interface Thread {
  id: string;
  title: string;
  description: string;
  state: ThreadState;
  revision: string;
  headSequence: string;
  creator: string;
  createdAt: string;
}
type TicketState = 'todo' | 'in_progress' | 'blocked' | 'done';
export interface Ticket {
  id: string;
  title: string;
  description: string;
  owner: string;
  ownerName: string;
  state: TicketState;
  body: string;
  dependsOn: string[];
  revision: string;
  creator: string;
  creatorName: string;
  lastEditor: string;
  lastEditorName: string;
  createdAt: string;
  updatedAt: string;
}
export interface Message {
  id: string;
  threadId: string;
  sequence: string;
  identityId: string;
  name: string;
  instanceId: string;
  createdAt: string;
  body: string;
  mentions?: { agents: string[]; here: boolean; global?: boolean };
  retracted?: boolean;
}
export interface Snapshot {
  resourceType: 'thread';
  thread: Thread;
  revision: string;
  messages: Message[];
  truncated: boolean;
  nextBefore: string | null;
}
export interface BodyPage {
  text: string;
  startLine: number;
  endLine: number;
  startByte: number;
  endByte: number;
  truncated: boolean;
  nextCursor: string | null;
}
export interface TicketSnapshot {
  resourceType: 'ticket';
  ticket: Ticket;
  revision: string;
  page: BodyPage;
}
export type ThreadMutation =
  | {
      kind: 'appendMessage';
      body: string;
      mentions?: { agents: string[]; here: boolean; global?: boolean };
    }
  | { kind: 'renameThread'; title: string }
  | { kind: 'setThreadDescription'; description: string }
  | { kind: 'archiveThread' }
  | { kind: 'activateThread' }
  | { kind: 'deleteThread' }
  | { kind: 'retractMessage'; messageId: string }
  | { kind: 'reinstateMessage'; messageId: string };
export type TicketMutation =
  | {
      kind: 'updateTicket';
      title?: string;
      description?: string;
      owner?: string;
      state?: TicketState;
      dependsOn?: string[];
    }
  | { kind: 'replaceTicketBody'; body: string }
  | { kind: 'appendTicketBody'; body: string }
  | { kind: 'patchTicketBody'; patch: string };
export type Mutation = ThreadMutation | TicketMutation;
interface ThreadWriteOperation {
  id: string;
  actor: Actor;
  resourceId: string;
  at: string;
  resourceType: 'thread';
  thread: Thread;
  mutation: ThreadMutation | { kind: 'createThread' };
  visibilityChanges?: { messageId: string; visible: boolean }[];
}
interface TicketWriteOperation {
  id: string;
  actor: Actor;
  resourceId: string;
  at: string;
  resourceType: 'ticket';
  ticket: Ticket;
  mutation: TicketMutation | { kind: 'createTicket' };
}
export type WriteOperation = ThreadWriteOperation | TicketWriteOperation;
export interface MutationResult {
  resourceId: string;
  previousRevision: string;
  revision: string;
  operationId: string;
  messageId?: string;
  sequence?: string;
}
export interface HistoryEntry {
  operationId: string;
  kind: string;
  actorIdentityId: string;
  actorName: string;
  instanceId: string;
  createdAt: string;
  reason: string | null;
  beforeRevision: string;
  afterRevision: string;
}
interface MessageVisibility {
  messageId: string;
  threadId: string;
  visible: boolean;
  threadRevision: string;
  operationId: string;
  createdAt: string;
}
export interface CurrentProject {
  exportedAt: string;
  threads: Thread[];
  messages: Message[];
  tickets: Ticket[];
  visibility: MessageVisibility[];
}
export interface ProjectHistoryEntry {
  resourceId: string;
  resourceType: ContentResourceType;
  revision: string;
  operationId: string;
  kind: string;
  actorIdentityId: string;
  actorName: string;
  instanceId: string;
  createdAt: string;
}
export type StorageResult = MutationResult;
export interface ContentStore {
  threadDelta(
    projectId: string,
    resourceId: string,
    fromRevision: string,
    revision?: string,
    before?: string,
  ): Promise<Snapshot>;
  messageAt(
    projectId: string,
    resourceId: string,
    messageId: string,
    revision: string,
  ): Promise<Message>;
  listTicketMetadata(projectId: string): Promise<Ticket[]>;
  ensureProject(projectId: string): Promise<void>;
  listThreads(projectId: string): Promise<Thread[]>;
  listTickets(projectId: string): Promise<Ticket[]>;
  resourceType(projectId: string, resourceId: string): Promise<ContentResourceType>;
  snapshot(
    projectId: string,
    resourceId: string,
    limit: number,
    before?: string,
    revision?: string,
  ): Promise<Snapshot>;
  ticketSnapshot(
    projectId: string,
    resourceId: string,
    cursor?: string,
    revision?: string,
  ): Promise<TicketSnapshot>;
  history(
    projectId: string,
    resourceType: ContentResourceType,
    resourceId: string,
  ): Promise<HistoryEntry[]>;
  projectSnapshot(projectId: string): Promise<CurrentProject>;
  projectHistory(projectId: string): Promise<ProjectHistoryEntry[]>;
  write(operation: WriteOperation): Promise<StorageResult>;
  close(): Promise<void>;
}
export const activeStates: TurnState[] = ['QUEUED', 'READY', 'OFFERED', 'CLAIMED', 'COMMITTING'];
export const reservedStates: TurnState[] = ['READY', 'OFFERED', 'CLAIMED', 'COMMITTING'];
export const increment = (value: string): string => (BigInt(value) + 1n).toString();

export function prepareMutation(thread: Thread, mutation: ThreadMutation): Thread {
  const next = { ...thread, revision: increment(thread.revision) };
  switch (mutation.kind) {
    case 'appendMessage':
      requireThat(
        thread.state === 'active',
        'RESOURCE_ARCHIVED',
        'Activate the thread before appending.',
      );
      next.headSequence = increment(thread.headSequence);
      break;
    case 'renameThread':
      requireThat(thread.title !== mutation.title, 'NO_CHANGE', 'The title is unchanged.');
      next.title = mutation.title;
      break;
    case 'setThreadDescription':
      requireThat(
        thread.description !== mutation.description,
        'NO_CHANGE',
        'The description is unchanged.',
      );
      next.description = mutation.description;
      break;
    case 'archiveThread':
      requireThat(thread.state === 'active', 'NO_CHANGE', 'Only an active thread can be archived.');
      next.state = 'archived';
      break;
    case 'activateThread':
      requireThat(thread.state !== 'active', 'NO_CHANGE', 'The thread is already active.');
      next.state = 'active';
      break;
    case 'deleteThread':
      requireThat(thread.state !== 'deleted', 'NO_CHANGE', 'The thread is already deleted.');
      next.state = 'deleted';
      break;
    case 'retractMessage':
    case 'reinstateMessage':
      break;
  }
  return next;
}

export function bodyPage(
  body: string,
  cursor?: string,
  maxLines = 200,
  maxBytes = 32 * 1024,
): BodyPage {
  let startByte = 0;
  if (cursor !== undefined) {
    requireThat(/^(0|[1-9][0-9]*)$/.test(cursor), 'INVALID_CURSOR', 'The body cursor is invalid.');
    startByte = Number(cursor);
  }
  const bytes = Buffer.from(body, 'utf8');
  requireThat(
    startByte >= 0 && startByte <= bytes.length,
    'INVALID_CURSOR',
    'The body cursor is outside the body.',
  );
  let endByte = Math.min(bytes.length, startByte + maxBytes);
  while (endByte > startByte && (bytes[endByte] ?? 0) >= 0x80 && (bytes[endByte] ?? 0) < 0xc0)
    endByte--;
  const prefix = bytes.subarray(0, startByte).toString('utf8');
  const candidate = bytes.subarray(startByte, endByte).toString('utf8');
  const lines = candidate.split('\n');
  if (lines.length > maxLines) {
    const limited = lines.slice(0, maxLines).join('\n') + '\n';
    endByte = startByte + Buffer.byteLength(limited);
  }
  const text = bytes.subarray(startByte, endByte).toString('utf8');
  const startLine = prefix.split('\n').length;
  const endLine = startLine + Math.max(0, text.split('\n').length - 1);
  return {
    text,
    startLine,
    endLine,
    startByte,
    endByte,
    truncated: endByte < bytes.length,
    nextCursor: endByte < bytes.length ? String(endByte) : null,
  };
}
