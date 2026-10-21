import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { ProtocolError } from "@modelcontextprotocol/server";
import type { AgentIdentity } from "./config.js";
import { CHAT_ACTIVITY_EVENT, type EventRequest, type EventsService } from "./events.js";
import type { EventHub } from "./hub.js";
import type { DebugLog } from "./debug-log.js";
import { SafeWebhookHttpClient, UnsafeWebhookAddressError, classifyWebhookError, parseWebhookUrl, waitFor,
  type WebhookErrorCategory, type WebhookHttpClient } from "./webhook-http.js";

const DEFAULT_TTL_MS = 5 * 60_000;
const MIN_TTL_MS = 60_000;
const RETRY_DELAYS_MS = [1000, 5000, 25_000, 125_000];
const ROTATION_GRACE_MS = 60_000;
const MAX_SUBSCRIPTIONS = 128;
const MAX_PER_AGENT = 16;

export type WebhookSubscribeRequest = EventRequest & {
  delivery: { mode: string; url: string; secret: string };
  ttlMs?: number | null;
};
export type WebhookUnsubscribeRequest = Pick<EventRequest, "name" | "arguments"> & { delivery: { url: string } };
type Subscription = {
  id: string; key: string; agent: AgentIdentity; url: string; secret: string;
  previousSecret?: { value: string; until: number };
  expiresAt: number; cursor: string; abort: AbortController; off: () => void;
  expiry?: ReturnType<typeof setTimeout>; worker?: Promise<void>;
  dirty?: boolean;
  lastDeliveryAt?: string; lastError?: WebhookErrorCategory; failedSince?: string;
};

/** Short-lived soft-state subscriptions; SQLite history and the client's cursor
 * recover restart gaps. No signing secrets or subscription cursors go to disk. */
export class WebhookService {
  private readonly subscriptions = new Map<string, Subscription>();
  private readonly agentListeners = new Map<string, { off: () => void; count: number }>();
  private readonly operations = new Map<string, Promise<unknown>>();
  private readonly reservations = new Map<string, string>();
  private readonly verified = new Map<string, number>();
  private readonly verificationRate = new Map<string, { count: number; until: number }>();
  private readonly stop = new AbortController();

  constructor(private readonly events: EventsService, private readonly hub: EventHub,
    private readonly http: WebhookHttpClient = new SafeWebhookHttpClient(), private readonly debug?: DebugLog) {}

