import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { ProtocolError } from "@modelcontextprotocol/server";
import { ArgumentsSchema, EVENT_NAME, Galaxy, type EventRequest, type WebhookLease } from "./galaxy.js";
import { SafeWebhookHttpClient, UnsafeWebhookAddressError, classifyWebhookError, parseWebhookUrl, waitFor, type WebhookHttpClient, type WebhookErrorCategory } from "./webhook-http.js";

export const MAX_WEBHOOK_TTL_MS = 30 * 60_000;
const MIN_TTL_MS = 5000;
const RETRIES = [1000, 5000, 25_000];
export type SubscribeRequest = EventRequest & { delivery: { mode: "webhook"; url: string; secret: string }; ttlMs?: number | null };
export type UnsubscribeRequest = Pick<EventRequest, "name" | "arguments"> & { delivery: { url: string; secret: string } };
type Subscription = {
  id: string; key: string; ip: string; url: string; secret: string; lease: WebhookLease;
  binding: ReturnType<Galaxy["attachWebhook"]>; cursor: string; abort: AbortController;
  expiry?: ReturnType<typeof setTimeout>; worker?: Promise<void>; dirty: boolean;
  lastError?: WebhookErrorCategory; lastDeliveryAt?: string; failedSince?: string;
};

/** Playground-only deviation: a signing secret owns this callback registration
 * for its lease, not an account. Never expose URLs or secrets in the roster. */
export class WebhookService {
  private subscriptions = new Map<string, Subscription>();
  private operations = new Map<string, Promise<unknown>>();
  private reservations = new Map<string, string>();
  private stop = new AbortController();
  constructor(private galaxy: Galaxy, private http: WebhookHttpClient = new SafeWebhookHttpClient()) {}

