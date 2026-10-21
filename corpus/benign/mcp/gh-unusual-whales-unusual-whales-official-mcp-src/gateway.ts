/**
 * API gateway with built-in throttling, circuit breaking, and retry logic.
 * All outbound HTTP traffic to the Unusual Whales API flows through here.
 */

const API_ORIGIN = "https://api.unusualwhales.com"
const REQUEST_TIMEOUT = 30_000
const WINDOW_DURATION = 60_000

function readEnvInt(name: string, fallback: number): number {
  const raw = process.env[name]
  if (!raw) return fallback
  const n = parseInt(raw, 10)
  return Number.isNaN(n) ? fallback : n
}

// ---------------------------------------------------------------------------
// Throttle – sliding-window rate limiter
// ---------------------------------------------------------------------------

class Throttle {
  private stamps: number[] = []

  constructor(
    private cap: number,
    private windowMs: number,
  ) {}

  acquire(): { allowed: boolean; retryAfterMs?: number } {
    const now = Date.now()
    while (this.stamps.length > 0 && now - this.stamps[0] >= this.windowMs) {
      this.stamps.shift()
    }
    if (this.stamps.length >= this.cap) {
      return { allowed: false, retryAfterMs: this.windowMs - (now - this.stamps[0]) }
    }
    this.stamps.push(now)
    return { allowed: true }
  }
}

// ---------------------------------------------------------------------------
// Breaker – circuit breaker with three phases
// ---------------------------------------------------------------------------

type BreakerPhase = "closed" | "open" | "probing"

class Breaker {
  private phase: BreakerPhase = "closed"
  private faults = 0
  private probeWins = 0
  private reopenAt = 0

  constructor(
    private tripAfter: number,
    private cooldownMs: number,
    private probeTarget: number,
  ) {}

  get snapshot(): { phase: BreakerPhase; faults: number } {
    return { phase: this.phase, faults: this.faults }
  }

  get msUntilProbe(): number {
    return Math.max(0, this.reopenAt - Date.now())
  }

  tick(): void {
    if (this.phase === "open" && Date.now() >= this.reopenAt) {
      this.phase = "probing"
      this.probeWins = 0
      emit("info", "breaker entering probe phase")
    }
  }

  ok(): void {
    if (this.phase === "probing") {
      this.probeWins++
      if (this.probeWins >= this.probeTarget) {
        this.phase = "closed"
        this.faults = 0
        this.probeWins = 0
        this.reopenAt = 0
        emit("info", "breaker closed")
      }
    } else if (this.phase === "closed" && this.faults > 0) {
      this.faults = 0
    }
  }

  fail(): void {
    this.faults++
    if (this.phase === "probing" || (this.phase === "closed" && this.faults >= this.tripAfter)) {
      this.phase = "open"
      this.reopenAt = Date.now() + this.cooldownMs
      this.probeWins = 0
      emit("warn", "breaker tripped", { faults: this.faults })
    }
  }
}

// ---------------------------------------------------------------------------
// Structured logger (writes JSON to stderr)
// ---------------------------------------------------------------------------

type Severity = "debug" | "info" | "warn" | "error"
const RANK: Record<Severity, number> = { debug: 0, info: 1, warn: 2, error: 3 }
const floor = RANK[(process.env.LOG_LEVEL as Severity) || "info"] ?? 1

function emit(severity: Severity, msg: string, extra?: Record<string, unknown>): void {
  if (RANK[severity] < floor) return
  const entry: Record<string, unknown> = { ts: new Date().toISOString(), severity, msg, ...extra }
  process.stderr.write(JSON.stringify(entry) + "\n")
}

export const log = {
  debug: (msg: string, data?: Record<string, unknown>): void => emit("debug", msg, data),
  info: (msg: string, data?: Record<string, unknown>): void => emit("info", msg, data),
  warn: (msg: string, data?: Record<string, unknown>): void => emit("warn", msg, data),
  error: (msg: string, data?: Record<string, unknown>): void => emit("error", msg, data),
}

// ---------------------------------------------------------------------------
// Shared instances
// ---------------------------------------------------------------------------

