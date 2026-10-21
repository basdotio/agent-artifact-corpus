import { increment, requireThat } from './domain.js';
import type { Actor, Ticket, TicketMutation } from './domain.js';
import { applyUnifiedPatch } from './markdown.js';

export const normalizeDependencies = (dependencies: string[]): string[] => {
  requireThat(
    dependencies.length <= 64,
    'INVALID_ARGUMENT',
    'A ticket may have at most 64 dependencies.',
  );
  const sorted = [...dependencies].sort();
  requireThat(
    new Set(sorted).size === sorted.length,
    'INVALID_ARGUMENT',
    'Ticket dependencies must be unique.',
  );
  return sorted;
};

export function validateTicketGraph(tickets: Ticket[]): void {
  const byId = new Map(tickets.map(ticket => [ticket.id, ticket]));
  for (const ticket of tickets) {
    requireThat(
      !ticket.dependsOn.includes(ticket.id),
      'DEPENDENCY_CYCLE',
      'A ticket cannot depend on itself.',
    );
    for (const id of ticket.dependsOn)
      requireThat(
        byId.has(id),
        'DEPENDENCY_NOT_FOUND',
        `Dependency ${id} is not a ticket in this project.`,
      );
  }
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const visit = (id: string): void => {
    if (visited.has(id)) return;
    requireThat(!visiting.has(id), 'DEPENDENCY_CYCLE', 'Ticket dependencies must form a DAG.');
    visiting.add(id);
    for (const dependency of byId.get(id)!.dependsOn) visit(dependency);
    visiting.delete(id);
    visited.add(id);
  };
  for (const id of byId.keys()) visit(id);
}

export interface TicketStatus {
  blocks: string[];
  blockedBy: string[];
  dependenciesSatisfied: boolean;
  ready: boolean;
}

export function ticketStatuses(tickets: Ticket[]): Map<string, TicketStatus> {
  const byId = new Map(tickets.map(value => [value.id, value]));
  const blocks = new Map(tickets.map(ticket => [ticket.id, [] as string[]]));
  for (const ticket of tickets) {
    for (const dependencyId of ticket.dependsOn) blocks.get(dependencyId)?.push(ticket.id);
  }
  return new Map(
    tickets.map(ticket => {
      const blockedBy = ticket.dependsOn.filter(id => byId.get(id)?.state !== 'done');
      const dependenciesSatisfied = blockedBy.length === 0;
      return [
        ticket.id,
        {
          blocks: blocks.get(ticket.id)!.sort(),
          blockedBy,
          dependenciesSatisfied,
          ready: ticket.state === 'todo' && dependenciesSatisfied,
        },
      ];
    }),
  );
}

export function prepareTicket(
  ticket: Ticket,
  mutation: TicketMutation,
  actor: Actor,
  at: string,
): Ticket {
  const next = structuredClone(ticket);
  switch (mutation.kind) {
    case 'updateTicket':
      requireThat(
        mutation.title !== undefined ||
          mutation.description !== undefined ||
          mutation.owner !== undefined ||
          mutation.state !== undefined ||
          mutation.dependsOn !== undefined,
        'INVALID_ARGUMENT',
        'Provide at least one ticket metadata field.',
      );
      if (mutation.title !== undefined) next.title = mutation.title;
      if (mutation.description !== undefined) next.description = mutation.description;
      if (mutation.owner !== undefined) next.owner = mutation.owner;
      if (mutation.state !== undefined) next.state = mutation.state;
      if (mutation.dependsOn !== undefined)
        next.dependsOn = normalizeDependencies(mutation.dependsOn);
      break;
    case 'replaceTicketBody':
      next.body = mutation.body;
      break;
    case 'appendTicketBody':
      next.body += mutation.body;
      break;
    case 'patchTicketBody':
      next.body = applyUnifiedPatch(ticket.body, mutation.patch);
      break;
  }
  requireThat(
    Buffer.byteLength(next.body, 'utf8') <= 256 * 1024,
    'CONTENT_TOO_LARGE',
    'The resulting ticket body exceeds 256 KiB.',
  );
  requireThat(
    JSON.stringify({
      ...next,
      revision: 'x',
      lastEditor: 'x',
      lastEditorName: 'x',
      updatedAt: 'x',
    }) !==
      JSON.stringify({
        ...ticket,
        revision: 'x',
        lastEditor: 'x',
        lastEditorName: 'x',
        updatedAt: 'x',
      }),
    'NO_CHANGE',
    'The ticket mutation makes no change.',
  );
  next.revision = increment(ticket.revision);
  next.lastEditor = actor.identityId;
  next.lastEditorName = actor.name;
  next.updatedAt = at;
  return next;
}
