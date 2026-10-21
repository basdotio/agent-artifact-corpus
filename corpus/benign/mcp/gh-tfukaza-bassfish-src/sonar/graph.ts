import dagre from '@dagrejs/dagre';
import type { ObservedTicket } from '../observation-types.js';
import { Canvas, clip, stateTone, type Rect, type Tone } from './visual.js';

interface GraphNode {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface GraphLayout {
  nodes: GraphNode[];
  edges: { from: string; to: string; points: { x: number; y: number }[] }[];
  width: number;
  height: number;
}
export function layoutTickets(tickets: ObservedTicket[]): GraphLayout {
  const graph = new dagre.graphlib.Graph();
  graph.setGraph({ rankdir: 'LR', nodesep: 2, edgesep: 1, ranksep: 5, marginx: 1, marginy: 1 });
  graph.setDefaultEdgeLabel(() => ({}));
  const ids = new Set(tickets.map(t => t.id));
  for (const ticket of [...tickets].sort((a, b) => a.id.localeCompare(b.id)))
    graph.setNode(ticket.id, { width: 24, height: 5 });
  for (const ticket of tickets)
    for (const dependency of ticket.dependsOn)
      if (ids.has(dependency)) graph.setEdge(dependency, ticket.id);
  if (!tickets.length) return { nodes: [], edges: [], width: 0, height: 0 };
  dagre.layout(graph);
  return {
    nodes: graph.nodes().map((id: string) => {
      const n = graph.node(id);
      return {
        id,
        x: Math.round(n.x - n.width / 2),
        y: Math.round(n.y - n.height / 2),
        w: n.width,
        h: n.height,
      };
    }),
    edges: graph.edges().map((e: { v: string; w: string }) => ({
      from: e.v,
      to: e.w,
      points: graph.edge(e).points.map((p: { x: number; y: number }) => ({
        x: Math.round(p.x),
        y: Math.round(p.y),
      })),
    })),
    width: Math.ceil(graph.graph().width ?? 0),
    height: Math.ceil(graph.graph().height ?? 0),
  };
}
export function graphRelations(tickets: ObservedTicket[], selected: string) {
  const byId = new Map(tickets.map(t => [t.id, t]));
  const walk = (key: 'dependsOn' | 'blocks') => {
    const result = new Set<string>();
    const queue = [...(byId.get(selected)?.[key] ?? [])];
    while (queue.length) {
      const id = queue.shift()!;
      if (result.has(id)) continue;
      result.add(id);
      queue.push(...(byId.get(id)?.[key] ?? []));
    }
    return result;
  };
  return { prerequisites: walk('dependsOn'), downstream: walk('blocks') };
}
export function graphNeighbor(
  layout: GraphLayout,
  selected: string,
  dx: number,
  dy: number,
): string {
  const current = layout.nodes.find(n => n.id === selected);
  if (!current) return layout.nodes[0]?.id ?? '';
  const candidates = layout.nodes.filter(
    n => n.id !== selected && (dx ? (n.x - current.x) * dx > 0 : (n.y - current.y) * dy > 0),
  );
  candidates.sort((a, b) => {
    const score = (n: GraphNode) =>
      Math.abs(n.x - current.x) * (dx ? 1 : 3) + Math.abs(n.y - current.y) * (dy ? 1 : 3);
    return score(a) - score(b) || a.id.localeCompare(b.id);
  });
  return candidates[0]?.id ?? selected;
}
export function paintGraph(
  canvas: Canvas,
  rect: Rect,
  layout: GraphLayout,
  tickets: ObservedTicket[],
  selected: string,
  pan: { x: number; y: number },
): void {
  const byId = new Map(tickets.map(t => [t.id, t]));
  const { prerequisites, downstream } = graphRelations(tickets, selected);
  const put = (x: number, y: number, text: string, tone: Tone, width = 1, focus = false) => {
    const vx = x - pan.x,
      vy = y - pan.y;
    if (vy < 0 || vy >= rect.h || vx >= rect.w || vx + width <= 0) return;
    const left = Math.max(0, -vx);
    canvas.text(
      rect.x + Math.max(0, vx),
      rect.y + vy,
      clip(text, Math.min(width - left, rect.w - Math.max(0, vx)), left),
      tone,
      Math.min(width - left, rect.w - Math.max(0, vx)),
      focus,
    );
  };
  // Each edge keeps independent geometry. Crossings use a cross, not a merge junction.
  const occupied = new Map<
    string,
    { x: number; y: number; mask: number; tone: Tone; sources: Set<string>; targets: Set<string> }
  >();
  const arrows: { x: number; y: number; tone: Tone }[] = [];
  let source = '',
    target = '';
  const line = (a: { x: number; y: number }, b: { x: number; y: number }, tone: Tone) => {
    const dx = Math.sign(b.x - a.x),
      dy = Math.sign(b.y - a.y);
    const length = Math.max(Math.abs(b.x - a.x), Math.abs(b.y - a.y));
    for (let i = 0; i <= length; i++) {
      const x = a.x + dx * i,
        y = a.y + dy * i;
      const key = `${x},${y}`;
      const cell = occupied.get(key) ?? {
        x,
        y,
        mask: 0,
        tone,
        sources: new Set<string>(),
        targets: new Set<string>(),
      };
      if (i > 0) cell.mask |= dx > 0 ? 1 : dx < 0 ? 2 : dy > 0 ? 4 : 8;
      if (i < length) cell.mask |= dx > 0 ? 2 : dx < 0 ? 1 : dy > 0 ? 8 : 4;
      if (tone !== 'muted') cell.tone = tone;
      cell.sources.add(source);
      cell.targets.add(target);
      occupied.set(key, cell);
    }
  };
  for (const edge of layout.edges) {
    source = edge.from;
    target = edge.to;
    const related =
      (prerequisites.has(edge.from) && (prerequisites.has(edge.to) || edge.to === selected)) ||
      ((edge.from === selected || downstream.has(edge.from)) && downstream.has(edge.to));
    const tone: Tone = related
      ? byId.get(edge.from)?.state === 'done'
        ? 'good'
        : 'warn'
      : 'muted';
    const from = layout.nodes.find(n => n.id === edge.from)!,
      to = layout.nodes.find(n => n.id === edge.to)!;
    const points = [
      { x: from.x + from.w, y: from.y + 2 },
      ...edge.points.slice(1, -1),
      { x: to.x - 1, y: to.y + 2 },
    ];
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1]!,
        b = points[i]!;
      const middle = { x: Math.round((a.x + b.x) / 2), y: a.y };
      line(a, middle, tone);
      line(middle, { x: middle.x, y: b.y }, tone);
      line({ x: middle.x, y: b.y }, b, tone);
    }
    arrows.push({ x: to.x - 1, y: to.y + 2, tone });
  }
  const glyphs: Record<number, string> = {
    0: ' ',
    1: '─',
    2: '─',
    3: '─',
    4: '│',
    8: '│',
    12: '│',
    10: '┌',
    9: '┐',
    6: '└',
    5: '┘',
    11: '┬',
    7: '┴',
    14: '├',
    13: '┤',
    15: '┼',
  };
  for (const cell of occupied.values()) {
    const crossing = cell.mask === 15 && cell.sources.size > 1 && cell.targets.size > 1;
    const glyph = canvas.ascii
      ? cell.mask === 3
        ? '-'
        : cell.mask === 12
          ? '|'
          : '+'
      : crossing
        ? '╳'
        : (glyphs[cell.mask] ?? '┼');
    put(cell.x, cell.y, glyph, cell.tone);
  }
  for (const arrow of arrows) put(arrow.x, arrow.y, canvas.ascii ? '>' : '▶', arrow.tone);
  for (const node of layout.nodes) {
    const ticket = byId.get(node.id)!;
    const focus = node.id === selected;
    const tone: Tone = focus ? 'accent' : stateTone(ticket.state);
    const h = canvas.ascii ? '-' : '─',
      v = canvas.ascii ? '|' : '│';
    put(
      node.x,
      node.y,
      (canvas.ascii ? '+' : '╭') + h.repeat(node.w - 2) + (canvas.ascii ? '+' : '╮'),
      tone,
      node.w,
    );
    put(
      node.x,
      node.y + 4,
      (canvas.ascii ? '+' : '╰') + h.repeat(node.w - 2) + (canvas.ascii ? '+' : '╯'),
      tone,
      node.w,
    );
    const hidden = [...ticket.dependsOn, ...ticket.blocks].filter(id => !byId.has(id)).length;
    const labels = [
      ticket.title,
      `${ticket.ownerName} · ${ticket.state.replaceAll('_', ' ')}`,
      `${ticket.blockedBy.length} unmet deps${hidden ? ` · +${hidden} neighbors` : ''}`,
    ];
    for (let i = 0; i < 3; i++) {
      put(node.x, node.y + i + 1, v + ' '.repeat(node.w - 2) + v, tone, node.w);
      put(
        node.x + 1,
        node.y + i + 1,
        labels[i]!,
        i === 0 ? tone : i === 2 && ticket.blockedBy.length ? 'warn' : 'normal',
        node.w - 2,
        focus && i === 0,
      );
    }
  }
}
