import { recordEvent } from "./history.js";
import { clean, formatLog } from "./log-format.js";
export { clean } from "./log-format.js";

export function tint(text: string, code = 36): string {
  return process.stdout.isTTY && process.env.NO_COLOR === undefined ? `\x1b[${code}m${text}\x1b[0m` : text;
}
export function heading(title: string, subtitle?: string): void {
  console.log(`\n  ${tint("jev-classifier", 1)}  ${title}`);
  if (subtitle) console.log(`  ${subtitle}`);
  console.log("");
}
export function row(label: string, value: unknown): void { console.log(`  ${label.padEnd(15)} ${clean(value)}`); }
export function notice(message: string, kind: "ok" | "info" | "error" = "info"): void {
  console.log(`  ${tint(kind.toUpperCase().padEnd(5), kind === "ok" ? 32 : kind === "error" ? 31 : 36)} ${clean(message)}`);
}
export function gatewayEvent(agent: string, message: string, error = false, quiet = false): void {
  recordEvent(agent, clean(message), error);
  if (quiet) return;
  console.log(formatLog({ ts: new Date().toISOString(), agent, message, level: error ? "error" : "info" }, {
    columns: process.stdout.columns, color: Boolean(process.stdout.isTTY && process.env.NO_COLOR === undefined),
  }));
}
