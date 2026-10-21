import * as p from "@clack/prompts";
import { configFile, isSecret, publicSettings, readSettings, saveSettings, SETTING_KEYS, SETTING_LABELS, validateSettings, type Settings } from "./settings.js";
import { jevConfig } from "./jev.js";
import { setStartup, startupStatus } from "./service.js";
import { isEditor } from "./integrations.js";

export class Cancelled extends Error {
  constructor() { super("Setup canceled"); this.name = "SetupCancelled"; }
}
async function answer<T>(prompt: Promise<T>): Promise<Exclude<T, symbol>> {
  const value = await prompt;
  if (p.isCancel(value)) { p.cancel("Canceled. No settings were saved."); throw new Cancelled(); }
  return value as Exclude<T, symbol>;
}

export async function setup(localKeys: string[]): Promise<void> {
  if (!process.stdin.isTTY || !process.stdout.isTTY) throw new Error("Setup needs an interactive terminal. Run jev-classifier setup in your terminal.");
  p.intro("jev-classifier / Setup");
  let draft: Settings = { ...readSettings() };
  if (localKeys.length && await answer(p.confirm({ message: "Import the current .env settings into your global configuration?", initialValue: true }))) {
    for (const key of SETTING_KEYS) if (localKeys.includes(key) && process.env[key]) draft[key] = process.env[key];
  }
  const previousProvider = draft.JEV_PROVIDER;
  draft.JEV_PROVIDER = await answer(p.select({ message: "Where should Jev run?", initialValue: draft.JEV_PROVIDER || "vercel", options: [
    { value: "vercel", label: "Vercel AI Gateway" }, { value: "openrouter", label: "OpenRouter" }, { value: "typesafe", label: "TypeSafe" },
  ] }));
  if (previousProvider && previousProvider !== draft.JEV_PROVIDER) { delete draft.JEV_API_KEY; delete draft.JEV_MODEL; }
  draft.JEV_STUB = await answer(p.select({ message: "Classifier connection", initialValue: draft.JEV_STUB || "0", options: [
    { value: "0", label: "Live Jev", hint: "use a provider API key" }, { value: "1", label: "Offline test", hint: "no inference or API key" },
  ] }));
  const key = jevConfig(draft).keyVariable as keyof Settings;
  if (draft.JEV_STUB !== "1") {
    const existing = Boolean(draft[key] || draft.JEV_API_KEY);
    const action = await answer(p.select({ message: `${SETTING_LABELS[key]}${existing ? " (saved)" : ""}`, options: [
      ...(existing ? [{ value: "keep", label: "Keep the saved key" }] : []),
      { value: "replace", label: "Enter a key", hint: "input is hidden" },
      { value: "environment", label: "Configure the key later", hint: "remove the saved key" },
    ] }));
    if (action === "replace") {
      draft[key] = (await answer(p.password({ message: "API key", validate: v => !v?.trim() ? "Enter a key." : /[\r\n\0]/.test(v) ? "Enter a single-line key." : undefined }))).trim();
      delete draft.JEV_API_KEY;
    } else if (action === "environment") { delete draft[key]; delete draft.JEV_API_KEY; }
  }
  const modelChoice = await answer(p.select({ message: "Which Jev model should be used?", initialValue: draft.JEV_MODEL ? "custom" : "default", options: [
    { value: "default", label: "Recommended model", hint: jevConfig({ JEV_PROVIDER: draft.JEV_PROVIDER }).model },
    { value: "custom", label: "Choose a model ID", hint: "advanced" },
  ] }));
  if (modelChoice === "custom") draft.JEV_MODEL = (await answer(p.text({ message: "Jev model ID", initialValue: draft.JEV_MODEL || "", validate: v => !v?.trim() ? "Enter a model ID." : undefined }))).trim();
  else delete draft.JEV_MODEL;
  draft.JEV_DEFAULT_AGENT = await answer(p.select({ message: "Default coding agent", initialValue: draft.JEV_DEFAULT_AGENT || "codex", options: [
    { value: "codex", label: "Codex", hint: "Responses Lite runs in shadow mode" }, { value: "claude", label: "Claude Code" }, { value: "grok", label: "Grok Build" },
    { value: "opencode", label: "OpenCode", hint: "proxy for OpenAI, Anthropic and xAI API-key models" },
    { value: "cursor", label: "Cursor", hint: "MCP advice; no automatic enforcement" },
    { value: "antigravity", label: "Antigravity", hint: "MCP advice; no automatic enforcement" },
  ] }));
  if (isEditor(draft.JEV_DEFAULT_AGENT)) {
    p.log.info("Your editor keeps its own login. Jev is an MCP tool the agent can consult; it does not intercept requests. After saving, use run to connect the editor.");
  } else if (draft.JEV_DEFAULT_AGENT === "opencode") {
    draft.JEV_AUTH = "api-key";
    p.log.info("Use /connect inside OpenCode to configure an OpenAI, Anthropic or xAI API key. Subscription plugins are not routed by this integration.");
  } else {
    draft.JEV_AUTH = await answer(p.select({ message: "Agent authentication", initialValue: draft.JEV_AUTH || "oauth", options: [
      { value: "oauth", label: "Existing login", hint: "agent owns sign-in and token refresh" }, { value: "api-key", label: "Provider API key", hint: "configure a separate key for the agent" },
    ] }));
    if (draft.JEV_AUTH === "api-key") {
      const agentKey = { codex: "OPENAI_API_KEY", claude: "ANTHROPIC_API_KEY", grok: "XAI_API_KEY" }[draft.JEV_DEFAULT_AGENT!] as keyof Settings;
      const keep = draft[agentKey] && await answer(p.confirm({ message: `Keep the saved ${SETTING_LABELS[agentKey]}?`, initialValue: true }));
      if (!keep) draft[agentKey] = (await answer(p.password({ message: SETTING_LABELS[agentKey], validate: v => !v?.trim() ? "Enter the agent provider's key." : undefined }))).trim();
    }
  }
  draft.JEV_MODE = await answer(p.select({ message: "Routing mode", initialValue: draft.JEV_MODE || "shadow", options: [
    { value: "shadow", label: "Observe", hint: "classify and compare; preserve requests" },
    { value: "enforce", label: "Enforce", hint: "force tool selection where supported" },
  ] }));
  draft.PORT = await answer(p.text({ message: "Local gateway port", initialValue: draft.PORT || "8080", validate: value => {
    try { validateSettings({ PORT: value || "invalid" }); } catch { return "Enter a port between 1 and 65535."; }
  } }));
  if (await answer(p.confirm({ message: "Edit advanced settings?", initialValue: false }))) {
    const advanced = SETTING_KEYS.filter(k => !isSecret(k) && !["JEV_PROVIDER", "JEV_MODEL", "JEV_DEFAULT_AGENT", "JEV_AUTH", "JEV_MODE", "JEV_STUB", "PORT"].includes(k));
    while (true) {
      const option = await answer(p.select({ message: "Advanced settings", options: [
        { value: "done", label: "Done" }, ...advanced.map(k => ({ value: k, label: SETTING_LABELS[k], hint: draft[k] || "default" })),
        { value: "UPSTREAM_API_KEY", label: "Agent API credential override", hint: "only for API-key connections" },
      ] }));
      if (option === "done") break;
      const setting = option as keyof Settings;
      const value = setting === "JEV_SYSTEM_CA" ? await answer(p.select({ message: "Trust certificates installed on this computer?", initialValue: draft[setting] || "1", options: [{ value: "1", label: "Yes", hint: "recommended for managed computers" }, { value: "0", label: "No", hint: "use Node's default certificates" }] })) : isSecret(setting) ? await answer(p.password({ message: `${SETTING_LABELS[setting]} (blank removes it)` })) : await answer(p.text({
        message: `${SETTING_LABELS[setting]} (blank restores default)`, initialValue: draft[setting] || "", validate: v => {
          try { validateSettings({ [setting]: v }); } catch (e) { return (e as Error).message; }
        },
      }));
      if (value.trim()) draft[setting] = value.trim(); else delete draft[setting];
    }
  }
  draft = validateSettings(draft);
  const automaticStartup = ["win32", "darwin", "linux"].includes(process.platform) ? await answer(p.confirm({
    message: "Start the gateway automatically when you sign in to your desktop?", initialValue: startupStatus(),
  })) : undefined;
  const display = (key: string, value: string) => key === "JEV_MODE" ? (value === "shadow" ? "Observe" : "Enforce where supported")
    : key === "JEV_AUTH" ? (value === "oauth" ? "Existing login" : "Provider API key")
    : ["JEV_STUB", "JEV_SYSTEM_CA"].includes(key) ? (value === "1" ? "Yes" : "No") : value;
  p.note(Object.entries(publicSettings(draft)).map(([k, v]) => `${SETTING_LABELS[k as keyof Settings]}: ${display(k, v!)}`).join("\n"), "Review / secrets hidden");
  p.log.info(`Global file: ${configFile()}\nKeys are stored locally in this file, not in agent configuration.`);
  if (await answer(p.confirm({ message: "Save this configuration?", initialValue: true }))) {
    saveSettings(draft);
    if (automaticStartup !== undefined) await setStartup(automaticStartup);
    if (localKeys.length) p.log.info("Imported settings are now global. The original file was preserved; omit --env-file to use your saved preferences.");
    p.outro("Saved. Next: jev-classifier doctor --check, then jev-classifier run");
  } else p.outro("No changes saved.");
}

