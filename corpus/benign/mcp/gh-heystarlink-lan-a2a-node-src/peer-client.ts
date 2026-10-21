import { isIP } from "node:net";
import type { NodeIdentity } from "./security.js";
import type { NodeAttestation, PeerRecord } from "./types.js";

export class PeerClient {
  constructor(
    private readonly identity: NodeIdentity,
    private readonly nodeName: string,
  ) {}

  async pair(url: string, code: string, localPort: number, expectedFingerprint?: string): Promise<{
    attestation: NodeAttestation;
    url: string;
  }> {
    const baseUrl = normalizeUrl(url);
    const nonce = this.identity.createNonce();
    const response = await this.json(`${baseUrl}/a2a/pair`, {
      method: "POST",
      body: {
        code,
        port: localPort,
        attestation: this.identity.attest(this.nodeName, nonce),
      },
    });
    const attestation = this.identity.inspectAttestation((response as { attestation?: unknown }).attestation, nonce);
    if (expectedFingerprint && attestation.fingerprint !== expectedFingerprint.toLowerCase()) {
      throw new Error("发现记录与配对响应的节点指纹不一致");
    }
    return { attestation, url: baseUrl };
  }

  async ping(peer: PeerRecord): Promise<boolean> {
    try {
      const nonce = this.identity.createNonce();
      const value = await this.json(`${peer.url}/a2a/info?nonce=${nonce}`);
      const attestation = this.identity.inspectAttestation(value, nonce);
      return attestation.nodeId === peer.nodeId && attestation.fingerprint === peer.fingerprint;
    } catch {
      return false;
    }
  }

  sendTask(peer: PeerRecord, body: unknown): Promise<unknown> {
    return this.signed(peer, "POST", "/a2a/tasks", body);
  }

  getTask(peer: PeerRecord, taskId: string): Promise<unknown> {
    return this.signed(peer, "GET", `/a2a/tasks/${encodeURIComponent(taskId)}`, null);
  }

  sendMessage(peer: PeerRecord, taskId: string, message: string): Promise<unknown> {
    return this.signed(peer, "POST", `/a2a/tasks/${encodeURIComponent(taskId)}/messages`, { message });
  }

  cancelTask(peer: PeerRecord, taskId: string): Promise<unknown> {
    return this.signed(peer, "POST", `/a2a/tasks/${encodeURIComponent(taskId)}/cancel`, {});
  }

  private async signed(peer: PeerRecord, method: string, path: string, body: unknown): Promise<unknown> {
    return this.json(`${peer.url}${path}`, {
      method,
      body: method === "GET" ? undefined : body,
      headers: this.identity.signRequest(method, path, method === "GET" ? null : body),
    });
  }

  private async json(url: string, options: {
    method?: string;
    body?: unknown;
    headers?: Record<string, string>;
  } = {}): Promise<unknown> {
    const response = await fetch(url, {
      method: options.method ?? "GET",
      redirect: "error",
      signal: AbortSignal.timeout(10_000),
      headers: {
        ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
        ...options.headers,
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
    const text = await response.text();
    let value: unknown = {};
    if (text) {
      try { value = JSON.parse(text); } catch { throw new Error(`节点返回无效 JSON（HTTP ${response.status}）`); }
    }
    if (!response.ok) {
      const message = typeof value === "object" && value && "error" in value
        ? String((value as { error: unknown }).error)
        : `节点请求失败（HTTP ${response.status}）`;
      throw new Error(message);
    }
    return value;
  }
}

export function peerUrl(remoteAddress: string | undefined, port: number): string {
  let address = remoteAddress ?? "";
  if (address.startsWith("::ffff:")) address = address.slice(7);
  if (!isIP(address)) throw new Error("无法识别配对节点地址");
  return `http://${address.includes(":") ? `[${address}]` : address}:${port}`;
}

function normalizeUrl(value: string): string {
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol)) throw new Error("节点地址只支持 HTTP 或 HTTPS");
  if (url.username || url.password) throw new Error("节点地址不能包含用户名或密码");
  return url.toString().replace(/\/$/, "");
}
