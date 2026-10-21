import Bonjour, { type Browser, type Service } from "bonjour-service";
import type { NearbyAgent, RuntimeConfig } from "./types.js";
import type { NodeIdentity } from "./security.js";

const SERVICE_TYPE = "lan-a2a";
const STALE_MS = 30_000;

export class LanDiscovery {
  private bonjour: Bonjour | null = null;
  private browser: Browser | null = null;
  private readonly nearby = new Map<string, NearbyAgent>();

  constructor(
    private readonly config: RuntimeConfig,
    private readonly identity: NodeIdentity,
  ) {}

  start(port: number): void {
    if (!this.config.discoveryEnabled || this.bonjour) return;
    this.bonjour = new Bonjour();
    this.bonjour.publish({
      name: `${this.config.nodeName}-${this.identity.fingerprint.slice(-6)}`,
      type: SERVICE_TYPE,
      protocol: "tcp",
      port,
      disableIPv6: true,
      txt: {
        protocolVersion: "1",
        nodeId: this.identity.nodeId,
        nodeName: this.config.nodeName,
        fingerprint: this.identity.fingerprint,
      },
    });
    this.browser = this.bonjour.find({ type: SERVICE_TYPE, protocol: "tcp" });
    this.browser.on("up", (service) => this.remember(service));
    this.browser.on("txt-update", (service) => this.remember(service));
    this.browser.on("srv-update", (service) => this.remember(service));
    this.browser.on("down", (service) => this.forget(service));
  }

  stop(): void {
    this.browser?.stop();
    this.bonjour?.unpublishAll();
    this.bonjour?.destroy();
    this.browser = null;
    this.bonjour = null;
    this.nearby.clear();
  }

  list(): NearbyAgent[] {
    const threshold = Date.now() - STALE_MS;
    for (const [id, agent] of this.nearby) {
      if (Date.parse(agent.lastSeenAt) < threshold) this.nearby.delete(id);
    }
    return [...this.nearby.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  get(nodeId: string): NearbyAgent | null {
    return this.list().find((agent) => agent.nodeId === nodeId) ?? null;
  }

  private remember(service: Service): void {
    const txt = service.txt as Record<string, unknown> | undefined;
    const nodeId = text(txt?.nodeId);
    const name = text(txt?.nodeName);
    const fingerprint = text(txt?.fingerprint);
    if (!nodeId || nodeId === this.identity.nodeId || !name || !/^sha256:[a-f0-9]{64}$/i.test(fingerprint)) return;
    const address = service.addresses?.find((value) => /^\d{1,3}(?:\.\d{1,3}){3}$/.test(value));
    if (!address) return;
    this.nearby.set(nodeId, {
      nodeId,
      name,
      fingerprint: fingerprint.toLowerCase(),
      url: `http://${address}:${service.port}`,
      lastSeenAt: new Date().toISOString(),
    });
  }

  private forget(service: Service): void {
    const nodeId = text((service.txt as Record<string, unknown> | undefined)?.nodeId);
    if (nodeId) this.nearby.delete(nodeId);
  }
}

function text(value: unknown): string {
  return Buffer.isBuffer(value) ? value.toString("utf8") : typeof value === "string" ? value : "";
}
