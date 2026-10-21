import { readFileSync } from "node:fs";

/**
 * Single source of truth for the version. Read from `package.json` (always
 * shipped in the npm tarball, one level up from `dist/`) so the CLI
 * `--version`, the `--help` banner, and the API User-Agent can never drift
 * from the published package version. Falls back to "0.0.0" if it can't be
 * read (e.g. an unusual bundling setup) rather than crashing.
 */
function readVersion(): string {
  try {
    const pkg = JSON.parse(
      readFileSync(new URL("../package.json", import.meta.url), "utf8"),
    ) as { version?: string };
    return pkg.version ?? "0.0.0";
  } catch {
    return "0.0.0";
  }
}

export const VERSION = readVersion();
const REPO = "https://github.com/tobiasosDev/citecheck";

/**
 * Contact address for the CrossRef / OpenAlex "polite pool" (faster, more
 * reliable rate limits). Opt-in via `CITECHECK_MAILTO` or the CLI `--mailto`
 * flag. Never defaults to a hardcoded address — your traffic is yours.
 */
export function politeMailto(): string | undefined {
  const m = process.env.CITECHECK_MAILTO?.trim();
  return m && m.includes("@") ? m : undefined;
}

export function userAgent(): string {
  const mailto = politeMailto();
  return `citecheck/${VERSION} (+${REPO}${mailto ? `; mailto:${mailto}` : ""})`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}

export interface FetchOpts {
  headers?: Record<string, string>;
  timeoutMs?: number;
  retries?: number;
}

/** Upper bound on how long a single Retry-After instruction may stall us. */
const RETRY_AFTER_CAP_MS = 30_000;

/**
 * Shared per-host cooldown. When one request gets a 429, EVERY in-flight and
 * queued request to that host must back off together — otherwise a batch of
 * parallel reference checks retries into the same rate-limit window and the
 * whole batch dies as check_failed (the exact failure mode observed against
 * Crossref's anonymous pool).
 */
const hostCooldownUntil = new Map<string, number>();

/** Test hook: clear cooldown state between test cases. */
export function resetHostCooldowns(): void {
  hostCooldownUntil.clear();
}

/**
 * Parse a Retry-After header (delta-seconds or HTTP-date) into milliseconds,
 * capped at RETRY_AFTER_CAP_MS. Returns undefined when absent or unparseable.
 */
export function parseRetryAfterMs(res: Response): number | undefined {
  const h = res.headers.get("retry-after");
  if (!h) return undefined;
  const secs = Number(h);
  if (Number.isFinite(secs) && secs >= 0) return Math.min(secs * 1000, RETRY_AFTER_CAP_MS);
  const date = Date.parse(h);
  if (!Number.isNaN(date)) return Math.min(Math.max(date - Date.now(), 0), RETRY_AFTER_CAP_MS);
  return undefined;
}

function noteCooldown(host: string, ms: number): void {
  const until = Date.now() + ms;
  if (until > (hostCooldownUntil.get(host) ?? 0)) hostCooldownUntil.set(host, until);
}

async function awaitCooldown(host: string): Promise<void> {
  // Re-check after sleeping: another 429 may have extended the window while we
  // waited, and honoring the extension is the whole point of the shared gate.
  for (;;) {
    const wait = (hostCooldownUntil.get(host) ?? 0) - Date.now();
    if (wait <= 0) return;
    await sleep(wait);
  }
}

/**
 * `fetch` with retry on *transient* failures (HTTP 429, 5xx, network errors,
 * timeouts). After the retries are exhausted on a transient failure it THROWS,
 * so callers can tell "couldn't reach the API" apart from a definitive answer.
 * A clean response — including a definitive 4xx like 404 — is returned as-is for
 * the caller to interpret.
 *
 * 429 handling honors the server's Retry-After (falling back to backoff) and
 * shares the wait across all requests to the same host, with a little jitter so
 * a released batch does not stampede back in lockstep.
 */
export async function fetchRetry(url: string, opts: FetchOpts = {}): Promise<Response> {
  const { headers, timeoutMs = 10_000, retries = 2 } = opts;
  const host = new URL(url).host;
  let lastErr: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    await awaitCooldown(host);
    try {
      const res = await fetch(url, { headers, signal: AbortSignal.timeout(timeoutMs) });
      if (res.status === 429 || res.status >= 500) {
        lastErr = new Error(`transient HTTP ${res.status}`);
        if (res.status === 429) {
          const ra = parseRetryAfterMs(res) ?? 300 * (attempt + 1) ** 2;
          noteCooldown(host, ra + Math.random() * 300);
          if (attempt < retries) continue; // top of loop awaits the cooldown
        } else if (attempt < retries) {
          await sleep(300 * (attempt + 1) ** 2);
          continue;
        }
        throw lastErr;
      }
      return res;
    } catch (e) {
      lastErr = e;
      if (attempt < retries) {
        await sleep(300 * (attempt + 1) ** 2);
        continue;
      }
      throw lastErr;
    }
  }
  throw lastErr;
}
