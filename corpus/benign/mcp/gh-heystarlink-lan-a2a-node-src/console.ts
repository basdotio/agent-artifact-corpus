#!/usr/bin/env node

import { createInterface, type Interface } from "node:readline";
import { cursorTo, clearLine } from "node:readline";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { loadConfig } from "./config.js";
import { LocalApi } from "./local-api.js";
import type { Permission, RuntimeConfig } from "./types.js";

const terminalStatuses = new Set(["completed", "failed", "cancelled", "rejected"]);
const colors = {
  reset: "\x1b[0m",
  bold: "\x1b[1m",
  dim: "\x1b[2m",
  cyan: "\x1b[36m",
  blue: "\x1b[94m",
  green: "\x1b[92m",
  yellow: "\x1b[93m",
  red: "\x1b[91m",
  magenta: "\x1b[95m",
  gray: "\x1b[90m",
};

export interface ConsoleApi {
  get(path: string): Promise<unknown>;
  post(path: string, body?: unknown): Promise<unknown>;
  patch(path: string, body: unknown): Promise<unknown>;
}

export type ConsoleAction =
  | { type: "render"; title: string; value: unknown }
  | { type: "message"; message: string }
  | { type: "watch"; enabled: boolean }
  | { type: "clear" }
  | { type: "exit" };

export async function runConsole(
  configPath = process.env.LAN_A2A_CONFIG ?? "config.json",
): Promise<void> {
  const config = await loadConfig(configPath);
  const api = await LocalApi.connect(config);
  const terminal = new TerminalConsole(config, api);
  await terminal.run();
}

export function tokenizeCommandLine(input: string): string[] {
  const tokens: string[] = [];
  let current = "";
  let quote: "'" | '"' | null = null;
  let escaping = false;
  let started = false;

  for (const character of input.trim()) {
    if (escaping) {
      current += character;
      escaping = false;
      started = true;
      continue;
    }
    if (character === "\\" && quote !== "'") {
      escaping = true;
      started = true;
      continue;
    }
    if (quote) {
      if (character === quote) quote = null;
      else current += character;
      started = true;
      continue;
    }
    if (character === "'" || character === '"') {
      quote = character;
      started = true;
      continue;
    }
    if (/\s/.test(character)) {
      if (started) {
        tokens.push(current);
        current = "";
        started = false;
      }
      continue;
    }
    current += character;
    started = true;
  }
  if (escaping) throw new Error("命令末尾不能是转义符");
  if (quote) throw new Error("命令中的引号没有闭合");
  if (started) tokens.push(current);
  return tokens;
}