export async function home(): Promise<string> {
  p.intro("jev-classifier");
  const command = await answer(p.select({ message: "What would you like to do?", options: [
    { value: "run", label: "Open an agent", hint: process.env.JEV_PROXY === "0" ? "without Jev" : "connect through the gateway" },
    { value: "proxy", label: "Turn Jev proxy on or off", hint: "choose how future agent sessions connect" },
    { value: "connect", label: "Connect an editor", hint: "Cursor or Antigravity via MCP advice" },
    { value: "setup", label: "Configure", hint: "provider, keys, agent and routing" },
    { value: "serve", label: "Start the gateway", hint: "separate window; this terminal stays free" },
    { value: "status", label: "View status", hint: "connections and classification results" },
    { value: "logs", label: "View log history", hint: "recent activity and errors" },
    { value: "stop", label: "Stop the gateway", hint: "keep saved settings and logs" },
    ...(["win32", "darwin", "linux"].includes(process.platform) ? [{ value: "startup", label: "Automatic startup", hint: "start at desktop sign-in" }] : []),
    { value: "doctor", label: "Diagnose", hint: "installation and configuration" },
    { value: "help", label: "All commands" },
  ] }));
  p.outro(command === "help" ? "Commands" : "Ready");
  return command;
}

export async function startupMenu(enabled: boolean): Promise<string> {
  p.intro("jev-classifier / Automatic startup");
  const action = await answer(p.select({ message: `Start automatically when you sign in? Currently ${enabled ? "enabled" : "disabled"}.`, options: [
    { value: "enable", label: "Enable", hint: "open the gateway window at sign-in" },
    { value: "disable", label: "Disable", hint: "start the gateway manually" },
    { value: "status", label: "Keep current setting" },
  ] }));
  p.outro("Startup preference");
  return action;
}

export async function proxyMenu(enabled: boolean): Promise<string> {
  return answer(p.select({ message: `Jev proxy is ${enabled ? "on" : "off"}. Apply to future agent launches:`, options: [
    { value: "off", label: "Off", hint: "run agents without Jev or its gateway" },
    { value: "on", label: "On", hint: "route agent requests through Jev" },
    { value: "status", label: "Keep current setting" },
  ] }));
}

export async function selectEditor(): Promise<string> {
  if (!process.stdin.isTTY || !process.stdout.isTTY) throw new Error("Use connect cursor or connect antigravity.");
  return answer(p.select({ message: "Connect an editor using MCP routing advice", options: [
    { value: "cursor", label: "Cursor" }, { value: "antigravity", label: "Antigravity" },
  ] }));
}
