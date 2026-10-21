import { buildState, type ToolSpec, type Turn } from "../router.js";
import type { Adapter, Body, ParsedRequest } from "./types.js";
import { toolsOf } from "./types.js";

function textOfContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content
      .map((p: any) => (p?.type === "text" ? String(p.text ?? "") : ""))
      .filter(Boolean)
      .join("\n");
  }
  return "";
}

function turns(messages: unknown): Turn[] {
  const out: Turn[] = [];
  if (!Array.isArray(messages)) return out;
  for (const m of messages) {
    if (m?.role === "user") {
      const t = textOfContent(m.content);
      if (t) out.push({ role: "user", text: t });
    } else if (m?.role === "assistant") {
      const calls = (Array.isArray(m.tool_calls) ? m.tool_calls : []).map((c: any) => ({
        id: String(c?.id ?? ""),
        tool: String(c?.function?.name ?? ""),
        input: c?.function?.arguments,
      }));
      const text = textOfContent(m.content);
      if (text || calls.length) out.push({ role: "assistant", text, calls });
    } else if (m?.role === "tool") {
      out.push({ role: "tool", id: String(m.tool_call_id ?? ""), tool: m.name ? String(m.name) : undefined, output: m.content });
    }
  }
  return out;
}

export const openaiChat: Adapter = {
  agent: "openai-chat",
  path: "/v1/chat/completions",
  upstreamEnv: "XAI_UPSTREAM",
  defaultUpstream: "https://api.x.ai",

  parse(body: Body): ParsedRequest {
    const options: ToolSpec[] = toolsOf(body)
      .map((t: any) => ({
        name: String(t?.function?.name ?? ""),
        description: t?.function?.description ? String(t.function.description) : undefined,
      }))
      .filter((t) => t.name);
    return {
      state: buildState(turns(body.messages)),
      options,
      model: String(body.model ?? "unknown"),
      session: body.user ? String(body.user) : undefined,
    };
  },

  apply(body: Body, tool: string | null): void {
    body.tool_choice = tool ? { type: "function", function: { name: tool } } : "auto";
  },

  hint(body: Body, text: string): void {
    if (!Array.isArray(body.messages)) return;
    const system = body.messages.find((m: any) => m?.role === "system" || m?.role === "developer");
    if (system && typeof system.content === "string") system.content = `${system.content}\n\n${text}`;
    else body.messages.unshift({ role: "system", content: text });
  },

  actualFrom(json: Body): string | undefined {
    const name = json?.choices?.[0]?.message?.tool_calls?.[0]?.function?.name;
    return name ? String(name) : undefined;
  },

  actualFromEvent(data: Body): string | undefined {
    const name = data?.choices?.[0]?.delta?.tool_calls?.[0]?.function?.name;
    return name ? String(name) : undefined;
  },
};
