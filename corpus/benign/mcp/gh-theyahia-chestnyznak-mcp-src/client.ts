// HTTP client for the two Chestny ZNAK / CRPT APIs this server wraps:
//   * Public mobile-app endpoint  (no auth)  — https://mobile.api.crpt.ru/mobile
//   * Authenticated "True API" (ГИС МТ)        — https://markirovka.crpt.ru/api/v3
//
// NOTE on the authenticated half: the real True API auth is a certificate-challenge
// flow (GET /auth/key → sign `data` with a УКЭП/GOST CAdES-BES signature →
// POST /auth/simpleSignIn → short-lived ~10h JWT). A static long-lived Bearer token
// is NOT how it works. This client therefore treats CHESTNYZNAK_TOKEN as an
// *externally minted* token (you obtain/refresh it via the cert flow yourself) and
// sends it as `Authorization: Bearer`. See README "Авторизация".

const PUBLIC_BASE_URL =
  process.env.CHESTNYZNAK_PUBLIC_BASE_URL ?? "https://mobile.api.crpt.ru/mobile";

// Core True API methods live under /api/v3; some newer methods (e.g. product/info)
// use /api/v4. Paths passed to crptAuth* include the version-specific prefix.
const DEFAULT_AUTH_BASE_URL = "https://markirovka.crpt.ru";

const TIMEOUT = 10_000;
const MAX_RETRIES = 3;

/** Exponential backoff between retries (1s, 2s, …, capped at 8s). */
function backoff(attempt: number): Promise<void> {
  const delay = Math.min(1000 * 2 ** (attempt - 1), 8000);
  return new Promise((r) => setTimeout(r, delay));
}

// Real OSS clients of the public mobile endpoint send app-mimic headers; a bare
// server User-Agent is more likely to be blocked (403). This is best-effort.
const PUBLIC_HEADERS: Record<string, string> = {
  "User-Agent": "Chestnyznak/4.47.0 (chestnyznak-mcp)",
};

function getToken(): string | undefined {
  return process.env.CHESTNYZNAK_TOKEN;
}

/**
 * Resolve the authenticated API base URL, validating any CHESTNYZNAK_BASE_URL
 * override. The Bearer token is attached to every authenticated request, so an
 * unvalidated override would leak the token to an arbitrary host (SSRF). We only
 * allow https hosts under the crpt.ru / crptech.ru (sandbox) suffixes.
 */
export function getAuthBaseUrl(): string {
  const override = process.env.CHESTNYZNAK_BASE_URL;
  if (!override) return DEFAULT_AUTH_BASE_URL;

  let url: URL;
  try {
    url = new URL(override);
  } catch {
    throw new Error(`CHESTNYZNAK_BASE_URL не является корректным URL: ${override}`);
  }
  const host = url.hostname.toLowerCase();
  const allowed =
    url.protocol === "https:" &&
    (host === "crpt.ru" ||
      host.endsWith(".crpt.ru") ||
      host === "crptech.ru" ||
      host.endsWith(".crptech.ru"));
  if (!allowed) {
    throw new Error(
      `CHESTNYZNAK_BASE_URL отклонён (ожидается https и хост *.crpt.ru/*.crptech.ru): ${override}`,
    );
  }
  return url.origin;
}

function isRetryable(error: unknown, attempt: number): boolean {
  if (attempt >= MAX_RETRIES) return false;
  // Request timeout (AbortController) or a transient network failure (fetch throws
  // a TypeError on DNS/TCP errors) — both are worth retrying.
  if (error instanceof DOMException && error.name === "AbortError") return true;
  if (error instanceof TypeError) return true;
  return false;
}

async function request(
  url: string,
  method: "GET" | "POST",
  body: unknown | undefined,
  token?: string,
  extraHeaders?: Record<string, string>,
): Promise<unknown> {
  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT);

    try {
      const headers: Record<string, string> = {
        Accept: "application/json",
        ...extraHeaders,
      };
      if (body !== undefined) headers["Content-Type"] = "application/json";
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      clearTimeout(timer);

      if (response.ok) return parseJson(response, url);

      if ((response.status === 429 || response.status >= 500) && attempt < MAX_RETRIES) {
        await backoff(attempt);
        continue;
      }

      throw new Error(`Честный ЗНАК HTTP ${response.status}: ${response.statusText}`);
    } catch (error) {
      clearTimeout(timer);
      if (isRetryable(error, attempt)) {
        await backoff(attempt);
        continue;
      }
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new Error(
          `Честный ЗНАК: таймаут запроса (${TIMEOUT} мс) после ${MAX_RETRIES} попыток`,
        );
      }
      throw error;
    }
  }
  throw new Error("Честный ЗНАК: все попытки исчерпаны");
}

/** Parse a successful response as JSON, with a readable error on non-JSON bodies. */
async function parseJson(response: Response, url: string): Promise<unknown> {
  const text = await response.text();
  if (text.trim() === "") return {};
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(
      `Честный ЗНАК: некорректный JSON от ${url} (тело: ${text.slice(0, 200)})`,
    );
  }
}

/** Public API (no auth), GET with query string. */
export async function crptPublicGet(path: string): Promise<unknown> {
  return request(`${PUBLIC_BASE_URL}${path}`, "GET", undefined, undefined, PUBLIC_HEADERS);
}

/** Authenticated True API, GET. */
export async function crptAuthGet(path: string): Promise<unknown> {
  const token = requireToken();
  return request(`${getAuthBaseUrl()}${path}`, "GET", undefined, token);
}

/** Authenticated True API, POST. */
export async function crptAuthPost(path: string, body: unknown): Promise<unknown> {
  const token = requireToken();
  return request(`${getAuthBaseUrl()}${path}`, "POST", body, token);
}

function requireToken(): string {
  const token = getToken();
  if (!token) {
    throw new Error(
      "CHESTNYZNAK_TOKEN не задан — этот инструмент доступен только с авторизацией. " +
        "Установите переменную окружения CHESTNYZNAK_TOKEN.",
    );
  }
  return token;
}

export function hasToken(): boolean {
  return !!getToken();
}
