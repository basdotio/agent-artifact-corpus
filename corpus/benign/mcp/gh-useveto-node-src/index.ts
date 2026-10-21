export { VetoClient } from "./client.js";
export type {
  VetoClientOptions,
  CreateAgentInput,
  CreatePolicyInput,
  UpdatePolicyInput,
  AuditLogFilters,
  PaginatedAuditLogResponse,
} from "./client.js";
export { VetoError, UnauthorizedError, RateLimitError } from "./errors.js";
export { vetoMiddleware, createVetoGuard } from "./mcp.js";
export type { VetoMcpOptions, McpToolResponse } from "./mcp.js";

// Re-export types for convenience
export type {
  Agent,
  Policy,
  PolicyRule,
  AuthorizationRequest,
  AuthorizationResult,
  AuditLogEntry,
  ParameterConstraint,
  RateLimitConfig,
  TimeWindowConfig,
  AgentStatus,
  AuthorizationOutcome,
  ApiKey,
} from "./types.js";
export { ErrorCodes, DefaultRateLimits, Defaults } from "./constants.js";
export type { ErrorCode } from "./constants.js";
