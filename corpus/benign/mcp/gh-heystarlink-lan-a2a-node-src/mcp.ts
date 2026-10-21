#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { loadConfig } from "./config.js";
import { LocalApi } from "./local-api.js";

process.title = "lan-a2a-mcp";

const config = await loadConfig(process.env.LAN_A2A_CONFIG ?? "config.json");
const api = await LocalApi.connect(config);
const taskOwners = new Map<string, string>();
const server = new McpServer({ name: "lan-a2a-node", version: "0.1.0" });
const id = z.string().min(1).max(100).regex(/^[A-Za-z0-9._:-]+$/);

server.registerTool("list_agents", {
  description: "List paired and nearby LAN agents with current reachability.",
}, async () => result(await api.get("/local/agents")));

server.registerTool("send_task", {
  description: "Send a bounded task to a paired LAN agent.",
  inputSchema: {
    agentId: id,
    objective: z.string().trim().min(1).max(100_000),
    summary: z.string().trim().max(100_000).optional(),
    expectedOutput: z.string().trim().max(100_000).optional(),
  },
}, async ({ agentId, objective, summary, expectedOutput }) => {
  const value = await api.post("/local/send", { peerId: agentId, objective, summary, expectedOutput });
  const taskId = extractTaskId(value);
  if (taskId) taskOwners.set(taskId, agentId);
  return result(value);
});

server.registerTool("list_tasks", {
  description: "List task references created by this MCP process. Task state itself lives on the remote node.",
}, async () => result({ tasks: [...taskOwners].map(([taskId, agentId]) => ({ taskId, agentId })) }));

server.registerTool("get_task", {
  description: "Get the latest state of a task created by this MCP process.",
  inputSchema: { taskId: id },
}, async ({ taskId }) => result(await api.get(taskPath(owner(taskId), taskId))));

server.registerTool("wait_task", {
  description: "Wait for a task to complete, fail, be rejected, or be cancelled.",
  inputSchema: {
    taskId: id,
    timeoutSeconds: z.number().int().min(1).max(120).default(60),
  },
}, async ({ taskId, timeoutSeconds }, extra) => {
  const deadline = Date.now() + timeoutSeconds * 1_000;
  let latest: unknown;
  while (Date.now() < deadline) {
    if (extra.signal.aborted) throw new Error("Wait cancelled");
    latest = await api.get(taskPath(owner(taskId), taskId));
    const status = statusOf(latest);
    if (["completed", "failed", "cancelled", "rejected"].includes(status)) return result(latest);
    await delay(Math.min(1_000, deadline - Date.now()), extra.signal);
  }
  return result({ timedOut: true, latest });
});

server.registerTool("send_message", {
  description: "Continue an existing remote Agent conversation.",
  inputSchema: { taskId: id, message: z.string().trim().min(1).max(100_000) },
}, async ({ taskId, message }) => result(await api.post(`${taskPath(owner(taskId), taskId)}/messages`, { message })));

server.registerTool("cancel_task", {
  description: "Cancel an active task created by this MCP process.",
  inputSchema: { taskId: id },
}, async ({ taskId }) => result(await api.post(`${taskPath(owner(taskId), taskId)}/cancel`)));

await server.connect(new StdioServerTransport());

function owner(taskId: string): string {
  const agentId = taskOwners.get(taskId);
  if (!agentId) throw new Error("当前 MCP 进程没有该任务引用；服务和 MCP 重启后不会恢复任务索引");
  return agentId;
}

function taskPath(agentId: string, taskId: string): string {
  return `/local/remote/${encodeURIComponent(agentId)}/tasks/${encodeURIComponent(taskId)}`;
}

function extractTaskId(value: unknown): string | null {
  if (!value || typeof value !== "object" || !("task" in value)) return null;
  const task = (value as { task?: unknown }).task;
  return task && typeof task === "object" && "id" in task ? String((task as { id: unknown }).id) : null;
}

function statusOf(value: unknown): string {
  if (!value || typeof value !== "object" || !("task" in value)) return "";
  const task = (value as { task?: unknown }).task;
  return task && typeof task === "object" && "status" in task ? String((task as { status: unknown }).status) : "";
}

function result(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
    ...(value && typeof value === "object" && !Array.isArray(value) ? { structuredContent: value as Record<string, unknown> } : {}),
  };
}

function delay(milliseconds: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolveDelay, reject) => {
    const onAbort = () => { clearTimeout(timer); reject(new Error("Wait cancelled")); };
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolveDelay();
    }, Math.max(0, milliseconds));
    signal.addEventListener("abort", onAbort, { once: true });
  });
}
