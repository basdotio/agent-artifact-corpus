import { spawn, type ChildProcessWithoutNullStreams, type SpawnOptions } from "node:child_process";

import type { InitializeParams } from "../protocol/codex-0.147.0-ts/InitializeParams.js";

export type JsonRpcId = string | number;
export type JsonObject = Record<string, unknown>;

export type AppServerMessage = JsonObject & {
  id?: JsonRpcId;
  method?: string;
  params?: unknown;
  result?: unknown;
  error?: unknown;
};

export class AppServerError extends Error {
  readonly code: number | string | null;
  readonly data: unknown;

  constructor(message: string, code: number | string | null = null, data: unknown = null) {
    super(message);
    this.name = "AppServerError";
    this.code = code;
    this.data = data;
  }
}

export interface AppServerClient {
  addMessageListener(listener: MessageListener): () => void;
  addExitListener(listener: ExitListener): () => void;
  start(): Promise<void>;
  request<T>(method: string, params?: unknown): Promise<T>;
  respond(id: JsonRpcId, result: unknown): void;
  respondError(id: JsonRpcId, code: number, message: string): void;
}

type PendingRequest = {
  method: string;
  resolve: (value: unknown) => void;
  reject: (reason: unknown) => void;
  timer: NodeJS.Timeout;
};

type ChildLifecycle = {
  child: ChildProcessWithoutNullStreams;
  exit: Promise<void>;
  resolveExit: () => void;
  intentionalStop: boolean;
  exitNotified: boolean;
  originalFailure: Error | null;
};

type MessageListener = (message: AppServerMessage) => void;
type ExitListener = (error: Error) => void;
type SpawnFunction = typeof spawn;

const SUPPORTED_SERVER_REQUESTS = new Set([
  "item/commandExecution/requestApproval",
  "item/fileChange/requestApproval",
  "item/permissions/requestApproval",
  "applyPatchApproval",
  "execCommandApproval",
]);

