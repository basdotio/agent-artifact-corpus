import { AGENTS, isEditor, mcpConfig, openCodeConfig } from "./integrations.js";
export type Agent = typeof AGENTS[number];
export type Auth = "oauth" | "api-key";
export type Shell = "powershell" | "bash";

/** Print setup only; login and refresh remain owned by the agent. */
export function agentConfig(agent: string, auth: string, shell: string, port: number): string {
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Port must be between 1 and 65535");
  if (!AGENTS.includes(agent as Agent)) throw new Error(`Agent must be ${AGENTS.join(", ")}`);
  if (!["oauth", "api-key"].includes(auth)) throw new Error("Auth must be oauth or api-key");
  if (!["powershell", "bash"].includes(shell)) throw new Error("Shell must be powershell or bash");
  if (isEditor(agent)) return `MCP advisory integration: consult Jev without changing your editor's login or model.\nRun jev-classifier connect ${agent} to merge this entry into the global MCP configuration, then reload MCP servers.\n\n${JSON.stringify(mcpConfig(agent), null, 2)}\n\nAsk the agent to call jev_status, then jev_choose_next_tool with your task and available tools.\nDecisions appear in: jev-classifier logs --decisions\nThis does not intercept model requests or enforce tool_choice.\n`;
  if (agent === "opencode") return `OpenCode v1 proxy integration for OpenAI, Anthropic and xAI API-key providers.\nRun jev-classifier run opencode --auth api-key, then select one of these providers in /models.\nUse /connect in OpenCode to save its API key if needed. Subscription plugins and other providers are not routed.\nAlternatively, merge this into opencode.json and start the gateway:\n\n${JSON.stringify(openCodeConfig(port), null, 2)}\n`;
  const oauth = auth === "oauth";
  const url = `http://127.0.0.1:${port}/${oauth ? "oauth" : "api"}/${agent}`;
  const set = (key: string, value: string) => shell === "powershell" ? `$env:${key} = "${value}"` : `export ${key}="${value}"`;
  const unset = (key: string) => shell === "powershell" ? `Remove-Item Env:${key} -ErrorAction SilentlyContinue` : `unset ${key}`;
  if (agent === "codex") {
    return `# Merge into your USER config: $CODEX_HOME/config.toml (default ~/.codex/config.toml).
# Keep model_provider at the top level, before any [table].
model_provider = "jev"

[model_providers.jev]
name = "jev-classifier"
base_url = "${url}${oauth ? "" : "/v1"}"
wire_api = "responses"
supports_websockets = false
${oauth ? 'requires_openai_auth = true\n# No env_key: uses your existing ChatGPT login.' : 'env_key = "OPENAI_API_KEY"\n# env_key is a variable NAME; set its value in the agent shell.'}

# Agent terminal:
${oauth ? 'codex login   # only if not already signed in with ChatGPT\ncodex login status' : set("OPENAI_API_KEY", "your-api-key")}
codex
`;
  }
  if (agent === "claude") {
    return `# Agent terminal:
${oauth ? ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"].map(unset).join("\n") + '\n# Disable apiKeyHelper if configured; it overrides subscription login.' : set("ANTHROPIC_API_KEY", "your-api-key")}
${set("ANTHROPIC_BASE_URL", url)}
claude
${oauth ? '# Use /login if needed. Claude Code owns login and token refresh.\n' : ''}`;
  }
  return `# Agent terminal (official Grok Build):
${oauth ? ["XAI_API_KEY", "GROK_MODELS_BASE_URL"].map(unset).join("\n") + '\n# Remove per-model api_key/env_key overrides if configured.\ngrok login   # only if not already signed in' : set("XAI_API_KEY", "your-api-key")}
${set(oauth ? "GROK_CLI_CHAT_PROXY_BASE_URL" : "GROK_MODELS_BASE_URL", `${url}/v1`)}
grok
`;
}
