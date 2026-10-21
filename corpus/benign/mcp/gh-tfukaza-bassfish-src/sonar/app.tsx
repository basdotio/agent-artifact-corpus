import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import { Box, Text, useApp, useInput, useWindowSize } from 'ink';
import type { ReactNode } from 'react';
import type {
  ActivityEvent,
  ActivityPage,
  ContentObservation,
  ObservationGraph,
  ObservationSnapshot,
  ObservedThreadDetail,
  ObservedTicketDetail,
  ObservedTurn,
} from '../observation-types.js';
import { SonarClient, type SonarState } from './client.js';
import { graphNeighbor, layoutTickets } from './graph.js';
import {
  initialScreen,
  itemsFor,
  paintScreen,
  selectionKey,
  views,
  type ScreenModel,
  type View,
} from './screen.js';
import type { Cell, Tone } from './visual.js';

const colors: Record<Tone, string | undefined> = {
  normal: undefined,
  muted: 'gray',
  accent: 'cyan',
  good: 'green',
  warn: 'yellow',
  bad: 'red',
};
function Row({ cells, color }: { cells: Cell[]; color: boolean }) {
  const segments: ReactNode[] = [];
  let start = 0;
  for (let i = 1; i <= cells.length; i++) {
    const a = cells[start]!,
      b = cells[i];
    if (b && a.tone === b.tone && a.selected === b.selected && a.bold === b.bold) continue;
    segments.push(
      <Text
        key={start}
        color={color ? (a.selected ? 'black' : colors[a.tone]) : undefined}
        backgroundColor={color && a.selected ? 'cyan' : undefined}
        bold={a.bold || (!color && a.selected)}
      >
        {cells
          .slice(start, i)
          .map(c => c.text)
          .join('')}
      </Text>,
    );
    start = i;
  }
  return <Text>{segments}</Text>;
}

