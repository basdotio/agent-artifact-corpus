import { appendFileSync, existsSync, mkdirSync, renameSync, rmSync, statSync, openSync, readSync, closeSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as delay } from "node:timers/promises";
import { configDirectory } from "./settings.js";
import { formatLog } from "./log-format.js";
import { StringDecoder } from "node:string_decoder";

export const eventLogPath = () => join(configDirectory(), "gateway.jsonl");
export function recordEvent(agent: string, message: string, error = false): void {
  const file = eventLogPath();
  try {
    mkdirSync(configDirectory(), { recursive: true, mode: 0o700 });
    // Keep one previous 5 MB segment; decision logs have their own existing retention policy.
    if (existsSync(file) && statSync(file).size > 5 * 1024 * 1024) {
      rmSync(`${file}.1`, { force: true });
      renameSync(file, `${file}.1`);
    }
    appendFileSync(file, JSON.stringify({ ts: new Date().toISOString(), agent, level: error ? "error" : "info", message }) + "\n", { mode: 0o600 });
  } catch { /* Log failure must not interrupt inference. */ }
}

/** Read only a bounded tail, including the previous segment after rotation. */
export function tailLines(file: string, count: number): string[] {
  if (!existsSync(file)) return [];
  const handle = openSync(file, "r");
  try {
    const size = statSync(file).size;
    const start = Math.max(0, size - 1024 * 1024);
    const bytes = Buffer.alloc(size - start);
    readSync(handle, bytes, 0, bytes.length, start);
    const lines = bytes.toString("utf8").split("\n");
    if (start > 0) lines.shift();
    // Ignore the final partial line until the writer finishes it.
    lines.pop();
    return lines.filter(Boolean).slice(-count);
  } finally { closeSync(handle); }
}
export function printLogLine(line: string, json: boolean): void {
  try {
    const item = JSON.parse(line);
    if (json) console.log(JSON.stringify(item));
    else {
      console.log(formatLog(item, { date: true, columns: process.stdout.columns,
        color: Boolean(process.stdout.isTTY && process.env.NO_COLOR === undefined) }));
    }
  } catch { /* ignore an incomplete or malformed record */ }
}
export async function showLogs(file: string, count: number, follow: boolean, json: boolean): Promise<void> {
  const current = tailLines(file, count);
  const previous = current.length < count ? tailLines(`${file}.1`, count - current.length) : [];
  for (const line of [...previous, ...current]) printLogLine(line, json);
  if (!current.length && !previous.length && !json) console.log("No log entries yet. Start the gateway and connect an agent.");
  if (!follow) return;
  const stop = new AbortController();
  const interrupt = () => stop.abort();
  process.on("SIGINT", interrupt);
  let position = existsSync(file) ? statSync(file).size : 0;
  let partial = "";
  let decoder = new StringDecoder("utf8");
  try {
    while (!stop.signal.aborted) {
      await delay(500, undefined, { signal: stop.signal }).catch(() => {});
      if (!existsSync(file)) continue;
      const size = statSync(file).size;
      if (size < position) { position = 0; partial = ""; decoder = new StringDecoder("utf8"); }
      if (size === position) continue;
      const handle = openSync(file, "r");
      try {
        const bytes = Buffer.alloc(Math.min(size - position, 1024 * 1024));
        const read = readSync(handle, bytes, 0, bytes.length, position);
        position += read;
        const lines = (partial + decoder.write(bytes.subarray(0, read))).split("\n");
        partial = lines.pop() || "";
        for (const line of lines) printLogLine(line, json);
      } finally { closeSync(handle); }
    }
  } finally { process.off("SIGINT", interrupt); }
}
