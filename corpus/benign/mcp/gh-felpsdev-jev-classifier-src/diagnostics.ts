import { executable } from "./agents.js";
import { evaluateJev, jevConfig } from "./jev.js";
import { configFile } from "./settings.js";
import { heading, notice, row } from "./terminal.js";
import { AGENTS, integrationPath, isEditor } from "./integrations.js";
import { existsSync } from "node:fs";

export async function readHealth(port: number): Promise<any> {
  const response = await fetch(`http://127.0.0.1:${port}/__jev/health`, { signal: AbortSignal.timeout(1500), redirect: "error" });
  if (!response.ok) throw new Error("The service on this port did not return a valid health response.");
  const health = await response.json() as any;
  if (health?.service !== "jev-classifier") throw new Error("This port belongs to another service.");
  return health;
}

export function showHealth(health: any, port: number): void {
  heading("Gateway status", `http://127.0.0.1:${port}`);
  row("Classifier", `${health.jevProvider} / ${health.jevModel || "default"}${health.stub ? " (offline stub)" : ""}`);
  row("Credentials", health.jevConfigured ? "configured (not proof of authentication)" : "missing");
  row("Requests", health.requests);
  row("Classified", health.classified);
  row("Failures", health.classificationFailures);
  if (!health.requests) notice("Waiting for an agent. Start one with jev-classifier run <codex|claude|grok>.");
  for (const [name, value] of Object.entries(health.agents || {})) {
    const agent = value as any;
    console.log("");
    row(name, `${agent.requests} requests / ${agent.classified} classified / ${agent.failures} failures`);
    if (agent.lastDecision) row("Last decision", `${agent.lastDecision.tool} / ${agent.lastDecision.mode} / ${agent.lastDecision.applied ? "applied" : "observed"}`);
    if (agent.lastError) notice(agent.lastError, "error");
  }
  console.log("");
}

export async function doctor(port: number, check: boolean, json: boolean, localKeys: string[]): Promise<boolean> {
  const config = jevConfig();
  const report: any = {
    configFile: configFile(), localOverrides: localKeys, node: process.version,
    classifier: { provider: config.provider, model: config.model, configured: Boolean(config.apiKey), stub: process.env.JEV_STUB === "1" },
    agents: Object.fromEntries(AGENTS.map(agent => [agent, Boolean(executable(agent) || (agent === "antigravity" && executable("agy")))])),
    integrations: Object.fromEntries(AGENTS.filter(isEditor).map(agent => [agent, { mode: "mcp-advisory", configExists: existsSync(integrationPath(agent)) }])),
  };
  try { report.gateway = await readHealth(port); } catch { report.gateway = null; }
  let ok = Boolean(config.apiKey) || report.classifier.stub;
  if (!json) {
    heading("Doctor", "Installation, configuration and connectivity");
    row("Global config", report.configFile);
    row("Local .env", localKeys.length ? `${localKeys.length} overrides (use --global to ignore)` : "none");
    row("Classifier", `${config.provider} / ${config.model}`);
    notice(ok ? "Classifier configured." : "Classifier key missing. Run jev-classifier setup.", ok ? "ok" : "error");
    for (const [agent, installed] of Object.entries(report.agents)) row(agent, installed ? "available on PATH" : "not found on PATH");
    notice("Cursor and Antigravity use local MCP advice; their desktop apps do not need to be on PATH. Use connect <editor>. MCP activity appears in logs --decisions, independently of gateway counters.");
    row("Gateway", report.gateway ? `running on port ${port}` : `not running on port ${port}; run will start it`);
    if (report.gateway && (report.gateway.jevProvider !== config.provider || report.gateway.jevModel !== config.model)) {
      notice("The running gateway uses different settings. Restart it to apply this configuration.");
    }
  }
  if (check && !report.classifier.stub) {
    if (!json) notice("Testing the local classifier configuration with one small synthetic request...");
    try {
      const started = performance.now();
      const result = await evaluateJev({ state: "The user asked to read a file. No tools have run.",
        instructions: "Choose the next action.", doneInstructions: "Has the file already been read?", criteria: { read_file: "Read the requested file", respond: "Reply when finished" } });
      report.probe = { ok: true, latencyMs: Math.round(performance.now() - started), choice: result.choice };
      ok = true;
      if (!json) notice(`Jev responded in ${report.probe.latencyMs} ms. Choice: ${result.choice}.`, "ok");
    } catch (error) { ok = false; report.probe = { ok: false, error: (error as Error).message }; if (!json) notice(report.probe.error, "error"); }
  } else if (!json) notice(report.classifier.stub ? "Offline stub enabled; no model connection was tested." : "Use doctor --check to verify the key and model with a live request.");
  if (json) console.log(JSON.stringify(report, null, 2));
  return ok;
}
