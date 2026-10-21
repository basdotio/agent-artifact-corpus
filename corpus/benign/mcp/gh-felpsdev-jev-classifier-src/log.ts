import { appendFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

export interface DecisionRecord {
  ts: string;
  agent: string;
  model: string;
  session: string;
  mode: "enforce" | "shadow";
  chosen: string;
  confidence: number;
  done: number;
  gated: boolean;
  truncated: boolean;
  top3: { name: string; p: number }[];
  jevMs: number;
  upstreamMs: number;
  toolsCount: number;
  applied: boolean;
  shadowReason?: string;
  actual?: string;
  match?: boolean;
}

export function logPath(): string {
  return process.env.JEV_LOG || ".jev-classifier/decisions.jsonl";
}

export function appendDecision(record: DecisionRecord): void {
  const file = logPath();
  mkdirSync(dirname(file), { recursive: true });
  appendFileSync(file, `${JSON.stringify(record)}\n`);
}
