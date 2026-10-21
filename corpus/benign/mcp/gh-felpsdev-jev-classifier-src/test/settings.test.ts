import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { saveSettings, readSettings, publicSettings, validateSettings } from "../settings.js";
import { launchPlan, spawnCommand } from "../agents.js";

test("global settings round trip, redact keys, and reject unsafe values without overwriting", () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-settings-"));
  try {
    const original = { JEV_PROVIDER: "vercel", AI_GATEWAY_API_KEY: "secret", PORT: "8181", JEV_DEFAULT_AGENT: "grok" };
    saveSettings(original, dir);
    assert.deepEqual(readSettings(join(dir, "config.json")), original);
    assert.equal(publicSettings(original).AI_GATEWAY_API_KEY, "[saved]");
    for (const values of [{ PORT: "NaN" }, { PORT: "0" }, { JEV_MODE: "typo" }, { MIN_CONFIDENCE: "2" }, { JEV_API_KEY: "bad\nkey" }, { UPSTREAM: "file:///secret" }]) {
      assert.throws(() => saveSettings(values, dir));
      assert.deepEqual(readSettings(join(dir, "config.json")), original);
    }
    assert.deepEqual(validateSettings({ UNRELATED_KEY: "ignored" }), {});
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test("environment beats explicit project overrides; saved preferences ignore an old .env", () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-precedence-"));
  const module = new URL("../settings.js", import.meta.url).href;
  const script = `import {loadSettings} from ${JSON.stringify(module)};loadSettings(false,process.argv[1]==='local'?'.env':undefined);console.log(JSON.stringify({port:process.env.PORT,model:process.env.JEV_MODEL,provider:process.env.JEV_PROVIDER}));`;
  try {
    saveSettings({ PORT: "8111", JEV_MODEL: "global-model", JEV_PROVIDER: "vercel" }, dir);
    writeFileSync(join(dir, ".env"), "PORT=8222\nJEV_MODEL=local-model\n");
    const env: NodeJS.ProcessEnv = { ...process.env, JEV_CONFIG_HOME: dir, PORT: "8333" };
    delete env.JEV_MODEL; delete env.JEV_PROVIDER;
    for (const globalOnly of [false, true]) {
      const result = spawnSync(process.execPath, ["--input-type=module", "-e", script, globalOnly ? "global" : "local"], { cwd: dir, env, encoding: "utf8" });
      assert.equal(result.status, 0, result.stderr);
      assert.deepEqual(JSON.parse(result.stdout), { port: "8333", model: globalOnly ? "global-model" : "local-model", provider: "vercel" });
    }
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test("launch settings isolate classifier keys and preserve existing agent credentials", () => {
  const env = { AI_GATEWAY_API_KEY: "secret", JEV_API_KEY: "secret2", OPENAI_API_KEY: "openai", ANTHROPIC_API_KEY: "anthropic", XAI_API_KEY: "xai", CODEX_HOME: "home", GROK_MODELS_BASE_URL: "wrong" };
  for (const agent of ["codex", "claude", "grok"]) {
    const plan = launchPlan(agent, "oauth", 8123, env);
    assert.equal(plan.env.AI_GATEWAY_API_KEY, undefined);
    assert.equal(plan.env.JEV_API_KEY, undefined);
    assert.equal(plan.env.CODEX_HOME, "home");
    assert.match(plan.url, new RegExp(`/oauth/${agent}$`));
    if (agent === "codex") { assert.match(plan.args.join(" "), /requires_openai_auth=true/); assert.doesNotMatch(plan.args.join(" "), /env_key/); }
    if (agent === "claude") assert.equal(plan.env.ANTHROPIC_API_KEY, undefined);
    if (agent === "grok") { assert.equal(plan.env.XAI_API_KEY, undefined); assert.equal(plan.env.GROK_MODELS_BASE_URL, undefined); }
    assert.throws(() => launchPlan(agent, "api-key", 8080, {}), /Set /);
    assert.equal(launchPlan(agent, "api-key", 8080, env).env.OPENAI_API_KEY, "openai");
  }
  assert.equal(env.AI_GATEWAY_API_KEY, "secret", "the parent environment remains unchanged");
});

test("CLI rejects bad flags and noninteractive setup without saving or disclosing secrets", () => {
  const dir = mkdtempSync(join(tmpdir(), "jev-cli-"));
  const cli = fileURLToPath(new URL("../cli.js", import.meta.url));
  try {
    saveSettings({ JEV_PROVIDER: "vercel", AI_GATEWAY_API_KEY: "never-print-this" }, dir);
    const env = { ...process.env, JEV_CONFIG_HOME: dir };
    for (const args of [["setup"], ["serve", "--port", "bad"], ["serve", "--shdaow"]]) {
      const result = spawnSync(process.execPath, [cli, ...args, "--global"], { cwd: dir, env, encoding: "utf8" });
      assert.equal(result.status, 1);
      assert.doesNotMatch(result.stdout + result.stderr, /never-print-this/);
    }
    const result = spawnSync(process.execPath, [cli, "settings", "--json", "--global"], { cwd: dir, env, encoding: "utf8" });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(JSON.parse(result.stdout).settings.AI_GATEWAY_API_KEY, "[saved]");
    assert.match(readFileSync(join(dir, "config.json"), "utf8"), /never-print-this/);
  } finally { rmSync(dir, { recursive: true, force: true }); }
});

test("Windows shim arguments are literal PowerShell strings", () => {
  if (process.platform !== "win32") return;
  const command = spawnCommand("C:\\Program Files\\codex.cmd", ["hello'; Write-Output injected; 'world", "$(echo secret)"]);
  assert.equal(command.file, "powershell.exe");
  const script = Buffer.from(command.args.at(-1)!, "base64").toString("utf16le");
  assert.match(script, /'hello''; Write-Output injected; ''world'/);
  assert.match(script, /'\$\(echo secret\)'/);
});
