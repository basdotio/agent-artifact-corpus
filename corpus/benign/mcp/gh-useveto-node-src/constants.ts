// ── Error codes returned by the Veto API ──

export const ErrorCodes = {
  // Auth errors
  UNAUTHORIZED: "UNAUTHORIZED",
  API_KEY_EXPIRED: "API_KEY_EXPIRED",
  INSUFFICIENT_SCOPE: "INSUFFICIENT_SCOPE",

  // Authorization errors
  DENIED_BY_POLICY: "DENIED_BY_POLICY",
  DENIED_DEFAULT: "DENIED_DEFAULT",
  RATE_LIMITED: "RATE_LIMITED",
  OUTSIDE_TIME_WINDOW: "OUTSIDE_TIME_WINDOW",
  TOOL_NOT_ALLOWED: "TOOL_NOT_ALLOWED",
  PARAMETER_VIOLATION: "PARAMETER_VIOLATION",

  // Resource errors
  AGENT_NOT_FOUND: "AGENT_NOT_FOUND",
  POLICY_NOT_FOUND: "POLICY_NOT_FOUND",
  AGENT_SUSPENDED: "AGENT_SUSPENDED",

  // General
  VALIDATION_ERROR: "VALIDATION_ERROR",
  INTERNAL_ERROR: "INTERNAL_ERROR",
} as const;

export type ErrorCode = (typeof ErrorCodes)[keyof typeof ErrorCodes];

// ── Default rate limits ──

export const DefaultRateLimits = {
  /** Default max requests per minute per API key */
  API_REQUESTS_PER_MINUTE: 600,
  /** Default max authorization checks per minute per agent */
  AUTH_CHECKS_PER_MINUTE: 1000,
  /** Default max audit log query results */
  AUDIT_LOG_PAGE_SIZE: 100,
  /** Maximum audit log query results */
  AUDIT_LOG_MAX_PAGE_SIZE: 1000,
} as const;

// ── API defaults ──

export const Defaults = {
  /** Default API port for local development */
  API_PORT: 8787,
  /** Default policy priority */
  POLICY_PRIORITY: 0,
  /** Authorization request timeout in ms */
  AUTH_TIMEOUT_MS: 5000,
} as const;
