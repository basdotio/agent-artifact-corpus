import { appendFile, mkdir, readFile } from "node:fs/promises";
import { dirname } from "node:path";

export class AuditLog {
  constructor(readonly path: string) {}

  async record(event: string, data: Record<string, unknown> = {}): Promise<void> {
    await mkdir(dirname(this.path), { recursive: true });
    const line = JSON.stringify({ timestamp: new Date().toISOString(), event, ...data });
    await appendFile(this.path, `${line}\n`, { encoding: "utf8", mode: 0o600 });
  }

  async tail(limit = 50): Promise<string[]> {
    try {
      return (await readFile(this.path, "utf8")).trim().split(/\r?\n/).filter(Boolean).slice(-limit);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
      throw error;
    }
  }
}
