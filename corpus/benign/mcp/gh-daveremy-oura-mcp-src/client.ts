import type {
  OuraApiResponse,
  OuraDailyActivity,
  OuraDailyReadiness,
  OuraDailySleep,
  OuraDailySpO2,
  OuraDailyStress,
  OuraHeartRate,
  OuraSession,
  OuraSleepPeriod,
  OuraTokens,
  OuraWorkout,
} from "./types.js";
import { loadConfig } from "./config.js";
import { nextDay } from "./utils.js";

export class OuraClient {
  private accessToken: string;
  private refreshToken: string;
  private clientId: string;
  private clientSecret: string;
  private baseUrl = "https://api.ouraring.com";
  private refreshPromise: Promise<void> | null = null;

  constructor(opts: {
    accessToken: string;
    refreshToken: string;
    clientId: string;
    clientSecret: string;
  }) {
    this.accessToken = opts.accessToken;
    this.refreshToken = opts.refreshToken;
    this.clientId = opts.clientId;
    this.clientSecret = opts.clientSecret;
  }

  /** Create client from environment variables, falling back to ~/.oura-mcp/config.json. */
  static fromEnv(): OuraClient {
    const config = loadConfig();

    // Environment OAuth vars take highest priority (explicit override)
    const envAccessToken = process.env.OURA_ACCESS_TOKEN;
    const envRefreshToken = process.env.OURA_REFRESH_TOKEN;
    if (envAccessToken && envRefreshToken) {
      const clientId = process.env.OURA_CLIENT_ID ?? config.clientId;
      const clientSecret = process.env.OURA_CLIENT_SECRET ?? config.clientSecret;
      if (!clientId || !clientSecret) {
        throw new Error("Missing OURA_CLIENT_ID or OURA_CLIENT_SECRET in environment.");
      }
      return new OuraClient({ accessToken: envAccessToken, refreshToken: envRefreshToken, clientId, clientSecret });
    }

    // Personal access token: env, then config file
    const pat = process.env.OURA_TOKEN ?? config.token;
    if (pat) {
      return new OuraClient({ accessToken: pat, refreshToken: "", clientId: "", clientSecret: "" });
    }

    throw new Error(
      "Missing OURA_TOKEN (personal access token) or OURA_ACCESS_TOKEN/OURA_REFRESH_TOKEN (OAuth).\n" +
      "Set via environment variable or run: oura config set-token <token>"
    );
  }

