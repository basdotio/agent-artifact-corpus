import { readFile } from "node:fs/promises";
import { join } from "node:path";
import type { RuntimeConfig } from "./types.js";

export class LocalApi {
  private constructor(
    private readonly baseUrl: string,
    private readonly token: string,
  ) {}

  static async connect(config: RuntimeConfig): Promise<LocalApi> {
    if (config.port === 0) throw new Error("CLI 不能连接配置为随机端口的节点");
    const token = (await readFile(join(config.dataDir, "admin-token"), "utf8")).trim();
    return new LocalApi(`http://127.0.0.1:${config.port}`, token);
  }

  get(path: string): Promise<unknown> {
    return this.request(path);
  }

  post(path: string, body: unknown = {}): Promise<unknown> {
    return this.request(path, "POST", body);
  }

  patch(path: string, body: unknown): Promise<unknown> {
    return this.request(path, "PATCH", body);
  }

  private async request(path: string, method = "GET", body?: unknown): Promise<unknown> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      redirect: "error",
      signal: AbortSignal.timeout(20_000),
      headers: {
        Authorization: `Bearer ${this.token}`,
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const text = await response.text();
    let value: unknown = {};
    if (text) {
      try { value = JSON.parse(text); } catch { throw new Error(`本机节点返回无效 JSON（HTTP ${response.status}）`); }
    }
    if (!response.ok) {
      const message = typeof value === "object" && value && "error" in value
        ? String((value as { error: unknown }).error)
        : `本机节点请求失败（HTTP ${response.status}）`;
      throw new Error(message);
    }
    return value;
  }
}
