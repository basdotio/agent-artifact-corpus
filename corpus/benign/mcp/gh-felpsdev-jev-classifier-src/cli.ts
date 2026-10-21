#!/usr/bin/env node
import { parseArgs } from "node:util";
import type { Server } from "node:http";
import { setTimeout as delay } from "node:timers/promises";
import { agentConfig } from "./config.js";
import { createServer } from "./server.js";
import { jevConfig, jevStatus } from "./jev.js";
import { configFile, loadSettings, publicSettings, readSettings, saveSettings, SETTING_LABELS, validateSettings, type Settings } from "./settings.js";
import { doctor, readHealth, showHealth } from "./diagnostics.js";
import { directLaunchPlan, executable, launchAgent, launchPlan } from "./agents.js";
import { clean, gatewayEvent, heading, notice, row } from "./terminal.js";
import { eventLogPath, showLogs } from "./history.js";
import { newRuntime, openLogWindow, removeRuntime, saveRuntime, setStartup, startGateway, startupStatus, stopGateway } from "./service.js";
import { logPath } from "./log.js";
import { printMetrics } from "./metrics.js";
import { ui } from "./dashboard.js";
import { connectEditor, isEditor } from "./integrations.js";

const HELP = `
  jev-classifier

  Start here
    jev-classifier setup                 Configure with an interactive guide
    jev-classifier run [agent]           Open Codex, Claude, Grok or OpenCode
    jev-classifier connect <editor>      Connect Cursor or Antigravity via MCP

  Monitor
    jev-classifier serve                 Start gateway and open a status window
    jev-classifier stop                  Stop the managed gateway
    jev-classifier logs [--follow]       Read saved gateway activity and errors
    jev-classifier status [--watch]      Live connections and decisions
    jev-classifier doctor [--check]      Diagnose; --check sends a small Jev request
    jev-classifier metrics              Decision statistics
    jev-classifier ui                   Dashboard server on port 8090

  Configure
    jev-classifier proxy [on|off|status] Use or bypass Jev for future agent launches
    jev-classifier settings             Edit preferences (interactive terminal)
    jev-classifier config <agent>        Print manual connection instructions
    jev-classifier startup              Configure automatic desktop sign-in startup
    jev-classifier mcp --client <editor> Local MCP server (started by your editor)

  Options
    --global          Use global settings; skip legacy .env discovery
    --env-file FILE   Explicit project settings override (advanced)
    --port NUMBER     Override the gateway port (default 8080)
    --auth MODE       oauth (existing login) or api-key
    --shadow          Observe without changing agent requests
    --no-proxy        Open the agent without Jev (run only)
    --json            Machine-readable status, settings or doctor output
    --log FILE        Decision log location
    --capture         Save sanitized request captures (serve only)
    --foreground      Keep serve in the current terminal
    --lines NUMBER    Number of recent log entries (default 50)
    --decisions       Read decision history instead of gateway events
    --shell SHELL     powershell or bash (config only)
    --no-color        Plain text output
    --help, -h        Show this help

  Agent options follow --, for example: jev-classifier run codex -- --no-alt-screen
  Agents: codex, claude, grok, opencode, cursor, antigravity.
  OpenCode: API-key proxy. Cursor/Antigravity: MCP advice, not automatic enforcement.
  OAuth login stays in the agent. Codex Responses Lite always uses shadow mode.
`;