function idKey(id: JsonRpcId): string {
  return `${typeof id}:${String(id)}`;
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isRpcId(value: unknown): value is JsonRpcId {
  return (typeof value === "string" && value.length > 0) || (typeof value === "number" && Number.isFinite(value));
}

function errorFromRpc(value: unknown, fallback = "Error de app-server."): AppServerError {
  if (!isObject(value)) return new AppServerError(fallback);
  const rawCode = value.code;
  const code = typeof rawCode === "number" || typeof rawCode === "string" ? rawCode : null;
  const message = typeof value.message === "string" ? value.message : fallback;
  return new AppServerError(message, code, value.data ?? null);
}

function parseDuration(value: number | undefined, fallback: number): number {
  return value === undefined ? fallback : Number.isInteger(value) && value > 0 ? value : fallback;
}

export type CodexAppServerOptions = {
  command?: string;
  commandArgs?: string[];
  rpcTimeoutMs?: number;
  shutdownTimeoutMs?: number;
  killTimeoutMs?: number;
  spawnProcess?: SpawnFunction;
  spawnOptions?: SpawnOptions;
};

export class CodexAppServer implements AppServerClient {
  private readonly command: string;
  private readonly commandArgs: string[];
  private readonly rpcTimeoutMs: number;
  private readonly shutdownTimeoutMs: number;
  private readonly killTimeoutMs: number;
  private readonly spawnProcess: SpawnFunction;
  private readonly spawnOptions: SpawnOptions;
  private current: ChildLifecycle | null = null;
  private nextId = 1;
  private lineBuffer = "";
  private initialized = false;
  private lifecycleOperation: Promise<void> = Promise.resolve();
  private readonly pending = new Map<string, PendingRequest>();
  private readonly messageListeners = new Set<MessageListener>();
  private readonly exitListeners = new Set<ExitListener>();
  private stderrTail = "";
  private lastError: Error | null = null;

  constructor(options: string | CodexAppServerOptions = {}) {
    const normalized: CodexAppServerOptions = typeof options === "string" ? { command: options } : options;
    this.command = normalized.command ?? process.env.CODEX_BIN ?? "codex";
    this.commandArgs = normalized.commandArgs ?? ["app-server", "--stdio"];
    this.rpcTimeoutMs = parseDuration(normalized.rpcTimeoutMs, Number(process.env.CODEX_RPC_TIMEOUT_MS) || 30_000);
    this.shutdownTimeoutMs = parseDuration(normalized.shutdownTimeoutMs, Number(process.env.CODEX_SHUTDOWN_TIMEOUT_MS) || 2_000);
    this.killTimeoutMs = parseDuration(normalized.killTimeoutMs, 1_000);
    this.spawnProcess = normalized.spawnProcess ?? spawn;
    this.spawnOptions = normalized.spawnOptions ?? {};
  }

  addMessageListener(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  addExitListener(listener: ExitListener): () => void {
    this.exitListeners.add(listener);
    return () => this.exitListeners.delete(listener);
  }

  isAlive(): boolean {
    const child = this.current?.child;
    return child !== undefined && child.exitCode === null && !child.killed;
  }

  isReady(): boolean {
    return this.isAlive() && this.initialized;
  }

  getLastError(): string | null {
    if (!this.lastError) return this.stderrTail.length > 0 ? this.stderrTail : null;
    return this.stderrTail.length > 0 ? `${this.lastError.message}\n${this.stderrTail}` : this.lastError.message;
  }

  async start(): Promise<void> {
    return this.serializeLifecycle(async () => {
      if (this.isReady()) return;
      await this.startInternal();
    });
  }

  async stop(): Promise<void> {
    return this.serializeLifecycle(async () => {
      const lifecycle = this.current;
      this.initialized = false;
      if (!lifecycle) return;
      lifecycle.intentionalStop = true;
      this.failAll(new AppServerError("codex app-server detenido por el servidor MCP."), false);
      await this.stopLifecycle(lifecycle);
    });
  }

  async request<T>(method: string, params?: unknown): Promise<T> {
    if (!this.isAlive()) throw new AppServerError("codex app-server no está vivo.");
    const id = this.nextId++;
    const key = idKey(id);
    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        if (!this.pending.delete(key)) return;
        reject(new AppServerError(`Timeout de RPC para ${method} después de ${this.rpcTimeoutMs} ms.`, -32002));
      }, this.rpcTimeoutMs);
      timer.unref?.();
      this.pending.set(key, { method, resolve: resolve as (value: unknown) => void, reject, timer });
      try {
        this.writeMessage(params === undefined ? { id, method } : { id, method, params });
      } catch (error) {
        clearTimeout(timer);
        this.pending.delete(key);
        reject(error);
      }
    });
  }

  private sendNotification(method: string, params?: unknown): void {
    this.writeMessage(params === undefined ? { method } : { method, params });
  }

  respond(id: JsonRpcId, result: unknown): void {
    this.writeMessage({ id, result });
  }

  respondError(id: JsonRpcId, code: number, message: string): void {
    this.writeMessage({ id, error: { code, message } });
  }

  private serializeLifecycle<T>(operation: () => Promise<T>): Promise<T> {
    const previous = this.lifecycleOperation;
    let release!: () => void;
    this.lifecycleOperation = new Promise<void>((resolve) => { release = resolve; });
    return previous.then(operation).finally(release);
  }

  private async startInternal(): Promise<void> {
    this.initialized = false;
    this.lastError = null;
    this.lineBuffer = "";
    this.stderrTail = "";

    const child = this.spawnProcess(this.command, this.commandArgs, {
      env: process.env,
      stdio: ["pipe", "pipe", "pipe"],
      ...this.spawnOptions,
    }) as ChildProcessWithoutNullStreams;
    let resolveExit!: () => void;
    const lifecycle: ChildLifecycle = {
      child,
      exit: new Promise<void>((resolve) => { resolveExit = resolve; }),
      resolveExit: () => resolveExit(),
      intentionalStop: false,
      exitNotified: false,
      originalFailure: null,
    };
    this.current = lifecycle;

    child.stdout.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => this.consumeStdout(chunk, lifecycle));
    child.stderr.setEncoding("utf8");
    child.stderr.on("data", (chunk: string) => {
      if (this.current === lifecycle) this.stderrTail = `${this.stderrTail}${chunk}`.slice(-4000);
    });
    child.once("error", (error) => {
      if (this.current !== lifecycle) return;
      this.failAll(new Error(`No se pudo iniciar codex app-server: ${error.message}`), true, lifecycle);
    });
    child.once("close", (code, signal) => this.handleClose(lifecycle, code, signal));

    try {
      const initializeParams: InitializeParams = {
        clientInfo: { name: "codex-agent-mcp", title: "Codex Agent", version: "0.3.1" },
        capabilities: { experimentalApi: true, requestAttestation: false },
      };
      await this.request("initialize", initializeParams);
      this.sendNotification("initialized");
      this.initialized = true;
    } catch (error) {
      const failure = error instanceof Error ? error : new Error(String(error));
      this.failAll(failure, false, lifecycle);
      lifecycle.intentionalStop = true;
      await this.stopLifecycle(lifecycle);
      throw failure;
    }
  }

  private async stopLifecycle(lifecycle: ChildLifecycle): Promise<void> {
    const child = lifecycle.child;
    if (child.exitCode !== null) {
      await lifecycle.exit;
      return;
    }
    try {
      child.stdin.end();
    } catch {
      // The process may already have closed its stdin.
    }
    if (await this.waitForExit(lifecycle, this.shutdownTimeoutMs)) return;
    try { child.kill("SIGTERM"); } catch { /* Best effort. */ }
    if (await this.waitForExit(lifecycle, this.killTimeoutMs)) return;
    try { child.kill("SIGKILL"); } catch { /* Best effort. */ }
    await this.waitForExit(lifecycle, this.killTimeoutMs);
  }

  private async waitForExit(lifecycle: ChildLifecycle, timeoutMs: number): Promise<boolean> {
    let timer: NodeJS.Timeout | undefined;
    const timeout = new Promise<false>((resolve) => {
      timer = setTimeout(() => resolve(false), timeoutMs);
      timer.unref?.();
    });
    const result = await Promise.race([lifecycle.exit.then(() => true as const), timeout]);
    if (timer) clearTimeout(timer);
    return result;
  }

  private handleClose(lifecycle: ChildLifecycle, code: number | null, signal: NodeJS.Signals | null): void {
    lifecycle.resolveExit();
    if (this.current !== lifecycle) return;
    if (!lifecycle.intentionalStop && !lifecycle.exitNotified) {
      const suffix = signal ? `señal ${signal}` : `código ${code ?? "desconocido"}`;
      const failure = lifecycle.originalFailure ?? new Error(`codex app-server terminó inesperadamente (${suffix}).`);
      this.failAll(failure, false, lifecycle);
      this.notifyExit(lifecycle, failure);
    }
    this.current = null;
    this.initialized = false;
  }

  private writeMessage(message: JsonObject): void {
    const child = this.current?.child;
    if (!child || child.stdin.destroyed || !child.stdin.writable) {
      throw new AppServerError("codex app-server no acepta nuevos mensajes.");
    }
    child.stdin.write(`${JSON.stringify(message)}\n`);
  }

  private consumeStdout(chunk: string, lifecycle: ChildLifecycle): void {
    if (this.current !== lifecycle) return;
    this.lineBuffer += chunk;
    let newlineIndex = this.lineBuffer.indexOf("\n");
    while (newlineIndex >= 0) {
      const line = this.lineBuffer.slice(0, newlineIndex);
      this.lineBuffer = this.lineBuffer.slice(newlineIndex + 1);
      if (line.trim().length > 0) this.consumeLine(line);
      newlineIndex = this.lineBuffer.indexOf("\n");
    }
  }

  private consumeLine(line: string): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(line);
    } catch (error) {
      this.protocolFailure(new AppServerError(`JSONL inválido de codex app-server: ${error instanceof Error ? error.message : String(error)}`));
      return;
    }
    if (!isObject(parsed)) {
      this.protocolFailure(new AppServerError("JSONL inválido de codex app-server: se esperaba un objeto."));
      return;
    }
    if ("jsonrpc" in parsed && parsed.jsonrpc !== "2.0") {
      this.protocolFailure(new AppServerError("JSON-RPC inválido de codex app-server: jsonrpc debe ser 2.0."));
      return;
    }

    const message = parsed as AppServerMessage;
    const hasMethod = typeof message.method === "string";
    const hasId = isRpcId(message.id);
    if ("id" in message && !hasId) {
      this.protocolFailure(new AppServerError("JSON-RPC inválido de codex app-server: id no válido."));
      return;
    }
    if (hasMethod && hasId) {
      if (!SUPPORTED_SERVER_REQUESTS.has(message.method as string)) {
        try { this.respondError(message.id as JsonRpcId, -32601, `Unsupported server request: ${message.method}`); } catch { /* Closing. */ }
        return;
      }
      this.emitMessage(message);
      return;
    }
    if (hasId) {
      if (!("result" in message) && !("error" in message)) {
        this.protocolFailure(new AppServerError("JSON-RPC inválido de codex app-server: response sin result/error."));
        return;
      }
      const key = idKey(message.id as JsonRpcId);
      const pending = this.pending.get(key);
      if (!pending) return;
      this.pending.delete(key);
      clearTimeout(pending.timer);
      if ("error" in message) pending.reject(errorFromRpc(message.error, `RPC ${pending.method} falló.`));
      else pending.resolve(message.result);
      return;
    }
    if (hasMethod) {
      this.emitMessage(message);
      return;
    }
    this.protocolFailure(new AppServerError("JSON-RPC inválido de codex app-server: mensaje sin method ni id."));
  }

  private emitMessage(message: AppServerMessage): void {
    for (const listener of this.messageListeners) {
      try { listener(message); } catch (error) { this.lastError = error instanceof Error ? error : new Error(String(error)); }
    }
  }

  private protocolFailure(error: Error): void {
    const lifecycle = this.current;
    this.failAll(error, true, lifecycle);
    const child = lifecycle?.child;
    if (child && child.exitCode === null) {
      try { child.kill("SIGTERM"); } catch { /* close handler performs cleanup */ }
    }
  }

  private failAll(error: Error, notify: boolean, lifecycle = this.current): void {
    if (lifecycle && this.current !== lifecycle) return;
    this.initialized = false;
    this.lastError = this.lastError ?? error;
    if (lifecycle && lifecycle.originalFailure === null && notify) lifecycle.originalFailure = error;
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
    if (notify && lifecycle) this.notifyExit(lifecycle, error);
  }

  private notifyExit(lifecycle: ChildLifecycle, error: Error): void {
    if (lifecycle.exitNotified) return;
    lifecycle.exitNotified = true;
    lifecycle.originalFailure ??= error;
    this.lastError = this.lastError ?? error;
    for (const listener of this.exitListeners) {
      try { listener(error); } catch (listenerError) { this.lastError = listenerError instanceof Error ? listenerError : new Error(String(listenerError)); }
    }
  }
}
