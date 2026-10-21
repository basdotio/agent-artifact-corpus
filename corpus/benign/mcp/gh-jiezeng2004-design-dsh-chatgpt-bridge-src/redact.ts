/**
 * Secret redaction helpers. Every bridge log line and every tool output that
 * can carry caller or DSH error text passes through these so credentials,
 * tokens, cookies and API keys never leak into logs or MCP results.
 */

/** Patterns that match secret-shaped substrings. */
const SECRET_PATTERNS: RegExp[] = [
  // Authorization: Bearer <token> as one unit.
  /(?:authorization|auth)\s*[:=]\s*bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi,
  // Whole key=value assignments, so a pair is masked as one unit.
  /(?:api[_-]?key|access[_-]?token|authorization|auth|secret|credential|cookie|session[_-]?token|password|passwd|token|otp|one[-_]?time[-_]?password|2fa[-_]?code)\s*[:=]\s*["']?[^"'\s,;)]{4,}/gi,
  // Standalone bearer tokens.
  /bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi,
  // OpenAI/DeepSeek-style API keys.
  /sk-[A-Za-z0-9_-]{8,}/g,
];

/** Object keys whose whole value is secret-shaped. */
const SECRET_KEYS = /^(authorization|api[-_]?key|access[-_]?key|access[-_]?token|secret|credential|cookie|set-cookie|token|password|passwd|refresh[-_]?token|session[-_]?token|proxy-auth|auth|otp|one[-_]?time[-_]?password|2fa[-_]?code)$/i;

/** True when text contains a secret-shaped token, key assignment, or bearer value. */
export function containsSecret(text: string): boolean {
  for (const pattern of SECRET_PATTERNS) {
    pattern.lastIndex = 0;
    if (pattern.test(text)) return true;
  }
  return false;
}

/** Redact secret-shaped substrings from one text value. */
export function redactText(text: string): string {
  let out = text;
  for (const pattern of SECRET_PATTERNS) {
    pattern.lastIndex = 0;
    out = out.replace(pattern, '[REDACTED]');
  }
  return out;
}

/**
 * Deep-redact a JSON value: secret-shaped keys become '[REDACTED]' and
 * secret-shaped substrings inside string values are masked. Returns a new
 * value; the input is never mutated.
 */
export function redactValue(value: unknown): unknown {
  if (typeof value === 'string') return redactText(value);
  if (Array.isArray(value)) return value.map((item) => redactValue(item));
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
      out[key] = SECRET_KEYS.test(key) ? '[REDACTED]' : redactValue(child);
    }
    return out;
  }
  return value;
}

/** Redact a message plus optional payload into one safe log line. */
export function redactMessage(message: string, payload?: unknown): string {
  const base = redactText(message);
  if (payload === undefined) return base;
  try {
    return `${base} ${JSON.stringify(redactValue(payload))}`;
  } catch {
    return base;
  }
}