export async function dispatchConsoleCommand(
  tokens: string[],
  api: ConsoleApi,
  config: RuntimeConfig,
): Promise<ConsoleAction> {
  const args = [...tokens];
  const command = (args.shift() ?? "").toLowerCase();
  if (!command) return { type: "message", message: "" };
  if (["help", "?"].includes(command)) return { type: "message", message: helpText() };
  if (["exit", "quit", "q"].includes(command)) return { type: "exit" };
  if (["clear", "cls"].includes(command)) return { type: "clear" };
  if (command === "watch") {
    const mode = (args[0] ?? "on").toLowerCase();
    if (!["on", "off"].includes(mode)) throw new Error("用法：watch on|off");
    return { type: "watch", enabled: mode === "on" };
  }
  if (command === "status") return render("NODE STATUS", await api.get("/health"));
  if (command === "config") {
    return render("LOCAL CONFIG", {
      nodeName: config.nodeName,
      endpoint: `http://127.0.0.1:${config.port}`,
      discovery: config.discoveryEnabled,
      maxConcurrentTasks: config.maxConcurrentTasks,
      logFile: config.logFile,
      workspaces: config.workspaces,
    });
  }
  if (["agents", "peers"].includes(command)) return render("LAN AGENTS", await api.get("/local/agents"));
  if (command === "node") return nodeCommand(args, api);
  if (["inbox", "tasks"].includes(command)) return render("TASK INBOX", await api.get("/local/tasks"));
  if (command === "accept") {
    const [taskId, workspace, permission = "read-only"] = args;
    requireArgument(taskId, "task-id");
    requireArgument(workspace, "workspace");
    assertPermission(permission);
    return render("TASK ACCEPTED", await api.post(`/local/tasks/${encodeURIComponent(taskId)}/accept`, {
      workspace,
      permission,
    }));
  }
  if (command === "reject") {
    const [taskId, ...reasonParts] = args;
    requireArgument(taskId, "task-id");
    return render("TASK REJECTED", await api.post(`/local/tasks/${encodeURIComponent(taskId)}/reject`, {
      reason: reasonParts.join(" ") || undefined,
    }));
  }
  if (command === "send") {
    const summary = takeOption(args, "--summary");
    const expectedOutput = takeOption(args, "--expected-output") ?? takeOption(args, "--expected");
    const [peerId, objective] = args;
    requireArgument(peerId, "peer-id");
    requireArgument(objective, "objective（包含空格时请使用引号）");
    if (args.length !== 2) throw new Error("objective 包含空格时必须用引号包裹");
    return render("TASK SENT", await api.post("/local/send", {
      peerId,
      objective,
      summary,
      expectedOutput,
    }));
  }
  if (["get", "wait", "message", "cancel"].includes(command)) {
    return remoteTaskCommand(command, args, api);
  }
  if (["logs", "log"].includes(command)) {
    const limit = parseInteger(args[0] ?? "30", "日志条数", 1, 500);
    return render("AUDIT LOG", await api.get(`/local/logs?limit=${limit}`));
  }
  if (["sh", "shell", "exec", "!"].includes(command) || command.startsWith("!")) {
    throw new Error("控制台不执行系统 Shell；请输入 help 查看受控 LAN A2A 命令");
  }
  throw new Error(`未知命令：${command}。输入 help 查看可用命令`);
}

async function nodeCommand(args: string[], api: ConsoleApi): Promise<ConsoleAction> {
  const subcommand = (args.shift() ?? "list").toLowerCase();
  if (["list", "ls"].includes(subcommand)) return render("LAN AGENTS", await api.get("/local/agents"));
  if (["code", "open"].includes(subcommand)) {
    return render("PAIRING CODE", await api.post("/local/pairing/open"));
  }
  if (["add", "pair"].includes(subcommand)) {
    const [target, code] = args;
    requireArgument(target, "node-id 或 http://IP:PORT");
    requireArgument(code, "六位配对码");
    if (!/^\d{6}$/.test(code)) throw new Error("配对码必须是六位数字");
    return render("NODE PAIRED", await api.post("/local/peers/pair", { target, code }));
  }
  if (subcommand === "trust") {
    const [peerId, workspace, permission = "read-only", mode = "manual"] = args;
    requireArgument(peerId, "peer-id");
    requireArgument(workspace, "workspace");
    assertPermission(permission);
    if (!["auto", "manual"].includes(mode)) throw new Error("接收模式只能是 auto 或 manual");
    return render("NODE POLICY", await api.patch(`/local/peers/${encodeURIComponent(peerId)}/policy`, {
      autoAccept: mode === "auto",
      workspace,
      permission,
    }));
  }
  throw new Error("用法：node list | node code | node add <URL|node-id> <code> | node trust <peer> <workspace> <permission> <auto|manual>");
}

