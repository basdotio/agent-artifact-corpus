import {
  createHash,
  createPrivateKey,
  createPublicKey,
  generateKeyPairSync,
  randomBytes,
  sign,
  timingSafeEqual,
  verify,
} from "node:crypto";
import { join } from "node:path";
import { z } from "zod";
import { readJson, writePrivateJson } from "./files.js";
import type { NodeAttestation, PeerRecord, RuntimeConfig } from "./types.js";

const MAX_CLOCK_SKEW_MS = 60_000;
const nonceSchema = z.string().regex(/^[a-f0-9]{32,128}$/i);
const identitySchema = z.object({
  version: z.literal(1),
  createdAt: z.string().datetime(),
  privateKey: z.string().min(100),
  publicKey: z.string().min(100),
});

export class NodeIdentity {
  readonly nodeId: string;
  readonly fingerprint: string;
  private readonly seenNonces = new Map<string, number>();

  private constructor(
    readonly publicKey: string,
    private readonly privateKey: string,
  ) {
    this.fingerprint = fingerprint(publicKey);
    this.nodeId = `node:${this.fingerprint.slice("sha256:".length, 30)}`;
  }

  static async load(config: RuntimeConfig): Promise<NodeIdentity> {
    const path = join(config.dataDir, "identity.json");
    let value = await readJson<unknown>(path);
    if (!value) {
      const pair = generateKeyPairSync("ed25519");
      value = {
        version: 1,
        createdAt: new Date().toISOString(),
        privateKey: pair.privateKey.export({ type: "pkcs8", format: "pem" }).toString(),
        publicKey: pair.publicKey.export({ type: "spki", format: "pem" }).toString(),
      };
      await writePrivateJson(path, value);
    }
    const parsed = identitySchema.parse(value);
    return new NodeIdentity(parsed.publicKey, parsed.privateKey);
  }

  createNonce(): string {
    return randomBytes(32).toString("hex");
  }

  attest(nodeName: string, nonce: string): NodeAttestation {
    nonceSchema.parse(nonce);
    const payload = {
      protocolVersion: 1 as const,
      nodeId: this.nodeId,
      nodeName,
      fingerprint: this.fingerprint,
      publicKey: this.publicKey,
      issuedAt: new Date().toISOString(),
      nonce,
    };
    return { ...payload, signature: signValue(payload, this.privateKey) };
  }

  inspectAttestation(value: unknown, expectedNonce?: string): NodeAttestation {
    const parsed = attestationSchema.parse(value);
    const { signature, ...payload } = parsed;
    assertFresh(parsed.issuedAt);
    if (expectedNonce && !safeEqual(parsed.nonce, expectedNonce)) throw new Error("节点握手随机数不匹配");
    if (fingerprint(parsed.publicKey) !== parsed.fingerprint) throw new Error("节点公钥指纹不匹配");
    if (`node:${parsed.fingerprint.slice("sha256:".length, 30)}` !== parsed.nodeId) {
      throw new Error("节点 ID 与公钥不匹配");
    }
    if (!verifyValue(payload, signature, parsed.publicKey)) throw new Error("节点握手签名无效");
    return parsed;
  }

  signRequest(method: string, path: string, body: unknown): Record<string, string> {
    const timestamp = new Date().toISOString();
    const nonce = this.createNonce();
    const bodyHash = digest(body);
    const payload = requestPayload(this.nodeId, method, path, timestamp, nonce, bodyHash);
    return {
      "X-LAN-A2A-Node-Id": this.nodeId,
      "X-LAN-A2A-Timestamp": timestamp,
      "X-LAN-A2A-Nonce": nonce,
      "X-LAN-A2A-Body-SHA256": bodyHash,
      "X-LAN-A2A-Signature": signValue(payload, this.privateKey),
    };
  }

  verifyRequest(
    peer: PeerRecord,
    method: string,
    path: string,
    body: unknown,
    headers: Record<string, string | string[] | undefined>,
  ): void {
    const nodeId = header(headers, "x-lan-a2a-node-id");
    const timestamp = header(headers, "x-lan-a2a-timestamp");
    const nonce = header(headers, "x-lan-a2a-nonce");
    const bodyHash = header(headers, "x-lan-a2a-body-sha256");
    const signature = header(headers, "x-lan-a2a-signature");
    if (nodeId !== peer.nodeId) throw new Error("请求节点与已配对节点不一致");
    assertFresh(timestamp);
    nonceSchema.parse(nonce);
    this.pruneNonces();
    if (this.seenNonces.has(`${nodeId}:${nonce}`)) throw new Error("检测到重复请求");
    if (!safeEqual(digest(body), bodyHash)) throw new Error("请求正文摘要不匹配");
    const payload = requestPayload(nodeId, method, path, timestamp, nonce, bodyHash);
    if (!verifyValue(payload, signature, peer.publicKey)) throw new Error("节点请求签名无效");
    this.seenNonces.set(`${nodeId}:${nonce}`, Date.now() + MAX_CLOCK_SKEW_MS);
  }

  private pruneNonces(): void {
    for (const [nonce, expiresAt] of this.seenNonces) {
      if (expiresAt < Date.now()) this.seenNonces.delete(nonce);
    }
  }
}

const attestationSchema = z.object({
  protocolVersion: z.literal(1),
  nodeId: z.string().min(10).max(100),
  nodeName: z.string().min(1).max(100),
  fingerprint: z.string().regex(/^sha256:[a-f0-9]{64}$/),
  publicKey: z.string().min(100).max(10_000),
  issuedAt: z.string().datetime(),
  nonce: nonceSchema,
  signature: z.string().min(20).max(1_000),
});

function requestPayload(nodeId: string, method: string, path: string, timestamp: string, nonce: string, bodyHash: string) {
  return { protocolVersion: 1, nodeId, method: method.toUpperCase(), path, timestamp, nonce, bodyHash };
}

function digest(value: unknown): string {
  const json = JSON.stringify(value ?? null);
  const wireValue = json === undefined ? null : JSON.parse(json) as unknown;
  return createHash("sha256").update(stableStringify(wireValue)).digest("hex");
}

function fingerprint(publicKey: string): string {
  const der = createPublicKey(publicKey).export({ type: "spki", format: "der" });
  return `sha256:${createHash("sha256").update(der).digest("hex")}`;
}

function signValue(value: unknown, privateKey: string): string {
  return sign(null, Buffer.from(stableStringify(value)), createPrivateKey(privateKey)).toString("base64");
}

function verifyValue(value: unknown, signature: string, publicKey: string): boolean {
  try {
    return verify(null, Buffer.from(stableStringify(value)), createPublicKey(publicKey), Buffer.from(signature, "base64"));
  } catch {
    return false;
  }
}

function stableStringify(value: unknown): string {
  if (value === null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(record[key])}`).join(",")}}`;
}

function header(headers: Record<string, string | string[] | undefined>, name: string): string {
  const value = headers[name];
  const text = Array.isArray(value) ? value[0] : value;
  if (!text) throw new Error(`缺少请求头 ${name}`);
  return text;
}

function assertFresh(timestamp: string): void {
  const time = Date.parse(timestamp);
  if (!Number.isFinite(time) || Math.abs(Date.now() - time) > MAX_CLOCK_SKEW_MS) {
    throw new Error("节点请求已过期");
  }
}

function safeEqual(left: string, right: string): boolean {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}
