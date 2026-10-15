// Jev クライアント (同梱版)。~/.claude/shared/jev/jev.mjs と同じ内容。キーの読み方: 環境変数 TYPESAFE_API_KEY、無ければ ~/.config/typesafe/credentials.json の api_key
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

export const DEFAULT_ENDPOINT = "https://api.typesafe.ai/v1/systemone";

export class JevError extends Error {
  // code: "no-key" | "http" | "network" | "timeout" | "bad-response"
  // status: HTTP ステータス(無ければ 0)
  constructor(message, { code, status = 0 }) {
    super(message);
    this.name = "JevError";
    this.code = code;
    this.status = status;
  }
}

// 1.0 節の順で探す。無ければ null
export function getApiKey(env = process.env) {
  const fromEnv = env.TYPESAFE_API_KEY;
  if (fromEnv) return fromEnv;
  const path = env.TYPESAFE_CREDENTIALS_FILE || join(homedir(), ".config", "typesafe", "credentials.json");
  try {
    const data = JSON.parse(readFileSync(path, "utf8"));
    const key = data && typeof data === "object" ? data.api_key : null;
    return typeof key === "string" && key ? key : null;
  } catch {
    return null;
  }
}

function retryWaitMs(retryAfter, n) {
  let seconds = retryAfter == null || retryAfter === "" ? NaN : Number(retryAfter);
  if (!Number.isFinite(seconds) || seconds < 0) seconds = 2 ** n;
  return Math.min(seconds, 30) * 1000;
}

// 応答 JSON(オブジェクト)を返す。失敗は JevError を投げる
export async function callJev({ state, questions, model, endpoint = DEFAULT_ENDPOINT,
  apiKey = getApiKey(), timeoutMs = 120000, maxRetries = 3,
  sleep = (ms) => new Promise((r) => setTimeout(r, ms)) }) {
  if (!apiKey) throw new JevError("Jev の API キーが見つからない", { code: "no-key" });
  const body = JSON.stringify({ state, model, questions });
  const headers = { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" };

  let rateRetries = 0;
  let otherRetried = false;
  for (;;) {
    let res;
    try {
      res = await fetch(endpoint, { method: "POST", headers, body, signal: AbortSignal.timeout(timeoutMs) });
    } catch (e) {
      const isTimeout = e?.name === "TimeoutError";
      const err = new JevError(`${isTimeout ? "タイムアウト" : "接続エラー"}: ${e?.message ?? e}`,
        { code: isTimeout ? "timeout" : "network" });
      if (!otherRetried) { otherRetried = true; continue; }
      throw err;
    }
    let text;
    try {
      text = await res.text();
    } catch (e) {
      const isTimeout = e?.name === "TimeoutError";
      const err = new JevError(`${isTimeout ? "タイムアウト" : "接続エラー"}: ${e?.message ?? e}`,
        { code: isTimeout ? "timeout" : "network" });
      if (!otherRetried) { otherRetried = true; continue; }
      throw err;
    }
    const status = res.status;
    if (status >= 200 && status < 300) {
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        throw new JevError(`応答が JSON でない: ${text.slice(0, 500)}`, { code: "bad-response", status });
      }
      const answers = data && typeof data === "object" ? data.answers : null;
      if (!answers || typeof answers !== "object" || Array.isArray(answers)) {
        throw new JevError(`応答に answers が無い: ${text.slice(0, 500)}`, { code: "bad-response", status });
      }
      return data;
    }
    const err = new JevError(`HTTP ${status}: ${text.slice(0, 500)}`, { code: "http", status });
    if (status === 429 || status === 529) {
      if (rateRetries < maxRetries) {
        await sleep(retryWaitMs(res.headers.get("retry-after"), rateRetries));
        rateRetries += 1;
        continue;
      }
      throw err;
    }
    if (status >= 500 && status <= 599 && !otherRetried) { otherRetried = true; continue; }
    throw err;
  }
}
