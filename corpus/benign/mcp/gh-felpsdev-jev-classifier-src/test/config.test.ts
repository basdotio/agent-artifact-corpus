import assert from "node:assert/strict";
import { test } from "node:test";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { agentConfig } from "../config.js";
import { routeUpstream } from "../upstream.js";

const cli = fileURLToPath(new URL("../cli.js", import.meta.url));

test("CLI prints session config whose base reaches the Codex subscription service", () => {
  const result = spawnSync(process.execPath, [cli, "config", "codex", "--port", "8123"], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /requires_openai_auth = true/);
  assert.doesNotMatch(result.stdout, /^env_key\s*=/m);
  assert.match(result.stdout, /supports_websockets = false/);
  const url = new URL(/base_url = "([^"]+)"/.exec(result.stdout)![1]!);
  assert.equal(url.port, "8123");
  const route = routeUpstream(`${url.pathname}/responses`);
  assert.equal(route.preserveAuth, true);
  assert.equal(route.adapter?.agent, "openai-responses");
});

test("OAuth setup uses native Claude and Grok login without supplying a replacement key", () => {
  const claude = agentConfig("claude", "oauth", "powershell", 8080);
  assert.match(claude, /\$env:ANTHROPIC_BASE_URL = "http:\/\/127\.0\.0\.1:8080\/oauth\/claude"/);
  assert.doesNotMatch(claude, /\$env:ANTHROPIC_API_KEY\s*=/);
  const grok = agentConfig("grok", "oauth", "bash", 8080);
  assert.match(grok, /grok login/);
  assert.match(grok, /export GROK_CLI_CHAT_PROXY_BASE_URL="http:\/\/127\.0\.0\.1:8080\/oauth\/grok\/v1"/);
  assert.doesNotMatch(grok, /export XAI_API_KEY=/);
});

test("API-key configuration stays separate and invalid config options fail", () => {
  const codex = agentConfig("codex", "api-key", "bash", 8080);
  assert.match(codex, /env_key = "OPENAI_API_KEY"/);
  assert.match(codex, /\/api\/codex\/v1/);
  assert.doesNotMatch(codex, /requires_openai_auth = true/);
  const result = spawnSync(process.execPath, [cli, "config", "grok", "--auth", "invalid"], { encoding: "utf8" });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Auth must be/);
  assert.throws(() => agentConfig("claude", "oauth", "powershell", NaN), /Port must/);
});
