import { createReadStream, existsSync } from "node:fs";
import { createServer as createHttpServer } from "node:http";
import { fileURLToPath } from "node:url";
import { logPath } from "./log.js";
const UI_FILE = fileURLToPath(new URL("../ui/index.html", import.meta.url));
export function ui(flags: {log?: string; port?: string}): void {
  if (flags.log) process.env.JEV_LOG = flags.log;
  const port = Number(flags.port ?? 8090);
  const file = logPath();
  createHttpServer((req, res) => {
    const path = (req.url ?? "/").split("?")[0];
    if (path === "/decisions.jsonl") {
      if (!existsSync(file)) {
        res.writeHead(200, { "content-type": "text/plain" });
        res.end("");
        return;
      }
      res.writeHead(200, { "content-type": "text/plain", "cache-control": "no-store" });
      createReadStream(file).pipe(res);
      return;
    }
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    createReadStream(UI_FILE).pipe(res);
  }).listen(port, "127.0.0.1", () => console.log(`jev-classifier ui on http://localhost:${port}  (reading ${file})`));
}

