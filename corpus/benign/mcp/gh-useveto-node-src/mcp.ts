import type { VetoClient } from "./client.js";
import { VetoError } from "./errors.js";

/**
 * MCP tool handler response shape.
 * Matches the MCP SDK's expected return type from tool callbacks.
 */
export interface McpToolResponse {
  content: Array<{ type: "text"; text: string }>;
  isError?: boolean;
}

/**
 * Configuration options for Veto MCP integration.
 *
 * Used by both {@link vetoMiddleware} and {@link createVetoGuard}.
 */
export interface VetoMcpOptions {
  /** The agent ID to authorize against */
  agentId: string;

  /**
   * What to do when the Veto API is unreachable (network error, timeout, 5xx).
   *
   * - `"deny"` — fail closed, block the tool call (default, recommended for production)
   * - `"allow"` — fail open, let the tool call proceed
   *
   * @default "deny"
   */
  onError?: "deny" | "allow";

  /**
   * Optional callback invoked when authorization is denied.
   * Useful for logging, metrics, or custom side effects.
   */
  onDenied?: (toolName: string, reason: string) => void;
}

/**
 * Creates a manual guard function for MCP tool handlers.
 *
 * Call the returned function at the start of each tool handler to check
 * authorization before executing the tool logic. Throws {@link VetoError}
 * if the action is denied.
 *
 * @example
 * ```ts
 * import { VetoClient, vetoMiddleware } from "@useveto/node";
 * import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
 * import { z } from "zod";
 *
 * const veto = new VetoClient({ apiKey: "veto_..." });
 * const guard = vetoMiddleware(veto, { agentId: "agent-uuid" });
 *
 * const server = new McpServer({ name: "my-server", version: "1.0.0" });
 *
 * server.registerTool("file-read", {
 *   description: "Read a file",
 *   inputSchema: z.object({ path: z.string() }),
 * }, async ({ path }) => {
 *   await guard("file-read", { path }); // throws if denied
 *   const content = await readFile(path, "utf-8");
 *   return { content: [{ type: "text", text: content }] };
 * });
 * ```
 *
 * @param client - An initialized {@link VetoClient}
 * @param options - Guard configuration
 * @returns An async guard function that throws on denied authorization
 */
export function vetoMiddleware(
  client: VetoClient,
  options: VetoMcpOptions,
): (toolName: string, parameters?: Record<string, unknown>) => Promise<void> {
  const failMode = options.onError ?? "deny";

  return async function checkAuthorization(
    toolName: string,
    parameters: Record<string, unknown> = {},
  ): Promise<void> {
    let result: Awaited<ReturnType<VetoClient["authorize"]>>;

    try {
      result = await client.authorize(options.agentId, toolName, parameters);
    } catch (error: unknown) {
      if (error instanceof VetoError && error.statusCode === 403) {
        // Explicit denial from the API — always throw
        throw error;
      }

      // Network error, timeout, or server error
      if (failMode === "allow") {
        return;
      }

      throw new VetoError(
        `Veto API unreachable — denying tool "${toolName}" (fail-closed). ${error instanceof Error ? error.message : String(error)}`,
        "NETWORK_ERROR",
        503,
      );
    }

    if (!result.allowed) {
      if (options.onDenied) {
        options.onDenied(toolName, result.reason);
      }

      throw new VetoError(
        `Authorization denied for tool "${toolName}": ${result.reason}`,
        "DENIED_BY_POLICY",
        403,
      );
    }
  };
}

/**
 * Creates a higher-order wrapper that protects MCP tool handlers with Veto authorization.
 *
 * Unlike {@link vetoMiddleware}, this wraps the entire handler — the tool logic
 * never executes if authorization is denied. Instead of throwing, it returns an
 * MCP-compatible error response with `isError: true`.
 *
 * @example
 * ```ts
 * import { VetoClient, createVetoGuard } from "@useveto/node";
 * import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
 * import { z } from "zod";
 *
 * const veto = new VetoClient({ apiKey: "veto_..." });
 * const protect = createVetoGuard(veto, { agentId: "agent-uuid" });
 *
 * const server = new McpServer({ name: "my-server", version: "1.0.0" });
 *
 * server.registerTool("file-read", {
 *   description: "Read a file",
 *   inputSchema: z.object({ path: z.string() }),
 * }, protect("file-read", async ({ path }) => {
 *   const content = await readFile(path, "utf-8");
 *   return { content: [{ type: "text", text: content }] };
 * }));
 * ```
 *
 * When denied, returns:
 * ```json
 * {
 *   "content": [{ "type": "text", "text": "Authorization denied: <reason>" }],
 *   "isError": true
 * }
 * ```
 *
 * @param client - An initialized {@link VetoClient}
 * @param options - Guard configuration
 * @returns A function that wraps MCP tool handlers with authorization checks
 */
export function createVetoGuard(
  client: VetoClient,
  options: VetoMcpOptions,
): <TParams extends Record<string, unknown>>(
  toolName: string,
  handler: (params: TParams) => Promise<McpToolResponse>,
) => (params: TParams) => Promise<McpToolResponse> {
  const failMode = options.onError ?? "deny";

  return function protect<TParams extends Record<string, unknown>>(
    toolName: string,
    handler: (params: TParams) => Promise<McpToolResponse>,
  ): (params: TParams) => Promise<McpToolResponse> {
    return async function guardedHandler(
      params: TParams,
    ): Promise<McpToolResponse> {
      let result: Awaited<ReturnType<VetoClient["authorize"]>>;

      try {
        result = await client.authorize(
          options.agentId,
          toolName,
          params as Record<string, unknown>,
        );
      } catch (error: unknown) {
        if (error instanceof VetoError && error.statusCode === 403) {
          // Explicit denial from the API
          if (options.onDenied) {
            options.onDenied(toolName, error.message);
          }
          return {
            content: [
              { type: "text", text: `Authorization denied: ${error.message}` },
            ],
            isError: true,
          };
        }

        // Network error, timeout, or server error
        if (failMode === "allow") {
          return handler(params);
        }

        const errorMsg = error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: "text",
              text: `Veto authorization unavailable — tool "${toolName}" blocked (fail-closed). ${errorMsg}`,
            },
          ],
          isError: true,
        };
      }

      if (!result.allowed) {
        if (options.onDenied) {
          options.onDenied(toolName, result.reason);
        }
        return {
          content: [
            { type: "text", text: `Authorization denied: ${result.reason}` },
          ],
          isError: true,
        };
      }

      return handler(params);
    };
  };
}
