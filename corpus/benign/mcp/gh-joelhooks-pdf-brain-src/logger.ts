import type { LogLevel } from "./agent/protocol.js";

const LEVEL_SEVERITY: Record<LogLevel, number> = {
  silent: 0,
  error: 1,
  info: 2,
  debug: 3,
};

let currentLevel: LogLevel = (() => {
  const raw = process.env.PDF_BRAIN_LOG_LEVEL;
  if (raw === "silent" || raw === "error" || raw === "info" || raw === "debug") {
    return raw;
  }
  return "silent";
})();

export function setLogLevel(level: LogLevel): void {
  currentLevel = level;
  process.env.PDF_BRAIN_LOG_LEVEL = level;
}

export function getLogLevel(): LogLevel {
  return currentLevel;
}

function shouldLog(level: Exclude<LogLevel, "silent">): boolean {
  return LEVEL_SEVERITY[currentLevel] >= LEVEL_SEVERITY[level];
}

function write(prefix: string, message: string): void {
  try {
    process.stderr.write(`${prefix}${message}\n`);
  } catch {
    // ignore
  }
}

export function logError(message: string): void {
  if (!shouldLog("error")) return;
  write("[pdf-brain:error] ", message);
}

export function logInfo(message: string): void {
  if (!shouldLog("info")) return;
  write("[pdf-brain] ", message);
}

export function logDebug(message: string): void {
  if (!shouldLog("debug")) return;
  write("[pdf-brain:debug] ", message);
}

