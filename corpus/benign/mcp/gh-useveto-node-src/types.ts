/**
 * Core domain types for the Veto SDK.
 *
 * ⚠️  SYNC NOTE: These types are duplicated from @veto/shared (packages/shared/src/types.ts).
 * The SDK ships as a standalone npm package and cannot depend on the internal workspace
 * package. When updating types, keep both files in sync.
 */

/** Status of a registered agent */
export type AgentStatus = "active" | "suspended" | "revoked";

/** A registered AI agent */
export interface Agent {
  id: string;
  name: string;
  description: string | null;
  ownerId: string;
  status: AgentStatus;
  createdAt: string;
  updatedAt: string;
}

/** Authorization outcome */
export type AuthorizationOutcome = "allowed" | "denied" | "escalated";

/** A single rule inside a policy */
export interface PolicyRule {
  /** Rule type determines how it's evaluated */
  type:
    | "tool_allowlist"
    | "tool_denylist"
    | "parameter_constraint"
    | "rate_limit"
    | "time_based";

  /** Tool names this rule applies to (glob patterns supported) */
  tools?: string[];

  /** Parameter constraints — key is param name */
  parameters?: Record<string, ParameterConstraint>;

  /** Rate limit config */
  rateLimit?: RateLimitConfig;

  /** Time-based access window */
  timeWindow?: TimeWindowConfig;
}

/** Constraint on a single parameter value */
export interface ParameterConstraint {
  /** Must match this regex */
  regex?: string;
  /** Must be one of these values */
  enum?: string[];
  /** Numeric minimum (inclusive) */
  min?: number;
  /** Numeric maximum (inclusive) */
  max?: number;
}

/** Rate limiting configuration */
export interface RateLimitConfig {
  /** Maximum allowed calls */
  maxCalls: number;
  /** Time window in seconds */
  windowSeconds: number;
  /** Current call count in the window (provided by caller, tracked externally) */
  currentCount?: number;
}

/** Time-based access window */
export interface TimeWindowConfig {
  /** Allowed hours of day (0-23) — e.g. [9, 10, ..., 17] for business hours */
  allowedHours?: number[];
  /** Allowed days of week (0=Sunday, 6=Saturday) */
  allowedDays?: number[];
  /** IANA timezone string — e.g. "America/Chicago" */
  timezone?: string;
}

/** A policy governing what an agent can do */
export interface Policy {
  id: string;
  agentId: string;
  name: string;
  rules: PolicyRule[];
  /** Higher priority policies are evaluated first */
  priority: number;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Incoming authorization request */
export interface AuthorizationRequest {
  agentId: string;
  toolName: string;
  parameters: Record<string, unknown>;
  /** Current rate limit counts keyed by policy rule index */
  rateLimitCounts?: Record<string, number>;
  /** Current timestamp override (ISO string) — defaults to now */
  timestamp?: string;
}

/** Result of an authorization evaluation */
export interface AuthorizationResult {
  allowed: boolean;
  outcome: AuthorizationOutcome;
  /** ID of the policy that produced this decision (null if default deny) */
  matchedPolicyId: string | null;
  /** Human-readable explanation */
  reason: string;
  evaluatedAt: string;
}

/** Audit log entry for every authorization decision */
export interface AuditLogEntry {
  id: string;
  agentId: string;
  action: string;
  toolName: string;
  parameters: Record<string, unknown>;
  result: AuthorizationOutcome;
  policyId: string | null;
  reason: string;
  latencyMs: number;
  timestamp: string;
}

/** API key metadata (never expose the raw key after creation) */
export interface ApiKey {
  id: string;
  agentId: string;
  /** First 8 chars of the key for identification */
  prefix: string;
  keyHash: string;
  scopes: string[];
  expiresAt: string | null;
  createdAt: string;
}
