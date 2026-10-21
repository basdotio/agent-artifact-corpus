import { readFileSync } from "node:fs";
import type { DecisionRecord } from "./log.js";
import { logPath } from "./log.js";

export function readDecisions(file = logPath()): DecisionRecord[] {
  let text: string;
  try {
    text = readFileSync(file, "utf8");
  } catch {
    return [];
  }
  const out: DecisionRecord[] = [];
  for (const line of text.split("\n")) {
    if (!line.trim()) continue;
    try {
      out.push(JSON.parse(line) as DecisionRecord);
    } catch {
      // skip a half-written line
    }
  }
  return out;
}

export function percentile(values: readonly number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length));
  return sorted[index] ?? 0;
}

export interface Aggregate {
  agent: string;
  model: string;
  mode: string;
  count: number;
  appliedPct: number;
  gatedPct: number;
  matchPct: number | undefined;
  avgConfidence: number;
  jevP50: number;
  jevP95: number;
}

export function aggregate(records: readonly DecisionRecord[]): Aggregate[] {
  const groups = new Map<string, DecisionRecord[]>();
  for (const r of records) {
    const key = `${r.agent}|${r.model}|${r.mode}`;
    const list = groups.get(key);
    if (list) list.push(r);
    else groups.set(key, [r]);
  }
  const rows: Aggregate[] = [];
  for (const [key, list] of groups) {
    const [agent = "", model = "", mode = ""] = key.split("|");
    const withActual = list.filter((r) => r.actual !== undefined);
    const jev = list.map((r) => r.jevMs);
    rows.push({
      agent,
      model,
      mode,
      count: list.length,
      appliedPct: pct(list.filter((r) => r.applied).length, list.length),
      gatedPct: pct(list.filter((r) => r.gated).length, list.length),
      matchPct: withActual.length ? pct(withActual.filter((r) => r.match).length, withActual.length) : undefined,
      avgConfidence: list.reduce((s, r) => s + r.confidence, 0) / list.length,
      jevP50: percentile(jev, 50),
      jevP95: percentile(jev, 95),
    });
  }
  return rows.sort((a, b) => b.count - a.count);
}

function pct(n: number, total: number): number {
  return total === 0 ? 0 : Math.round((n / total) * 1000) / 10;
}

export function printMetrics(file = logPath()): void {
  const records = readDecisions(file);
  if (records.length === 0) {
    console.log(`No decisions in ${file}. Run 'jev-classifier serve' and point an agent at it first.`);
    return;
  }
  const rows = aggregate(records).map((r) => ({
    agent: r.agent,
    model: r.model,
    mode: r.mode,
    n: r.count,
    "applied%": r.appliedPct,
    "gated%": r.gatedPct,
    "match%": r.matchPct ?? "-",
    conf: Math.round(r.avgConfidence * 100) / 100,
    "jev p50": r.jevP50,
    "jev p95": r.jevP95,
  }));
  console.log(`${records.length} decisions in ${file}`);
  console.table(rows);
}