  async subscribe(input: SubscribeRequest, ip: string, callerSignal?: AbortSignal) {
    const { url, key } = this.identity(input);
    const ttlMs = grantTtl(input.ttlMs);
    if (input.delivery.mode !== "webhook") throw new ProtocolError(-32014, "Unsupported", { feature: "deliveryMode" });
    if (input.cursor != null && !/^[a-f0-9]{24}:\d+$/.test(input.cursor)) throw new ProtocolError(-32602, "InvalidParams", { field: "cursor" });
    this.sweep();
    return this.exclusive(key, async () => {
      this.stop.signal.throwIfAborted();
      this.sweep();
      const existing = this.subscriptions.get(key);
      if (existing) {
        this.requireOwner(existing, input.delivery.secret);
        this.galaxy.limiter.consume([{ key: "webhook-refresh:" + ip, capacity: 30, period: 60_000 }]);
        const now = this.galaxy.now();
        Object.assign(existing.lease, { renewedAt: now, expiresAt: now + ttlMs, ttlMs });
        this.armExpiry(existing);
        const result = this.result(existing, false);
        this.wake(existing);
        return result;
      }
      const perIp = [...this.subscriptions.values()].filter(s => s.ip === ip).length + [...this.reservations.values()].filter(value => value === ip).length;
      if (perIp >= 4 || this.subscriptions.size + this.reservations.size >= 128) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "webhooks", max: 128, perIp: 4 });
      this.galaxy.limiter.consume([
        { key: "webhook-register:" + ip, capacity: 4, period: 60_000 },
        { key: "webhook-host:" + new URL(url).hostname, capacity: 8, period: 60_000 },
        { key: "webhook-register:global", capacity: 16, period: 60_000 }
      ]);
      this.reservations.set(key, ip);
      try {
        const signal = callerSignal ? AbortSignal.any([this.stop.signal, callerSignal]) : this.stop.signal;
        const id = "sub_" + createHash("sha256").update(key).digest("hex").slice(0, 32);
        await this.verify(url, id, input.delivery.secret, signal);
        signal.throwIfAborted();
        const now = this.galaxy.now();
        const lease = { renewedAt: now, expiresAt: now + ttlMs, ttlMs };
        let sub!: Subscription;
        const binding = this.galaxy.attachWebhook(input, ip, id, lease, () => this.wake(sub));
        sub = { id, key, ip, url, secret: input.delivery.secret, lease, binding, cursor: binding.cursor, abort: new AbortController(), dirty: false };
        this.subscriptions.set(key, sub);
        this.armExpiry(sub);
        const result = this.result(sub, binding.truncated);
        this.wake(sub);
        return result;
      } finally { this.reservations.delete(key); }
    });
  }

  async unsubscribe(input: UnsubscribeRequest) {
    const { key } = this.identity(input);
    this.sweep();
    return this.exclusive(key, async () => {
      this.sweep();
      const sub = this.subscriptions.get(key);
      if (!sub) throw new ProtocolError(-32011, "NotFound", { kind: "subscription" });
      this.requireOwner(sub, input.delivery.secret);
      this.remove(sub);
      await sub.worker;
      return {};
    });
  }
  sweep() { for (const sub of this.subscriptions.values()) if (!this.live(sub)) this.remove(sub); }
  async close() {
    this.stop.abort();
    const workers = [...this.subscriptions.values()].map(s => s.worker);
    for (const sub of this.subscriptions.values()) this.remove(sub);
    await Promise.allSettled([...workers, ...this.operations.values()]);
  }
  private identity(input: UnsubscribeRequest) {
    if (input.name !== EVENT_NAME) throw new ProtocolError(-32011, "NotFound", { kind: "event" });
    const parsed = ArgumentsSchema.safeParse(input.arguments);
    if (!parsed.success) throw new ProtocolError(-32602, "InvalidParams", { field: "arguments" });
    decodeSecret(input.delivery.secret);
    const url = parseWebhookUrl(input.delivery.url).toString();
    return { url, key: JSON.stringify([EVENT_NAME, parsed.data, url]) };
  }
  private requireOwner(sub: Subscription, secret: string) {
    const digest = (value: string) => createHash("sha256").update(value).digest();
    if (!timingSafeEqual(digest(sub.secret), digest(secret))) throw new ProtocolError(-32012, "Forbidden", { reason: "subscription_secret_required" });
  }
  private async exclusive<T>(key: string, action: () => Promise<T>): Promise<T> {
    if (this.operations.has(key) || this.operations.size >= 8) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "concurrentWebhookUpdates", max: 8 });
    const operation = Promise.resolve().then(action);
    this.operations.set(key, operation);
    try { return await operation; } finally { this.operations.delete(key); }
  }
  private async verify(url: string, id: string, secret: string, signal: AbortSignal) {
    const challenge = randomBytes(32).toString("base64url");
    let response;
    try { response = await this.send(url, id, "msg_verification_" + randomBytes(16).toString("hex"), { type: "verification", challenge }, secret, signal); }
    catch (error) {
      if (signal.aborted) throw error;
      if (error instanceof UnsafeWebhookAddressError) throw new ProtocolError(-32602, "InvalidParams", { field: "delivery.url" });
      throw new ProtocolError(-32015, "CallbackEndpointError", { reason: classifyWebhookError(error) });
    }
    if (response.status < 200 || response.status >= 300) throw new ProtocolError(-32015, "CallbackEndpointError", { reason: statusCategory(response.status) });
    let echoed: unknown;
    try { echoed = JSON.parse(response.body).challenge; } catch { /* Never expose endpoint data. */ }
    const actual = Buffer.from(typeof echoed === "string" ? echoed : "");
    const expected = Buffer.from(challenge);
    if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) throw new ProtocolError(-32015, "CallbackEndpointError", { reason: "challenge_failed" });
  }
  private wake(sub: Subscription) {
    sub.dirty = true;
    if (sub.worker || !this.live(sub)) return;
    sub.worker = Promise.resolve().then(async () => {
      while (this.live(sub)) {
        sub.dirty = false;
        const batch = sub.binding.read(sub.cursor);
        const event = batch.events[0];
        if (batch.truncated) {
          const gapCursor = event ? event.cursor.replace(/:\d+$/, ":" + (Number(event.cursor.split(":")[1]) - 1)) : batch.cursor;
          await this.deliver(sub, "msg_gap_" + randomBytes(16).toString("hex"), { type: "gap", cursor: gapCursor });
          if (!this.live(sub)) return;
          sub.cursor = gapCursor;
        }
        if (!event) { sub.cursor = batch.cursor; return; }
        await this.deliver(sub, event.eventId, { ...event, cursor: batch.cursor });
        if (!this.live(sub)) return;
        sub.cursor = batch.cursor; // Earlier occurrences are ACKed or abandoned.
        await waitFor(500, sub.abort.signal);
      }
    }).catch(error => {
      if (this.live(sub)) { sub.lastError = classifyWebhookError(error); sub.failedSince ??= new Date(this.galaxy.now()).toISOString(); }
    }).finally(() => {
      sub.worker = undefined;
      if (sub.dirty && this.live(sub)) this.wake(sub);
    });
  }
  private async deliver(sub: Subscription, messageId: string, body: Record<string, unknown>) {
    for (let attempt = 0; attempt <= RETRIES.length; attempt++) {
      if (attempt) await waitFor(RETRIES[attempt - 1], sub.abort.signal);
      if (!this.live(sub)) return;
      try {
        const response = await this.send(sub.url, sub.id, messageId, body, sub.secret, sub.abort.signal);
        if (!this.live(sub)) return;
        if (response.status >= 200 && response.status < 300) {
          sub.lastDeliveryAt = new Date(this.galaxy.now()).toISOString(); sub.lastError = undefined; sub.failedSince = undefined; return;
        }
        sub.lastError = statusCategory(response.status);
        sub.failedSince ??= new Date(this.galaxy.now()).toISOString();
        if (response.status === 410 || response.status === 413) return;
      } catch (error) {
        if (!this.live(sub)) return;
        sub.lastError = classifyWebhookError(error); sub.failedSince ??= new Date(this.galaxy.now()).toISOString();
        if (error instanceof UnsafeWebhookAddressError) return;
      }
    }
  }
  private send(url: string, id: string, messageId: string, payload: object, secret: string, signal: AbortSignal) {
    const body = JSON.stringify(payload);
    const timestamp = String(Math.floor(this.galaxy.now() / 1000));
    const signature = createHmac("sha256", decodeSecret(secret)).update(`${messageId}.${timestamp}.${body}`).digest("base64");
    return this.http.post(url, body, { "Content-Type": "application/json", "webhook-id": messageId, "webhook-timestamp": timestamp, "webhook-signature": "v1," + signature, "X-MCP-Subscription-Id": id }, signal);
  }
  private result(sub: Subscription, truncated: boolean) {
    return { id: sub.id, subscriberId: sub.binding.subscriberId, refreshBefore: new Date(sub.lease.expiresAt).toISOString(), cursor: sub.cursor, truncated,
      deliveryStatus: { active: this.live(sub), lastDeliveryAt: sub.lastDeliveryAt, lastError: sub.lastError ?? null, failedSince: sub.failedSince } };
  }
  private live(sub: Subscription) { return !this.stop.signal.aborted && !sub.abort.signal.aborted && sub.lease.expiresAt > this.galaxy.now(); }
  private armExpiry(sub: Subscription) {
    clearTimeout(sub.expiry);
    sub.expiry = setTimeout(() => this.remove(sub), Math.max(0, sub.lease.expiresAt - this.galaxy.now())); sub.expiry.unref();
  }
  private remove(sub: Subscription) {
    if (this.subscriptions.get(sub.key) !== sub) return;
    this.subscriptions.delete(sub.key); sub.abort.abort(); clearTimeout(sub.expiry); sub.binding.detach();
  }
}
export function grantTtl(value?: number | null) {
  if (value == null) return MAX_WEBHOOK_TTL_MS; // No never-expiring grants.
  if (!Number.isSafeInteger(value) || value < 0) throw new ProtocolError(-32602, "InvalidParams", { field: "ttlMs" });
  return Math.min(MAX_WEBHOOK_TTL_MS, Math.max(MIN_TTL_MS, value));
}
export function decodeSecret(value: string) {
  const encoded = value.startsWith("whsec_") ? value.slice(6) : "";
  const bytes = Buffer.from(encoded, "base64");
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(encoded) || bytes.length < 24 || bytes.length > 64 || bytes.toString("base64") !== encoded) throw new ProtocolError(-32602, "InvalidParams", { field: "delivery.secret" });
  return bytes;
}
function statusCategory(status: number): WebhookErrorCategory { return status >= 500 ? "http_5xx" : "http_4xx"; }
