import type { RouterState, ToolSpec } from "../router.js";

/** Wire bodies are untyped JSON; adapters poke at known fields. */
export type Body = Record<string, any>;

export interface ParsedRequest {
  readonly state: RouterState;
  readonly options: readonly ToolSpec[];
  readonly model: string;
  readonly session?: string;
  /** Set when this request cannot be enforced (e.g. server-side history); server falls back to shadow. */
  readonly shadowReason?: string;
}

export interface Adapter {
  /** Agent/API family this adapter speaks; used as the `agent` field in the log. */
  readonly agent: string;
  readonly path: string;
  readonly upstreamEnv: string;
  readonly defaultUpstream: string;
  parse(body: Body): ParsedRequest;
  /** Rewrite tool_choice in place. `null` means "let the model decide". */
  apply(body: Body, tool: string | null): void;
  /** Add a nudge to the system prompt when confidence is too low to force a tool. */
  hint(body: Body, text: string): void;
  /** Tool name from a non-streaming response body. */
  actualFrom(json: Body): string | undefined;
  /** Tool name from one parsed SSE `data:` payload. */
  actualFromEvent(data: Body): string | undefined;
}

export function toolsOf(body: Body): unknown[] {
  return Array.isArray(body.tools) ? body.tools : [];
}