  async subscribe(agent: AgentIdentity, input: WebhookSubscribeRequest) {
    this.events.webhookStart(agent, input); // Validate before any outbound request.
    if (input.delivery.mode !== "webhook") throw new ProtocolError(-32014, "Unsupported", { feature: "deliveryMode", value: input.delivery.mode });
    const url = parseWebhookUrl(input.delivery.url).toString();
    decodeSecret(input.delivery.secret);
    const ttl = grantTtl(input.ttlMs);
    const key = JSON.stringify([agent.id, url, CHAT_ACTIVITY_EVENT, {}]);
    return this.exclusive(key, async () => {
      this.stop.signal.throwIfAborted();
      this.removeExpired();
      const existing = this.subscriptions.get(key);
      const previousStatus = existing ? this.status(existing) : undefined;
      if (!existing) {
        const perAgent = [...this.subscriptions.values()].filter((s) => s.agent.id === agent.id).length
          + [...this.reservations.values()].filter((id) => id === agent.id).length;
        if (perAgent >= MAX_PER_AGENT || this.subscriptions.size + this.reservations.size >= MAX_SUBSCRIPTIONS) {
          throw new ProtocolError(-32013, "ResourceExhausted", { limit: "subscriptions", max: perAgent >= MAX_PER_AGENT ? MAX_PER_AGENT : MAX_SUBSCRIPTIONS });
        }
        this.reservations.set(key, agent.id);
      }
      try {
        const id = `sub_${createHash("sha256").update(key).digest("hex").slice(0, 32)}`;
        const endpoint = JSON.stringify([agent.id, url]);
        if (!existing && (this.verified.get(endpoint) ?? 0) <= Date.now()) {
          try {
            await this.verify(url, id, input.delivery.secret);
            this.debug?.record("webhook.verified", { actor: agent, mode: "webhook", subscriptionId: id });
          } catch (error) {
            this.debug?.record("webhook.verification_failed", { actor: agent, mode: "webhook", subscriptionId: id, reason: "verification_rejected" });
            throw error;
          }
          this.verified.set(endpoint, Date.now() + DEFAULT_TTL_MS);
        }
        this.stop.signal.throwIfAborted();
        const now = Date.now();
        if (existing && !existing.abort.signal.aborted) {
          if (existing.secret !== input.delivery.secret) {
            existing.previousSecret = { value: existing.secret, until: now + ROTATION_GRACE_MS };
            existing.secret = input.delivery.secret;
          }
          existing.expiresAt = now + ttl;
          this.armExpiry(existing);
          if (!existing.worker) {
            const batch = this.events.poll(agent, { name: CHAT_ACTIVITY_EVENT, cursor: existing.cursor, maxEvents: 1 });
            if (!batch.events.length) existing.cursor = batch.cursor;
          }
          const result = this.result(existing, false, previousStatus);
          this.debug?.record("subscription.renewed", this.debugDetails(existing));
          this.wake(existing);
          return result;
        }
        const start = this.events.webhookStart(agent, input);
        const sub: Subscription = {
          id, key, agent, url, secret: input.delivery.secret, expiresAt: now + ttl,
          cursor: start.cursor, abort: new AbortController(), off: () => {}
        };
        this.subscriptions.set(key, sub);
        sub.off = this.listenForAgent(agent.id);
        this.armExpiry(sub);
        const result = this.result(sub, start.truncated);
        this.debug?.record("subscription.created", { ...this.debugDetails(sub), truncated: start.truncated });
        this.wake(sub);
        return result;
      } finally { this.reservations.delete(key); }
    });
  }

  async unsubscribe(agent: AgentIdentity, input: WebhookUnsubscribeRequest) {
    this.events.webhookStart(agent, input);
    const url = parseWebhookUrl(input.delivery.url).toString();
    const key = JSON.stringify([agent.id, url, CHAT_ACTIVITY_EVENT, {}]);
    return this.exclusive(key, async () => {
      const sub = this.subscriptions.get(key);
      if (!sub || sub.expiresAt <= Date.now()) throw new ProtocolError(-32011, "NotFound", { kind: "subscription" });
      this.remove(sub, "unsubscribed");
      await sub.worker; // Abort in-flight HTTP and sleeping retries before ACK.
      return {};
    });
  }

  async close() {
    this.stop.abort();
    const workers = [...this.subscriptions.values()].map((s) => s.worker);
    for (const sub of this.subscriptions.values()) this.remove(sub, "server_stopped");
    await Promise.allSettled([...workers, ...this.operations.values()]);
    this.verified.clear();
    this.verificationRate.clear();
  }

