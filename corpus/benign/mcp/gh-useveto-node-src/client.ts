import type {
  Agent,
  AuthorizationResult,
  AuditLogEntry,
  Policy,
  PolicyRule,
} from "./types.js";
import { VetoError, UnauthorizedError, RateLimitError } from "./errors.js";

// ── Client options ──

export interface VetoClientOptions {
  /** Your Veto API key */
  apiKey: string;
  /** API base URL (default: https://api.veto.tools) */
  endpoint?: string;
  /** Request timeout in ms (default: 5000) */
  timeout?: number;
}

// ── Request/response types for CRUD operations ──

export interface CreateAgentInput {
  name: string;
  description?: string;
}

export interface CreatePolicyInput {
  agentId: string;
  name: string;
  rules: PolicyRule[];
  priority?: number;
  enabled?: boolean;
}

export interface UpdatePolicyInput {
  name?: string;
  rules?: PolicyRule[];
  priority?: number;
  enabled?: boolean;
}

export interface AuditLogFilters {
  agentId?: string;
  action?: string;
  toolName?: string;
  result?: "allowed" | "denied" | "escalated";
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

export interface PaginatedAuditLogResponse {
  data: AuditLogEntry[];
  pagination: {
    limit: number;
    offset: number;
    count: number;
    total: number;
  };
}

interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
  };
}

// ── Client ──

export class VetoClient {
  private readonly apiKey: string;
  private readonly endpoint: string;
  private readonly timeout: number;

  constructor(options: VetoClientOptions) {
    this.apiKey = options.apiKey;
    this.endpoint = (options.endpoint ?? "https://api.veto.tools").replace(
      /\/$/,
      "",
    );
    this.timeout = options.timeout ?? 5000;
  }

  // ── Authorization (the main event) ──

  /**
   * Check if an agent is authorized to call a tool with given parameters.
   * This is the primary method — the whole reason Veto exists.
   */
  async authorize(
    agentId: string,
    toolName: string,
    parameters: Record<string, unknown> = {},
  ): Promise<AuthorizationResult> {
    return this.request<AuthorizationResult>("POST", "/v1/authorize", {
      agent_id: agentId,
      tool_name: toolName,
      parameters,
    });
  }

  // ── Agents CRUD ──

  async createAgent(input: CreateAgentInput): Promise<Agent> {
    return this.request<Agent>("POST", "/v1/agents", input);
  }

  async listAgents(): Promise<Agent[]> {
    const res = await this.request<{ data: Agent[]; pagination: unknown }>(
      "GET",
      "/v1/agents",
    );
    return res.data;
  }

  async getAgent(agentId: string): Promise<Agent> {
    return this.request<Agent>("GET", `/v1/agents/${agentId}`);
  }

  async deleteAgent(agentId: string): Promise<void> {
    await this.request<void>("DELETE", `/v1/agents/${agentId}`);
  }

  // ── Policies CRUD ──

  async createPolicy(input: CreatePolicyInput): Promise<Policy> {
    return this.request<Policy>("POST", "/v1/policies", {
      agent_id: input.agentId,
      name: input.name,
      rules: input.rules,
      priority: input.priority,
      enabled: input.enabled,
    });
  }

  async listPolicies(agentId?: string): Promise<Policy[]> {
    const query = agentId ? `?agent_id=${agentId}` : "";
    const res = await this.request<{ data: Policy[]; pagination: unknown }>(
      "GET",
      `/v1/policies${query}`,
    );
    return res.data;
  }

  async getPolicy(policyId: string): Promise<Policy> {
    return this.request<Policy>("GET", `/v1/policies/${policyId}`);
  }

  async updatePolicy(
    policyId: string,
    input: UpdatePolicyInput,
  ): Promise<Policy> {
    return this.request<Policy>("PATCH", `/v1/policies/${policyId}`, input);
  }

  async deletePolicy(policyId: string): Promise<void> {
    await this.request<void>("DELETE", `/v1/policies/${policyId}`);
  }

  // ── Audit Logs ──

  async queryAuditLog(
    filters: AuditLogFilters = {},
  ): Promise<PaginatedAuditLogResponse> {
    const params = new URLSearchParams();
    if (filters.agentId) params.set("agent_id", filters.agentId);
    if (filters.action) params.set("action", filters.action);
    if (filters.toolName) params.set("tool_name", filters.toolName);
    if (filters.result) params.set("result", filters.result);
    if (filters.from) params.set("from", filters.from);
    if (filters.to) params.set("to", filters.to);
    if (filters.limit !== undefined) params.set("limit", String(filters.limit));
    if (filters.offset !== undefined)
      params.set("offset", String(filters.offset));

    const query = params.toString() ? `?${params.toString()}` : "";
    return this.request<PaginatedAuditLogResponse>(
      "GET",
      `/v1/audit-logs${query}`,
    );
  }

  // ── HTTP layer ──

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const url = `${this.endpoint}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${this.apiKey}`,
          "Content-Type": "application/json",
          "User-Agent": "@useveto/node",
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!response.ok) {
        await this.handleError(response);
      }

      // 204 No Content (e.g. DELETE)
      if (response.status === 204) {
        return undefined as T;
      }

      return (await response.json()) as T;
    } catch (error) {
      if (error instanceof VetoError) throw error;
      if (
        error instanceof Error &&
        (error.name === "AbortError" || error.name === "TimeoutError")
      ) {
        throw new VetoError("Request timed out", "TIMEOUT", 408);
      }
      throw new VetoError(
        `Request failed: ${error instanceof Error ? error.message : String(error)}`,
        "NETWORK_ERROR",
        0,
      );
    } finally {
      clearTimeout(timer);
    }
  }

  private async handleError(response: Response): Promise<never> {
    let errorBody: ApiErrorResponse | undefined;
    try {
      errorBody = (await response.json()) as ApiErrorResponse;
    } catch {
      // Couldn't parse error body — fall through
    }

    const message = errorBody?.error?.message ?? response.statusText;
    const code = errorBody?.error?.code ?? "UNKNOWN";

    if (response.status === 401) {
      throw new UnauthorizedError(message);
    }
    if (response.status === 429) {
      const retryAfter =
        parseInt(response.headers.get("Retry-After") ?? "60", 10) * 1000;
      throw new RateLimitError(message, retryAfter);
    }

    throw new VetoError(message, code, response.status);
  }
}