export function SonarApp({
  client,
  initialView = 'monitor',
  ascii = false,
  color = true,
  dimensions,
}: {
  client: SonarClient;
  initialView?: View;
  ascii?: boolean;
  color?: boolean;
  dimensions?: { columns: number; rows: number };
}) {
  const live = useSyncExternalStore(client.subscribe, client.getState);
  const [frozen, setFrozen] = useState<SonarState>();
  const state = frozen ?? live;
  const [ui, setUi] = useState<ScreenModel>(() => initialScreen(initialView));
  const [graphRoot, setGraphRoot] = useState('');
  const [focusedGraph, setFocusedGraph] = useState(false);
  const [page, setPage] = useState<ContentObservation>();
  const [coordinationPage, setCoordinationPage] = useState<ObservationSnapshot>();
  const [refreshDetail, setRefreshDetail] = useState(0);
  const window = useWindowSize();
  const width = Math.min(300, Math.max(1, dimensions?.columns ?? window.columns));
  const height = Math.min(120, Math.max(1, dimensions?.rows ?? window.rows));
  const { exit } = useApp();
  const initialSeen = useRef(false);
  const latest = useRef(ui);
  latest.current = ui;
  const displayState = useMemo(
    () =>
      (page || coordinationPage) && state.snapshot
        ? {
            ...state,
            message: 'Browsing a pinned page · End returns to live data',
            snapshot: {
              ...state.snapshot,
              ...(coordinationPage
                ? {
                    agents: coordinationPage.agents,
                    turns: coordinationPage.turns,
                    nextAgentOffset: coordinationPage.nextAgentOffset,
                    nextTurnOffset: coordinationPage.nextTurnOffset,
                  }
                : {}),
              content: page ?? state.snapshot.content,
            },
          }
        : state,
    [state, page, coordinationPage],
  );
  const snapshot = displayState.snapshot;
  const observation = snapshot?.content
    ? `${snapshot.epoch}:${snapshot.cursor}:${snapshot.at}`
    : undefined;
  const fail = (error: unknown) =>
    setUi(old => ({
      ...old,
      error: error instanceof Error ? error.message : 'Unable to load observation',
    }));
  useEffect(() => {
    const timer = setInterval(() => setUi(old => ({ ...old, now: Date.now() })), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!snapshot) return;
    setUi(old => {
      const selected = { ...old.selected };
      for (const view of ['threads', 'files', 'tickets', 'activity'] as View[]) {
        const items = itemsFor(displayState, { ...old, view, modal: null });
        if (!items.some(i => i.id === selected[view])) selected[view] = items[0]?.id ?? '';
        if (view === 'activity' && !old.activity) selected.activity = items[0]?.id ?? '';
      }
      if (!selected.agents) selected.agents = snapshot.agents[0]?.id ?? '';
      let seen = old.seen;
      if (!initialSeen.current && snapshot.content) {
        seen = Object.fromEntries(snapshot.content.threads.map(t => [t.id, t.headSequence]));
        initialSeen.current = true;
      }
      if (
        old.view === 'threads' &&
        old.scroll === 0 &&
        old.thread &&
        old.thread.thread.id === selected.threads
      )
        seen = { ...seen, [selected.threads!]: old.thread.thread.headSequence };
      return { ...old, selected, seen };
    });
  }, [snapshot, ui.query, displayState]);
  useEffect(() => {
    if (ui.paused || !observation || ui.view !== 'threads' || !ui.selected.threads || ui.scroll > 0)
      return;
    let cancelled = false;
    void client
      .read<ObservedThreadDetail>({
        kind: 'thread',
        id: ui.selected.threads,
        revision: snapshot?.content?.threads.find(thread => thread.id === ui.selected.threads)
          ?.revision,
      })
      .then(
        thread => {
          if (!cancelled)
            setUi(old => ({
              ...old,
              thread,
              error: undefined,
              seen: { ...old.seen, [thread.thread.id]: thread.thread.headSequence },
            }));
        },
        error => {
          if (!cancelled) fail(error);
        },
      );
    return () => {
      cancelled = true;
    };
  }, [
    client,
    observation,
    ui.view,
    ui.selected.threads,
    ui.paused,
    ui.scroll === 0,
    refreshDetail,
  ]);
  useEffect(() => {
    if (ui.paused || !observation || ui.view !== 'tickets' || !ui.selected.tickets || ui.scroll > 0)
      return;
    let cancelled = false;
    void client
      .read<ObservedTicketDetail>({
        kind: 'ticket',
        id: ui.selected.tickets,
        revision: snapshot?.content?.tickets.find(ticket => ticket.id === ui.selected.tickets)
          ?.revision,
      })
      .then(
        ticket => {
          if (!cancelled) setUi(old => ({ ...old, ticket, error: undefined }));
        },
        error => {
          if (!cancelled) fail(error);
        },
      );
    return () => {
      cancelled = true;
    };
  }, [
    client,
    observation,
    ui.view,
    ui.selected.tickets,
    ui.paused,
    ui.scroll === 0,
    refreshDetail,
  ]);
  const root = graphRoot || ui.selected.tickets;
  useEffect(() => {
    if (ui.paused || !observation || !root || ui.view !== 'tickets') return;
    let cancelled = false;
    void client.read<ObservationGraph>({ kind: 'graph', id: root, focused: focusedGraph }).then(
      graph => {
        if (!cancelled) {
          setUi(old => ({ ...old, graph, error: undefined }));
          if (!graphRoot) setGraphRoot(root);
        }
      },
      error => {
        if (!cancelled) fail(error);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [client, observation, root, focusedGraph, ui.view, ui.paused]);
  const topology = JSON.stringify(
    ui.graph?.tickets
      .map(t => [t.id, [...t.dependsOn].sort()])
      .sort((a, b) => String(a[0]).localeCompare(String(b[0]))) ?? [],
  );
  const layout = useMemo(() => layoutTickets(ui.graph?.tickets ?? []), [topology]);
  useEffect(() => {
    const selected = layout.nodes.find(n => n.id === latest.current.selected.tickets);
    const viewport = width - (width >= 140 ? 37 : 0) - 4;
    if (selected)
      setUi(old => ({
        ...old,
        pan: {
          x: Math.max(
            0,
            Math.min(layout.width - viewport, selected.x - Math.floor(viewport / 2) + 12),
          ),
          y: Math.max(
            0,
            Math.min(layout.height - (height - 10), selected.y - Math.floor((height - 10) / 2) + 2),
          ),
        },
      }));
  }, [layout, width, height]);
  useEffect(() => {
    if (!snapshot?.content || snapshot.content.tickets.some(t => t.dependsOn.length)) return;
    setUi(old =>
      old.ticketMode === 'graph' && !old.graph?.tickets.some(t => t.dependsOn.length)
        ? { ...old, ticketMode: 'board' }
        : old,
    );
  }, [snapshot?.project?.id]);

  const switchView = (view: View) => {
    setPage(undefined);
    setCoordinationPage(undefined);
    setUi(old => ({
      ...old,
      view,
      focus: 0,
      scroll: 0,
      horizontal: 0,
      modal: null,
      error: undefined,
      activity: undefined,
      reservation: undefined,
    }));
  };
  const center = (id: string) => {
    const node = layout.nodes.find(n => n.id === id);
    const viewport = width - (width >= 140 ? 37 : 0) - 4;
    setUi(old => ({
      ...old,
      selected: { ...old.selected, tickets: id },
      scroll: 0,
      pan: node
        ? {
            x:
              node.x >= old.pan.x && node.x + node.w <= old.pan.x + viewport
                ? old.pan.x
                : Math.max(
                    0,
                    Math.min(layout.width - viewport, node.x - Math.floor(viewport / 2) + 12),
                  ),
            y:
              node.y >= old.pan.y && node.y + node.h <= old.pan.y + height - 10
                ? old.pan.y
                : Math.max(0, node.y - 2),
          }
        : old.pan,
    }));
  };
  const more = async () => {
    if (ui.modal === 'event') {
      const offset = ui.event?.details.nextPathOffset;
      if (typeof offset === 'number') {
        const event = await client.read<ActivityEvent>({
          kind: 'event',
          id: ui.event!.id,
          pathOffset: offset,
        });
        setUi(old => ({ ...old, event, scroll: 0 }));
      }
      return;
    }
    if (!ui.modal && ui.view === 'files' && ui.focus === 1) {
      const current =
        ui.reservation?.id === ui.selected.files
          ? ui.reservation
          : snapshot?.turns.find(t => t.id === ui.selected.files);
      if (current?.nextPathOffset != null || current?.nextBlockerOffset != null) {
        const reservation = await client.read<ObservedTurn>({
          kind: 'files',
          id: ui.selected.files!,
          pathOffset: current.nextPathOffset ?? current.pathCount ?? 0,
          blockerOffset: current.nextPathOffset != null ? 0 : (current.nextBlockerOffset ?? 0),
        });
        setUi(old => ({ ...old, reservation, scroll: 0 }));
      }
      return;
    }
    if (ui.modal === 'agents' || (!ui.modal && ui.view === 'files')) {
      const offset = ui.modal === 'agents' ? snapshot?.nextAgentOffset : snapshot?.nextTurnOffset;
      if (offset != null)
        setCoordinationPage(
          await client.read<ObservationSnapshot>({
            kind: 'snapshot',
            filter: ui.modal === 'agents' ? { agentOffset: offset } : { turnOffset: offset },
          }),
        );
      return;
    }
    if (!observation) return;
    if (!ui.modal && ui.view === 'tickets' && ui.focus === 1 && ui.ticket?.page.nextCursor) {
      const ticket = await client.read<ObservedTicketDetail>({
        kind: 'ticket',
        id: ui.selected.tickets!,
        revision: ui.ticket.revision,
        cursor: ui.ticket.page.nextCursor,
      });
      setUi(old => ({ ...old, ticket, scroll: 0 }));
      return;
    }
    const isThread = ui.view === 'threads';
    const offset = isThread
      ? snapshot?.content?.nextThreadOffset
      : snapshot?.content?.nextTicketOffset;
    if (offset === null || offset === undefined) return;
    const content = await client.read<ContentObservation>({
      kind: 'content',
      filter: {
        threadState: ui.threadState,
        ticketState: ui.ticketState,
        query: ui.query.replace(/^@/, ''),
        ...(isThread ? { threadOffset: offset } : { ticketOffset: offset }),
      },
    });
    setPage(content);
  };
  const older = async () => {
    if (ui.view === 'threads' && ui.thread?.nextBefore) {
      const id = ui.selected.threads;
      const thread = await client.read<ObservedThreadDetail>({
        kind: 'thread',
        id: id!,
        revision: ui.thread.revision,
        before: ui.thread.nextBefore,
      });
      setUi(old => (old.selected.threads === id ? { ...old, thread, scroll: 1 } : old));
    } else if (ui.view === 'activity') {
      const before = ui.activity?.nextBefore ?? snapshot?.activity?.nextBefore;
      if (!before) return;
      const activity = await client.read<ActivityPage>({
        kind: 'activity',
        before,
        actor: ui.query.startsWith('@') ? ui.query.slice(1) : undefined,
        eventKind: ui.query.startsWith('type:') ? ui.query.slice(5) : undefined,
        resourceId: ui.query.startsWith('resource:') ? ui.query.slice(9) : undefined,
      });
      setUi(old => ({
        ...old,
        activity,
        selected: { ...old.selected, activity: activity.events[0]?.id ?? '' },
      }));
    }
  };
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      client.close();
      exit();
      return;
    }
    if (ui.filtering) {
      if (key.escape) setUi(old => ({ ...old, filtering: false, query: '' }));
      else if (key.return) {
        setUi(old => ({ ...old, filtering: false }));
        if (ui.view === 'threads' || ui.view === 'tickets')
          void client
            .refresh({
              query: ui.query.startsWith('@') ? undefined : ui.query,
              owner: ui.query.startsWith('@') ? ui.query.slice(1) : undefined,
              threadState: ui.threadState,
              ticketState: ui.ticketState,
            })
            .catch(fail);
        if (ui.view === 'activity')
          void client
            .read<ActivityPage>({
              kind: 'activity',
              actor: ui.query.startsWith('@') ? ui.query.slice(1) : undefined,
              eventKind: ui.query.startsWith('type:') ? ui.query.slice(5) : undefined,
              resourceId: ui.query.startsWith('resource:') ? ui.query.slice(9) : undefined,
            })
            .then(activity => setUi(old => ({ ...old, activity })), fail);
      } else if (key.backspace || key.delete)
        setUi(old => ({ ...old, query: old.query.slice(0, -1) }));
      else if (!key.ctrl && !key.meta)
        setUi(old => ({ ...old, query: (old.query + input).slice(0, 200) }));
      return;
    }
    if (input === 'q') {
      client.close();
      exit();
      return;
    }
    if (input === '?') {
      setUi(old => ({ ...old, modal: old.modal === 'help' ? null : 'help', scroll: 0 }));
      return;
    }
    if (key.escape) {
      if (ui.modal) setUi(old => ({ ...old, modal: null, scroll: 0 }));
      else if (ui.focus) setUi(old => ({ ...old, focus: 0, scroll: 0 }));
      else switchView('monitor');
      return;
    }
    if (ui.modal) {
      if (input === 'n') {
        void more().catch(fail);
        return;
      }
      if (key.return && ui.modal !== 'help') {
        const id = ui.selected[ui.modal];
        if (id && ui.modal !== 'agents') {
          setGraphRoot(id);
          setUi(old => ({
            ...old,
            view: 'tickets',
            ticketMode: 'graph',
            modal: null,
            focus: 0,
            scroll: 0,
            selected: { ...old.selected, tickets: id },
          }));
        }
        return;
      }
      if (ui.modal === 'help' || ui.modal === 'event' || key.pageDown || key.pageUp) {
        if (key.downArrow || key.pageDown) setUi(old => ({ ...old, scroll: old.scroll + 5 }));
        if (key.upArrow || key.pageUp)
          setUi(old => ({ ...old, scroll: Math.max(0, old.scroll - 5) }));
        return;
      }
    } else {
      if (/^[1-5]$/.test(input)) {
        switchView(views[Number(input) - 1]!);
        return;
      }
      if (input === 'm') {
        switchView('monitor');
        return;
      }
      if (input === ' ') {
        setFrozen(ui.paused ? undefined : live);
        setUi(old => ({ ...old, paused: !old.paused, now: Date.now() }));
        return;
      }
      if (input === '/') {
        setUi(old => ({ ...old, filtering: true }));
        return;
      }
      if (key.tab) {
        setUi(old => ({
          ...old,
          focus:
            (old.focus + (key.shift ? (old.view === 'monitor' ? 4 : 1) : 1)) %
            (old.view === 'monitor' ? 5 : 2),
          scroll: 0,
        }));
        return;
      }
      if (input === 'a' || (input === 'd' && ui.view === 'tickets')) {
        const modal =
          input === 'd'
            ? 'dependencies'
            : ui.view === 'tickets' && ui.ticketMode === 'graph'
              ? 'components'
              : 'agents';
        const entries = itemsFor(displayState, { ...ui, modal });
        setUi(old => ({
          ...old,
          modal,
          scroll: 0,
          selected: { ...old.selected, [modal]: entries[0]?.id ?? '' },
        }));
        return;
      }
      if (input === 't' && ui.view === 'threads') {
        const values = ['active', 'archived', 'deleted', 'all'] as const;
        const threadState = values[(values.indexOf(ui.threadState) + 1) % values.length]!;
        setPage(undefined);
        setUi(old => ({ ...old, threadState }));
        void client.refresh({ threadState }).catch(fail);
        return;
      }
      if (input === 's' && ui.view === 'tickets') {
        const values = ['all', 'todo', 'in_progress', 'blocked', 'done'] as const;
        const ticketState = values[(values.indexOf(ui.ticketState) + 1) % values.length]!;
        setUi(old => ({ ...old, ticketState }));
        void client.refresh({ ticketState, threadState: ui.threadState }).catch(fail);
        return;
      }
      if (['g', 'b', 'l'].includes(input) && ui.view === 'tickets') {
        setUi(old => ({
          ...old,
          ticketMode: input === 'g' ? 'graph' : input === 'b' ? 'board' : 'list',
          focus: 0,
          scroll: 0,
        }));
        return;
      }
      if (input === 'o' && ui.view === 'tickets') {
        const sorts = ['updated', 'title', 'owner', 'state'] as const;
        setUi(old => ({
          ...old,
          ticketSort: sorts[(sorts.indexOf(old.ticketSort ?? 'updated') + 1) % sorts.length],
        }));
        return;
      }
      if (input === 'f' && ui.view === 'tickets') {
        setGraphRoot(ui.selected.tickets!);
        setFocusedGraph(old => !old);
        return;
      }
      if (input === 'c' && ui.view === 'files') {
        setUi(old => {
          const collapsed = new Set(old.collapsed);
          const id = old.selected.files!;
          if (collapsed.has(id)) collapsed.delete(id);
          else collapsed.add(id);
          return { ...old, collapsed };
        });
        return;
      }
      if (input === 'p') {
        void older().catch(fail);
        return;
      }
      if (input === 'n') {
        void more().catch(fail);
        return;
      }
      if (key.end) {
        setPage(undefined);
        setCoordinationPage(undefined);
        setUi(old => ({ ...old, scroll: 0, activity: undefined, reservation: undefined }));
        setRefreshDetail(old => old + 1);
        return;
      }
      if (key.return) {
        if (ui.view === 'monitor') {
          if (ui.focus === 3) setUi(old => ({ ...old, modal: 'agents' }));
          else
            switchView(
              (['threads', 'files', 'tickets', 'monitor', 'activity'] as View[])[ui.focus]!,
            );
        } else if (ui.view === 'activity') {
          const event = (ui.activity?.events ?? snapshot?.activity?.events)?.find(
            e => e.id === ui.selected.activity,
          );
          if (event?.resourceType === 'thread' || event?.resourceType === 'ticket') {
            const view = event.resourceType === 'thread' ? 'threads' : 'tickets';
            setUi(old => ({
              ...old,
              view,
              focus: 1,
              scroll: 0,
              selected: { ...old.selected, [view]: event.resourceId },
            }));
            if (view === 'tickets') setGraphRoot(event.resourceId);
          } else if (event?.resourceType === 'files')
            setUi(old => ({ ...old, modal: 'event', event, scroll: 0 }));
          else if (event?.identityId)
            setUi(old => ({
              ...old,
              modal: 'agents',
              selected: { ...old.selected, agents: event.identityId! },
            }));
        } else
          setUi(old => ({
            ...old,
            focus: 1,
            ticketMode:
              old.view === 'tickets' && (width < 140 || old.ticketMode === 'board')
                ? 'list'
                : old.ticketMode,
            scroll: 0,
          }));
        return;
      }
      if (
        ui.view === 'tickets' &&
        ui.ticketMode === 'graph' &&
        ui.focus === 0 &&
        (key.leftArrow || key.rightArrow || key.upArrow || key.downArrow)
      ) {
        const dx = key.rightArrow ? 1 : key.leftArrow ? -1 : 0,
          dy = key.downArrow ? 1 : key.upArrow ? -1 : 0;
        if (key.shift)
          setUi(old => ({
            ...old,
            pan: {
              x: Math.max(0, Math.min(layout.width, old.pan.x + dx * 8)),
              y: Math.max(0, Math.min(layout.height, old.pan.y + dy * 3)),
            },
          }));
        else center(graphNeighbor(layout, ui.selected.tickets ?? '', dx, dy));
        return;
      }
      if (ui.view === 'tickets' && ui.ticketMode === 'board' && (key.leftArrow || key.rightArrow)) {
        const tickets = [...(snapshot?.content?.tickets ?? []), ...(ui.graph?.tickets ?? [])];
        const states = ['todo', 'in_progress', 'blocked', 'done'];
        const current = states.indexOf(
          tickets.find(t => t.id === ui.selected.tickets)?.state ?? 'todo',
        );
        for (let offset = 1; offset < 4; offset++) {
          const state = states[(current + (key.rightArrow ? offset : 4 - offset)) % 4];
          const target = tickets.find(t => t.state === state);
          if (target) {
            center(target.id);
            break;
          }
        }
        return;
      }
      if ((key.leftArrow || key.rightArrow) && ui.focus === 1) {
        setUi(old => ({
          ...old,
          horizontal: Math.max(0, old.horizontal + (key.rightArrow ? 8 : -8)),
        }));
        return;
      }
      if (ui.focus === 1 && ui.view !== 'monitor' && ui.view !== 'activity') {
        const delta =
          key.downArrow || input === 'j'
            ? 1
            : key.upArrow || input === 'k'
              ? -1
              : key.pageDown
                ? 5
                : key.pageUp
                  ? -5
                  : 0;
        if (delta)
          setUi(old => ({
            ...old,
            scroll: Math.max(0, old.scroll + delta * (old.view === 'threads' ? -1 : 1)),
          }));
        return;
      }
    }
    const delta =
      key.downArrow || input === 'j'
        ? 1
        : key.upArrow || input === 'k'
          ? -1
          : key.pageDown
            ? 5
            : key.pageUp
              ? -5
              : 0;
    if (delta) {
      const entries = itemsFor(displayState, ui),
        key = selectionKey(ui);
      const index = entries.findIndex(i => i.id === ui.selected[key]);
      const selected = entries[Math.max(0, Math.min(entries.length - 1, index + delta))]?.id;
      if (selected)
        setUi(old => ({
          ...old,
          selected: { ...old.selected, [key]: selected },
          scroll: 0,
          activity:
            old.view === 'activity'
              ? (old.activity ?? snapshot?.activity ?? undefined)
              : old.activity,
        }));
    }
  });
  const pendingEvents =
    frozen?.snapshot && live.snapshot
      ? String(BigInt(live.snapshot.cursor) - BigInt(frozen.snapshot.cursor))
      : '0';
  const frame = paintScreen(
    displayState,
    { ...ui, layout, pendingEvents, now: ui.paused ? (frozen?.snapshot?.at ?? ui.now) : ui.now },
    width,
    height,
    ascii,
  );
  return (
    <Box flexDirection="column" width={width} height={height}>
      {frame.rows.map((cells, i) => (
        <Row key={i} cells={cells} color={color} />
      ))}
    </Box>
  );
}
