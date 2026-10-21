import { randomInt, randomUUID } from "node:crypto";
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import { z } from "zod";
import { loadAdminToken, matchesToken } from "./admin-token.js";
import { AuditLog } from "./audit-log.js";
import { LanDiscovery } from "./discovery.js";
import { CodexExecutor } from "./executor.js";
import { PeerClient, peerUrl } from "./peer-client.js";
import { PeerStore } from "./peer-store.js";
import { NodeIdentity } from "./security.js";
import { TaskManager } from "./task-manager.js";
import type { AgentExecutor, Permission, RuntimeConfig } from "./types.js";

const idSchema = z.string().min(1).max(100).regex(/^[A-Za-z0-9._:-]+$/);
const taskInputSchema = z.object({
  taskId: idSchema.optional(),
  objective: z.string().trim().min(1).max(100_000),
  summary: z.string().trim().max(100_000).nullable().optional(),
  expectedOutput: z.string().trim().max(100_000).nullable().optional(),
});
const pairSchema = z.object({
  code: z.string().regex(/^\d{6}$/),
  port: z.number().int().min(1).max(65535),
  attestation: z.unknown(),
});
const policySchema = z.object({
  autoAccept: z.boolean(),
  workspace: z.string().min(1).max(100).nullable(),
  permission: z.enum(["read-only", "workspace-write"]),
});

export interface StartedNode {
  port: number;
  localUrl: string;
}

export class LanA2ANode {
  private server: Server | null = null;
  private startedPort = 0;
  private pairingCode: { code: string; expiresAt: number; failedAttempts: number } | null = null;

  private constructor(
    readonly config: RuntimeConfig,
    private readonly adminToken: string,
    readonly identity: NodeIdentity,
    readonly peers: PeerStore,
    readonly tasks: TaskManager,
    readonly discovery: LanDiscovery,
    readonly client: PeerClient,
    readonly audit: AuditLog,
  ) {}

  static async create(config: RuntimeConfig, executor: AgentExecutor = new CodexExecutor()): Promise<LanA2ANode> {
    const adminToken = await loadAdminToken(config);
    const identity = await NodeIdentity.load(config);
    const peers = await PeerStore.load(config);
    const audit = new AuditLog(config.logFile);
    return new LanA2ANode(
      config,
      adminToken,
      identity,
      peers,
      new TaskManager(config, executor, audit),
      new LanDiscovery(config, identity),
      new PeerClient(identity, config.nodeName),
      audit,
    );
  }

  async start(): Promise<StartedNode> {
    if (this.server) throw new Error("节点已经启动");
    this.server = createServer((request, response) => {
      void this.handle(request, response).catch((error) => this.sendError(response, error));
    });
    await new Promise<void>((resolveStart, reject) => {
      this.server!.once("error", reject);
      this.server!.listen(this.config.port, this.config.host, () => resolveStart());
    });
    const address = this.server.address();
    if (!address || typeof address === "string") throw new Error("无法获取节点监听端口");
    this.startedPort = address.port;
    this.discovery.start(this.startedPort);
    await this.audit.record("node.started", {
      nodeId: this.identity.nodeId,
      nodeName: this.config.nodeName,
      port: this.startedPort,
    });
    return { port: this.startedPort, localUrl: `http://127.0.0.1:${this.startedPort}` };
  }

  async stop(): Promise<void> {
    this.tasks.stop();
    this.discovery.stop();
    const server = this.server;
    this.server = null;
    if (server) await new Promise<void>((resolveStop, reject) => server.close((error) => error ? reject(error) : resolveStop()));
    await this.audit.record("node.stopped", { nodeId: this.identity.nodeId });
  }

  private async handle(request: IncomingMessage, response: ServerResponse): Promise<void> {
    const method = request.method?.toUpperCase() ?? "GET";
    const url = new URL(request.url ?? "/", `http://${request.headers.host ?? "127.0.0.1"}`);
    const path = `${url.pathname}${url.search}`;
    const body = await readBody(request);

    if (method === "GET" && url.pathname === "/health") {
      return sendJson(response, 200, {
        ok: true,
        nodeId: this.identity.nodeId,
        nodeName: this.config.nodeName,
        protocolVersion: 1,
        persistence: "memory-tasks-jsonl-audit",
      });
    }
    if (method === "GET" && url.pathname === "/a2a/info") {
      const nonce = z.string().regex(/^[a-f0-9]{32,128}$/i).parse(url.searchParams.get("nonce"));
      return sendJson(response, 200, this.identity.attest(this.config.nodeName, nonce));
    }
    if (method === "POST" && url.pathname === "/a2a/pair") {
      const input = pairSchema.parse(body);
      const remote = this.identity.inspectAttestation(input.attestation);
      this.consumePairingCode(input.code);
      const peer = await this.peers.upsert({
        nodeId: remote.nodeId,
        name: remote.nodeName,
        fingerprint: remote.fingerprint,
        publicKey: remote.publicKey,
        url: peerUrl(request.socket.remoteAddress, input.port),
      });
      await this.audit.record("peer.paired", { peerNodeId: peer.nodeId, peerName: peer.name });
      return sendJson(response, 201, { attestation: this.identity.attest(this.config.nodeName, remote.nonce) });
    }

    if (url.pathname.startsWith("/local/")) {
      this.requireLocalAdmin(request);
      return this.handleLocal(method, url, body, response);
    }

    if (url.pathname.startsWith("/a2a/tasks")) {
      const peer = this.verifyPeerRequest(request, method, path, body);
      return this.handlePeerTask(peer.nodeId, method, url, body, response);
    }

    sendJson(response, 404, { error: "route_not_found" });
  }

