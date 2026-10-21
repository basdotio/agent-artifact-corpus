import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync, rmSync, mkdirSync, existsSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import type { AddressInfo } from "node:net";
import { createServer } from "../server.js";
import { newRuntime, saveRuntime, removeRuntime, stopGateway, windowScript, setStartup, startupStatus, startupPath } from "../service.js";
import { eventLogPath, recordEvent, tailLines } from "../history.js";

test("managed stop requires a secret; stale runtime records cannot stop another instance", async () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-service-"));
  const previous = process.env.JEV_CONFIG_HOME;
  process.env.JEV_CONFIG_HOME = dir;
  const runtime = newRuntime(0);
  let stopped = 0;
  const server = createServer({ instanceId: runtime.instanceId, controlToken: runtime.token, onStop: () => { stopped++; }, quiet: true });
  try {
    await new Promise<void>(r => server.listen(0, "127.0.0.1", r));
    runtime.port = (server.address() as AddressInfo).port;
    saveRuntime(runtime);
    const url = `http://127.0.0.1:${runtime.port}`;
    const health = await (await fetch(`${url}/__jev/health`)).json();
    assert.doesNotMatch(JSON.stringify(health), new RegExp(runtime.token));
    assert.equal((await fetch(`${url}/__jev/stop`, { method: "POST" })).status, 403);
    assert.equal(stopped, 0);
    saveRuntime({ ...runtime, instanceId: "stale" });
    await assert.rejects(stopGateway(runtime.port), /ownership changed/);
    assert.equal(stopped, 0);
    saveRuntime(runtime);
    await stopGateway(runtime.port);
    assert.equal(stopped, 1);
    removeRuntime({ ...runtime, instanceId: "stale" });
    assert.ok(existsSync(join(dir, `gateway-${runtime.port}.json`)));
    removeRuntime(runtime);
    assert.equal(existsSync(join(dir, `gateway-${runtime.port}.json`)), false);
  } finally {
    await new Promise<void>(r => { server.close(() => r()); server.closeAllConnections(); });
    if (previous === undefined) delete process.env.JEV_CONFIG_HOME; else process.env.JEV_CONFIG_HOME = previous;
    rmSync(dir, { recursive: true, force: true });
  }
});

test("gateway history persists errors, rotates, and ignores incomplete tail records", () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-history-"));
  const previous = process.env.JEV_CONFIG_HOME;
  process.env.JEV_CONFIG_HOME = dir;
  try {
    recordEvent("codex", "A decision completed");
    recordEvent("vercel", "HTTP 400", true);
    const last = JSON.parse(tailLines(eventLogPath(), 1)[0]!);
    assert.equal(last.level, "error");
    assert.equal(last.message, "HTTP 400");
    writeFileSync(eventLogPath(), '{"message":"complete"}\n{"partial":');
    assert.deepEqual(tailLines(eventLogPath(), 50), ['{"message":"complete"}']);
    writeFileSync(eventLogPath(), "x".repeat(5 * 1024 * 1024 + 1));
    recordEvent("gateway", "New segment");
    assert.ok(existsSync(eventLogPath() + ".1"));
    assert.match(readFileSync(eventLogPath(), "utf8"), /New segment/);
  } finally {
    if (previous === undefined) delete process.env.JEV_CONFIG_HOME; else process.env.JEV_CONFIG_HOME = previous;
    rmSync(dir, { recursive: true, force: true });
  }
});

test("window launch scripts quote paths and arguments as literals", () => {
  const script = windowScript(["serve", "--foreground", "--log", "x'; $(bad); 'y"], "C:/space path", "C:/prefs", "C:/node.exe", "C:/cli.js");
  assert.match(script, /Set-Location -LiteralPath 'C:\/space path'/);
  assert.match(script, /'x''; \$\(bad\); ''y'/);
  assert.doesNotMatch(script, /API_KEY/);
});

test("Windows startup registration can be enabled, inspected and removed in an isolated user directory", async () => {
  if (process.platform !== "win32") return;
  const dir = mkdtempSync(join(tmpdir(), "jev-startup-"));
  const previous = { appdata: process.env.APPDATA, config: process.env.JEV_CONFIG_HOME };
  process.env.APPDATA = dir;
  process.env.JEV_CONFIG_HOME = join(dir, "config");
  try {
    mkdirSync(dirname(startupPath()), { recursive: true });
    assert.equal(startupStatus(), false);
    await setStartup(true);
    assert.equal(startupStatus(), true);
    assert.ok(statSync(startupPath()).size > 0);
    await setStartup(false);
    assert.equal(startupStatus(), false);
  } finally {
    if (previous.appdata === undefined) delete process.env.APPDATA; else process.env.APPDATA = previous.appdata;
    if (previous.config === undefined) delete process.env.JEV_CONFIG_HOME; else process.env.JEV_CONFIG_HOME = previous.config;
    rmSync(dir, { recursive: true, force: true });
  }
});
