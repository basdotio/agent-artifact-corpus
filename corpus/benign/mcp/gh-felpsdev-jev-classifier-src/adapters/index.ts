import { anthropic } from "./anthropic.js";
import { openaiChat } from "./openai-chat.js";
import { openaiResponses } from "./openai-responses.js";
import type { Adapter } from "./types.js";

export type { Adapter, Body, ParsedRequest } from "./types.js";

export const ADAPTERS: readonly Adapter[] = [anthropic, openaiChat, openaiResponses];

export function adapterFor(url: string): Adapter | undefined {
  const path = url.split("?")[0] ?? "";
  return ADAPTERS.find((a) => path.endsWith(a.path));
}

export function upstreamFor(a: Adapter): string {
  return (process.env.UPSTREAM || process.env[a.upstreamEnv] || a.defaultUpstream).replace(/\/+$/, "");
}