  private async handleLocal(
    method: string,
    url: URL,
    body: unknown,
    response: ServerResponse,
  ): Promise<void> {
    if (method === "GET" && url.pathname === "/local/agents") {
      const paired = await Promise.all(this.peers.list().map(async (peer) => ({
        id: peer.nodeId,
        name: peer.name,
        url: peer.url,
        paired: true,
        reachable: await this.client.ping(peer),
        policy: peer.policy,
      })));
      const pairedIds = new Set(paired.map((peer) => peer.id));
      const nearby = this.discovery.list().filter((peer) => !pairedIds.has(peer.nodeId)).map((peer) => ({
        id: peer.nodeId,
        name: peer.name,
        url: peer.url,
        paired: false,
        reachable: true,
      }));
      return sendJson(response, 200, { agents: [...paired, ...nearby] });
    }
    if (method === "POST" && url.pathname === "/local/pairing/open") {
      const code = String(randomInt(0, 1_000_000)).padStart(6, "0");
      this.pairingCode = { code, expiresAt: Date.now() + 5 * 60_000, failedAttempts: 0 };
      await this.audit.record("pairing.opened", { expiresInSeconds: 300 });
      return sendJson(response, 201, { code, expiresAt: new Date(this.pairingCode.expiresAt).toISOString() });
    }
    if (method === "POST" && url.pathname === "/local/peers/pair") {
      const input = z.object({ target: z.string().min(1).max(2_000), code: z.string().regex(/^\d{6}$/) }).parse(body);
      const discovered = this.discovery.get(input.target);
      const targetUrl = discovered?.url ?? input.target;
      const paired = await this.client.pair(targetUrl, input.code, this.startedPort, discovered?.fingerprint);
      const peer = await this.peers.upsert({
        nodeId: paired.attestation.nodeId,
        name: paired.attestation.nodeName,
        fingerprint: paired.attestation.fingerprint,
        publicKey: paired.attestation.publicKey,
        url: paired.url,
      });
      await this.audit.record("peer.paired", { peerNodeId: peer.nodeId, peerName: peer.name });
      return sendJson(response, 201, { peer });
    }
    const policyMatch = url.pathname.match(/^\/local\/peers\/([^/]+)\/policy$/);
    if (method === "PATCH" && policyMatch) {
      const nodeId = decodeURIComponent(policyMatch[1]);
      const policy = policySchema.parse(body);
      if (policy.workspace && !this.config.workspaces[policy.workspace]) throw new HttpError(400, "工作区不在允许列表");
      if (policy.autoAccept && !policy.workspace) throw new HttpError(400, "自动接收必须指定工作区");
      const workspace = policy.workspace ? this.config.workspaces[policy.workspace] : null;
      if (workspace && policy.permission === "workspace-write" && workspace.maxPermission !== "workspace-write") {
        throw new HttpError(400, "策略权限超过工作区上限");
      }
      return sendJson(response, 200, { peer: await this.peers.setPolicy(nodeId, policy) });
    }
    if (method === "GET" && url.pathname === "/local/tasks") {
      return sendJson(response, 200, { tasks: this.tasks.list() });
    }
    const acceptMatch = url.pathname.match(/^\/local\/tasks\/([^/]+)\/accept$/);
    if (method === "POST" && acceptMatch) {
      const input = z.object({
        workspace: z.string().min(1).max(100),
        permission: z.enum(["read-only", "workspace-write"]),
      }).parse(body);
      return sendJson(response, 200, {
        task: this.tasks.accept(decodeURIComponent(acceptMatch[1]), input.workspace, input.permission),
      });
    }
    const rejectMatch = url.pathname.match(/^\/local\/tasks\/([^/]+)\/reject$/);
    if (method === "POST" && rejectMatch) {
      const input = z.object({ reason: z.string().trim().min(1).max(2_000).optional() }).parse(body);
      return sendJson(response, 200, {
        task: this.tasks.reject(decodeURIComponent(rejectMatch[1]), input.reason),
      });
    }
    if (method === "POST" && url.pathname === "/local/send") {
      const input = taskInputSchema.extend({ peerId: idSchema }).parse(body);
      const peer = this.peers.require(input.peerId);
      const result = await this.client.sendTask(peer, {
        taskId: input.taskId ?? randomUUID(),
        objective: input.objective,
        summary: input.summary,
        expectedOutput: input.expectedOutput,
      });
      return sendJson(response, 201, result);
    }
    const remoteMatch = url.pathname.match(/^\/local\/remote\/([^/]+)\/tasks\/([^/]+)(?:\/(messages|cancel))?$/);
    if (remoteMatch) {
      const peer = this.peers.require(decodeURIComponent(remoteMatch[1]));
      const taskId = decodeURIComponent(remoteMatch[2]);
      if (method === "GET" && !remoteMatch[3]) return sendJson(response, 200, await this.client.getTask(peer, taskId));
      if (method === "POST" && remoteMatch[3] === "messages") {
        const input = z.object({ message: z.string().trim().min(1).max(100_000) }).parse(body);
        return sendJson(response, 200, await this.client.sendMessage(peer, taskId, input.message));
      }
      if (method === "POST" && remoteMatch[3] === "cancel") {
        return sendJson(response, 200, await this.client.cancelTask(peer, taskId));
      }
    }
    if (method === "GET" && url.pathname === "/local/logs") {
      const limit = z.coerce.number().int().min(1).max(500).default(50).parse(url.searchParams.get("limit") ?? 50);
      return sendJson(response, 200, { entries: await this.audit.tail(limit) });
    }
    sendJson(response, 404, { error: "local_route_not_found" });
  }