const throttle = new Throttle(
  readEnvInt("UW_RATE_LIMIT_PER_MINUTE", 120),
  WINDOW_DURATION,
)

const breaker = new Breaker(
  readEnvInt("UW_CIRCUIT_BREAKER_THRESHOLD", 5),
  readEnvInt("UW_CIRCUIT_BREAKER_RESET_TIMEOUT", 30000),
  readEnvInt("UW_CIRCUIT_BREAKER_SUCCESS_THRESHOLD", 2),
)

const maxAttempts = readEnvInt("UW_MAX_RETRIES", 3)

// ---------------------------------------------------------------------------
// Public helpers
// ---------------------------------------------------------------------------

export function breakerSnapshot(): { phase: string; faults: number } {
  return breaker.snapshot
}

export function sanitizeSegment(value: unknown): string {
  if (value === undefined || value === null) throw new Error("Path segment is required")
  const s = String(value)
  if (s.includes("/") || s.includes("\\") || s.includes("..")) throw new Error("Invalid path segment")
  return encodeURIComponent(s)
}

// ---------------------------------------------------------------------------
// Core request function
// ---------------------------------------------------------------------------

export interface GatewayResult<T = unknown> {
  payload?: T
  fault?: string
}

function pause(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function request<T = unknown>(
  route: string,
  query?: Record<string, string | number | boolean | string[] | undefined>,
): Promise<GatewayResult<T>> {
  const token = process.env.UW_API_KEY
  if (!token) return { fault: "UW_API_KEY environment variable is not set" }

  const slot = throttle.acquire()
  if (!slot.allowed) {
    return { fault: `Rate limit exceeded. Retry in ${Math.ceil((slot.retryAfterMs || 0) / 1000)}s.` }
  }

  const target = new URL(route, API_ORIGIN)
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null || v === "" || v === false) continue
      if (Array.isArray(v)) {
        for (const item of v) target.searchParams.append(k, String(item))
      } else {
        target.searchParams.append(k, String(v))
      }
    }
  }

  breaker.tick()
  if (breaker.snapshot.phase === "open") {
    const wait = Math.ceil(breaker.msUntilProbe / 1000)
    return { fault: `Service temporarily unavailable (circuit open). Retry in ~${wait}s.` }
  }

  let lastFault: string | null = null

  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    const ac = new AbortController()
    const timer = setTimeout(() => ac.abort(), REQUEST_TIMEOUT)

    try {
      const resp = await fetch(target.toString(), {
        method: "GET",
        headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
        signal: ac.signal,
      })
      clearTimeout(timer)

      if (resp.ok) {
        breaker.ok()
        const body = await resp.text()
        if (!body) return { payload: {} as T }
        try {
          return { payload: JSON.parse(body) as T }
        } catch {
          return { fault: `Malformed JSON: ${body.slice(0, 120)}` }
        }
      }

      if (resp.status === 429) {
        breaker.ok()
        const after = resp.headers.get("retry-after")
        return { fault: `Rate limited (429).${after ? ` Retry after ${after}s.` : ""} Approaching daily quota.` }
      }

      const errBody = await resp.text()
      lastFault = `HTTP ${resp.status}: ${errBody}`

      if (resp.status >= 400 && resp.status < 500) {
        breaker.ok()
        return { fault: lastFault }
      }

      if (attempt < maxAttempts - 1) {
        const delay = Math.pow(2, attempt) * 1000
        emit("warn", "retrying server error", { route, status: resp.status, attempt: attempt + 1, delay })
        await pause(delay)
        continue
      }
      breaker.fail()
    } catch (err) {
      clearTimeout(timer)
      const e = err instanceof Error ? err : new Error(String(err))
      lastFault = e.name === "AbortError" ? "Request timed out" : `Network error: ${e.message}`

      if (attempt < maxAttempts - 1) {
        const delay = Math.pow(2, attempt) * 1000
        emit("warn", "retrying network error", { route, error: e.message, attempt: attempt + 1, delay })
        await pause(delay)
        continue
      }
      breaker.fail()
    }
  }

  return { fault: lastFault ?? "All retry attempts exhausted" }
}

export function faultJson(msg: string): string {
  return JSON.stringify({ error: msg })
}
