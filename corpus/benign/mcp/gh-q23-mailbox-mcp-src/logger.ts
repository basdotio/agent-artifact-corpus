export type LogLevel = "debug" | "info" | "warn" | "error";

const LOG_LEVEL = (process.env.LOG_LEVEL || "info") as LogLevel;

const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
};

const SAFE_ARGUMENT_FIELDS = [
  "folder",
  "uid",
  "limit",
  "offset",
  "sort_order",
  "since",
  "before",
  "reply_all",
] as const;

function shouldLog(level: LogLevel): boolean {
  return LOG_LEVELS[level] >= LOG_LEVELS[LOG_LEVEL];
}

function emit(level: LogLevel, msg: string, data?: unknown): void {
  if (!shouldLog(level)) {
    return;
  }

  if (data === undefined) {
    console.error(`[${level.toUpperCase()}] ${msg}`);
    return;
  }

  console.error(`[${level.toUpperCase()}] ${msg}`, data);
}

export function errorToMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function maskEmail(value: string): string {
  const [localPart, domain] = value.split("@");

  if (!localPart || !domain) {
    return "[redacted]";
  }

  if (localPart.length <= 2) {
    return `${localPart[0] || "*"}***@${domain}`;
  }

  return `${localPart[0]}***${localPart[localPart.length - 1]}@${domain}`;
}

export function summarizeHeaderCredentials(
  headerUser: unknown,
  headerPass: unknown
): Record<string, unknown> {
  const user = typeof headerUser === "string" ? headerUser : undefined;
  const pass = typeof headerPass === "string" ? headerPass : undefined;

  return {
    has_header_credentials: Boolean(user && pass),
    header_user: user ? maskEmail(user) : undefined,
  };
}

export function summarizeToolArguments(
  toolName: string,
  args: unknown
): Record<string, unknown> {
  const summary: Record<string, unknown> = {
    tool: toolName,
  };

  if (!args || typeof args !== "object" || Array.isArray(args)) {
    return summary;
  }

  const input = args as Record<string, unknown>;

  for (const field of SAFE_ARGUMENT_FIELDS) {
    if (field in input) {
      summary[field] = input[field];
    }
  }

  if (typeof input.from === "string") {
    summary.from = maskEmail(input.from);
  }

  if (typeof input.imap_user === "string") {
    summary.imap_user = maskEmail(input.imap_user);
  }

  if ("credentials" in input) {
    summary.has_credentials = typeof input.credentials === "string" && input.credentials.length > 0;
  }

  if ("imap_pass" in input) {
    summary.has_imap_pass = typeof input.imap_pass === "string" && input.imap_pass.length > 0;
  }

  if ("subject" in input) {
    summary.has_subject = typeof input.subject === "string" && input.subject.length > 0;
  }

  if ("query" in input) {
    summary.has_query = typeof input.query === "string" && input.query.length > 0;
  }

  if ("text" in input) {
    summary.text_length = typeof input.text === "string" ? input.text.length : undefined;
  }

  if ("html" in input) {
    summary.has_html = typeof input.html === "string" && input.html.length > 0;
  }

  if (Array.isArray(input.to)) {
    summary.to_count = input.to.length;
  }

  if (Array.isArray(input.cc)) {
    summary.cc_count = input.cc.length;
  }

  if (Array.isArray(input.bcc)) {
    summary.bcc_count = input.bcc.length;
  }

  return summary;
}

export const logger = {
  debug: (msg: string, data?: unknown): void => emit("debug", msg, data),
  info: (msg: string, data?: unknown): void => emit("info", msg, data),
  warn: (msg: string, data?: unknown): void => emit("warn", msg, data),
  error: (msg: string, data?: unknown): void => emit("error", msg, data),
};