  private async handlePeerTask(
    peerNodeId: string,
    method: string,
    url: URL,
    body: unknown,
    response: ServerResponse,
  ): Promise<void> {
    const peer = this.peers.require(peerNodeId);
    if (method === "POST" && url.pathname === "/a2a/tasks") {
      const task = this.tasks.receive(peer, taskInputSchema.parse(body));
      return sendJson(response, 201, { task });
    }
    const match = url.pathname.match(/^\/a2a\/tasks\/([^/]+)(?:\/(messages|cancel))?$/);
    if (!match) return sendJson(response, 404, { error: "task_route_not_found" });
    const taskId = decodeURIComponent(match[1]);
    if (method === "GET" && !match[2]) {
      return sendJson(response, 200, { task: this.tasks.requireOwned(taskId, peerNodeId) });
    }
    if (method === "POST" && match[2] === "messages") {
      const input = z.object({ message: z.string().trim().min(1).max(100_000) }).parse(body);
      return sendJson(response, 202, { task: this.tasks.followUp(taskId, peerNodeId, input.message) });
    }
    if (method === "POST" && match[2] === "cancel") {
      return sendJson(response, 200, { task: this.tasks.cancel(taskId, peerNodeId) });
    }
    sendJson(response, 405, { error: "method_not_allowed" });
  }

  private verifyPeerRequest(request: IncomingMessage, method: string, path: string, body: unknown) {
    const nodeId = firstHeader(request.headers["x-lan-a2a-node-id"]);
    if (!nodeId) throw new HttpError(401, "缺少节点身份");
    const peer = this.peers.require(nodeId);
    try {
      this.identity.verifyRequest(peer, method, path, body, request.headers);
    } catch (error) {
      throw new HttpError(401, error instanceof Error ? error.message : String(error));
    }
    return peer;
  }

  private requireLocalAdmin(request: IncomingMessage): void {
    const address = request.socket.remoteAddress ?? "";
    const loopback = address === "127.0.0.1" || address === "::1" || address === "::ffff:127.0.0.1";
    if (!loopback || !matchesToken(this.adminToken, firstHeader(request.headers.authorization))) {
      throw new HttpError(401, "本机管理接口认证失败");
    }
  }

  private consumePairingCode(code: string): void {
    const current = this.pairingCode;
    if (!current || current.expiresAt < Date.now()) {
      this.pairingCode = null;
      throw new HttpError(401, "配对码无效或已过期");
    }
    if (current.code !== code) {
      current.failedAttempts += 1;
      if (current.failedAttempts >= 10) this.pairingCode = null;
      throw new HttpError(401, "配对码无效或已过期");
    }
    this.pairingCode = null;
  }

  private sendError(response: ServerResponse, error: unknown): void {
    const status = error instanceof HttpError ? error.status : error instanceof z.ZodError ? 400 : 500;
    const message = error instanceof Error ? error.message : String(error);
    void this.audit.record("request.failed", { status, error: message }).catch(() => undefined);
    if (!response.headersSent) sendJson(response, status, { error: message });
    else if (!response.writableEnded) response.end();
  }
}

class HttpError extends Error {
  constructor(readonly status: number, message: string) { super(message); }
}

async function readBody(request: IncomingMessage): Promise<unknown> {
  if (["GET", "HEAD"].includes(request.method?.toUpperCase() ?? "GET")) return null;
  let body = "";
  for await (const chunk of request) {
    body += chunk;
    if (Buffer.byteLength(body) > 1_000_000) throw new HttpError(413, "请求正文超过 1 MB");
  }
  if (!body) return {};
  try { return JSON.parse(body); } catch { throw new HttpError(400, "请求正文不是有效 JSON"); }
}

function sendJson(response: ServerResponse, status: number, value: unknown): void {
  if (response.writableEnded) return;
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  response.end(`${JSON.stringify(value)}\n`);
}

function firstHeader(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
