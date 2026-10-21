import test from "node:test";
import assert from "node:assert/strict";
import { createServer as http, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { createServer } from "../server.js";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

async function listen(server: Server): Promise<string> {
  await new Promise<void>(r => server.listen(0, "127.0.0.1", r));
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}
async function close(server: Server): Promise<void> {
  await new Promise<void>(r => { server.close(() => r()); server.closeAllConnections(); });
}

test("disconnecting the agent cancels the upstream response instead of leaving it running", async () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-lifecycle-"));
  const previousHome = process.env.JEV_CONFIG_HOME;
  process.env.JEV_CONFIG_HOME = dir;
  let disconnected!: () => void;
  const remoteClosed = new Promise<void>(r => { disconnected = r; });
  const remote = http((req, res) => {
    req.resume();
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.write('data: {"type":"response.created"}\n\n');
    res.once("close", disconnected);
  });
  const previous = process.env.CODEX_OAUTH_UPSTREAM;
  const proxy = createServer({ quiet: true });
  let timeout: ReturnType<typeof setTimeout> | undefined;
  try {
    process.env.CODEX_OAUTH_UPSTREAM = await listen(remote);
    const base = await listen(proxy);
    const controller = new AbortController();
    const response = await fetch(`${base}/oauth/codex/responses`, { method: "POST", body: '{"input":"hello"}', signal: controller.signal });
    assert.equal(response.status, 200);
    await response.body!.getReader().read();
    controller.abort();
    await Promise.race([remoteClosed, new Promise((_, reject) => { timeout = setTimeout(() => reject(new Error("Upstream remained connected")), 1500); })]);
  } finally {
    clearTimeout(timeout);
    if (previous === undefined) delete process.env.CODEX_OAUTH_UPSTREAM; else process.env.CODEX_OAUTH_UPSTREAM = previous;
    await Promise.all([close(proxy), close(remote)]);
    if (previousHome === undefined) delete process.env.JEV_CONFIG_HOME; else process.env.JEV_CONFIG_HOME = previousHome;
    rmSync(dir, { recursive: true, force: true });
  }
});
