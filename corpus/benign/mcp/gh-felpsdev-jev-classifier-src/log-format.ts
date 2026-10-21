import { stripVTControlCharacters } from "node:util";

export function clean(value: unknown): string {
  return stripVTControlCharacters(String(value)).replace(/[\x00-\x1f\x7f\u2028\u2029]/g, " ");
}

export function agentLabel(agent: unknown): string {
  const name = clean(agent ?? "gateway");
  return ({ anthropic: "claude", "openai-responses": "codex", "openai-chat": "grok" } as Record<string, string>)[name] ?? name;
}

/** Wrap before applying ANSI colors. Reserve one terminal column to avoid auto-wrap. */
export function wrapText(text: string, width: number): string[] {
  const lines: string[] = [];
  let rest = clean(text).trim();
  width = Math.max(1, width);
  while (Array.from(rest).length > width) {
    const chars = Array.from(rest);
    const candidate = chars.slice(0, width).join("");
    const space = candidate.lastIndexOf(" ");
    const cut = space > width / 2 ? Array.from(candidate.slice(0, space)).length : width;
    lines.push(chars.slice(0, cut).join(""));
    rest = chars.slice(cut).join("").trimStart();
  }
  lines.push(rest);
  return lines;
}

interface LogItem {
  ts?: unknown; agent?: unknown; level?: unknown; message?: unknown;
  chosen?: unknown; actual?: unknown; mode?: unknown; confidence?: unknown;
  jevMs?: unknown; upstreamMs?: unknown; applied?: unknown; match?: unknown;
}

export function formatLog(item: LogItem, options: { columns?: number; color?: boolean; date?: boolean } = {}): string {
  const paint = (value: string, code: number) => options.color ? `\x1b[${code}m${value}\x1b[0m` : value;
  const parsed = new Date(String(item.ts));
  const valid = !Number.isNaN(parsed.getTime());
  const clock = valid ? parsed.toLocaleTimeString("en-GB", { hour12: false }) : "--:--:--";
  const date = valid ? `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${String(parsed.getDate()).padStart(2, "0")}` : "----------";
  const time = options.date ? `${date} ${clock}` : clock;
  const level = item.level === "error" ? "ERROR" : "INFO";
  const agent = agentLabel(item.agent);
  const message = item.message === undefined
    ? [
      `Decision | chosen=${clean(item.chosen ?? "-")}`,
      `actual=${clean(item.actual ?? "-")}`,
      `confidence=${typeof item.confidence === "number" ? `${Math.round(item.confidence * 100)}%` : "-"}`,
      `mode=${item.mode === "shadow" ? "observe" : clean(item.mode ?? "-")}`,
      `result=${item.applied ? "applied" : "observed"}`,
      ...(typeof item.match === "boolean" ? [`match=${item.match ? "yes" : "no"}`] : []),
      ...(typeof item.jevMs === "number" ? [`jev=${item.jevMs}ms`] : []),
      ...(typeof item.upstreamMs === "number" ? [`upstream=${item.upstreamMs}ms`] : []),
    ].join(" | ") : clean(item.message);
  const width = Math.max(20, (options.columns || 120) - 1);
  const prefix = `${time}  ${level.padEnd(5)}  ${agent.padEnd(10)}  `;
  if (width - prefix.length < 28) {
    // Compact terminals get a separate metadata line instead of tiny message fragments.
    return [...wrapText(`${time}  ${level}  ${agent}`, width).map(line => paint(line, level === "ERROR" ? 31 : 90)),
      ...wrapText(message, width - 2).map(line => `  ${line}`)].join("\n");
  }
  const lines = wrapText(message, width - prefix.length);
  return `${paint(time, 90)}  ${paint(level.padEnd(5), level === "ERROR" ? 31 : 90)}  ${paint(agent.padEnd(10), 36)}  ${lines[0]}`
    + lines.slice(1).map(line => `\n${" ".repeat(prefix.length)}${line}`).join("");
}
