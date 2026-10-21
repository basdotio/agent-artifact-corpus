import { lookup } from "node:dns/promises";
import { request as httpsRequest } from "node:https";
import { BlockList, isIP, type LookupFunction } from "node:net";
import { ProtocolError } from "@modelcontextprotocol/server";

export type WebhookErrorCategory = "connection_refused" | "timeout" | "tls_error" | "http_4xx" | "http_5xx" | "challenge_failed";
export type WebhookPostResult = { status: number; body: string };
export interface WebhookHttpClient {
  post(url: string, body: string, headers: Record<string, string>, signal: AbortSignal): Promise<WebhookPostResult>;
}
export class UnsafeWebhookAddressError extends Error {}

export function parseWebhookUrl(value: string): URL {
  let url: URL;
  try { url = new URL(value); } catch { throw invalidUrl(); }
  if (value.length > 2048 || url.protocol !== "https:" || url.username || url.password || url.hash || !url.hostname) throw invalidUrl();
  return url;
}
function invalidUrl() { return new ProtocolError(-32602, "InvalidParams", { field: "delivery.url" }); }

// Conservative public-address policy based on the IANA special-purpose registries.
// BlockList handles compressed/expanded IPv6 and IPv4-mapped encodings correctly.
const blocked = new BlockList();
for (const [address, prefix] of [
  ["0.0.0.0", 8], ["10.0.0.0", 8], ["100.64.0.0", 10], ["127.0.0.0", 8],
  ["169.254.0.0", 16], ["172.16.0.0", 12], ["192.0.0.0", 24], ["192.0.2.0", 24],
  ["192.88.99.0", 24], ["192.168.0.0", 16], ["198.18.0.0", 15],
  ["198.51.100.0", 24], ["203.0.113.0", 24], ["224.0.0.0", 3]
] as const) blocked.addSubnet(address, prefix, "ipv4");
for (const [address, prefix] of [
  ["2001::", 23], ["2001:db8::", 32], ["2002::", 16], ["3fff::", 20]
] as const) blocked.addSubnet(address, prefix, "ipv6");
const globalV6 = new BlockList();
globalV6.addSubnet("2000::", 3, "ipv6");

export function isGloballyRoutableIp(address: string): boolean {
  const family = isIP(address);
  if (family === 4) return !blocked.check(address, "ipv4");
  return family === 6 && globalV6.check(address, "ipv6") && !blocked.check(address, "ipv6");
}

export class SafeWebhookHttpClient implements WebhookHttpClient {
  async post(value: string, body: string, headers: Record<string, string>, parentSignal: AbortSignal): Promise<WebhookPostResult> {
    const url = parseWebhookUrl(value);
    const hostname = url.hostname.replace(/^\[|\]$/g, "");
    const timeout = new AbortController();
    const timer = setTimeout(() => timeout.abort(new DOMException("Webhook timed out", "TimeoutError")), 5000);
    timer.unref();
    const signal = AbortSignal.any([parentSignal, timeout.signal]);
    try {
      signal.throwIfAborted();
      const addresses = isIP(hostname)
        ? [{ address: hostname, family: isIP(hostname) }]
        : await abortable(lookup(hostname, { all: true, verbatim: true }), signal);
      // Re-resolve every attempt, reject mixed private/public answers, and pin the
      // checked address into a fresh socket. Never perform a second DNS lookup.
      if (!addresses.length || addresses.some(({ address }) => !isGloballyRoutableIp(address))) {
        throw new UnsafeWebhookAddressError("Callback address is not public");
      }
      const address = addresses.find((entry) => entry.family === 4) ?? addresses[0];
      const pinnedLookup: LookupFunction = (_host, options, callback) => {
        if (typeof options === "object" && options.all) {
          (callback as (error: null, entries: typeof addresses) => void)(null, [address]);
        } else callback(null, address.address, address.family);
      };
      return await new Promise<WebhookPostResult>((resolve, reject) => {
        const request = httpsRequest({
          hostname, port: url.port || undefined, path: `${url.pathname}${url.search}`,
          method: "POST", agent: false, signal, lookup: pinnedLookup,
          servername: isIP(hostname) ? undefined : hostname,
          headers: { ...headers, "Content-Length": String(Buffer.byteLength(body)) }
        }, (response) => {
          let size = 0;
          const chunks: Buffer[] = [];
          response.on("error", reject);
          response.on("aborted", () => reject(new Error("Callback response aborted")));
          response.on("data", (chunk: Buffer) => {
            size += chunk.length;
            if (size > 16 * 1024) request.destroy(new Error("Callback response too large"));
            else chunks.push(chunk);
          });
          response.on("end", () => resolve({ status: response.statusCode ?? 500, body: Buffer.concat(chunks).toString("utf8") }));
        });
        request.on("error", reject);
        request.end(body);
        // node:https does not follow redirects. The original hostname remains
        // the Host header and TLS verification/SNI target, not the pinned IP.
      });
    } catch (error) {
      if (timeout.signal.aborted) throw timeout.signal.reason;
      throw error;
    } finally { clearTimeout(timer); }
  }
}

export function classifyWebhookError(error: unknown): WebhookErrorCategory {
  const code = (error as NodeJS.ErrnoException)?.code ?? "";
  if ((error as Error)?.name === "TimeoutError" || code === "ETIMEDOUT") return "timeout";
  if (code.includes("CERT") || code.includes("TLS") || code.includes("SSL") || code === "DEPTH_ZERO_SELF_SIGNED_CERT") return "tls_error";
  return "connection_refused";
}

export function abortable<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise((resolve, reject) => {
    const abort = () => reject(signal.reason);
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) abort();
    promise.then(resolve, reject).finally(() => signal.removeEventListener("abort", abort));
  });
}

export function waitFor(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const done = () => { clearTimeout(timer); signal.removeEventListener("abort", done); resolve(); };
    const timer = setTimeout(done, ms);
    timer.unref();
    signal.addEventListener("abort", done, { once: true });
    if (signal.aborted) done();
  });
}
