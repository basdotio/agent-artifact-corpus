import { buildState, type ToolSpec, type Turn } from "../router.js";
import type { Adapter, Body, ParsedRequest } from "./types.js";
import { toolsOf } from "./types.js";

/** Codex Responses Lite declares tools inside input, including namespace containers. */
function responseTools(body: Body): Body[] {
  const catalog: Body[] = [];
  const visit = (tools: unknown[]) => {
    for (const tool of tools as Body[]) {
      if (tool?.type === "namespace" && Array.isArray(tool.tools)) visit(tool.tools);
      else if ((tool?.type === "function" || tool?.type === "custom") && tool.name) catalog.push(tool);
    }
  };
  visit(toolsOf(body));
  if (Array.isArray(body.input)) {
    for (const item of body.input) {
      if (item?.type === "additional_tools" && Array.isArray(item.tools)) visit(item.tools);
    }
  }
  return catalog;
}

function textOfContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((p: any) => (p?.type === "input_text" || p?.type === "output_text" ? String(p.text ?? "") : ""))
      .filter(Boolean)
      .join("\n");
  }
  return "";
}

function turns(input: unknown): Turn[] {
  if (typeof input === "string") return input ? [{ role: "user", text: input }] : [];
  const out: Turn[] = [];
  if (!Array.isArray(input)) return out;
  for (const item of input) {
    if (item?.type === "function_call" || item?.type === "custom_tool_call") {
      out.push({
        role: "assistant",
        calls: [{ id: String(item.call_id ?? item.id ?? ""), tool: String(item.name ?? ""), input: item.type === "custom_tool_call" ? item.input : item.arguments }],
      });
    } else if (item?.type === "function_call_output" || item?.type === "custom_tool_call_output") {
      out.push({ role: "tool", id: String(item.call_id ?? ""), output: item.output });
    } else if (item?.role === "assistant") {
      const text = textOfContent(item.content);
      if (text) out.push({ role: "assistant", text });
    } else if (item?.role === "user" || item?.role === "system" || item?.role === "developer") {
      if (item.role !== "user") continue;
      const text = textOfContent(item.content);
      if (text) out.push({ role: "user", text });
    }
  }
  return out;
}

export const openaiResponses: Adapter = {
  agent: "openai-responses",
  path: "/v1/responses",
  upstreamEnv: "OPENAI_UPSTREAM",
  defaultUpstream: "https://api.openai.com",

  parse(body: Body): ParsedRequest {
    const catalog = responseTools(body);
    const options: ToolSpec[] = catalog
      .map((t: any) => ({ name: String(t?.name ?? ""), description: t?.description ? String(t.description) : undefined }))
      .filter((t) => t.name);
    return {
      state: buildState(turns(body.input)),
      options,
      model: String(body.model ?? "unknown"),
      session: body.previous_response_id ? String(body.previous_response_id) : undefined,
      shadowReason: body.previous_response_id
        ? "previous_response_id: history lives on the server, local state is incomplete"
        : new Set(options.map((tool) => tool.name)).size !== options.length
          ? "duplicate tool names across declarations: cannot force an unambiguous tool"
          : Array.isArray(body.input) && body.input.some((item: Body) => item?.type === "additional_tools")
            ? "Codex Responses Lite: tool_choice enforcement is not validated; preserving the original request"
          : undefined,
    };
  },

  apply(body: Body, tool: string | null): void {
    const spec = responseTools(body).find((t) => t.name === tool);
    body.tool_choice = tool ? { type: spec?.type === "custom" ? "custom" : "function", name: tool } : "auto";
  },

  hint(body: Body, text: string): void {
    body.instructions = body.instructions ? `${body.instructions}\n\n${text}` : text;
  },

  actualFrom(json: Body): string | undefined {
    const item = Array.isArray(json?.output) ? json.output.find((o: any) => o?.type === "function_call" || o?.type === "custom_tool_call") : undefined;
    return item?.name ? String(item.name) : undefined;
  },

  actualFromEvent(data: Body): string | undefined {
    if (data?.type === "response.output_item.added" && (data.item?.type === "function_call" || data.item?.type === "custom_tool_call")) {
      return data.item.name ? String(data.item.name) : undefined;
    }
    return undefined;
  },
};
