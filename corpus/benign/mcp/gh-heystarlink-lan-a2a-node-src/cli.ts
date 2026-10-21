#!/usr/bin/env node

import { hostname } from "node:os";
import { dirname, resolve } from "node:path";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { loadAdminToken } from "./admin-token.js";
import { loadConfig } from "./config.js";
import { NodeIdentity } from "./security.js";
import { LocalApi } from "./local-api.js";
import { LanA2ANode } from "./server.js";

const terminalStatuses = new Set(["completed", "failed", "cancelled", "rejected"]);

export async function main(argv = process.argv.slice(2)): Promise<void> {
  const args = [...argv];
  const configPath = resolve(option(args, "--config") ?? process.env.LAN_A2A_CONFIG ?? "config.json");
  const command = args.shift();
  if (!command || ["help", "--help", "-h"].includes(command)) return usage();
  if (command === "init") return initialize(configPath, args);

  const config = await loadConfig(configPath);
  if (command === "serve") {
    process.title = "lan-a2a-node";
    const node = await LanA2ANode.create(config);
    const started = await node.start();
    console.log(`LAN A2A 节点已启动：${config.nodeName}`);
    console.log(`Node ID：${node.identity.nodeId}`);
    console.log(`监听端口：${started.port}`);
    const shutdown = async () => {
      await node.stop();
      process.exitCode = 0;
    };
    process.once("SIGINT", () => void shutdown());
    process.once("SIGTERM", () => void shutdown());
    return;
  }

  const api = await LocalApi.connect(config);
  if (command === "status") return print(await api.get("/health"));
  if (command === "agents") return print(await api.get("/local/agents"));
  if (command === "pair-code") return print(await api.post("/local/pairing/open"));
  if (command === "pair") {
    const [target, code] = args;
    requireArg(target, "node-id 或 URL");
    requireArg(code, "配对码");
    return print(await api.post("/local/peers/pair", { target, code }));
  }
  if (command === "trust") {
    const [peerId, workspace, permission = "read-only"] = args.filter((value) => value !== "--auto");
    requireArg(peerId, "peer-id");
    requireArg(workspace, "workspace");
    assertPermission(permission);
    return print(await api.patch(`/local/peers/${encodeURIComponent(peerId)}/policy`, {
      autoAccept: args.includes("--auto"),
      workspace,
      permission,
    }));
  }
  if (command === "inbox") return print(await api.get("/local/tasks"));
  if (command === "accept") {
    const [taskId, workspace, permission = "read-only"] = args;
    requireArg(taskId, "task-id");
    requireArg(workspace, "workspace");
    assertPermission(permission);
    return print(await api.post(`/local/tasks/${encodeURIComponent(taskId)}/accept`, { workspace, permission }));
  }
  if (command === "reject") {
    const [taskId, reason] = args;
    requireArg(taskId, "task-id");
    return print(await api.post(`/local/tasks/${encodeURIComponent(taskId)}/reject`, { reason }));
  }
  if (command === "send") {
    const summary = option(args, "--summary");
    const expectedOutput = option(args, "--expected-output");
    const [peerId, objective] = args;
    requireArg(peerId, "peer-id");
    requireArg(objective, "objective");
    return print(await api.post("/local/send", { peerId, objective, summary, expectedOutput }));
  }
  if (command === "get") {
    const [peerId, taskId] = args;
    requireArg(peerId, "peer-id");
    requireArg(taskId, "task-id");
    return print(await api.get(remoteTaskPath(peerId, taskId)));
  }
  if (command === "wait") {
    const timeoutSeconds = Number(option(args, "--timeout") ?? 300);
    const [peerId, taskId] = args;
    requireArg(peerId, "peer-id");
    requireArg(taskId, "task-id");
    if (!Number.isInteger(timeoutSeconds) || timeoutSeconds < 1 || timeoutSeconds > 86_400) {
      throw new Error("timeout 必须是 1 到 86400 秒的整数");
    }
    const deadline = Date.now() + timeoutSeconds * 1_000;
    let latest: unknown;
    while (Date.now() < deadline) {
      latest = await api.get(remoteTaskPath(peerId, taskId));
      const status = taskStatus(latest);
      if (status && terminalStatuses.has(status)) return print(latest);
      await delay(Math.min(1_000, deadline - Date.now()));
    }
    return print({ timedOut: true, latest });
  }
  if (command === "message") {
    const [peerId, taskId, message] = args;
    requireArg(peerId, "peer-id");
    requireArg(taskId, "task-id");
    requireArg(message, "message");
    return print(await api.post(`${remoteTaskPath(peerId, taskId)}/messages`, { message }));
  }
  if (command === "cancel") {
    const [peerId, taskId] = args;
    requireArg(peerId, "peer-id");
    requireArg(taskId, "task-id");
    return print(await api.post(`${remoteTaskPath(peerId, taskId)}/cancel`));
  }
  if (command === "logs") {
    const limit = Number(args[0] ?? 50);
    return print(await api.get(`/local/logs?limit=${limit}`));
  }
  throw new Error(`未知命令：${command}`);
}

