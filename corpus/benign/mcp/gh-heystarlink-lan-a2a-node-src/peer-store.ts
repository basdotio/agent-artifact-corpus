import { join } from "node:path";
import { z } from "zod";
import { readJson, writePrivateJson } from "./files.js";
import type { PeerPolicy, PeerRecord, RuntimeConfig } from "./types.js";

const peerSchema = z.object({
  nodeId: z.string().min(10).max(100),
  name: z.string().min(1).max(100),
  url: z.string().url(),
  fingerprint: z.string().regex(/^sha256:[a-f0-9]{64}$/),
  publicKey: z.string().min(100).max(10_000),
  pairedAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
  policy: z.object({
    autoAccept: z.boolean(),
    workspace: z.string().min(1).max(100).nullable(),
    permission: z.enum(["read-only", "workspace-write"]),
  }),
});
const fileSchema = z.object({ version: z.literal(1), peers: z.array(peerSchema).max(100) });

export class PeerStore {
  private readonly path: string;
  private readonly peers = new Map<string, PeerRecord>();

  private constructor(config: RuntimeConfig) {
    this.path = join(config.dataDir, "peers.json");
  }

  static async load(config: RuntimeConfig): Promise<PeerStore> {
    const store = new PeerStore(config);
    const value = await readJson<unknown>(store.path);
    if (value) {
      for (const peer of fileSchema.parse(value).peers) store.peers.set(peer.nodeId, peer);
    }
    return store;
  }

  list(): PeerRecord[] {
    return [...this.peers.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  get(nodeId: string): PeerRecord | null {
    return this.peers.get(nodeId) ?? null;
  }

  require(nodeId: string): PeerRecord {
    const peer = this.get(nodeId);
    if (!peer) throw new Error(`节点尚未配对：${nodeId}`);
    return peer;
  }

  async upsert(value: Omit<PeerRecord, "pairedAt" | "updatedAt" | "policy">): Promise<PeerRecord> {
    const current = this.peers.get(value.nodeId);
    if (current && current.fingerprint !== value.fingerprint) throw new Error("已配对节点指纹发生变化，已拒绝覆盖");
    const now = new Date().toISOString();
    const peer: PeerRecord = {
      ...value,
      pairedAt: current?.pairedAt ?? now,
      updatedAt: now,
      policy: current?.policy ?? { autoAccept: false, workspace: null, permission: "read-only" },
    };
    this.peers.set(peer.nodeId, peer);
    await this.save();
    return peer;
  }

  async setPolicy(nodeId: string, policy: PeerPolicy): Promise<PeerRecord> {
    const peer = this.require(nodeId);
    const updated = { ...peer, policy, updatedAt: new Date().toISOString() };
    this.peers.set(nodeId, updated);
    await this.save();
    return updated;
  }

  private save(): Promise<void> {
    return writePrivateJson(this.path, { version: 1, peers: this.list() });
  }
}
