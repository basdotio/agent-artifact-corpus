import type { FileTarget, Snapshot, Thread, Ticket, TicketSnapshot } from './domain.js';

export interface ActivityDraft {
  id: string;
  projectId: string;
  kind: string;
  at: number;
  actor?: string;
  identityId?: string;
  resourceType: 'thread' | 'ticket' | 'files' | 'agent' | 'project';
  resourceId: string;
  details: Record<string, unknown>;
}
export interface ActivityEvent extends ActivityDraft {
  cursor: string;
}
export interface ActivityQuery {
  projectId: string;
  before?: string;
  limit?: number;
  actor?: string;
  resourceId?: string;
  kind?: string;
}
export interface ActivityPage {
  events: ActivityEvent[];
  nextBefore: string | null;
  recordingSince: number;
  retainedSince: number | null;
  buckets: number[];
  bucketStart: number;
}
export type ObservedThread = Thread & {
  updatedAt: string;
  latestAuthor: string | null;
  preview: string;
  participants: string[];
};
export type ObservedTicket = Omit<Ticket, 'body'> & {
  blockedBy: string[];
  blocks: string[];
  ready: boolean;
};
export interface ContentObservation {
  threads: ObservedThread[];
  tickets: ObservedTicket[];
  totals: { threads: number; tickets: number; states: Record<string, number> };
  nextThreadOffset: number | null;
  nextTicketOffset: number | null;
}
export interface ObservedAgent {
  id: string;
  name: string;
  online: boolean;
  host: string | null;
  workspace: string | null;
  lastSeen: number | null;
}
export interface ObservedTurn {
  id: string;
  projectId: string;
  resourceType: 'thread' | 'ticket' | 'project' | 'files';
  resourceId?: string;
  state: string;
  owner: string;
  identityId: string;
  workspace: string;
  paths?: FileTarget[];
  pathCount?: number;
  nextPathOffset?: number | null;
  blockerCount?: number;
  nextBlockerOffset?: number | null;
  createdAt: number;
  claimedAt?: number;
  expiresAt?: number;
  reason?: string;
  blockers: {
    id: string;
    owner: string;
    project: string;
    paths: FileTarget[];
    overlapCount?: number;
    reason: 'held' | 'earlier_request';
  }[];
}
export interface ObservationSnapshot {
  protocolVersion: 2;
  epoch: string;
  cursor: string;
  at: number;
  project: { id: string; commonDir: string } | null;
  status: 'ready' | 'empty' | 'content_unavailable';
  contentError?: string;
  agents: ObservedAgent[];
  turns: ObservedTurn[];
  coordinationTotals?: { agents: number; online: number; turns: number; files: number };
  nextAgentOffset?: number | null;
  nextTurnOffset?: number | null;
  content: ContentObservation | null;
  activity: ActivityPage | null;
}
export type ObservedThreadDetail = Snapshot;
export type ObservedTicketDetail = Omit<TicketSnapshot, 'ticket'> & {
  ticket: Omit<Ticket, 'body'>;
};
export interface ObservationGraph {
  tickets: ObservedTicket[];
  hidden: number;
}