async function initialize(configPath: string, args: string[]): Promise<void> {
  const skipGitRepoCheck = args.includes("--skip-git-check");
  if (skipGitRepoCheck) args.splice(args.indexOf("--skip-git-check"), 1);
  const networkAccessEnabled = args.includes("--allow-network");
  if (networkAccessEnabled) args.splice(args.indexOf("--allow-network"), 1);
  const name = option(args, "--name") ?? hostname();
  const port = Number(option(args, "--port") ?? 4545);
  const workspacePath = resolve(option(args, "--workspace") ?? process.cwd());
  const workspaceName = option(args, "--workspace-name") ?? "default";
  const maxPermission = option(args, "--permission") ?? "read-only";
  const webSearchMode = option(args, "--web-search") ?? "disabled";
  assertPermission(maxPermission);
  assertWebSearchMode(webSearchMode);
  if (args.length > 0) throw new Error(`无法识别参数：${args.join(" ")}`);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("端口必须是 1 到 65535 的整数");
  await mkdir(dirname(configPath), { recursive: true });
  const config = {
    nodeName: name,
    host: "0.0.0.0",
    port,
    dataDir: "./data",
    logFile: "./logs/lan-a2a.jsonl",
    maxConcurrentTasks: 2,
    discovery: { enabled: true },
    workspaces: {
      [workspaceName]: {
        path: workspacePath,
        maxPermission,
        skipGitRepoCheck,
        networkAccessEnabled,
        webSearchMode,
      },
    },
  };
  await writeFile(configPath, `${JSON.stringify(config, null, 2)}\n`, { encoding: "utf8", flag: "wx" });
  const runtime = await loadConfig(configPath);
  await loadAdminToken(runtime);
  const identity = await NodeIdentity.load(runtime);
  print({ ok: true, configPath, nodeId: identity.nodeId, nodeName: name, workspace: workspaceName });
}

function remoteTaskPath(peerId: string, taskId: string): string {
  return `/local/remote/${encodeURIComponent(peerId)}/tasks/${encodeURIComponent(taskId)}`;
}

function option(args: string[], name: string): string | undefined {
  const index = args.indexOf(name);
  if (index < 0) return undefined;
  const value = args[index + 1];
  if (!value || value.startsWith("--")) throw new Error(`${name} 缺少参数`);
  args.splice(index, 2);
  return value;
}

function assertPermission(value: string): asserts value is "read-only" | "workspace-write" {
  if (!["read-only", "workspace-write"].includes(value)) throw new Error(`无效权限：${value}`);
}

function assertWebSearchMode(value: string): asserts value is "disabled" | "cached" | "live" {
  if (!["disabled", "cached", "live"].includes(value)) throw new Error(`无效 Web Search 模式：${value}`);
}

function requireArg(value: string | undefined, name: string): asserts value is string {
  if (!value) throw new Error(`缺少参数：${name}`);
}

function taskStatus(value: unknown): string | null {
  if (!value || typeof value !== "object" || !("task" in value)) return null;
  const task = (value as { task?: unknown }).task;
  return task && typeof task === "object" && "status" in task ? String((task as { status: unknown }).status) : null;
}

function print(value: unknown): void {
  console.log(JSON.stringify(value, null, 2));
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, Math.max(0, milliseconds)));
}

function usage(): void {
  console.log(`LAN A2A Node（macOS / Windows / Linux）

Commands:
  init [--name <name>] [--port 4545] [--workspace <path>] [--workspace-name default]
       [--permission read-only|workspace-write] [--skip-git-check] [--allow-network]
       [--web-search disabled|cached|live]
  serve
  status
  agents
  pair-code
  pair <node-id|url> <code>
  trust <peer-id> <workspace> [read-only|workspace-write] [--auto]
  inbox
  accept <task-id> <workspace> [read-only|workspace-write]
  reject <task-id> [reason]
  send <peer-id> <objective> [--summary <text>] [--expected-output <text>]
  get <peer-id> <task-id>
  wait <peer-id> <task-id> [--timeout 300]
  message <peer-id> <task-id> <message>
  cancel <peer-id> <task-id>
  logs [limit]

Global option:
  --config <path>`);
}

if (resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
