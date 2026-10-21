import { basename, relative } from 'node:path';
import type {
  ActivityEvent,
  ActivityPage,
  ObservationGraph,
  ObservationSnapshot,
  ObservedAgent,
  ObservedThreadDetail,
  ObservedTicket,
  ObservedTicketDetail,
  ObservedTurn,
} from '../observation-types.js';
import type { SonarState } from './client.js';
import {
  Canvas,
  age,
  markdown,
  stateTone,
  timeLabel,
  wrapped,
  type Rect,
  type Tone,
} from './visual.js';
import { paintGraph, type GraphLayout } from './graph.js';

export type View = 'monitor' | 'threads' | 'files' | 'tickets' | 'activity';
export const views: View[] = ['monitor', 'threads', 'files', 'tickets', 'activity'];
export interface ScreenModel {
  view: View;
  focus: number;
  selected: Record<string, string>;
  scroll: number;
  horizontal: number;
  now: number;
  paused: boolean;
  pendingEvents: string;
  query: string;
  filtering: boolean;
  modal: 'help' | 'agents' | 'components' | 'dependencies' | 'event' | null;
  event?: ActivityEvent;
  reservation?: ObservedTurn;
  ticketSort?: 'updated' | 'title' | 'owner' | 'state';
  ticketMode: 'graph' | 'board' | 'list';
  threadState: 'active' | 'archived' | 'deleted' | 'all';
  ticketState: 'todo' | 'in_progress' | 'blocked' | 'done' | 'all';
  thread?: ObservedThreadDetail;
  ticket?: ObservedTicketDetail;
  graph?: ObservationGraph;
  layout: GraphLayout;
  pan: { x: number; y: number };
  activity?: ActivityPage;
  seen: Record<string, string>;
  collapsed: Set<string>;
  error?: string;
}
export const initialScreen = (view: View): ScreenModel => ({
  view,
  focus: 0,
  selected: {},
  scroll: 0,
  horizontal: 0,
  now: Date.now(),
  paused: false,
  pendingEvents: '0',
  query: '',
  filtering: false,
  modal: null,
  ticketMode: 'graph',
  threadState: 'active',
  ticketState: 'all',
  layout: { nodes: [], edges: [], width: 0, height: 0 },
  pan: { x: 0, y: 0 },
  seen: {},
  collapsed: new Set(),
});
function eventLabel(event: ActivityEvent): string {
  const title = String(event.details.title ?? event.resourceId.slice(0, 8));
  const labels: Record<string, string> = {
    appendMessage: `Posted in ${title}`,
    createThread: `Created conversation ${title}`,
    createTicket: `Created ticket ${title}`,
    updateTicket: `${title} · ${event.details.state ?? 'updated'}`,
    replaceTicketBody: `Updated ${title}`,
    appendTicketBody: `Appended to ${title}`,
    patchTicketBody: `Patched ${title}`,
    retractMessage: `Retracted a message in ${title}`,
  };
  const action = event.kind.split('.').at(-1)!;
  if (labels[action]) return labels[action];
  if (event.resourceType === 'files') {
    const paths = event.details.paths as { path: string }[] | undefined;
    return `${action} ${paths?.map(p => basename(p.path)).join(', ') ?? ''}${event.details.reason ? ` · ${event.details.reason}` : ''}`;
  }
  return `${event.kind.replaceAll('.', ' · ').replaceAll('_', ' ')}${event.resourceType === 'thread' || event.resourceType === 'ticket' ? ` · ${title}` : ''}`;
}
function filtered<T>(items: T[], query: string, text: (item: T) => string): T[] {
  const term = query.toLowerCase().replace(/^(@|type:|resource:)/, '');
  return !term ? items : items.filter(item => text(item).toLowerCase().includes(term));
}
function sortedTickets(tickets: ObservedTicket[], ui: ScreenModel): ObservedTicket[] {
  return [...tickets].sort(
    (a, b) =>
      (ui.ticketSort === 'title'
        ? a.title.localeCompare(b.title)
        : ui.ticketSort === 'owner'
          ? a.ownerName.localeCompare(b.ownerName)
          : ui.ticketSort === 'state'
            ? a.state.localeCompare(b.state)
            : b.updatedAt.localeCompare(a.updatedAt)) || a.id.localeCompare(b.id),
  );
}
export function itemsFor(state: SonarState, ui: ScreenModel): { id: string; label: string }[] {
  const snapshot = state.snapshot;
  const view =
    ui.modal === 'components' || ui.modal === 'dependencies'
      ? 'tickets'
      : ui.modal === 'agents'
        ? 'agents'
        : ui.view === 'monitor'
          ? ['threads', 'files', 'tickets', 'agents', 'activity'][ui.focus]
          : ui.view;
  if (view === 'threads')
    return filtered(
      snapshot?.content?.threads ?? [],
      ui.query,
      t => `${t.title} ${t.participants.join(' ')}`,
    ).map(t => ({ id: t.id, label: t.title }));
  if (view === 'files')
    return filtered(
      snapshot?.turns.filter(t => t.resourceType === 'files') ?? [],
      ui.query,
      t => `${t.owner} ${t.paths?.map(p => p.path).join(' ')}`,
    )
      .sort(
        (a, b) =>
          Number(b.state === 'QUEUED') - Number(a.state === 'QUEUED') || a.createdAt - b.createdAt,
      )
      .map(t => ({ id: t.id, label: t.paths?.map(p => basename(p.path)).join(', ') ?? '' }));
  if (view === 'agents')
    return filtered(snapshot?.agents ?? [], ui.query, a => a.name).map(a => ({
      id: a.id,
      label: a.name,
    }));
  if (view === 'tickets') {
    let tickets = [
      ...new Map(
        [...(snapshot?.content?.tickets ?? []), ...(ui.graph?.tickets ?? [])].map(t => [t.id, t]),
      ).values(),
    ];
    if (ui.modal === 'dependencies') {
      const current = tickets.find(t => t.id === ui.selected.tickets);
      const related = new Set([...(current?.dependsOn ?? []), ...(current?.blocks ?? [])]);
      tickets = tickets.filter(t => related.has(t.id));
    }
    return filtered(sortedTickets(tickets, ui), ui.query, t => `${t.title} ${t.ownerName}`)
      .filter(t => ui.ticketState === 'all' || t.state === ui.ticketState)
      .map(t => ({ id: t.id, label: t.title }));
  }
  return filtered(
    ui.activity?.events ?? snapshot?.activity?.events ?? [],
    ui.query,
    e => `${e.actor} ${e.kind} ${e.resourceId} ${eventLabel(e)}`,
  ).map(e => ({ id: e.id, label: eventLabel(e) }));
}
export function selectionKey(ui: ScreenModel): string {
  if (ui.modal) return ui.modal;
  return ui.view === 'monitor'
    ? ['threads', 'files', 'tickets', 'agents', 'activity'][ui.focus]!
    : ui.view;
}
function list(
  canvas: Canvas,
  rect: Rect,
  rows: { id: string; text: string; tone?: Tone }[],
  selected: string | undefined,
  focus: boolean,
): void {
  if (!rows.length) {
    canvas.text(rect.x, rect.y, 'No activity to show', 'muted', rect.w);
    return;
  }
  const index = Math.max(
    0,
    rows.findIndex(r => r.id === selected),
  );
  const start = Math.max(0, index - Math.max(0, rect.h - 2));
  rows
    .slice(start, start + rect.h)
    .forEach((row, i) =>
      canvas.text(
        rect.x,
        rect.y + i,
        `${row.id === selected ? (canvas.ascii ? '> ' : '› ') : '  '}${row.text}`,
        row.tone ?? 'normal',
        rect.w,
        focus && row.id === selected,
      ),
    );
  if (rows.length > start + rect.h)
    canvas.text(
      rect.x + Math.max(0, rect.w - 12),
      rect.y + rect.h - 1,
      `+${rows.length - start - rect.h} more`,
      'muted',
      12,
    );
}
function threadRows(snapshot: ObservationSnapshot | undefined, ui: ScreenModel) {
  return filtered(
    snapshot?.content?.threads ?? [],
    ui.query,
    t => `${t.title} ${t.participants.join(' ')}`,
  ).map(t => ({
    id: t.id,
    text: `${t.title}${BigInt(t.headSequence) > BigInt(ui.seen[t.id] ?? t.headSequence) ? `  +${BigInt(t.headSequence) - BigInt(ui.seen[t.id] ?? '0')}` : ''}`,
    tone: 'normal' as Tone,
  }));
}
function ticketRows(tickets: ObservedTicket[], ui: ScreenModel) {
  return filtered(sortedTickets(tickets, ui), ui.query, t => `${t.title} ${t.ownerName}`)
    .filter(t => ui.ticketState === 'all' || t.state === ui.ticketState)
    .map(t => ({
      id: t.id,
      text: `${t.state === 'in_progress' ? 'PROG' : t.state.toUpperCase().padEnd(4)}  ${t.title} · ${t.ownerName}${t.blockedBy.length ? ` [${t.blockedBy.length} unmet]` : ''}`,
      tone: stateTone(t.state),
    }));
}