async function remoteTaskCommand(
  command: string,
  args: string[],
  api: ConsoleApi,
): Promise<ConsoleAction> {
  const [peerId, taskId] = args;
  requireArgument(peerId, "peer-id");
  requireArgument(taskId, "task-id");
  const path = `/local/remote/${encodeURIComponent(peerId)}/tasks/${encodeURIComponent(taskId)}`;
  if (command === "get") return render("REMOTE TASK", await api.get(path));
  if (command === "cancel") return render("TASK CANCELLED", await api.post(`${path}/cancel`));
  if (command === "message") {
    const message = args.slice(2).join(" ").trim();
    requireArgument(message, "message");
    return render("MESSAGE SENT", await api.post(`${path}/messages`, { message }));
  }

  const timeout = parseInteger(args[2] ?? "300", "等待秒数", 1, 86_400);
  const deadline = Date.now() + timeout * 1_000;
  let latest: unknown;
  while (Date.now() < deadline) {
    latest = await api.get(path);
    const status = taskStatus(latest);
    if (status && terminalStatuses.has(status)) return render("REMOTE TASK", latest);
    await delay(Math.min(1_000, deadline - Date.now()));
  }
  return render("WAIT TIMED OUT", { timedOut: true, latest });
}

class TerminalConsole {
  private readonly ansi = Boolean(process.stdout.isTTY && !process.env.NO_COLOR);
  private readonly promptText = "lan-a2a > ";
  private readonly seenLogs = new Set<string>();
  private readonly readline: Interface;
  private watchEnabled = true;
  private promptActive = false;
  private polling = false;
  private running = true;
  private timer: NodeJS.Timeout | null = null;

  constructor(
    private readonly config: RuntimeConfig,
    private readonly api: ConsoleApi,
  ) {
    this.readline = createInterface({
      input: process.stdin,
      output: process.stdout,
      terminal: Boolean(process.stdin.isTTY && process.stdout.isTTY),
      historySize: 200,
      removeHistoryDuplicates: true,
    });
  }

  async run(): Promise<void> {
    this.renderBanner();
    await this.renderOverview();
    await this.seedLogs();
    this.writeLine(this.paint("dim", "Type help for commands. Live audit log: ON"));
    this.timer = setInterval(() => void this.pollLogs(), 1_500);
    this.timer.unref();
    this.readline.once("SIGINT", () => {
      this.running = false;
      this.readline.close();
    });

    try {
      while (this.running) {
        this.promptActive = true;
        let input: string;
        try {
          input = await new Promise<string>((resolveInput) => this.readline.question(
            this.paint("cyan", this.promptText),
            resolveInput,
          ));
        } catch {
          break;
        } finally {
          this.promptActive = false;
        }
        const trimmed = input.trim();
        if (!trimmed) continue;
        try {
          const action = await dispatchConsoleCommand(tokenizeCommandLine(trimmed), this.api, this.config);
          if (action.type === "exit") break;
          if (action.type === "clear") {
            this.clear();
            this.renderBanner();
            await this.renderOverview();
          } else if (action.type === "watch") {
            this.watchEnabled = action.enabled;
            this.writeLine(this.paint(action.enabled ? "green" : "yellow", `Live audit log: ${action.enabled ? "ON" : "OFF"}`));
          } else if (action.type === "message") {
            if (action.message) this.writeLine(action.message);
          } else {
            this.renderValue(action.title, action.value);
          }
        } catch (error) {
          this.writeLine(`${this.paint("red", "ERROR")} ${error instanceof Error ? error.message : String(error)}`);
        }
      }
    } finally {
      if (this.timer) clearInterval(this.timer);
      this.readline.close();
      this.writeLine(this.paint("dim", "Console closed. LAN A2A node keeps running."));
    }
  }

  private renderBanner(): void {
    const width = Math.max(64, Math.min(process.stdout.columns ?? 96, 110));
    const rule = "=".repeat(width);
    this.writeLine(this.paint("blue", rule));
    this.writeLine(`${this.paint("bold", " LAN A2A CONTROL DECK")}  ${this.paint("dim", "headless agent network")}`);
    this.writeLine(this.paint("blue", rule));
  }

