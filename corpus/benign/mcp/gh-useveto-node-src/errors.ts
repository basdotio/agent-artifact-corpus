/** Base error for all Veto SDK errors */
export class VetoError extends Error {
  public readonly code: string;
  public readonly statusCode: number;

  constructor(message: string, code: string, statusCode: number = 500) {
    super(message);
    this.name = "VetoError";
    this.code = code;
    this.statusCode = statusCode;
  }
}

/** Thrown when authentication fails (invalid/expired API key) */
export class UnauthorizedError extends VetoError {
  constructor(message: string = "Unauthorized") {
    super(message, "UNAUTHORIZED", 401);
    this.name = "UnauthorizedError";
  }
}

/** Thrown when rate limit is exceeded */
export class RateLimitError extends VetoError {
  public readonly retryAfterMs: number;

  constructor(message: string = "Rate limit exceeded", retryAfterMs: number = 60000) {
    super(message, "RATE_LIMITED", 429);
    this.name = "RateLimitError";
    this.retryAfterMs = retryAfterMs;
  }
}