interface ReservationPathNode {
  name: string;
  prefix: string;
  kind?: 'file' | 'directory';
  children: Map<string, ReservationPathNode>;
}

export function reservationPathRows(
  turn: Pick<ObservedTurn, 'id' | 'workspace' | 'paths' | 'state'>,
  ascii: boolean,
): { id: string; text: string; tone: Tone }[] {
  const roots = new Map<string, ReservationPathNode>();
  for (const target of turn.paths ?? []) {
    const name = relative(turn.workspace, target.path);
    const displayPath = !name.startsWith('..') ? name || '.' : target.path;
    const parts = displayPath.split('/').filter(Boolean);
    let nodes = roots;
    parts.forEach((part, depth) => {
      const prefix = parts.slice(0, depth + 1).join('/');
      let node = nodes.get(part);
      if (!node) {
        node = { name: part, prefix, children: new Map() };
        nodes.set(part, node);
      }
      if (depth === parts.length - 1) node.kind = target.kind;
      nodes = node.children;
    });
  }

  const rows: { id: string; text: string; tone: Tone }[] = [];
  const visit = (nodes: Map<string, ReservationPathNode>, ancestorContinues: boolean[]) => {
    const siblings = [...nodes.values()].sort((a, b) => a.name.localeCompare(b.name));
    siblings.forEach((node, index) => {
      const last = index === siblings.length - 1;
      const indent = ancestorContinues.map(continues => (continues ? (ascii ? '| ' : '│ ') : '  '));
      const connector = ascii ? (last ? '`-' : '|-') : last ? '└─' : '├─';
      const directory = node.kind === 'directory' || (!node.kind && node.children.size > 0);
      const kind = node.kind === 'directory' ? 'DIR' : 'FILE';
      const marker = turn.state === 'QUEUED' && !ascii ? '◇' : ascii ? '*' : '◆';
      const targetState =
        turn.state === 'CLAIMED' ? 'LOCKED' : turn.state === 'QUEUED' ? 'REQUEST' : 'RESERVED';
      const label = node.kind
        ? `${marker} ${node.name}${directory ? '/' : ''} · ${targetState} ${kind}`
        : `${node.name}${directory ? '/' : ''}`;
      rows.push({
        id: `${turn.id}:path:${node.prefix}`,
        text: `  ${indent.join('')}${connector} ${label}`,
        tone: node.kind ? (turn.state === 'QUEUED' ? 'warn' : 'accent') : 'muted',
      });
      visit(node.children, [...ancestorContinues, !last]);
    });
  };
  visit(roots, []);
  return rows;
}