  private async renderOverview(): Promise<void> {
    try {
      const [health, agents, tasks] = await Promise.all([
        this.api.get("/health"),
        this.api.get("/local/agents"),
        this.api.get("/local/tasks"),
      ]);
      const agentList = arrayAt(agents, "agents");
      const taskList = arrayAt(tasks, "tasks");
      const reachable = agentList.filter((agent) => record(agent).reachable === true).length;
      const pending = taskList.filter((task) => record(task).status === "pending_acceptance").length;
      const nodeId = String(record(health).nodeId ?? "unknown");
      this.writeLine(
        `${this.paint("green", "ONLINE")}  ${this.paint("bold", this.config.nodeName)}  ` +
        `${this.paint("dim", nodeId)}  tcp:${this.config.port}`,
      );
      this.writeLine(
        `Agents ${this.paint(reachable > 0 ? "green" : "yellow", `${reachable}/${agentList.length}`)}  ` +
        `Pending ${this.paint(pending > 0 ? "yellow" : "green", String(pending))}  ` +
        `Workspaces ${Object.keys(this.config.workspaces).length}  ` +
        `Discovery ${this.config.discoveryEnabled ? this.paint("green", "mDNS + manual") : this.paint("yellow", "manual only")}`,
      );
      this.writeLine(this.paint("dim", `VPN/manual pairing: node add http://<ip>:${this.config.port} <six-digit-code>`));
      this.writeLine("");
    } catch (error) {
      this.writeLine(`${this.paint("red", "OFFLINE")} ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private async seedLogs(): Promise<void> {
    const value = await this.api.get("/local/logs?limit=8").catch(() => ({ entries: [] }));
    for (const line of stringsAt(value, "entries")) {
      this.seenLogs.add(line);
      this.writeLine(formatAuditLine(line, this.paint.bind(this)));
    }
    if (this.seenLogs.size > 0) this.writeLine("");
  }

  private async pollLogs(): Promise<void> {
    if (!this.watchEnabled || this.polling || !this.running) return;
    this.polling = true;
    try {
      const value = await this.api.get("/local/logs?limit=100");
      for (const line of stringsAt(value, "entries")) {
        if (this.seenLogs.has(line)) continue;
        this.seenLogs.add(line);
        this.printAbovePrompt(formatAuditLine(line, this.paint.bind(this)));
      }
      if (this.seenLogs.size > 1_000) {
        const keep = [...this.seenLogs].slice(-500);
        this.seenLogs.clear();
        for (const line of keep) this.seenLogs.add(line);
      }
    } catch {
      // The explicit status command reports connectivity errors without interrupting typing.
    } finally {
      this.polling = false;
    }
  }

  private renderValue(title: string, value: unknown): void {
    this.writeLine(this.paint("blue", `-- ${title} ${"-".repeat(Math.max(1, 52 - title.length))}`));
    if (arrayAt(value, "agents").length > 0 || (record(value).agents && Array.isArray(record(value).agents))) {
      this.renderAgents(arrayAt(value, "agents"));
    } else if (arrayAt(value, "tasks").length > 0 || (record(value).tasks && Array.isArray(record(value).tasks))) {
      this.renderTasks(arrayAt(value, "tasks"));
    } else if (stringsAt(value, "entries").length > 0 || (record(value).entries && Array.isArray(record(value).entries))) {
      for (const line of stringsAt(value, "entries")) this.writeLine(formatAuditLine(line, this.paint.bind(this)));
    } else if (record(value).task) {
      this.renderTask(record(record(value).task));
    } else if (record(value).code) {
      this.writeLine(`${this.paint("yellow", "PAIR CODE")} ${this.paint("bold", String(record(value).code))}`);
      this.writeLine(this.paint("dim", `Expires ${String(record(value).expiresAt ?? "")}`));
    } else {
      this.writeLine(pretty(value, this.paint.bind(this)));
    }
    this.writeLine("");
  }

  private renderAgents(values: unknown[]): void {
    if (values.length === 0) return this.writeLine(this.paint("dim", "No paired or nearby agents."));
    this.writeLine(`${pad("STATE", 9)} ${pad("NAME", 22)} ${pad("NODE ID", 34)} ENDPOINT`);
    for (const value of values) {
      const agent = record(value);
      const reachable = agent.reachable === true;
      const state = reachable ? this.paint("green", "ONLINE") : this.paint("red", "OFFLINE");
      this.writeLine(
        `${padAnsi(state, 9)} ${pad(String(agent.name ?? "unknown"), 22)} ` +
        `${pad(String(agent.id ?? ""), 34)} ${String(agent.url ?? "")}`,
      );
      if (agent.paired === true && record(agent.policy).workspace) {
        const policy = record(agent.policy);
        this.writeLine(this.paint("dim", `          policy ${policy.autoAccept ? "auto" : "manual"} / ${policy.workspace} / ${policy.permission}`));
      }
    }
  }

  private renderTasks(values: unknown[]): void {
    if (values.length === 0) return this.writeLine(this.paint("dim", "No in-memory tasks."));
    this.writeLine(`${pad("STATUS", 20)} ${pad("TASK ID", 38)} REQUESTER`);
    for (const value of values) {
      const task = record(value);
      this.writeLine(
        `${padAnsi(statusColor(String(task.status ?? "unknown"), this.paint.bind(this)), 20)} ` +
        `${pad(String(task.id ?? ""), 38)} ${String(task.requesterName ?? task.requesterNodeId ?? "")}`,
      );
    }
  }

  private renderTask(task: Record<string, unknown>): void {
    this.writeLine(`Status     ${statusColor(String(task.status ?? "unknown"), this.paint.bind(this))}`);
    this.writeLine(`Task ID    ${String(task.id ?? "")}`);
    this.writeLine(`Requester  ${String(task.requesterName ?? task.requesterNodeId ?? "")}`);
    if (task.workspace) this.writeLine(`Workspace  ${String(task.workspace)} / ${String(task.permission)}`);
    if (task.result) this.writeLine(`\n${this.paint("green", "RESULT")}\n${String(task.result)}`);
    if (task.error) this.writeLine(`\n${this.paint("red", "ERROR")}\n${String(task.error)}`);
  }

  private printAbovePrompt(line: string): void {
    if (this.promptActive && process.stdout.isTTY) {
      clearLine(process.stdout, 0);
      cursorTo(process.stdout, 0);
      process.stdout.write(`${line}\n`);
      this.readline.prompt(true);
      return;
    }
    this.writeLine(line);
  }

  private clear(): void {
    process.stdout.write(process.stdout.isTTY ? "\x1b[2J\x1b[H" : "\n");
  }

  private writeLine(value: string): void {
    process.stdout.write(`${value}\n`);
  }

  private paint(name: keyof typeof colors, value: string): string {
    return this.ansi ? `${colors[name]}${value}${colors.reset}` : value;
  }
}

function helpText(): string {
  return `
${colors.bold}Node${colors.reset}
  agents | node list
  node code                              Generate a 5-minute pairing code
  node add <URL|node-id> <code>          Pair by VPN IP or mDNS discovery
  node trust <peer> <workspace> <permission> <auto|manual>

${colors.bold}Tasks${colors.reset}
  inbox | tasks
  accept <task-id> <workspace> [read-only|workspace-write]
  reject <task-id> [reason]
  send <peer-id> "<objective>" [--summary "..."] [--expected "..."]
  get <peer-id> <task-id>
  wait <peer-id> <task-id> [seconds]
  message <peer-id> <task-id> "<message>"
  cancel <peer-id> <task-id>

${colors.bold}Console${colors.reset}
  status | config | logs [count]
  watch on|off | clear | exit

System shell execution is intentionally disabled.`;
}

function formatAuditLine(
  line: string,
  paint: (name: keyof typeof colors, value: string) => string,
): string {
  try {
    const value = JSON.parse(line) as Record<string, unknown>;
    const timestamp = String(value.timestamp ?? "").slice(11, 19) || "--:--:--";
    const event = String(value.event ?? "event");
    const task = value.taskId ? ` task=${short(String(value.taskId), 16)}` : "";
    const peer = value.peerName ? ` peer=${String(value.peerName)}` : "";
    const status = value.status ? ` status=${String(value.status)}` : "";
    return `${paint("gray", timestamp)} ${eventColor(event, paint)}${paint("dim", `${task}${peer}${status}`)}`;
  } catch {
    return paint("dim", line);
  }
}

function eventColor(event: string, paint: (name: keyof typeof colors, value: string) => string): string {
  if (event.includes("failed") || event.includes("rejected")) return paint("red", event);
  if (event.includes("completed") || event.includes("paired") || event.includes("started")) return paint("green", event);
  if (event.includes("cancelled") || event.includes("pairing")) return paint("yellow", event);
  return paint("cyan", event);
}

function statusColor(status: string, paint: (name: keyof typeof colors, value: string) => string): string {
  if (["completed", "online"].includes(status)) return paint("green", status.toUpperCase());
  if (["failed", "rejected", "offline"].includes(status)) return paint("red", status.toUpperCase());
  if (["pending_acceptance", "queued", "cancelled"].includes(status)) return paint("yellow", status.toUpperCase());
  return paint("cyan", status.toUpperCase());
}

function pretty(value: unknown, paint: (name: keyof typeof colors, value: string) => string): string {
  return JSON.stringify(value, null, 2)
    .replace(/"([^"\\]+)":/g, (_, key: string) => `${paint("cyan", key)}:`)
    .replace(/: "([^"\\]*)"/g, (_, text: string) => `: ${paint("green", text)}`);
}

function render(title: string, value: unknown): ConsoleAction {
  return { type: "render", title, value };
}

function takeOption(args: string[], name: string): string | undefined {
  const index = args.indexOf(name);
  if (index < 0) return undefined;
  const value = args[index + 1];
  if (value === undefined || value.startsWith("--")) throw new Error(`${name} 缺少参数`);
  args.splice(index, 2);
  return value;
}

function requireArgument(value: string | undefined, name: string): asserts value is string {
  if (!value) throw new Error(`缺少参数：${name}`);
}

function assertPermission(value: string): asserts value is Permission {
  if (!["read-only", "workspace-write"].includes(value)) throw new Error(`无效权限：${value}`);
}

function parseInteger(value: string, name: string, minimum: number, maximum: number): number {
  const number = Number(value);
  if (!Number.isInteger(number) || number < minimum || number > maximum) {
    throw new Error(`${name}必须是 ${minimum} 到 ${maximum} 的整数`);
  }
  return number;
}

function taskStatus(value: unknown): string | null {
  const task = record(record(value).task);
  return typeof task.status === "string" ? task.status : null;
}

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function arrayAt(value: unknown, key: string): unknown[] {
  const item = record(value)[key];
  return Array.isArray(item) ? item : [];
}

function stringsAt(value: unknown, key: string): string[] {
  return arrayAt(value, key).filter((item): item is string => typeof item === "string");
}

function pad(value: string, width: number): string {
  return short(value, width).padEnd(width, " ");
}

function padAnsi(value: string, width: number): string {
  return `${value}${" ".repeat(Math.max(0, width - stripAnsi(value).length))}`;
}

function stripAnsi(value: string): string {
  return value.replace(/\x1b\[[0-9;]*m/g, "");
}

function short(value: string, length: number): string {
  return value.length <= length ? value : `${value.slice(0, Math.max(1, length - 3))}...`;
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, Math.max(0, milliseconds)));
}

if (resolve(process.argv[1] ?? "") === fileURLToPath(import.meta.url)) {
  process.title = "lan-a2a-console";
  const args = [...process.argv.slice(2)];
  const configIndex = args.indexOf("--config");
  let configPath = process.env.LAN_A2A_CONFIG ?? "config.json";
  if (configIndex >= 0) {
    const value = args[configIndex + 1];
    if (!value) throw new Error("--config 缺少路径");
    configPath = value;
  }
  runConsole(configPath).catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