  private async exclusive<T>(key: string, action: () => Promise<T>): Promise<T> {
    // Do not let simultaneous refreshes multiply challenge requests or workers.
    if (this.operations.has(key)) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "concurrentSubscriptionUpdates", max: 1 });
    const operation = Promise.resolve().then(action);
    this.operations.set(key, operation);
    try { return await operation; } finally { this.operations.delete(key); }
  }

  private async verify(url: string, id: string, secret: string) {
    const now = Date.now();
    for (const [key, expiry] of this.verified) if (expiry <= now) this.verified.delete(key);
    for (const [key, rate] of this.verificationRate) if (rate.until <= now) this.verificationRate.delete(key);
    if (this.verified.size >= 512 || this.verificationRate.size >= 512) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "verificationCache", max: 512 });
    const host = new URL(url).hostname;
    const rate = this.verificationRate.get(host) ?? { count: 0, until: now + 60_000 };
    if (rate.count >= 10 || this.reservations.size > 16) throw new ProtocolError(-32013, "ResourceExhausted", { limit: "endpointVerifications", max: 10 });
    rate.count++;
    this.verificationRate.set(host, rate);
    const challenge = randomBytes(32).toString("base64url");
    let response;
    try {
      response = await this.send(url, id, `msg_verification_${randomBytes(16).toString("hex")}`,
        { type: "verification", challenge }, [secret], this.stop.signal);
    } catch (error) {
      if (error instanceof UnsafeWebhookAddressError) throw new ProtocolError(-32602, "InvalidParams", { field: "delivery.url" });
      throw new ProtocolError(-32015, "CallbackEndpointError", { reason: classifyWebhookError(error) });
    }
    if (response.status < 200 || response.status >= 300) {
      throw new ProtocolError(-32015, "CallbackEndpointError", { reason: statusCategory(response.status) });
    }
    let echoed: unknown;
    try { echoed = JSON.parse(response.body).challenge; } catch { /* Never expose callback response contents. */ }
    const actual = Buffer.from(typeof echoed === "string" ? echoed : "");
    const expected = Buffer.from(challenge);
    if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) {
      throw new ProtocolError(-32015, "CallbackEndpointError", { reason: "challenge_failed" });
    }
  }

  private wake(sub: Subscription) {
    sub.dirty = true;
    if (sub.worker || !this.live(sub)) return;
    sub.worker = Promise.resolve().then(async () => {
      // Pull one occurrence at a time from SQLite. Backpressure never builds an
      // unbounded JS queue. Only ACKed/abandoned events advance the watermark.
      while (this.live(sub)) {
        sub.dirty = false;
        const batch = this.events.poll(sub.agent, { name: CHAT_ACTIVITY_EVENT, cursor: sub.cursor, maxEvents: 1 });
        const event = batch.events[0];
        if (!event) { sub.cursor = batch.cursor; return; }
        await this.deliver(sub, event.eventId, { ...event, cursor: batch.cursor });
        if (!this.live(sub)) return;
        sub.cursor = batch.cursor;
        await waitFor(500, sub.abort.signal); // At most two events/sec/subscription.
      }
    }).catch((error) => {
      if (this.live(sub)) {
        sub.lastError = classifyWebhookError(error); sub.failedSince ??= new Date().toISOString();
        this.debug?.record("delivery.failed", { ...this.debugDetails(sub), reason: sub.lastError });
      }
    }).finally(() => {
      sub.worker = undefined;
      if (sub.dirty && this.live(sub)) this.wake(sub);
    });
  }

  private async deliver(sub: Subscription, messageId: string, payload: Record<string, unknown>) {
    for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
      if (attempt) {
        this.debug?.record("delivery.retry_scheduled", { ...this.debugDetails(sub), eventId: messageId,
          attempt: attempt + 1, retryAfterMs: RETRY_DELAYS_MS[attempt - 1] });
        await waitFor(RETRY_DELAYS_MS[attempt - 1], sub.abort.signal);
      }
      if (!this.live(sub)) return;
      const secrets = [sub.secret];
      if (sub.previousSecret && sub.previousSecret.until > Date.now()) secrets.push(sub.previousSecret.value);
      const details = { ...this.debugDetails(sub), eventId: messageId, attempt: attempt + 1 };
      this.debug?.record("delivery.attempted", details);
      try {
        const response = await this.send(sub.url, sub.id, messageId, payload, secrets, sub.abort.signal);
        if (!this.live(sub)) return;
        if (response.status >= 200 && response.status < 300) {
          sub.lastDeliveryAt = new Date().toISOString();
          sub.lastError = undefined;
          sub.failedSince = undefined;
          this.debug?.record("delivery.sent", details);
          return;
        }
        sub.lastError = statusCategory(response.status);
        sub.failedSince ??= new Date().toISOString();
        this.debug?.record("delivery.failed", { ...details, reason: sub.lastError });
        if (response.status === 410 || response.status === 413) {
          this.debug?.record("delivery.abandoned", { ...details, reason: sub.lastError });
          return;
        }
      } catch (error) {
        if (!this.live(sub)) return;
        sub.lastError = classifyWebhookError(error);
        sub.failedSince ??= new Date().toISOString();
        this.debug?.record("delivery.failed", { ...details, reason: sub.lastError });
        if (error instanceof UnsafeWebhookAddressError) {
          this.debug?.record("delivery.abandoned", { ...details, reason: "unsafe_address" });
          return;
        }
      }
    }
    this.debug?.record("delivery.abandoned", { ...this.debugDetails(sub), eventId: messageId, reason: "retry_exhausted" });
  }

  private debugDetails(sub: Subscription) {
    return { actor: sub.agent, subscriptionId: sub.id, mode: "webhook" as const, expiresAt: new Date(sub.expiresAt).toISOString() };
  }

  private send(url: string, id: string, messageId: string, payload: Record<string, unknown>, secrets: string[], signal: AbortSignal) {
    const body = JSON.stringify(payload);
    const timestamp = String(Math.floor(Date.now() / 1000));
    const signatures = secrets.map((secret) => `v1,${createHmac("sha256", decodeSecret(secret)).update(`${messageId}.${timestamp}.${body}`).digest("base64")}`).join(" ");
    return this.http.post(url, body, {
      "Content-Type": "application/json", "webhook-id": messageId,
      "webhook-timestamp": timestamp, "webhook-signature": signatures, "X-MCP-Subscription-Id": id
    }, signal);
  }

  private result(sub: Subscription, truncated: boolean, status = this.status(sub)) {
    return { id: sub.id, refreshBefore: new Date(sub.expiresAt).toISOString(), cursor: sub.cursor, truncated, deliveryStatus: status };
  }
  private status(sub: Subscription) {
    return { active: this.live(sub), lastDeliveryAt: sub.lastDeliveryAt, lastError: sub.lastError ?? null, failedSince: sub.failedSince };
  }
  private live(sub: Subscription) { return !sub.abort.signal.aborted && !this.stop.signal.aborted && sub.expiresAt > Date.now(); }
  private listenForAgent(agentId: string) {
    let listener = this.agentListeners.get(agentId);
    if (!listener) {
      listener = { count: 0, off: this.hub.onEvent(agentId, () => {
        for (const sub of this.subscriptions.values()) if (sub.agent.id === agentId) this.wake(sub);
      }) };
      this.agentListeners.set(agentId, listener);
    }
    listener.count++;
    return () => {
      if (--listener.count === 0) { listener.off(); this.agentListeners.delete(agentId); }
    };
  }
  private armExpiry(sub: Subscription) {
    if (sub.expiry) clearTimeout(sub.expiry);
    sub.expiry = setTimeout(() => this.remove(sub, "expired"), Math.max(0, sub.expiresAt - Date.now()));
    sub.expiry.unref();
  }
  private removeExpired() { for (const sub of this.subscriptions.values()) if (!this.live(sub)) this.remove(sub, "expired"); }
  private remove(sub: Subscription, reason: "expired" | "unsubscribed" | "server_stopped") {
    if (this.subscriptions.get(sub.key) !== sub) return;
    sub.abort.abort();
    clearTimeout(sub.expiry);
    sub.off();
    if (this.subscriptions.get(sub.key) === sub) this.subscriptions.delete(sub.key);
    this.debug?.record(reason === "expired" ? "subscription.expired" : "subscription.closed", { ...this.debugDetails(sub), reason });
  }
}

function grantTtl(suggested: number | null | undefined) {
  if (suggested == null) return DEFAULT_TTL_MS;
  if (!Number.isSafeInteger(suggested) || suggested < 0) throw new ProtocolError(-32602, "InvalidParams", { field: "ttlMs" });
  return Math.min(DEFAULT_TTL_MS, Math.max(MIN_TTL_MS, suggested));
}
export function decodeSecret(secret: string): Buffer {
  const encoded = secret.startsWith("whsec_") ? secret.slice(6) : "";
  const bytes = Buffer.from(encoded, "base64");
  if (!/^[A-Za-z0-9+/]+={0,2}$/.test(encoded) || bytes.length < 24 || bytes.length > 64 || bytes.toString("base64") !== encoded) {
    throw new ProtocolError(-32602, "InvalidParams", { field: "delivery.secret" });
  }
  return bytes;
}
function statusCategory(status: number): WebhookErrorCategory { return status >= 500 ? "http_5xx" : "http_4xx"; }
