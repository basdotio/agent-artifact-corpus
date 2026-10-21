import type { Config } from "./config.js";

interface TokenState {
  token: string;
  // epoch(ms) 이후에는 만료로 간주하고 재발급
  expiresAt: number;
}

let cached: TokenState | null = null;

/**
 * 접근 토큰 발급. NH Open API 규약:
 *   POST {BASE_URL}/oauth2/token
 *   query: appkey, appsecretkey, grant_type=client_credentials, scope=oob
 *   content-type: application/x-www-form-urlencoded
 *   → { access_token, expires_in?, ... }
 * 발급된 토큰은 만료 전까지 메모리에 캐시합니다.
 */
export async function getAccessToken(config: Config, force = false): Promise<string> {
  const now = Date.now();
  if (!force && cached && cached.expiresAt > now + 30_000) {
    return cached.token;
  }

  const url = new URL(`${config.authUrl}/oauth2/token`);
  url.searchParams.set("appkey", config.appKey);
  url.searchParams.set("appsecretkey", config.appSecret);
  url.searchParams.set("grant_type", "client_credentials");
  url.searchParams.set("scope", "oob");

  let lastErr = "";
  // 토큰 발급 일시장애(IGW40054 등)에는 짧게 재시도. 유효하지 않은 AppKey(IGW40031)는 즉시 중단.
  for (let attempt = 0; attempt < 3; attempt++) {
    let res: Response;
    try {
      res = await fetch(url.toString(), {
        method: "POST",
        headers: { "content-type": "application/x-www-form-urlencoded" },
      });
    } catch (e) {
      lastErr = `네트워크 오류 — ${String(e)}`;
      await new Promise((r) => setTimeout(r, 300 * (attempt + 1)));
      continue;
    }

    const text = await res.text();
    if (res.ok) {
      let data: any;
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error(`토큰 응답이 JSON 이 아닙니다: ${text.slice(0, 300)}`);
      }
      const token: string | undefined = data.access_token ?? data.accessToken;
      if (!token) {
        throw new Error(`토큰 응답에 access_token 이 없습니다: ${text.slice(0, 300)}`);
      }
      // expires_in(초)이 오면 사용, 없으면 24h. 무효 응답 시 client 의 자동 재발급이 안전망.
      const expiresInSec = Number(data.expires_in ?? data.expiresIn ?? 86400);
      cached = {
        token,
        expiresAt: now + (Number.isFinite(expiresInSec) ? expiresInSec : 86400) * 1000,
      };
      return token;
    }

    lastErr = `HTTP ${res.status} — ${text.slice(0, 300)}`;
    // 일시장애면 재시도, 그 외(키 오류 등)는 즉시 실패
    if (text.includes("IGW40054") && attempt < 2) {
      await new Promise((r) => setTimeout(r, 400 * (attempt + 1)));
      continue;
    }
    throw new Error(`토큰 발급 실패 (인증서버 ${config.authUrl}, 운영 전용): ${lastErr}`);
  }
  throw new Error(`토큰 발급 실패 (재시도 후에도): ${lastErr}`);
}

/** 테스트/디버그용: 토큰 캐시 강제 초기화 */
export function clearTokenCache(): void {
  cached = null;
}
