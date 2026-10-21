import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { directLaunchPlan } from "../agents.js";
import { readSettings, saveSettings, SETTING_KEYS, validateSettings } from "../settings.js";

test("direct launches remove inherited Jev endpoints while preserving credentials and unrelated providers", () => {
  const inherited = {
    ANTHROPIC_BASE_URL: "http://127.0.0.1:9191/oauth/claude",
    OPENAI_BASE_URL: "http://localhost:8080/api/codex/v1",
    GROK_CLI_CHAT_PROXY_BASE_URL: "http://[::1]:8181/oauth/grok/v1",
    GROK_MODELS_BASE_URL: "https://custom.example/v1",
    ANTHROPIC_API_KEY: "agent-key", ANTHROPIC_AUTH_TOKEN: "agent-token",
    OPENAI_API_KEY: "openai-key", XAI_API_KEY: "xai-key", OPENROUTER_API_KEY: "native-provider-key",
    JEV_API_KEY: "classifier-secret", UPSTREAM_API_KEY: "upstream-secret", CODEX_HOME: "custom-home",
  };
  for (const agent of ["claude", "codex", "grok", "opencode"]) {
    const plan = directLaunchPlan(agent, inherited);
    assert.equal(plan.env.ANTHROPIC_BASE_URL, undefined);
    assert.equal(plan.env.OPENAI_BASE_URL, undefined);
    assert.equal(plan.env.GROK_CLI_CHAT_PROXY_BASE_URL, undefined);
    assert.equal(plan.env.GROK_MODELS_BASE_URL, inherited.GROK_MODELS_BASE_URL);
    for (const key of ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "XAI_API_KEY", "OPENROUTER_API_KEY", "CODEX_HOME"] as const) {
      assert.equal(plan.env[key], inherited[key]);
    }
    assert.equal(plan.env.JEV_API_KEY, undefined);
    assert.equal(plan.env.UPSTREAM_API_KEY, undefined);
    assert.equal(plan.url, "");
    assert.deepEqual(plan.args, agent === "codex" ? ["-c", 'model_provider="openai"'] : []);
    assert.doesNotThrow(() => directLaunchPlan(agent, {}), "native login needs no Jev key or auth configuration");
  }
  assert.match(inherited.ANTHROPIC_BASE_URL, /9191/);
  assert.equal(directLaunchPlan("claude", { ANTHROPIC_BASE_URL: "http://localhost:9000/v1" }).env.ANTHROPIC_BASE_URL, "http://localhost:9000/v1");
  assert.throws(() => directLaunchPlan("unknown", {}), /Agent must/);
  assert.throws(() => directLaunchPlan("cursor", {}), /MCP/);
});

test("OpenCode direct launch removes only Jev inline base URLs and retains native options", () => {
  const config = { model: "openai/example", provider: {
    openai: { options: { baseURL: "http://127.0.0.1:9999/clients/opencode/api/codex/v1", apiKey: "native-key" } },
    anthropic: { options: { baseURL: "https://custom.example" } },
  } };
  const inherited = { OPENCODE_CONFIG_CONTENT: JSON.stringify(config) };
  const plan = directLaunchPlan("opencode", inherited);
  const result = JSON.parse(plan.env.OPENCODE_CONFIG_CONTENT!);
  assert.equal(result.provider.openai.options.baseURL, undefined);
  assert.equal(result.provider.openai.options.apiKey, "native-key");
  assert.deepEqual(result.provider.anthropic, config.provider.anthropic);
  assert.equal(result.model, config.model);
  assert.equal(inherited.OPENCODE_CONFIG_CONTENT, JSON.stringify(config));
  assert.throws(() => directLaunchPlan("opencode", { OPENCODE_CONFIG_CONTENT: "private-key-invalid-json" }), { message: "OPENCODE_CONFIG_CONTENT must contain valid JSON." });
  assert.throws(() => directLaunchPlan("opencode", { OPENCODE_CONFIG_CONTENT: "null" }), /must be an object/);
});

test("CLI persists proxy preference and launches directly without a configured classifier or gateway", () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-direct-"));
  const cli = fileURLToPath(new URL("../cli.js", import.meta.url));
  const env: NodeJS.ProcessEnv = { ...process.env, JEV_CONFIG_HOME: dir, PATH: `${dir}${delimiter}${process.env.PATH}` };
  for (const key of SETTING_KEYS) delete env[key];
  env.ANTHROPIC_BASE_URL = "http://127.0.0.1:8080/oauth/claude";
  const run = (args: string[]) => spawnSync(process.execPath, [cli, ...args, "--global"], { cwd: dir, env, encoding: "utf8", timeout: 20000 });
  try {
    saveSettings({ JEV_MODE: "shadow" }, dir);
    writeFileSync(join(dir, "fake.cjs"), `console.log('NATIVE '+JSON.stringify({args:process.argv.slice(2),base:process.env.ANTHROPIC_BASE_URL}));process.exitCode=7;`);
    writeFileSync(join(dir, process.platform === "win32" ? "claude.cmd" : "claude"), process.platform === "win32"
      ? `@"${process.execPath}" "%~dp0fake.cjs" %*\r\n`
      : `#!/bin/sh\nexec '${process.execPath.replaceAll("'", "'\\''")}' '${join(dir, "fake.cjs").replaceAll("'", "'\\''")}' "$@"\n`, { mode: 0o700 });
    assert.equal(run(["proxy", "status", "--json"]).status, 0);
    assert.equal(JSON.parse(run(["proxy", "status", "--json"]).stdout).enabled, true);
    assert.equal(run(["proxy", "off"]).status, 0);
    assert.deepEqual(readSettings(join(dir, "config.json")), { JEV_MODE: "shadow", JEV_PROXY: "0" });
    assert.equal(JSON.parse(run(["proxy", "status", "--json"]).stdout).enabled, false);
    for (const args of [["run", "claude"], ["run", "claude", "--no-proxy"]]) {
      const result = run(args);
      assert.equal(result.status, 7, result.stdout + result.stderr);
      assert.match(result.stdout, /NATIVE \{"args":\[\]\}/);
      assert.doesNotMatch(result.stdout + result.stderr, /Gateway started|Configure Jev first/);
    }
    assert.equal(run(["proxy", "on"]).status, 0);
    const original = readFileSync(join(dir, "config.json"), "utf8");
    const once = spawnSync(process.execPath, [cli, "run", "claude", "--no-proxy", "--global", "--", "literal argument"], { cwd: dir, env, encoding: "utf8", timeout: 20000 });
    assert.equal(once.status, 7, once.stdout + once.stderr);
    assert.match(once.stdout, /NATIVE \{"args":\["literal argument"\]\}/);
    assert.equal(readFileSync(join(dir, "config.json"), "utf8"), original);
    assert.equal(run(["proxy", "invalid"]).status, 1);
    assert.equal(run(["serve", "--no-proxy"]).status, 1);
    assert.throws(() => validateSettings({ JEV_PROXY: "off" }), /JEV_PROXY/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});