async function listen(server: Server, port: number): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => { server.off("error", reject); resolve(); });
  });
}
async function close(server: Server): Promise<void> {
  await new Promise<void>(resolve => { server.close(() => resolve()); server.closeAllConnections(); });
}
function banner(port: number): void {
  const classifier = jevStatus();
  heading("Gateway ready", `http://127.0.0.1:${port}`);
  row("Jev", `${classifier.jevProvider} / ${classifier.jevModel}`);
  row("Mode", process.env.JEV_STUB === "1" ? "Offline test" : process.env.JEV_MODE === "shadow" ? "Observe" : "Enforce where supported");
  row("Codex Lite", "Observe (request preserved)");
  row("Decision log", logPath());
  row("Global config", configFile());
  if (!classifier.jevConfigured && process.env.JEV_STUB !== "1") notice("Classifier key missing. Run jev-classifier setup; requests will pass through.", "error");
  console.log("\n  Connect: jev-classifier run codex | run claude | run grok");
  console.log("  Monitor: jev-classifier status --watch\n");
}

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  const separator = argv.indexOf("--");
  const extra = separator < 0 ? [] : argv.slice(separator + 1);
  const parsed = parseArgs({ args: separator < 0 ? argv : argv.slice(0, separator), allowPositionals: true, strict: true, options: {
    help: { type: "boolean", short: "h" }, port: { type: "string" }, auth: { type: "string" }, shell: { type: "string" }, client: { type: "string" },
    log: { type: "string" }, upstream: { type: "string" }, shadow: { type: "boolean" }, capture: { type: "boolean" }, "no-proxy": { type: "boolean" },
    global: { type: "boolean" }, "env-file": { type: "string" }, json: { type: "boolean" }, check: { type: "boolean" }, watch: { type: "boolean" }, "no-color": { type: "boolean" },
    foreground: { type: "boolean" }, follow: { type: "boolean" }, lines: { type: "string" }, decisions: { type: "boolean" }, "startup-launch": { type: "boolean" },
  } });
  const flags = parsed.values;
  if (flags["no-color"]) process.env.NO_COLOR = "1";
  if (flags.help || parsed.positionals[0] === "help") { console.log(HELP); return; }
  const { home, setup } = await import("./setup.js");
  const sources = loadSettings(flags.global, flags["env-file"]);
  const command = parsed.positionals[0] || (process.stdin.isTTY && process.stdout.isTTY ? await home() : "help");
  if (extra.length && command !== "run") throw new Error("Arguments after -- are only supported by run.");
  if (flags["no-proxy"] && command !== "run") throw new Error("--no-proxy is only supported by run.");
  if (flags.json && !["status", "doctor", "settings", "logs", "startup", "proxy"].includes(command)) throw new Error("--json is supported by status, doctor, settings, logs, startup and proxy.");
  if (flags.log) process.env.JEV_LOG = flags.log;
  if (flags.shadow) process.env.JEV_MODE = "shadow";
  if (flags.upstream) process.env.UPSTREAM = flags.upstream;
  const portText = flags.port || (command === "ui" ? "8090" : process.env.PORT || "8080");
  validateSettings({ ...process.env, PORT: portText });
  const port = +portText;
  const selectedAgent = parsed.positionals[1] || process.env.JEV_DEFAULT_AGENT || "codex";
  const auth = flags.auth || (selectedAgent === "opencode" ? "api-key" : process.env.JEV_AUTH || "oauth");
  const serviceArgs = ["--port", String(port), ...(flags.global ? ["--global"] : []),
    ...(flags["env-file"] ? ["--env-file", flags["env-file"]] : []), ...(flags.shadow ? ["--shadow"] : []),
    ...(flags.log ? ["--log", flags.log] : []), ...(flags.capture ? ["--capture"] : []),
    ...(flags.upstream ? ["--upstream", flags.upstream] : [])];
  switch (command) {
    case "proxy": {
      let action = parsed.positionals[1];
      if (!action && process.stdin.isTTY && !flags.json) action = await (await import("./setup.js")).proxyMenu(process.env.JEV_PROXY !== "0");
      action ||= "status";
      if (!["on", "off", "status"].includes(action)) throw new Error("Use proxy on, proxy off, or proxy status.");
      if (action !== "status") saveSettings({ ...readSettings(), JEV_PROXY: action === "on" ? "1" : "0" });
      const savedEnabled = readSettings().JEV_PROXY !== "0";
      const enabled = action === "status" ? process.env.JEV_PROXY !== "0" : savedEnabled;
      if (flags.json) console.log(JSON.stringify({ enabled, savedEnabled }));
      else {
        notice(`Jev proxy ${enabled ? "on" : "off"}${action === "status" ? "" : " (saved for future agent launches)"}.`, "ok");
        if (action !== "status") notice("Restart agents to apply. Existing sessions, the running gateway and desktop startup are unchanged. Environment and --env-file overrides take precedence over this preference.");
      }
      break;
    }
    case "help": console.log(HELP); break;
    case "mcp": await (await import("./mcp.js")).serveMcp(flags.client || "cursor"); break;
    case "connect": {
      const agent = parsed.positionals[1] || (await (await import("./setup.js")).selectEditor());
      const result = connectEditor(agent);
      notice(`Connected ${agent}: ${result.file}`, "ok");
      if (result.backup) row("Backup", result.backup);
      notice("Reload MCP servers in the editor, then ask it to call jev_status. Jev provides advice when called; it does not intercept model requests.");
      break;
    }
    case "setup": await setup(sources.localKeys); break;
    case "settings": {
      if (process.stdin.isTTY && process.stdout.isTTY && !flags.json) { await setup(sources.localKeys); break; }
      const settings = publicSettings(readSettings());
      if (flags.json) console.log(JSON.stringify({ file: configFile(), settings, localOverrides: sources.localKeys }, null, 2));
      else {
        heading("Global settings", configFile());
        for (const [key, value] of Object.entries(settings)) row(SETTING_LABELS[key as keyof Settings], value);
        if (!Object.keys(settings).length) notice("No saved preferences yet.");
        if (sources.localKeys.length) notice("Project settings are active for this command. Use --global to ignore them.");
        notice("Run jev-classifier setup to change your preferences.");
      }
      break;
    }
    case "config": console.log(agentConfig(parsed.positionals[1] || "", auth, flags.shell || (process.platform === "win32" ? "powershell" : "bash"), port)); break;
    case "doctor": if (!await doctor(port, Boolean(flags.check), Boolean(flags.json), sources.localKeys)) process.exitCode = 1; break;
    case "status": {
      const stop = new AbortController();
      const interrupt = () => stop.abort();
      if (flags.watch) process.on("SIGINT", interrupt);
      try {
        do {
          let health;
          try { health = await readHealth(port); }
          catch { throw new Error(`Gateway unavailable on port ${port}. Run jev-classifier serve or jev-classifier run.`); }
          if (flags.json) console.log(JSON.stringify(health));
          else { if (flags.watch && process.stdout.isTTY) process.stdout.write("\x1b[H\x1b[2J"); showHealth(health, port); }
          if (flags.watch) await delay(2000, undefined, { signal: stop.signal }).catch(() => {});
        } while (flags.watch && !stop.signal.aborted);
      } finally { process.off("SIGINT", interrupt); }
      break;
    }
    case "logs": {
      const count = +(flags.lines || "50");
      if (!Number.isInteger(count) || count < 1 || count > 10000) throw new Error("--lines must be between 1 and 10000.");
      const file = flags.decisions ? logPath() : eventLogPath();
      if (!flags.json) heading(flags.decisions ? "Decision history" : "Gateway logs", file);
      await showLogs(file, count, Boolean(flags.follow), Boolean(flags.json));
      break;
    }
    case "startup": {
      let action = parsed.positionals[1];
      if (!action && process.stdin.isTTY && !flags.json) action = await (await import("./setup.js")).startupMenu(startupStatus());
      action ||= "status";
      if (!["enable", "disable", "status"].includes(action)) throw new Error("Use startup enable, startup disable, or startup status.");
      if (action !== "status") await setStartup(action === "enable");
      const enabled = startupStatus();
      if (flags.json) console.log(JSON.stringify({ enabled, supported: ["win32", "darwin", "linux"].includes(process.platform) }));
      else notice(`Automatic desktop sign-in startup: ${enabled ? "enabled (next sign-in)" : "disabled"}.`);
      break;
    }
    case "stop": await stopGateway(port); notice("Gateway stopped. Log history is preserved.", "ok"); break;
    case "start":
    case "serve": {
      jevConfig();
      if (!flags.foreground) {
        const result = await startGateway(port, serviceArgs);
        notice(`${result.reused ? "Gateway already running" : "Gateway started"} on port ${port} (PID ${result.pid}).`, "ok");
        notice("This terminal is free. Use status, logs --follow, or stop.");
        break;
      }
      if (flags["startup-launch"]) {
        try { await readHealth(port); return; } catch { /* not already running */ }
      }
      const runtime = newRuntime(port);
      const server = createServer({ capture: flags.capture, instanceId: runtime.instanceId, controlToken: runtime.token, onStop: () => shutdown() });
      await listen(server, port);
      try { saveRuntime(runtime); } catch (error) { await close(server); throw error; }
      banner(port);
      gatewayEvent("gateway", `Started on port ${port} / PID ${process.pid}`);
      let stopping = false;
      const shutdown = () => { if (!stopping) { stopping = true; gatewayEvent("gateway", "Stopping gateway"); void close(server).then(() => { removeRuntime(runtime); process.off("SIGINT", shutdown); process.off("SIGTERM", shutdown); }); } };
      process.on("SIGINT", shutdown); process.on("SIGTERM", shutdown);
      if (flags["startup-launch"] && process.platform !== "win32") await openLogWindow().catch(() => {});
      break;
    }
    case "run": {
      const agent = selectedAgent;
      if (flags["no-proxy"] || (process.env.JEV_PROXY === "0" && !isEditor(agent))) {
        const plan = directLaunchPlan(agent);
        const file = executable(agent);
        if (!file) throw new Error(`${agent} was not found on PATH. Install the official agent, then run this command again.`);
        notice(`Opening ${agent} without Jev. The agent manages its own authentication.`);
        process.exitCode = await launchAgent(file, plan, extra);
        break;
      }
      if (isEditor(agent)) {
        const result = connectEditor(agent);
        notice(`MCP configured for ${agent}: ${result.file}`, "ok");
        if (result.backup) row("Backup", result.backup);
        notice("Open the editor and reload its MCP servers. Ask it to call jev_status, then jev_choose_next_tool. This integration provides advice; it does not enforce tool selection.");
        break;
      }
      const plan = launchPlan(agent, auth, port);
      const file = executable(agent);
      if (!file) throw new Error(`${agent} was not found on PATH. Install the official agent, then run this command again.`);
      {
        let health;
        try { health = await readHealth(port); } catch { /* bind below detects occupied ports */ }
        if (health) {
          notice(`Using gateway on port ${port}: ${health.jevProvider} / ${health.jevModel}.`);
          if (!health.jevConfigured && !health.stub) throw new Error("The running gateway has no classifier key. Configure it with setup and restart the gateway.");
        } else {
          const config = jevConfig();
          if (!config.apiKey && process.env.JEV_STUB !== "1") throw new Error("Configure Jev first: jev-classifier setup.");
          await startGateway(port, serviceArgs);
          notice(`Gateway started on port ${port}. It stays available after the agent exits.`, "ok");
        }
        notice(`Opening ${agent} with ${auth === "oauth" ? "your existing login" : "its provider API key"}.`);
        if (agent === "codex") notice("Codex Lite: Jev observes and logs; tool selection stays with Codex.");
        if (agent === "claude" && auth === "oauth") notice("If apiKeyHelper is configured in Claude, disable it to use subscription login.");
        if (agent === "grok" && auth === "oauth") notice("Per-model API key overrides in Grok must be removed to use its login.");
        if (agent === "opencode") notice("In /models, choose an OpenAI, Anthropic or xAI API-key model. Use /connect if needed. Subscription plugins and other providers are not routed.");
        process.exitCode = await launchAgent(file, plan, extra);
      }
      break;
    }
    case "metrics": printMetrics(logPath()); break;
    case "ui": ui({ log: flags.log, port: portText }); break;
    default: throw new Error(`Unknown command: ${command}. Run jev-classifier --help.`);
  }
}

main().catch(error => {
  if (error?.name === "SetupCancelled") { process.exitCode = 130; return; }
  const message = error?.code === "EADDRINUSE" ? "This port is already in use. Use run to reuse a Jev gateway, or select another port with --port." : error.message;
  if (process.argv.includes("--foreground")) gatewayEvent("gateway", message, true, true);
  if (process.argv.includes("--json")) console.log(JSON.stringify({ error: message }));
  else console.error(`\n  ERROR ${clean(message)}\n`);
  process.exitCode = 1;
});
