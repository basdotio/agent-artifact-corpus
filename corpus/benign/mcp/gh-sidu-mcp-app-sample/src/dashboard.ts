/**
 * Dashboard View — exercises the App-side API surface.
 * Capabilities exercised (see server.ts for full labels):
 *   [CAP-APP]              — hosted iframe UI linked to a tool
 *   [CAP-APP-STRUCT]       — structuredContent from initial tool_result
 *   [CAP-APP-VIEWUUID]     — localStorage state keyed by CallToolResult._meta.viewUUID
 *   host-context adaptation (theme, styles, safe-area, display mode)
 *   callServerTool         — refreshing metrics via app-only poll-metrics tool
 *   sendMessage            — post text to the chat
 *   updateModelContext     — inject state the model can read
 *   openLink               — request the host to open an external URL
 *   requestDisplayMode     — toggle fullscreen
 *   onhostcontextchanged   — react to theme + display-mode changes
 *   onteardown             — clean up on unload
 */

import { App } from "@modelcontextprotocol/ext-apps";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";

interface Metric {
  label: string;
  value: number;
}

const titleEl = document.getElementById("title")!;
const infoEl = document.getElementById("info")!;
const metricsEl = document.getElementById("metrics")!;
const chartEl = document.getElementById("chart")!;
const logEl = document.getElementById("log")!;

let viewUUID: string | undefined;

function log(msg: string) {
  const entry = document.createElement("div");
  entry.className = "entry";
  entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
  logEl.prepend(entry);
  // keep only 20
  while (logEl.children.length > 20) logEl.removeChild(logEl.lastChild!);
}

function renderMetrics(title: string, metrics: Metric[]) {
  titleEl.textContent = title;
  metricsEl.innerHTML = "";
  chartEl.innerHTML = "";
  const max = Math.max(1, ...metrics.map((m) => m.value));
  for (const m of metrics) {
    const cell = document.createElement("div");
    cell.className = "metric";
    cell.innerHTML = `<div class="label">${m.label}</div><div class="value">${m.value}</div>`;
    metricsEl.appendChild(cell);

    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.height = `${(m.value / max) * 100}%`;
    bar.title = `${m.label}: ${m.value}`;
    chartEl.appendChild(bar);
  }
  saveState({ title, metrics });
}

function saveState(state: { title: string; metrics: Metric[] }) {
  if (!viewUUID) return;
  try {
    localStorage.setItem(viewUUID, JSON.stringify(state));
  } catch {}
}

function loadState(): { title: string; metrics: Metric[] } | null {
  if (!viewUUID) return null;
  try {
    const raw = localStorage.getItem(viewUUID);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

const app = new App({ name: "Dashboard View", version: "0.1.0" });

app.ontoolresult = (result: CallToolResult) => {
  const uuid = result._meta?.viewUUID;
  if (typeof uuid === "string") viewUUID = uuid;

  const sc = result.structuredContent as
    | { title?: string; metrics?: Metric[] }
    | undefined;
  const restored = loadState();
  if (sc?.metrics) {
    renderMetrics(sc.title ?? "Dashboard", sc.metrics);
    log(`Received initial tool result (viewUUID=${viewUUID ?? "-"})`);
  } else if (restored) {
    renderMetrics(restored.title, restored.metrics);
    log(`Restored state from localStorage`);
  }
};

app.ontoolinput = (params) => {
  log(`ontoolinput: ${JSON.stringify(params.arguments)}`);
};

app.ontoolinputpartial = (params) => {
  log(`ontoolinputpartial: ${JSON.stringify(params.arguments)}`);
};

app.onteardown = async () => {
  log("teardown");
  return {};
};

app.onhostcontextchanged = (ctx) => {
  const parts: string[] = [];
  if (ctx.theme) parts.push(`theme=${ctx.theme}`);
  if (ctx.displayMode) parts.push(`mode=${ctx.displayMode}`);
  if (ctx.locale) parts.push(`locale=${ctx.locale}`);
  if (parts.length) log(`host: ${parts.join(", ")}`);
  if (ctx.theme) {
    document.documentElement.dataset.theme = ctx.theme;
  }
};

document.getElementById("refresh")!.addEventListener("click", async () => {
  try {
    const result = await app.callServerTool({
      name: "poll-metrics",
      arguments: {},
    });
    const sc = result.structuredContent as
      | { metrics?: Metric[]; sampledAt?: string }
      | undefined;
    if (sc?.metrics) {
      renderMetrics(titleEl.textContent ?? "Dashboard", sc.metrics);
      infoEl.textContent = `Refreshed at ${sc.sampledAt}`;
    }
    log("Refreshed via poll-metrics");
  } catch (e) {
    log(`refresh failed: ${e}`);
  }
});

document.getElementById("fullscreen")!.addEventListener("click", async () => {
  const ctx = app.getHostContext();
  const target = ctx?.displayMode === "fullscreen" ? "inline" : "fullscreen";
  if (!ctx?.availableDisplayModes?.includes(target)) {
    log(`Host does not offer ${target} mode`);
    return;
  }
  const result = await app.requestDisplayMode({ mode: target });
  log(`display mode: ${result.mode}`);
});

document.getElementById("send-message")!.addEventListener("click", async () => {
  const { isError } = await app.sendMessage({
    role: "user",
    content: [{ type: "text", text: "Refresh the dashboard, please." }],
  });
  log(`sendMessage: ${isError ? "rejected" : "accepted"}`);
});

document
  .getElementById("update-context")!
  .addEventListener("click", async () => {
    await app.updateModelContext({
      content: [
        {
          type: "text",
          text: "User is looking at the sample dashboard. Metrics were last refreshed a moment ago.",
        },
      ],
    });
    log("updateModelContext sent");
  });

document.getElementById("open-link")!.addEventListener("click", async () => {
  const { isError } = await app.openLink({
    url: "https://modelcontextprotocol.io/",
  });
  log(`openLink: ${isError ? "rejected" : "accepted"}`);
});

document.getElementById("call-echo")!.addEventListener("click", async () => {
  const result = await app.callServerTool({
    name: "echo",
    arguments: { text: "hello from the view" },
  });
  const first = result.content?.[0];
  const text = first && first.type === "text" ? first.text : "[no text]";
  log(`echo -> ${text}`);
});

app.connect().then(() => {
  const ctx = app.getHostContext();
  if (ctx?.theme) document.documentElement.dataset.theme = ctx.theme;
  infoEl.textContent = `Connected. displayMode=${ctx?.displayMode ?? "-"}, theme=${ctx?.theme ?? "-"}.`;
  log("connected");
});
