import { BassfishError, requireThat, type Thread, type Ticket } from '../domain.js';
import { ticketStatuses } from '../ticket.js';

export type TicketMetadata = Omit<Ticket, 'body'> & {
  contentBytes: number;
  blocks: string[];
  blockedBy: string[];
  dependenciesSatisfied: boolean;
  ready: boolean;
};

export const compare = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);

export function sortThreads(threads: Thread[]): Thread[] {
  return [...threads].sort((a, b) => compare(a.createdAt, b.createdAt) || compare(a.id, b.id));
}

export function encodeCursor(pair: [string, string]): string {
  return Buffer.from(JSON.stringify(pair)).toString('base64url');
}

export function decodeCursor(cursor: unknown): [string, string] | undefined {
  if (!cursor) return undefined;
  let value: unknown;
  try {
    value = JSON.parse(Buffer.from(String(cursor), 'base64url').toString('utf8'));
  } catch {
    throw new BassfishError('INVALID_CURSOR', 'The cursor is invalid.');
  }
  requireThat(
    Array.isArray(value) && value.length === 2 && value.every(item => typeof item === 'string'),
    'INVALID_CURSOR',
    'The cursor is invalid.',
  );
  return value as [string, string];
}

export function describeTicket(ticket: Ticket, tickets: Ticket[]): TicketMetadata {
  const { body, ...metadata } = ticket;
  const status = ticketStatuses(tickets).get(ticket.id);
  requireThat(status, 'NOT_FOUND', 'Ticket not found in this project.');
  return { ...metadata, contentBytes: Buffer.byteLength(body, 'utf8'), ...status };
}

export function describeTickets(tickets: Ticket[]): TicketMetadata[] {
  const statuses = ticketStatuses(tickets);
  return tickets.map(ticket => {
    const { body, ...metadata } = ticket;
    return {
      ...metadata,
      contentBytes: Buffer.byteLength(body, 'utf8'),
      ...statuses.get(ticket.id)!,
    };
  });
}