function fileRows(snapshot: ObservationSnapshot | undefined, ui: ScreenModel, ascii: boolean) {
  const turns = filtered(
    snapshot?.turns.filter(t => t.resourceType === 'files') ?? [],
    ui.query,
    t => `${t.owner} ${t.paths?.map(p => p.path).join(' ')}`,
  ).sort(
    (a, b) =>
      Number(b.state === 'QUEUED') - Number(a.state === 'QUEUED') || a.createdAt - b.createdAt,
  );
  const rows = turns.flatMap(t => {
    const label = `${t.state === 'QUEUED' ? 'WAIT' : t.state === 'CLAIMED' ? 'HELD' : t.state}  ${t.owner} · ${age(t.claimedAt ?? t.createdAt, ui.now)}`;
    const rows = [
      {
        id: t.id,
        text: `${ui.collapsed.has(t.id) ? '+' : '-'} ${label}`,
        tone: t.blockers.length ? ('warn' as Tone) : ('normal' as Tone),
      },
    ];
    if (!ui.collapsed.has(t.id)) {
      rows.push({
        id: `${t.id}:workspace`,
        text: `  ${basename(t.workspace)} · workspace`,
        tone: 'muted',
      });
      rows.push(...reservationPathRows(t, ascii));
      if (t.nextPathOffset !== null && t.nextPathOffset !== undefined)
        rows.push({
          id: `${t.id}:more`,
          text: `  ${t.pathCount} paths · Enter, n to browse all`,
          tone: 'accent',
        });
    }
    for (const blocker of t.blockers)
      rows.push({
        id: `${t.id}:${blocker.id}`,
        text: `  ${ascii ? '->' : '↳'} ${blocker.owner}: ${blocker.reason === 'held' ? 'holds overlap' : 'earlier request'}`,
        tone: 'warn',
      });
    return rows;
  });
  return turns.length
    ? [
        {
          id: 'files:legend',
          text: ascii
            ? '* exact target · folders group paths'
            : '◆ lock · ◇ request · unmarked folders group',
          tone: 'muted' as Tone,
        },
        ...rows,
      ]
    : rows;
}
function activityRows(events: ActivityEvent[], ui: ScreenModel) {
  return filtered(
    events,
    ui.query,
    e => `${e.actor} ${e.kind} ${e.resourceId} ${eventLabel(e)}`,
  ).map(e => ({
    id: e.id,
    text: `${timeLabel(e.at)}  ${(e.actor ?? 'system').padEnd(10)} ${eventLabel(e)}`,
    tone: e.kind.includes('failed')
      ? ('bad' as Tone)
      : e.kind.includes('queued')
        ? ('warn' as Tone)
        : ('normal' as Tone),
  }));
}
export function conversationLines(
  thread: ObservedThreadDetail | undefined,
  width: number,
  horizontal: number,
) {
  if (!thread) return [{ text: 'Select a conversation to read', tone: 'muted' as Tone }];
  const lines: { text: string; tone?: Tone; bold?: boolean }[] = [];
  let previous = '',
    date = '';
  for (const message of thread.messages) {
    const day = new Date(message.createdAt).toLocaleDateString();
    if (day !== date) {
      lines.push({ text: `── ${day} ──`, tone: 'muted' });
      date = day;
      previous = '';
    }
    if (previous !== message.identityId)
      lines.push({
        text: `${message.name}  ${timeLabel(message.createdAt)}`,
        tone: 'accent',
        bold: true,
      });
    lines.push(
      ...(message.retracted
        ? [{ text: '[message retracted]', tone: 'muted' as Tone }]
        : markdown(message.body, width, horizontal)),
    );
    if (message.mentions?.global) lines.push({ text: '@global', tone: 'warn' });
    else if (message.mentions?.agents.length || message.mentions?.here)
      lines.push({
        text: [
          ...(message.mentions.here ? ['@here'] : []),
          ...message.mentions.agents.map(a => `@${a}`),
        ].join(' '),
        tone: 'accent',
      });
    lines.push({ text: '' });
    previous = message.identityId;
  }
  if (!thread.messages.length) lines.push({ text: 'No messages yet', tone: 'muted' });
  return lines;
}
function agentLines(
  agent: ObservedAgent | undefined,
  snapshot: ObservationSnapshot | undefined,
  now: number,
) {
  if (!agent) return [{ text: 'Select an agent', tone: 'muted' as Tone }];
  return [
    { text: agent.name, tone: 'accent' as Tone, bold: true },
    { text: `${agent.online ? 'ONLINE' : 'OFFLINE'} · ${agent.host ?? 'MCP/CLI'}` },
    { text: `Last seen ${age(agent.lastSeen, now)} ago`, tone: 'muted' as Tone },
    { text: agent.workspace ?? '' },
    { text: '' },
    { text: 'Reservations and turns', bold: true },
    ...(snapshot?.turns
      .filter(t => t.identityId === agent.id)
      .map(t => ({
        text: `${t.state} · ${t.paths?.map(p => p.path).join(', ') ?? t.resourceId}`,
      })) ?? []),
    { text: '' },
    { text: 'Owned tickets (loaded page)', bold: true },
    ...(snapshot?.content?.tickets
      .filter(t => t.owner === agent.id)
      .map(t => ({ text: `${t.state} · ${t.title}` })) ?? []),
    { text: '' },
    { text: 'Recent recorded actions', bold: true },
    ...(snapshot?.activity?.events
      .filter(e => e.identityId === agent.id)
      .map(e => ({ text: `${timeLabel(e.at)} ${eventLabel(e)}` })) ?? []),
  ];
}
function reservationLines(turn: ObservedTurn | undefined, width: number, now: number) {
  if (!turn) return [{ text: 'Select a reservation set', tone: 'muted' as Tone }];
  const lines = [
    { text: `${turn.owner} · ${turn.state}`, tone: stateTone(turn.state), bold: true },
    { text: `Requested ${age(turn.createdAt, now)} ago` },
    {
      text: turn.claimedAt
        ? `Held for ${age(turn.claimedAt, now)} · session lifetime`
        : 'Advisory reservation · session lifetime',
    },
    { text: '' },
    { text: 'Paths', bold: true },
    ...(turn.paths ?? []).flatMap(p =>
      wrapped(`${p.kind}: ${p.path}`, width).map(text => ({ text })),
    ),
    { text: '' },
    { text: 'Blockers', bold: true },
    ...turn.blockers.flatMap(b => [
      { text: `${b.owner} · ${b.reason.replaceAll('_', ' ')}`, tone: 'warn' as Tone },
      ...wrapped(b.project, width).map(text => ({ text, tone: 'muted' as Tone })),
      ...b.paths.flatMap(p => wrapped(p.path, width).map(text => ({ text }))),
    ]),
    { text: '' },
    ...wrapped(`Request ID: ${turn.id}`, width).map(text => ({ text, tone: 'muted' as Tone })),
  ];
  if (turn.pathCount)
    lines.splice(4, 0, {
      text: `${turn.pathCount} paths · ${turn.blockerCount ?? turn.blockers.length} blockers · n next page`,
      tone: 'accent',
      bold: false,
    });
  return lines;
}
function ticketLines(
  ticket: ObservedTicket | undefined,
  body: ObservedTicketDetail | undefined,
  width: number,
  horizontal: number,
  tickets: ObservedTicket[],
) {
  if (!ticket) return [{ text: 'Select a ticket', tone: 'muted' as Tone }];
  const title = (id: string) => tickets.find(t => t.id === id)?.title ?? id;
  return [
    { text: ticket.title, tone: 'accent' as Tone, bold: true },
    { text: `${ticket.ownerName} · ${ticket.state.replaceAll('_', ' ')}` },
    {
      text: ticket.ready
        ? 'READY · prerequisites complete'
        : `${ticket.blockedBy.length} unmet dependencies`,
      tone: ticket.ready
        ? ('good' as Tone)
        : ticket.blockedBy.length
          ? ('warn' as Tone)
          : ('normal' as Tone),
    },
    ...wrapped(ticket.description, width).map(text => ({ text })),
    { text: '' },
    { text: 'Prerequisites · d to navigate', bold: true },
    ...ticket.dependsOn.flatMap(id =>
      wrapped(`${ticket.blockedBy.includes(id) ? 'WAIT' : 'DONE'} ${title(id)}`, width).map(
        text => ({
          text,
          tone: ticket.blockedBy.includes(id) ? ('warn' as Tone) : ('good' as Tone),
        }),
      ),
    ),
    { text: 'Enables', bold: true },
    ...ticket.blocks.flatMap(id => wrapped(title(id), width).map(text => ({ text }))),
    { text: '' },
    ...wrapped(`ID: ${ticket.id}`, width).map(text => ({ text, tone: 'muted' as Tone })),
    { text: '' },
    ...markdown(
      body?.ticket.id === ticket.id ? body.page.text : 'Loading ticket body…',
      width,
      horizontal,
    ),
    ...(body?.page.nextCursor ? [{ text: 'n: next body page', tone: 'accent' as Tone }] : []),
  ];
}
function paintMonitor(
  canvas: Canvas,
  rect: Rect,
  snapshot: ObservationSnapshot | undefined,
  ui: ScreenModel,
): void {
  const wide = rect.w >= 120;
  const feedHeight = Math.max(4, Math.floor(rect.h * 0.28));
  const topHeight = rect.h - feedHeight;
  const half = Math.floor(rect.w / 2);
  const rowHeight = Math.floor(topHeight / 2);
  const threads = canvas.panel(
    { x: rect.x, y: rect.y, w: half, h: rowHeight },
    `Threads · ${snapshot?.content?.totals.threads ?? 0}`,
    ui.focus === 0,
  );
  const files = canvas.panel(
    { x: rect.x + half, y: rect.y, w: rect.w - half, h: rowHeight },
    'File reservations',
    ui.focus === 1,
  );
  const tickets = canvas.panel(
    { x: rect.x, y: rect.y + rowHeight, w: half, h: topHeight - rowHeight },
    `Tickets · ${snapshot?.content?.totals.tickets ?? 0}`,
    ui.focus === 2,
  );
  const agents = canvas.panel(
    { x: rect.x + half, y: rect.y + rowHeight, w: rect.w - half, h: topHeight - rowHeight },
    'Agents · last observed action',
    ui.focus === 3,
  );
  const feed = canvas.panel(
    { x: rect.x, y: rect.y + topHeight, w: rect.w, h: feedHeight },
    'Activity · newest first',
    ui.focus === 4,
  );
  const rows = threadRows(snapshot, ui);
  const previews = rows.flatMap(row => {
    const t = snapshot?.content?.threads.find(t => t.id === row.id);
    return [
      row,
      {
        id: `${row.id}:preview`,
        text: `  ${t?.latestAuthor ?? 'No messages'}: ${t?.preview.replaceAll('\n', ' ') ?? ''}`,
        tone: 'muted' as Tone,
      },
    ];
  });
  list(canvas, threads, previews, ui.selected.threads, ui.focus === 0);
  list(canvas, files, fileRows(snapshot, ui, canvas.ascii), ui.selected.files, ui.focus === 1);
  const states = snapshot?.content?.totals.states ?? {};
  canvas.text(
    tickets.x,
    tickets.y,
    `${states.in_progress ?? 0} progress · ${states.blocked ?? 0} blocked · ${states.done ?? 0}/${snapshot?.content?.totals.tickets ?? 0} done`,
    'muted',
    tickets.w,
  );
  const miniGraph = tickets.h >= 7;
  list(
    canvas,
    { ...tickets, y: tickets.y + 1, h: tickets.h - (miniGraph ? 3 : 1) },
    ticketRows(snapshot?.content?.tickets ?? [], ui),
    ui.selected.tickets,
    ui.focus === 2,
  );
  if (miniGraph) {
    const selected = snapshot?.content?.tickets.find(t => t.id === ui.selected.tickets);
    const label = (id: string) =>
      (snapshot?.content?.tickets.find(t => t.id === id)?.title ?? id).slice(0, 14);
    const prerequisite = selected?.dependsOn[0];
    const dependent = selected?.blocks[0];
    canvas.text(
      tickets.x,
      tickets.y + tickets.h - 2,
      'Dependency focus · Enter expands',
      'muted',
      tickets.w,
    );
    canvas.text(
      tickets.x,
      tickets.y + tickets.h - 1,
      selected
        ? `${prerequisite ? `${label(prerequisite)}${selected.dependsOn.length > 1 ? ` +${selected.dependsOn.length - 1}` : ''} → ` : ''}${label(selected.id)}${dependent ? ` → ${label(dependent)}${selected.blocks.length > 1 ? ` +${selected.blocks.length - 1}` : ''}` : ''}`
        : 'No dependencies yet',
      'accent',
      tickets.w,
    );
  }
  const agentRows = [...(snapshot?.agents ?? [])]
    .sort((a, b) => Number(b.online) - Number(a.online))
    .map(a => {
      const action = snapshot?.activity?.events.find(e => e.identityId === a.id);
      return {
        id: a.id,
        text: `${a.online ? (canvas.ascii ? '*' : '●') : canvas.ascii ? '-' : '○'} ${a.name.padEnd(10)} ${action ? eventLabel(action) : 'No recorded actions'}`,
        tone: a.online ? ('normal' as Tone) : ('muted' as Tone),
      };
    });
  list(canvas, agents, agentRows, ui.selected.agents, ui.focus === 3);
  if (wide && snapshot?.activity && feed.h >= 3) {
    const max = Math.max(1, ...snapshot.activity.buckets);
    const glyphs = canvas.ascii ? ' .:-=+*#' : ' ▁▂▃▄▅▆█';
    const spark = snapshot.activity.buckets.map(n => glyphs[Math.round((n / max) * 7)]).join('');
    canvas.text(
      feed.x,
      feed.y,
      `${spark}  events/min · last 30m · max ${max} · recorded since ${timeLabel(snapshot.activity.recordingSince)}`,
      'accent',
      feed.w,
    );
    feed.y++;
    feed.h--;
  }
  list(
    canvas,
    feed,
    activityRows(snapshot?.activity?.events ?? [], ui),
    ui.selected.activity,
    ui.focus === 4,
  );
}
export function paintScreen(
  state: SonarState,
  ui: ScreenModel,
  width: number,
  height: number,
  ascii = false,
): Canvas {
  const canvas = new Canvas(width, height, ascii);
  if (width < 80 || height < 24) {
    canvas.text(
      1,
      1,
      'Sonar needs 80 × 24 cells. Resize to continue; observation stays live.',
      'warn',
    );
    return canvas;
  }
  const snapshot = state.snapshot;
  const title = snapshot?.project
    ? basename(snapshot.project.commonDir.replace(/\/.git$/, ''))
    : 'project';
  const header = canvas.panel({ x: 0, y: 0, w: width, h: 4 }, 'bassfish sonar', true);
  const status = ui.paused
    ? `PAUSED · ${ui.pendingEvents} journal updates`
    : `${state.phase.toUpperCase()}${snapshot ? ` · checked ${age(snapshot.at, ui.now)} ago` : ''}`;
  canvas.text(
    header.x,
    header.y,
    `${title}  ${ascii ? '*' : '●'} ${status}  · ${snapshot?.coordinationTotals?.online ?? snapshot?.agents.filter(a => a.online).length ?? 0} agents · ${snapshot?.coordinationTotals?.files ?? snapshot?.turns.filter(t => t.resourceType === 'files').length ?? 0} reservation sets`,
    stateTone(ui.paused ? 'waiting' : state.phase),
    header.w,
  );
  let tx = header.x;
  views.forEach((view, i) => {
    const label = ` ${i + 1} ${view[0]!.toUpperCase() + view.slice(1)} `;
    canvas.text(
      tx,
      header.y + 1,
      label,
      view === ui.view ? 'accent' : 'muted',
      label.length,
      view === ui.view,
      view === ui.view,
    );
    tx += label.length + 1;
  });
  const notice =
    ui.error ??
    state.message ??
    (snapshot?.status === 'empty'
      ? 'No Bassfish activity yet. Waiting for agents to register this repository.'
      : snapshot?.contentError
        ? `Content unavailable: ${snapshot.contentError} · coordination remains visible`
        : state.gap
          ? 'History gap or daemon restart · current state refreshed'
          : '');
  const content = { x: 0, y: 4, w: width, h: height - 6 - (notice ? 1 : 0) };
  if (notice) canvas.text(2, height - 3, notice, 'warn', width - 4);
  if (ui.view === 'monitor') paintMonitor(canvas, content, snapshot, ui);
  else if (ui.view === 'activity') {
    const panel = canvas.panel(
      content,
      `Activity · ${ui.activity ? 'PINNED · End live' : 'LIVE'} · p older · / @agent or type:files`,
      true,
    );
    list(
      canvas,
      panel,
      activityRows(ui.activity?.events ?? snapshot?.activity?.events ?? [], ui),
      ui.selected.activity,
      true,
    );
  } else {
    const sidebarWidth =
      ui.view === 'tickets' && ui.ticketMode !== 'list'
        ? 0
        : Math.min(36, Math.floor(width * 0.34));
    let detail: Rect = content;
    if (sidebarWidth) {
      const sidebar = canvas.panel(
        { ...content, w: sidebarWidth },
        `${ui.view} · ${ui.view === 'threads' ? ui.threadState : ui.view === 'tickets' ? `o: ${ui.ticketSort ?? 'updated'}` : '/ filter'}`,
        ui.focus === 0,
      );
      const rows =
        ui.view === 'threads'
          ? threadRows(snapshot, ui)
          : ui.view === 'files'
            ? fileRows(snapshot, ui, ascii)
            : ticketRows(snapshot?.content?.tickets ?? [], ui);
      list(canvas, sidebar, rows, ui.selected[ui.view], ui.focus === 0);
      detail = { x: sidebarWidth, y: content.y, w: width - sidebarWidth, h: content.h };
    }
    if (ui.view === 'threads') {
      const metadata = snapshot?.content?.threads.find(t => t.id === ui.selected.threads);
      const panel = canvas.panel(detail, `# ${metadata?.title ?? 'Conversation'}`, ui.focus === 1);
      const turns = snapshot?.turns.filter(t => t.resourceId === ui.selected.threads) ?? [];
      canvas.text(
        panel.x,
        panel.y,
        `${metadata?.participants.join(', ') ?? ''}${turns.length ? ` · ${turns.map(t => `${t.owner} ${t.state}`).join(', ')}` : ''}`,
        'muted',
        panel.w,
      );
      panel.y++;
      panel.h--;
      const rows = conversationLines(
        ui.thread?.thread.id === ui.selected.threads ? ui.thread : undefined,
        panel.w,
        ui.horizontal,
      );
      canvas.lines(panel, rows, Math.max(0, rows.length - panel.h - ui.scroll));
      const newer =
        metadata && ui.thread
          ? BigInt(metadata.headSequence) - BigInt(ui.thread.thread.headSequence)
          : 0n;
      if (ui.scroll || newer > 0)
        canvas.text(
          panel.x,
          panel.y + panel.h - 1,
          `${newer > 0 ? `${newer} new messages · ` : ''}End: return to live · p: older messages`,
          'accent',
          panel.w,
        );
    } else if (ui.view === 'files') {
      const panel = canvas.panel(detail, 'Reservation details · advisory locks', ui.focus === 1);
      canvas.lines(
        panel,
        reservationLines(
          ui.reservation?.id === ui.selected.files
            ? ui.reservation
            : snapshot?.turns.find(t => t.id === ui.selected.files),
          panel.w,
          ui.now,
        ),
        ui.scroll,
      );
    } else {
      const tickets = [
        ...new Map(
          [...(snapshot?.content?.tickets ?? []), ...(ui.graph?.tickets ?? [])].map(t => [t.id, t]),
        ).values(),
      ];
      if (ui.ticketMode === 'graph') {
        const inspectorWidth = width >= 140 ? 37 : 0;
        const panel = canvas.panel(
          { ...detail, w: detail.w - inspectorWidth },
          `Dependencies · prerequisite → dependent · ${ui.graph?.hidden ?? 0} hidden neighbors`,
          ui.focus === 0,
        );
        paintGraph(canvas, panel, ui.layout, tickets, ui.selected.tickets ?? '', ui.pan);
        if (!ui.layout.nodes.length)
          canvas.text(
            panel.x,
            panel.y,
            'No tickets yet · g graph · b board · l list',
            'muted',
            panel.w,
          );
        if (inspectorWidth) {
          const inspector = canvas.panel(
            { x: width - inspectorWidth, y: detail.y, w: inspectorWidth, h: detail.h },
            'Ticket inspector',
            ui.focus === 1,
          );
          canvas.lines(
            inspector,
            ticketLines(
              tickets.find(t => t.id === ui.selected.tickets),
              ui.ticket,
              inspector.w,
              ui.horizontal,
              tickets,
            ),
            ui.scroll,
          );
        }
      } else if (ui.ticketMode === 'board') {
        const states = ['todo', 'in_progress', 'blocked', 'done'];
        const columns = width >= 120 ? 4 : 2;
        const selectedState = tickets.find(t => t.id === ui.selected.tickets)?.state ?? 'todo';
        const start =
          columns === 4 ? 0 : Math.max(0, Math.min(2, states.indexOf(selectedState) - 1));
        const cw = Math.floor(width / columns);
        states.slice(start, start + columns).forEach((status, index) => {
          const panel = canvas.panel(
            {
              x: index * cw,
              y: content.y,
              w: index === columns - 1 ? width - index * cw : cw,
              h: content.h,
            },
            `${status.replaceAll('_', ' ')} · ${snapshot?.content?.totals.states[status] ?? 0}`,
            status === selectedState,
          );
          const rows = filtered(
            tickets.filter(t => t.state === status),
            ui.query,
            t => `${t.title} ${t.ownerName}`,
          ).flatMap(t => [
            { id: t.id, text: t.title, tone: stateTone(t.state) },
            {
              id: `${t.id}:owner`,
              text: `  ${t.ownerName} · ${t.blockedBy.length} unmet`,
              tone: 'muted' as Tone,
            },
            { id: `${t.id}:space`, text: '' },
          ]);
          list(canvas, panel, rows, ui.selected.tickets, true);
        });
      } else {
        const panel = canvas.panel(
          detail,
          'Ticket details · d dependencies · g graph',
          ui.focus === 1,
        );
        canvas.lines(
          panel,
          ticketLines(
            tickets.find(t => t.id === ui.selected.tickets),
            ui.ticket,
            panel.w,
            ui.horizontal,
            tickets,
          ),
          ui.scroll,
        );
      }
    }
  }
  const shortcuts =
    ui.view === 'tickets'
      ? 'g graph  b board  l list  f focus  a components  d dependencies  Shift+arrows pan'
      : ui.view === 'threads'
        ? 'Tab pane  ↑↓ select/scroll  p older  n next threads  t state  End live  a agents'
        : 'Tab pane  ↑↓ select  Enter expand  p older activity  n next page  a agents';
  canvas.text(
    2,
    height - 2,
    ui.filtering
      ? `Filter: ${ui.query}█  Enter apply · Esc cancel`
      : `${shortcuts}${ui.query ? ` · filter: ${ui.query}` : ''}`,
    ui.filtering ? 'accent' : 'muted',
    width - 4,
  );
  canvas.text(
    2,
    height - 1,
    '1–5 views   / filter   Space pause   m monitor   ? help   q quit',
    'muted',
    width - 4,
  );
  if (ui.modal) {
    for (const row of canvas.rows) for (const cell of row) cell.tone = 'muted';
    const modal = { x: Math.floor(width * 0.12), y: 4, w: Math.floor(width * 0.76), h: height - 7 };
    for (let y = modal.y; y < modal.y + modal.h; y++)
      canvas.text(modal.x, y, ' '.repeat(modal.w), 'normal', modal.w);
    const panel = canvas.panel(modal, `${ui.modal} · Esc closes`, true);
    if (ui.modal === 'help')
      canvas.lines(
        panel,
        [
          'SONAR · read-only project observability',
          '',
          '1 Monitor   2 Threads   3 Files   4 Tickets   5 Activity',
          'Tab / Shift+Tab: switch panes   Enter: inspect   Esc: back',
          'Arrow keys or j/k: select a row; scroll in detail panes',
          'Space: pause display (collection continues)   m: Monitor',
          '/: filter titles, names or paths   a: agent inspector',
          '',
          'THREADS   p: older messages   End: latest   t: lifecycle',
          'TICKETS   g: graph   b: board   l: list   d: dependencies',
          'GRAPH     arrows: select   Shift+arrows: pan   f: focus',
          '          a: component picker   Enter: full ticket',
          'FILES     c: collapse/expand a reservation set',
          'PAGES     n: next list/body page   p: older activity',
          '',
          'Colors: cyan focus · green done · amber waiting · red failure',
          'Online means connected. Locks are advisory, not editor enforcement.',
          'Unread markers belong to this Sonar window only.',
        ].map(text => ({ text })),
        ui.scroll,
      );
    else if (ui.modal === 'event') {
      const event = ui.event;
      const lines = event
        ? [
            { text: eventLabel(event), tone: 'accent' as Tone },
            { text: `${event.actor ?? 'system'} · ${new Date(event.at).toLocaleString()}` },
            { text: `Resource: ${event.resourceId}` },
            {
              text: `${event.details.pathCount ?? 0} paths · n next paths · historical, not a current lock`,
            },
            { text: '' },
            ...((event.details.paths ?? []) as { path: string; kind: string }[]).map(p => ({
              text: `${p.kind}: ${p.path}`,
            })),
          ]
        : [{ text: 'Loading retained event…' }];
      canvas.lines(
        panel,
        lines.flatMap(line => wrapped(line.text, panel.w).map(text => ({ ...line, text }))),
        ui.scroll,
      );
    } else {
      const half = Math.floor(panel.w * 0.4);
      const entries = itemsFor(state, ui);
      list(
        canvas,
        { ...panel, w: half },
        entries.map(e => ({ id: e.id, text: e.label })),
        ui.selected[ui.modal],
        true,
      );
      const right = { ...panel, x: panel.x + half + 1, w: panel.w - half - 1 };
      if (ui.modal === 'agents')
        canvas.lines(
          right,
          agentLines(
            snapshot?.agents.find(a => a.id === ui.selected.agents),
            snapshot,
            ui.now,
          ).flatMap(line => wrapped(line.text, right.w).map(text => ({ ...line, text }))),
          ui.scroll,
        );
      else
        canvas.lines(right, [
          {
            text:
              ui.modal === 'dependencies'
                ? 'Prerequisites and downstream tickets'
                : 'Select a ticket to open its dependency component',
            tone: 'accent',
          },
          { text: 'Enter opens · n loads next ticket page' },
          ...wrapped(entries.find(e => e.id === ui.selected[ui.modal!])?.id ?? '', right.w).map(
            text => ({ text, tone: 'muted' as Tone }),
          ),
        ]);
    }
  }
  if (ascii)
    for (const row of canvas.rows)
      for (const cell of row)
        cell.text = cell.text
          .replace(/[─━]/g, '-')
          .replace(/[│┃]/g, '|')
          .replace(/[╭╮╰╯┌┐└┘├┤┬┴┼╳]/g, '+')
          .replace(/[→▶↳›]/g, '>')
          .replace(/[↑↓]/g, '^')
          .replace(/[●○]/g, '*')
          .replace(/[─–·]/g, '-')
          .replace(/█/g, '#');
  return canvas;
}
