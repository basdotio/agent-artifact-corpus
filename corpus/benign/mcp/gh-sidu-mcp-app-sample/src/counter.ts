/**
 * Counter View. Capabilities exercised:
 *   readServerResource — polls the live-counter resource
 *   preferredDisplayMode: pip (server declared)
 *
 * The server-side subscription (notifications/resources/updated) is exercised
 * by MCP Inspector, not by this View — the App SDK does not expose subscribe.
 */
import { App } from "@modelcontextprotocol/ext-apps";

const valueEl = document.getElementById("value")!;
const infoEl = document.getElementById("info")!;

const LIVE_COUNTER_URI = "resource:///live/counter";

const app = new App({ name: "Counter View", version: "0.1.0" });

async function tick() {
  try {
    const result = await app.readServerResource({ uri: LIVE_COUNTER_URI });
    const first = result.contents?.[0];
    if (first && "text" in first && typeof first.text === "string") {
      const data = JSON.parse(first.text) as { counter: number };
      valueEl.textContent = String(data.counter);
      infoEl.textContent = `updated ${new Date().toLocaleTimeString()}`;
    }
  } catch (e) {
    infoEl.textContent = `error: ${e}`;
  }
}

let intervalId: number | null = null;
app.onteardown = async () => {
  if (intervalId !== null) clearInterval(intervalId);
  return {};
};

app.connect().then(() => {
  tick();
  intervalId = window.setInterval(tick, 1000);
});