  private async request<T>(endpoint: string, params: Record<string, string> = {}): Promise<T> {
    const url = new URL(`${this.baseUrl}/${endpoint}`);
    for (const [k, v] of Object.entries(params)) {
      url.searchParams.set(k, v);
    }

    let res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${this.accessToken}` },
      signal: AbortSignal.timeout(30_000),
    });

    if (res.status === 401 && this.refreshToken) {
      await this.serializedRefresh();
      res = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${this.accessToken}` },
        signal: AbortSignal.timeout(30_000),
      });
    }

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Oura API ${res.status}: ${body}`);
    }

    return res.json() as Promise<T>;
  }

  private serializedRefresh(): Promise<void> {
    if (!this.refreshPromise) {
      this.refreshPromise = this.doRefresh().finally(() => {
        this.refreshPromise = null;
      });
    }
    return this.refreshPromise;
  }

  private async doRefresh(): Promise<void> {
    const res = await fetch(`${this.baseUrl}/oauth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: this.refreshToken,
        client_id: this.clientId,
        client_secret: this.clientSecret,
      }),
      signal: AbortSignal.timeout(30_000),
    });

    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Token refresh failed: ${body}`);
    }

    const tokens: OuraTokens = await res.json();
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    console.error("[oura] Token refreshed successfully.");
  }

  /**
   * Fetch one calendar day from a date-indexed collection.
   *
   * WHY THIS EXISTS: several Oura v2 collections treat `end_date` as
   * **exclusive**, so the natural `start_date == end_date` query silently
   * returns an empty array even when data exists. Verified against the live
   * API on 2026-07-29 for a complete day (2026-07-28):
   *
   * | endpoint          | start==end | padded +1 day |
   * |-------------------|-----------:|--------------:|
   * | `sleep`           |          0 |             2 |
   * | `workout`         |          0 |             2 |
   * | `daily_activity`  |          0 |             1 |
   * | `daily_sleep`     |          1 |             1 |
   * | `daily_readiness` |          1 |             1 |
   * | `daily_stress`    |          1 |             1 |
   * | `daily_spo2`      |          1 |             1 |
   *
   * The behaviour is inconsistent *per endpoint* — it is NOT simply
   * "`daily_*` are fine" — so rather than patching the known-broken three we
   * request `[date, date+1]` everywhere and filter client-side on `day`.
   * The filter makes padding a no-op for the already-inclusive endpoints
   * (identical results), and immunises us against Oura changing any single
   * endpoint's behaviour later.
   */
  private async requestDay<T extends { day?: string }>(
    endpoint: string,
    date: string
  ): Promise<T[]> {
    const res = await this.request<OuraApiResponse<T>>(endpoint, {
      start_date: date,
      end_date: nextDay(date),
    });
    return (res.data ?? []).filter((r) => r.day === date);
  }

  async getDailySleep(date: string): Promise<OuraDailySleep | null> {
    const data = await this.requestDay<OuraDailySleep>(
      "v2/usercollection/daily_sleep",
      date
    );
    return data[0] ?? null;
  }

  async getDailySleepRange(startDate: string, endDate: string): Promise<OuraDailySleep[]> {
    const res = await this.request<OuraApiResponse<OuraDailySleep>>(
      "v2/usercollection/daily_sleep",
      { start_date: startDate, end_date: endDate }
    );
    return res.data;
  }

  async getDailyReadiness(date: string): Promise<OuraDailyReadiness | null> {
    const data = await this.requestDay<OuraDailyReadiness>(
      "v2/usercollection/daily_readiness",
      date
    );
    return data[0] ?? null;
  }

  async getDailyReadinessRange(startDate: string, endDate: string): Promise<OuraDailyReadiness[]> {
    const res = await this.request<OuraApiResponse<OuraDailyReadiness>>(
      "v2/usercollection/daily_readiness",
      { start_date: startDate, end_date: endDate }
    );
    return res.data;
  }

  async getSleepPeriods(date: string): Promise<OuraSleepPeriod[]> {
    return this.requestDay<OuraSleepPeriod>("v2/usercollection/sleep", date);
  }

  async getDailyActivity(date: string): Promise<OuraDailyActivity | null> {
    const data = await this.requestDay<OuraDailyActivity>(
      "v2/usercollection/daily_activity",
      date
    );
    return data[0] ?? null;
  }

  async getWorkouts(date: string): Promise<OuraWorkout[]> {
    return this.requestDay<OuraWorkout>("v2/usercollection/workout", date);
  }

  async getHeartRate(startDatetime: string, endDatetime: string): Promise<OuraHeartRate[]> {
    const res = await this.request<OuraApiResponse<OuraHeartRate>>(
      "v2/usercollection/heartrate",
      { start_datetime: startDatetime, end_datetime: endDatetime }
    );
    return res.data;
  }

  async getDailyStress(date: string): Promise<OuraDailyStress | null> {
    const data = await this.requestDay<OuraDailyStress>(
      "v2/usercollection/daily_stress",
      date
    );
    return data[0] ?? null;
  }

  async getDailySpO2(date: string): Promise<OuraDailySpO2 | null> {
    const data = await this.requestDay<OuraDailySpO2>(
      "v2/usercollection/daily_spo2",
      date
    );
    return data[0] ?? null;
  }

  async getSessions(date: string): Promise<OuraSession[]> {
    return this.requestDay<OuraSession>("v2/usercollection/session", date);
  }
}
