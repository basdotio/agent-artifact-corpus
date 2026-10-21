import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { connectEditor, mcpConfig, openCodeRuntime } from "../integrations.js";
import { routeUpstream } from "../upstream.js";
import { launchPlan } from "../agents.js";
import { startupContents, startupPath, shQuote } from "../service.js";

test("editor connection preserves other servers, backs up once, and refuses invalid JSON", () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-editor-"));
  try {
    const file = join(dir, "mcp.json");
    const original = JSON.stringify({ mcpServers: { existing: { command: "existing" } }, preference: true });
    writeFileSync(file, original);
    const result = connectEditor("cursor", file);
    assert.equal(readFileSync(result.backup!, "utf8"), original);
    const saved = JSON.parse(readFileSync(file, "utf8"));
    assert.equal(saved.mcpServers.existing.command, "existing");
    assert.equal(saved.preference, true);
    assert.equal(saved.mcpServers["jev-classifier"].command, process.execPath);
    assert.equal(connectEditor("cursor", file).backup, undefined);
    for (const invalid of ["{", "null", '{"mcpServers":[]}']) {
      writeFileSync(file, invalid);
      assert.throws(() => connectEditor("antigravity", file));
      assert.equal(readFileSync(file, "utf8"), invalid);
    }
    assert.doesNotMatch(JSON.stringify(mcpConfig("antigravity")), /API_KEY/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test("OpenCode overlays only supported API endpoints and keeps unrelated configuration", () => {
  const inherited = { model: "openai/a-model", provider: { openai: { models: { custom: {} }, options: { apiKey: "agent-key", baseURL: "old" } }, other: { options: { baseURL: "untouched" } } } };
  const result = JSON.parse(openCodeRuntime(8123, JSON.stringify(inherited)));
  assert.equal(result.model, inherited.model);
  assert.deepEqual(result.provider.openai.models, inherited.provider.openai.models);
  assert.equal(result.provider.openai.options.apiKey, "agent-key");
  assert.equal(result.provider.openai.options.baseURL, "http://127.0.0.1:8123/clients/opencode/api/codex/v1");
  assert.equal(result.provider.other.options.baseURL, "untouched");
  const plan = launchPlan("opencode", "api-key", 8123, { JEV_API_KEY: "classifier-only" });
  assert.equal(plan.env.JEV_API_KEY, undefined);
  assert.ok(plan.env.OPENCODE_CONFIG_CONTENT);
  assert.throws(() => launchPlan("opencode", "oauth", 8123), /subscription plugins/);
  assert.throws(() => openCodeRuntime(8123, "null"), /object/);
});

test("OpenCode routes preserve protocol selection and client attribution", () => {
  for (const [provider, path, protocol] of [["codex", "responses", "openai-responses"], ["codex", "chat/completions", "openai-chat"], ["claude", "messages", "anthropic"], ["grok", "chat/completions", "openai-chat"]]) {
    const result = routeUpstream(`/clients/opencode/api/${provider}/v1/${path}`);
    assert.equal(result.client, "opencode");
    assert.equal(result.adapter?.agent, protocol);
    assert.equal(result.preserveAuth, false);
  }
  assert.throws(() => routeUpstream("/clients/opencode/oauth/codex/responses"));
  assert.throws(() => routeUpstream("/clients/unknown/api/codex/v1/responses"));
});

test("startup files use per-user paths and encode special path characters", () => {
  assert.equal(startupPath("linux", { XDG_CONFIG_HOME: "/prefs" }, "/user"), join("/prefs", "autostart", "jev-classifier.desktop"));
  assert.equal(startupPath("darwin", {}, "/user"), join("/user", "Library", "LaunchAgents", "ai.jev.classifier.plist"));
  const plist = startupContents("darwin", "/user/A&B", "/node path/node", "/code/<cli>.js");
  assert.match(plist, /A&amp;B/);
  assert.match(plist, /&lt;cli&gt;/);
  assert.match(plist, /<key>RunAtLoad<\/key><true\/>/);
  const desktop = startupContents("linux", "/user/100% $test", "/node path/node", "/code/cli.js");
  assert.match(desktop, /100%%/);
  assert.ok(desktop.includes('"/node path/node"'));
  assert.ok(desktop.includes('\\\\$test'));
  assert.doesNotMatch(plist + desktop, /API_KEY/);
  assert.equal(shQuote("it's $(literal)"), "'it'\"'\"'s $(literal)'");
});

test("real MCP stdio handshake, advice, validation and persistent history", async () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-mcp-"));
  const transport = new StdioClientTransport({ command: process.execPath,
    args: [fileURLToPath(new URL("../cli.js", import.meta.url)), "mcp", "--global", "--client", "antigravity"],
    env: { ...Object.fromEntries(Object.entries(process.env).filter((e): e is [string, string] => e[1] !== undefined)),
      JEV_CONFIG_HOME: dir, JEV_LOG: join(dir, "decisions.jsonl"), JEV_STUB: "1" }, stderr: "pipe" });
  const client = new Client({ name: "integration-test", version: "1.0.0" });
  try {
    await client.connect(transport);
    assert.equal((await client.listTools()).tools.length, 2);
    const status = await client.callTool({ name: "jev_status", arguments: {} });
    assert.match(JSON.stringify(status), /mcp-advisory/);
    const result = await client.callTool({ name: "jev_choose_next_tool", arguments: { user_request: "Read a file", tools: [{ name: "read_file" }] } });
    assert.equal(result.isError, undefined);
    assert.match(JSON.stringify(result), /read_file/);
    const invalid = await client.callTool({ name: "jev_choose_next_tool", arguments: { user_request: "Read", tools: [{ name: "respond_to_user" }] } });
    assert.equal(invalid.isError, true);
    const decision = JSON.parse(readFileSync(join(dir, "decisions.jsonl"), "utf8").trim());
    assert.equal(decision.agent, "antigravity");
    assert.equal(decision.applied, false);
    assert.equal(decision.mode, "shadow");
    assert.match(readFileSync(join(dir, "gateway.jsonl"), "utf8"), /MCP recommendation/);
  } finally { await client.close(); rmSync(dir, { recursive: true, force: true }); }
});
