import { buildState, type ToolSpec, type Turn } from "../router.js";
import type { Adapter, Body, ParsedRequest } from "./types.js";
import { toolsOf } from "./types.js";

function turns(messages: unknown): Turn[] {
  const out: Turn[] = [];
  if (!Array.isArray(messages)) return out;
  for (const m of messages) {
    const content = m?.content;
    if (typeof content === "string") {
      out.push(m.role === "assistant" ? { role: "assistant", text: content } : { role: "user", text: content });
      continue;
    }
    if (!Array.isArray(content)) continue;
    const texts: string[] = [];
    const calls: { id: string; tool: string; input: unknown }[] = [];
    for (const block of content) {
      if (block?.type === "text") texts.push(String(block.text ?? ""));
      else if (block?.type === "tool_use") calls.push({ id: String(block.id), tool: String(block.name), input: block.input });
      else if (block?.type === "tool_result")
        out.push({ role: "tool", id: String(block.tool_use_id), output: block.content });
    }
    const text = texts.join("\n");
    if (m.role === "assistant") {
      if (text || calls.length) out.push({ role: "assistant", text, calls });
    } else if (text) {
      out.push({ role: "user", text });
    }
  }
  return out;
}

export const anthropic: Adapter = {
  agent: "anthropic",
  path: "/v1/messages",
  upstreamEnv: "ANTHROPIC_UPSTREAM",
  defaultUpstream: "https://api.anthropic.com",

  parse(body: Body): ParsedRequest {
    const options: ToolSpec[] = toolsOf(body)
      .map((t: any) => ({ name: String(t?.name ?? ""), description: t?.description ? String(t.description) : undefined }))
      .filter((t) => t.name);
    return {
      state: buildState(turns(body.messages)),
      options,
      model: String(body.model ?? "unknown"),
      session: body.metadata?.user_id ? String(body.metadata.user_id) : undefined,
    };
  },

  apply(body: Body, tool: string | null): void {
    body.tool_choice = tool ? { type: "tool", name: tool } : { type: "auto" };
  },

  hint(body: Body, text: string): void {
    if (Array.isArray(body.system)) body.system.push({ type: "text", text });
    else if (typeof body.system === "string") body.system = `${body.system}\n\n${text}`;
    else body.system = text;
  },

  actualFrom(json: Body): string | undefined {
    const block = Array.isArray(json?.content) ? json.content.find((b: any) => b?.type === "tool_use") : undefined;
    return block?.name ? String(block.name) : undefined;
  },

  actualFromEvent(data: Body): string | undefined {
    if (data?.type === "content_block_start" && data.content_block?.type === "tool_use") {
      return String(data.content_block.name);
    }
    return undefined;
  },
};
