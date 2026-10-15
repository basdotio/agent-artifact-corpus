export type Sample = {
  timestamp: number;
  eventLoop: { min: number; max: number; mean: number; p50: number; p99: number };
  memory: {
    heapUsed: number;
    heapTotal: number;
    rss: number;
    external: number;
    arrayBuffers: number;
  };
  heapSpaces?: unknown;
  gc: { count: number; totalPause: number; maxPause: number; kinds?: unknown };
  backpressure: { events: number; totalStall: number; maxStall: number; hotspots?: Hotspot[] };
  dropped?: { samples: number; spans: number };
};
export type Hotspot = { site: string; events: number; totalStall: number; maxStall: number };
export type Window = {
  start: number;
  end: number;
  count: number;
  late: number;
  eventLoop: { max: number; p99: number; mean: number };
  memory: { heapUsedLast: number; heapUsedMax: number; rssLast: number; rssMax: number };
  gc: { count: number; totalPause: number; maxPause: number };
  backpressure: { events: number; totalStall: number; maxStall: number };
};
export type Span = {
  type?: 'span';
  traceId: string;
  spanId: string;
  name: string;
  method: string;
  path: string;
  statusCode: number;
  startTimeMs: number;
  durationNs: number;
};
export type Alert = {
  ruleId: string;
  metric: string;
  comparison: '>' | '>=';
  threshold: number;
  observed: number;
  windowStart: number;
  windowEnd: number;
  state: 'firing' | 'resolved';
};
export type Event =
  | { event: 'sample'; data: Sample }
  | { event: 'window'; data: Window }
  | { event: 'span'; data: Span }
  | { event: 'alert'; data: Alert };
export type Quality = {
  invalidRecords: number;
  ignoredLogs: number;
  truncated: boolean;
  gaps: number;
  loss: {
    known: boolean;
    initial: { samples: number; spans: number } | null;
    delta: { samples: number; spans: number };
    resets: number;
  };
};
export type CaptureManifest = {
  schemaVersion: 1;
  source: { kind: string; location: string };
  startedAt: string;
  endedAt: string;
  events: number;
  historyEvents: number;
  observedEvents: number;
  termination: string;
  quality: Quality;
  conditions?: Record<string, unknown>;
  intervalMs?: number;
};
export type IntervalSource = 'flag' | 'manifest' | 'conditions' | 'default';
export type Route = {
  method: string;
  path: string;
  count: number;
  p50Ns: number;
  p99Ns: number;
  maxNs: number;
  serverErrors: number;
};
export type Summary = {
  schemaVersion: 1;
  command: 'summarize';
  source: string;
  period: { startMs: number | null; endMs: number | null; durationMs: number };
  counts: { samples: number; windows: number; spans: number; alerts: number };
  coverage: {
    format: 'samples' | 'windows' | null;
    samplingIntervalMs: number | null;
    samplingIntervalSource: IntervalSource | null;
    observedIntervalMs: number | null;
    sampleCount: number;
  };
  requests: {
    period: { startMs: number | null; endMs: number | null; durationMs: number };
    inPeriod: number;
    outsidePeriod: number;
    selection: 'fully-contained-in-runtime-period';
    routes: Route[];
    distinctRoutes: number;
  };
  quality: Quality;
  metrics: Record<string, number | null>;
  memory: { first: Record<string, number> | null; last: Record<string, number> | null };
  hotspots: Hotspot[];
  conditions: Record<string, unknown> | null;
};
export type Rule = {
  id: string;
  metric: string;
  comparison: '>' | '>=';
  threshold: number;
  forWindows?: number;
};
export type RuleResult =
  | { ok: true; findings: { windowStart: number; message: string }[] }
  | { ok: false; error: { code: string; message: string } };
export type Runner = {
  run(source: string, windows: readonly Window[]): Promise<RuleResult>;
  close(): Promise<void>;
};
export type Collector = {
  windows: { snapshot(): Window[] };
  spans: { snapshot(): Span[] };
  alerts: { snapshot(): Alert[] };
  consume(source: AsyncIterable<Sample | Span>): Promise<void>;
  close(): Promise<void>;
};
export type CollectorModule = {
  createCollector(options: {
    windowMs: number;
    capacity: number;
    alerts?: Rule[];
    sinks?: Record<string, unknown>[];
    onSinkError?: (error: Error) => void;
  }): Collector;
  createWindowAggregator(options: { windowMs: number }): import('node:stream').Transform;
  createAlertEvaluator(rules: Rule[]): import('node:stream').Transform;
};
export type DashboardModule = {
  createDashboardServer(options: {
    collector: Collector;
    host: string;
    port: number;
    token?: string;
    allowedHosts?: string[];
  }): Promise<{ url: string; close(): Promise<void> }>;
};
export type AnalyzerModule = {
  summarizeHeapSnapshot(path: string): Promise<unknown>;
  diffHeapSnapshots(before: string, after: string): Promise<unknown>;
};
export type PluginModule = {
  createPluginRunner(): Runner;
  loadRulesDirectory(
    path: string,
  ): Promise<
    | { ok: true; rules: { id: string; source: string }[]; failures: unknown[] }
    | { ok: false; error: { code: string; message: string } }
  >;
  runRules(
    runner: Runner,
    rules: { id: string; source: string }[],
    windows: Window[],
  ): Promise<Record<string, RuleResult>>;
};
